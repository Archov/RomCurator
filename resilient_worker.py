#!/usr/bin/env python3
"""
Resilient Worker Thread for Ingestion Operations

Provides fault-tolerant processing with:
- Checkpoint-based recovery
- Configurable retry policies with exponential backoff
- Granular error handling and classification
- Progress persistence across interruptions
- Cancellation support
"""

import json
import time
import threading
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from PyQt5.QtCore import QThread, pyqtSignal
from contextlib import contextmanager

from enhanced_logging import (
    EnhancedLoggingManager,
    ErrorClassification,
    RetryPolicy,
    classify_error
)


class CheckpointManager:
    """Manages checkpoint state for resumable operations."""

    def __init__(self, checkpoint_file: Path):
        self.checkpoint_file = checkpoint_file
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()

    def save_checkpoint(self, state: Dict[str, Any]) -> None:
        """Save current processing state to checkpoint file."""
        state['timestamp'] = datetime.now().isoformat()
        state['version'] = '1.0'

        with self.lock:
            try:
                with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                    json.dump(state, f, indent=2, default=str)
            except Exception as e:
                # Log error but don't fail - checkpoint saving shouldn't break processing
                print(f"Warning: Failed to save checkpoint: {e}")

    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Load checkpoint state from file."""
        if not self.checkpoint_file.exists():
            return None

        with self.lock:
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)

                # Validate checkpoint version
                if state.get('version') != '1.0':
                    print(f"Warning: Checkpoint version mismatch, ignoring")
                    return None

                return state
            except Exception as e:
                print(f"Warning: Failed to load checkpoint: {e}")
                return None

    def clear_checkpoint(self) -> None:
        """Clear the checkpoint file."""
        with self.lock:
            try:
                if self.checkpoint_file.exists():
                    self.checkpoint_file.unlink()
            except Exception as e:
                print(f"Warning: Failed to clear checkpoint: {e}")


class BatchProcessor:
    """Handles database operations in batches with rollback support."""

    def __init__(self, db_path: str, batch_size: int = 100):
        self.db_path = db_path
        self.batch_size = batch_size
        self._connection = None

    @contextmanager
    def batch_operation(self):
        """Context manager for batched database operations."""
        self._connection = sqlite3.connect(self.db_path)
        self._connection.execute("PRAGMA foreign_keys = ON")
        cursor = self._connection.cursor()

        try:
            cursor.execute("BEGIN TRANSACTION")
            yield cursor
            self._connection.commit()
        except Exception as e:
            self._connection.rollback()
            raise e
        finally:
            if self._connection:
                self._connection.close()
                self._connection = None

    def execute_batch(self, operations: List[tuple]) -> int:
        """Execute a batch of operations, returning success count."""
        if not operations:
            return 0

        success_count = 0
        with self.batch_operation() as cursor:
            for operation in operations:
                try:
                    cursor.execute(operation[0], operation[1] if len(operation) > 1 else ())
                    success_count += 1
                except Exception as e:
                    # Log the failed operation but continue with others
                    print(f"Batch operation failed: {e}")
                    print(f"Failed operation: {operation}")

        return success_count


class ResilientWorkerThread(QThread):
    """Resilient worker thread with checkpoint recovery and retry policies."""

    # Signals
    progress_updated = pyqtSignal(int, int, str)  # current, total, message
    phase_changed = pyqtSignal(str, str)  # phase_name, description
    error_occurred = pyqtSignal(str, str, bool)  # error_msg, classification, is_recoverable
    retry_attempted = pyqtSignal(str, int, float)  # operation, attempt, delay
    operation_completed = pyqtSignal(bool, str)  # success, summary

    def __init__(self, config_manager, operation_name: str, items: List[Any]):
        super().__init__()
        self.config = config_manager
        self.operation_name = operation_name
        self.items = items
        self.total_items = len(items)

        # Control flags
        self.should_stop = False
        self.is_paused = False
        self.pause_event = threading.Event()
        self.pause_event.set()  # Start unpaused

        # Components
        self.logging_manager = EnhancedLoggingManager(config_manager)
        self.logger = self.logging_manager.get_logger('ingestion')
        self.retry_policy = RetryPolicy()
        self.checkpoint_manager = CheckpointManager(
            Path(config_manager.get('log_directory')) / f"{operation_name}_checkpoint.json"
        )

        # Processing state
        self.current_index = 0
        self.processed_count = 0
        self.failed_count = 0
        self.retry_count = 0
        self.start_time = None

        # Performance tracking
        self.phase_start_time = None
        self.current_phase = "initializing"

    def set_retry_policy(self, policy: RetryPolicy):
        """Set the retry policy for this worker."""
        self.retry_policy = policy

    def pause(self):
        """Pause processing."""
        self.is_paused = True
        self.pause_event.clear()
        self.logger.info("Processing paused by user")

    def resume(self):
        """Resume processing."""
        self.is_paused = False
        self.pause_event.set()
        self.logger.info("Processing resumed")

    def stop(self):
        """Request graceful stop."""
        self.should_stop = True
        self.pause_event.set()  # Unblock if paused
        self.logger.info("Stop requested by user")

    def _wait_if_paused(self):
        """Wait if processing is paused."""
        self.pause_event.wait()

    def _change_phase(self, phase_name: str, description: str):
        """Change processing phase and log the transition."""
        self.current_phase = phase_name
        self.phase_start_time = time.time()
        self.phase_changed.emit(phase_name, description)

        self.logger.info(
            f"Phase changed: {phase_name}",
            extra={'operation_type': 'phase_change', 'phase': phase_name}
        )

    def _load_checkpoint(self) -> bool:
        """Load checkpoint and resume from saved state."""
        checkpoint = self.checkpoint_manager.load_checkpoint()
        if not checkpoint:
            return False

        # Validate checkpoint is for this operation
        if checkpoint.get('operation_name') != self.operation_name:
            self.logger.warning("Checkpoint is for different operation, ignoring")
            return False

        # Restore state
        self.current_index = checkpoint.get('current_index', 0)
        self.processed_count = checkpoint.get('processed_count', 0)
        self.failed_count = checkpoint.get('failed_count', 0)
        self.retry_count = checkpoint.get('retry_count', 0)

        self.logger.info(
            f"Resumed from checkpoint: index {self.current_index}, "
            f"processed {self.processed_count}, failed {self.failed_count}"
        )

        return True

    def _save_checkpoint(self):
        """Save current state to checkpoint."""
        if self.current_index % 10 == 0:  # Save every 10 items
            state = {
                'operation_name': self.operation_name,
                'current_index': self.current_index,
                'processed_count': self.processed_count,
                'failed_count': self.failed_count,
                'retry_count': self.retry_count,
                'phase': self.current_phase
            }
            self.checkpoint_manager.save_checkpoint(state)

    def _execute_with_retry(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute an operation with retry logic."""
        last_error = None
        last_classification = ErrorClassification.UNKNOWN

        for attempt in range(1, self.retry_policy.max_attempts + 1):
            try:
                if self.should_stop:
                    raise InterruptedError("Operation cancelled by user")

                self._wait_if_paused()

                return operation(*args, **kwargs)

            except Exception as e:
                last_error = e
                last_classification = classify_error(e, {'attempt': attempt})

                if not self.retry_policy.should_retry(attempt, last_classification):
                    break

                delay = self.retry_policy.get_delay(attempt)
                self.retry_attempted.emit(str(e), attempt, delay)

                self.logger.warning(
                    f"Operation failed (attempt {attempt}/{self.retry_policy.max_attempts}): {e}",
                    extra={
                        'error_classification': last_classification.value,
                        'retry_attempt': attempt,
                        'retry_delay': delay
                    }
                )

                # Wait before retry
                time.sleep(delay)

        # All retries exhausted or non-retryable error
        self.retry_count += 1

        error_msg = f"Operation failed after {self.retry_policy.max_attempts} attempts: {last_error}"
        self.error_occurred.emit(error_msg, last_classification.value,
                               last_classification in [ErrorClassification.TRANSIENT_IO,
                                                     ErrorClassification.TRANSIENT_SYSTEM])

        raise last_error

    def _process_item(self, item: Any) -> bool:
        """Process a single item. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement _process_item")

    def _finalize_processing(self) -> str:
        """Finalize processing and return summary. Override in subclasses."""
        return f"Processed {self.processed_count} items, {self.failed_count} failed"

    def run(self):
        """Main processing loop with resilience features."""
        try:
            self.start_time = time.time()
            self._change_phase("initializing", "Preparing for processing")

            # Try to resume from checkpoint
            if self._load_checkpoint():
                self._change_phase("resuming", f"Resuming from item {self.current_index}")
            else:
                self._change_phase("starting", "Beginning processing")

            self.logger.info(
                f"Starting {self.operation_name} with {self.total_items} items",
                extra={'operation_type': 'start', 'total_items': self.total_items}
            )

            # Main processing loop
            while self.current_index < self.total_items:
                if self.should_stop:
                    self.logger.info("Processing stopped by user request")
                    break

                self._wait_if_paused()

                item = self.items[self.current_index]

                try:
                    self._change_phase("processing", f"Processing item {self.current_index + 1}/{self.total_items}")

                    # Process with retry logic
                    success = self._execute_with_retry(self._process_item, item)

                    if success:
                        self.processed_count += 1
                        self.progress_updated.emit(
                            self.current_index + 1, self.total_items,
                            f"Processed {self.processed_count} items successfully"
                        )
                    else:
                        self.failed_count += 1

                except Exception as e:
                    self.failed_count += 1
                    self.logger.error(
                        f"Failed to process item {self.current_index}: {e}",
                        extra={'item_index': self.current_index, 'error_type': type(e).__name__}
                    )

                self.current_index += 1
                self._save_checkpoint()

                # Small delay to prevent overwhelming the system
                time.sleep(0.01)

            # Finalization
            self._change_phase("finalizing", "Finalizing processing")

            # Clear checkpoint on successful completion
            if self.current_index >= self.total_items:
                self.checkpoint_manager.clear_checkpoint()

            summary = self._finalize_processing()
            elapsed_time = time.time() - self.start_time

            self.logger.info(
                f"{self.operation_name} completed: {summary} (elapsed: {elapsed_time:.2f}s)",
                extra={
                    'operation_type': 'complete',
                    'processed': self.processed_count,
                    'failed': self.failed_count,
                    'elapsed_time': elapsed_time
                }
            )

            # Log performance metrics
            if self.processed_count > 0:
                self.logging_manager.log_performance_metric(
                    self.operation_name, elapsed_time, self.processed_count
                )

            self.operation_completed.emit(True, summary)

        except Exception as e:
            error_msg = f"Critical error in {self.operation_name}: {e}"
            self.logger.critical(error_msg, exc_info=True)
            self.operation_completed.emit(False, error_msg)

    def get_progress_summary(self) -> Dict[str, Any]:
        """Get current progress summary."""
        elapsed = time.time() - self.start_time if self.start_time else 0

        return {
            'operation_name': self.operation_name,
            'current_index': self.current_index,
            'total_items': self.total_items,
            'processed_count': self.processed_count,
            'failed_count': self.failed_count,
            'retry_count': self.retry_count,
            'progress_percentage': (self.current_index / self.total_items * 100) if self.total_items > 0 else 0,
            'elapsed_time': elapsed,
            'current_phase': self.current_phase,
            'is_paused': self.is_paused,
            'should_stop': self.should_stop
        }
