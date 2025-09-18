#!/usr/bin/env python3
"""
Enhanced Logging System for ROM Curator

Provides specialized logging channels for ingestion workflows with:
- Dedicated channels for ingestion, archive handling, and organization
- Structured logging with context preservation
- Error classification and retry tracking
- Performance monitoring and telemetry
"""

import logging
import logging.handlers
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class ErrorClassification(Enum):
    """Classification of errors for retry and handling decisions."""

    TRANSIENT_IO = "transient_io"         # I/O hiccups, temporary locks, network issues
    PERMANENT_PERMISSION = "permanent_permission"  # Access denied, file permissions
    PERMANENT_SCHEMA = "permanent_schema"   # Database schema issues, constraint violations
    PERMANENT_MISSING = "permanent_missing" # Missing files, paths, or resources
    TRANSIENT_SYSTEM = "transient_system"   # Memory, CPU, temporary system issues
    UNKNOWN = "unknown"                    # Unclassified errors


class RetryPolicy:
    """Configurable retry policy with exponential backoff."""

    def __init__(self, max_attempts: int = 3, initial_delay: float = 30.0,
                 backoff_multiplier: float = 2.0, max_delay: float = 300.0):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.backoff_multiplier = backoff_multiplier
        self.max_delay = max_delay

    def should_retry(self, attempt: int, error_classification: ErrorClassification) -> bool:
        """Determine if a retry should be attempted."""
        if attempt >= self.max_attempts:
            return False

        # Only retry transient errors
        return error_classification in [
            ErrorClassification.TRANSIENT_IO,
            ErrorClassification.TRANSIENT_SYSTEM
        ]

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt number."""
        delay = self.initial_delay * (self.backoff_multiplier ** (attempt - 1))
        return min(delay, self.max_delay)


class IngestionLogger(logging.Logger):
    """Specialized logger for ingestion operations with context tracking."""

    def __init__(self, name: str, config_manager):
        super().__init__(name)
        self.config = config_manager
        self.context = {}

    def set_context(self, **kwargs):
        """Set contextual information for logging."""
        self.context.update(kwargs)

    def clear_context(self):
        """Clear all contextual information."""
        self.context.clear()

    def makeRecord(self, name, level, fn, lno, msg, args, exc_info, func=None, extra=None, sinfo=None):
        """Override to inject context into log records."""
        if extra is None:
            extra = {}

        # Add context to extra
        extra.update(self.context)

        return super().makeRecord(name, level, fn, lno, msg, args, exc_info, func, extra, sinfo)


class IngestionFormatter(logging.Formatter):
    """Custom formatter for ingestion logs with structured context."""

    def format(self, record):
        """Format log record with ingestion-specific context."""

        # Base format
        timestamp = datetime.fromtimestamp(record.created).isoformat()

        # Extract context from record
        context_info = {}
        if hasattr(record, 'session_id'):
            context_info['session_id'] = record.session_id
        if hasattr(record, 'operation_type'):
            context_info['operation_type'] = record.operation_type
        if hasattr(record, 'file_path'):
            context_info['file_path'] = record.file_path
        if hasattr(record, 'retry_attempt'):
            context_info['retry_attempt'] = record.retry_attempt
        if hasattr(record, 'error_classification'):
            context_info['error_classification'] = record.error_classification

        # Format message
        message = super().format(record)

        if context_info:
            # Add context as JSON for structured parsing
            context_str = json.dumps(context_info, default=str)
            return f"{timestamp} [{record.levelname}] {record.name}: {message} | {context_str}"
        else:
            return f"{timestamp} [{record.levelname}] {record.name}: {message}"


class EnhancedLoggingManager:
    """Enhanced logging manager with specialized channels for ingestion workflows."""

    def __init__(self, config_manager):
        self.config = config_manager
        self.log_dir = Path(config_manager.get('log_directory'))
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Create specialized loggers
        self.root_logger = self._setup_root_logger()
        self.ingestion_logger = self._setup_ingestion_logger()
        self.archive_logger = self._setup_archive_logger()
        self.organizer_logger = self._setup_organizer_logger()

        # Performance tracking
        self.performance_data = {}

    def _setup_root_logger(self):
        """Set up the root logger with basic configuration."""
        logger = logging.getLogger('rom_curator')
        logger.setLevel(getattr(logging, self.config.get('log_level', 'INFO').upper()))

        # Clear existing handlers
        logger.handlers.clear()

        # File handler for general logs
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'rom_curator.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        console_handler.stream.reconfigure(encoding='utf-8')
        logger.addHandler(console_handler)

        return logger

    def _setup_ingestion_logger(self):
        """Set up specialized logger for ingestion operations."""
        logger = IngestionLogger('ingestion', self.config)
        logger.setLevel(logging.DEBUG)
        logger.handlers.clear()

        # File handler for ingestion logs
        ingestion_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'ingestion.log',
            maxBytes=25*1024*1024,  # 25MB
            backupCount=10,
            encoding='utf-8'
        )
        ingestion_handler.setFormatter(IngestionFormatter())
        logger.addHandler(ingestion_handler)

        # Also send to root logger
        logger.addHandler(self.root_logger.handlers[0])

        return logger

    def _setup_archive_logger(self):
        """Set up specialized logger for archive handling."""
        logger = IngestionLogger('ingestion.archive', self.config)
        logger.setLevel(logging.DEBUG)
        logger.handlers.clear()

        # File handler for archive logs
        archive_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'archive.log',
            maxBytes=15*1024*1024,  # 15MB
            backupCount=5,
            encoding='utf-8'
        )
        archive_handler.setFormatter(IngestionFormatter())
        logger.addHandler(archive_handler)

        # Also send to root logger
        logger.addHandler(self.root_logger.handlers[0])

        return logger

    def _setup_organizer_logger(self):
        """Set up specialized logger for file organization."""
        logger = IngestionLogger('ingestion.organizer', self.config)
        logger.setLevel(logging.DEBUG)
        logger.handlers.clear()

        # File handler for organizer logs
        organizer_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'organizer.log',
            maxBytes=15*1024*1024,  # 15MB
            backupCount=5,
            encoding='utf-8'
        )
        organizer_handler.setFormatter(IngestionFormatter())
        logger.addHandler(organizer_handler)

        # Also send to root logger
        logger.addHandler(self.root_logger.handlers[0])

        return logger

    def get_logger(self, name: str) -> IngestionLogger:
        """Get a logger by name."""
        if name == 'ingestion':
            return self.ingestion_logger
        elif name == 'ingestion.archive':
            return self.archive_logger
        elif name == 'ingestion.organizer':
            return self.organizer_logger
        else:
            return self.root_logger

    def log_performance_metric(self, operation: str, duration: float, item_count: int = 1):
        """Log performance metrics for monitoring."""
        if operation not in self.performance_data:
            self.performance_data[operation] = []

        self.performance_data[operation].append({
            'timestamp': time.time(),
            'duration': duration,
            'item_count': item_count,
            'items_per_second': item_count / duration if duration > 0 else 0
        })

        # Keep only last 1000 entries per operation
        if len(self.performance_data[operation]) > 1000:
            self.performance_data[operation] = self.performance_data[operation][-1000:]

        # Log the metric
        self.ingestion_logger.info(
            f"Performance: {operation} completed in {duration:.2f}s "
            f"({item_count/duration:.1f} items/sec)",
            extra={'operation_type': 'performance', 'metric_duration': duration}
        )

    def get_performance_summary(self) -> Dict[str, Dict[str, float]]:
        """Get performance summary statistics."""
        summary = {}
        for operation, data in self.performance_data.items():
            if data:
                durations = [d['duration'] for d in data]
                rates = [d['items_per_second'] for d in data]

                summary[operation] = {
                    'count': len(data),
                    'avg_duration': sum(durations) / len(durations),
                    'min_duration': min(durations),
                    'max_duration': max(durations),
                    'avg_rate': sum(rates) / len(rates) if rates else 0,
                    'total_items': sum(d['item_count'] for d in data)
                }

        return summary


def classify_error(error: Exception, context: Dict[str, Any] = None) -> ErrorClassification:
    """Classify an error for retry and handling decisions."""

    error_str = str(error).lower()
    error_type = type(error).__name__.lower()

    # Permission errors
    if any(keyword in error_str for keyword in ['permission denied', 'access denied', 'unauthorized']):
        return ErrorClassification.PERMANENT_PERMISSION

    # Missing files/resources
    if any(keyword in error_str for keyword in ['no such file', 'file not found', 'path not found']):
        return ErrorClassification.PERMANENT_MISSING

    # Database schema/constraint errors
    if any(keyword in error_str for keyword in ['constraint failed', 'foreign key', 'no such table', 'no such column']):
        return ErrorClassification.PERMANENT_SCHEMA

    # System resource errors (transient) - check first for specificity
    if any(keyword in error_str for keyword in ['memory', 'disk space', 'too many files', 'resource temporarily unavailable']):
        return ErrorClassification.TRANSIENT_SYSTEM

    # I/O and network errors (transient)
    if any(keyword in error_str for keyword in ['connection', 'timeout', 'temporarily unavailable', 'busy']):
        return ErrorClassification.TRANSIENT_IO

    # SQLite locking issues
    if 'database is locked' in error_str or 'database locked' in error_str:
        return ErrorClassification.TRANSIENT_IO

    # Default to unknown
    return ErrorClassification.UNKNOWN
