#!/usr/bin/env python3
"""
Example Integration: Enhanced Importer with Work Item 2 Resilience

This example shows how to integrate the new resilient worker thread
and enhanced logging system with the existing enhanced importer GUI.
"""

import sys
import subprocess
import threading
import sqlite3
from pathlib import Path
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QPushButton, QFileDialog, QListWidget, QMessageBox, QInputDialog,
    QLabel, QLineEdit, QDialog, QDialogButtonBox, QFormLayout, QAbstractItemView,
    QTextEdit, QProgressBar, QSplitter, QGroupBox, QTabWidget, QCheckBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
import qdarkstyle

# Import new Work Item 2 components
from enhanced_logging import EnhancedLoggingManager, ErrorClassification
from resilient_worker import ResilientWorkerThread


class DatabaseManager:
    """Existing database manager - kept for compatibility."""

    def __init__(self, db_path):
        self.db_path = db_path
        self.connection = None

    def connect(self):
        if not self.connection:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.execute("PRAGMA foreign_keys = ON")
        return self.connection

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None


class EnhancedImportWorkerThread(ResilientWorkerThread):
    """Enhanced import worker using the new resilient framework."""

    # Additional signals for import-specific feedback
    console_output = pyqtSignal(str)
    import_session_started = pyqtSignal(str)  # session_id

    def __init__(self, config, source_id, script_path, files, logger):
        # Convert files to items for the resilient worker
        items = [(i, file_path) for i, file_path in enumerate(files)]
        super().__init__(config, f"import_source_{source_id}", items)

        self.source_id = source_id
        self.script_path = script_path
        self.original_files = files  # Keep original for compatibility
        self.logger = logger

        # Use specialized ingestion logger
        self.ingestion_logger = self.logging_manager.get_logger('ingestion')

    def _process_item(self, item):
        """Process a single file with enhanced error handling."""
        index, file_path = item
        file_name = Path(file_path).name

        # Log processing start with context
        self.ingestion_logger.info(
            f"Processing file: {file_name}",
            extra={
                'session_id': getattr(self, 'current_session_id', 'unknown'),
                'file_path': file_path,
                'item_index': index
            }
        )

        # Emit console output for UI feedback
        self.console_output.emit(f"Processing file {index + 1}/{self.total_items}: {file_name}")

        # Run the actual import (with error handling from parent class)
        success, output, error = self._run_single_import(file_path)

        if success:
            self.ingestion_logger.info(
                f"Successfully processed: {file_name}",
                extra={'file_path': file_path, 'processing_time': getattr(self, 'last_processing_time', 0)}
            )
            self.console_output.emit(f"✓ {file_name}: Success")
        else:
            # Error classification and logging is handled by parent class
            self.ingestion_logger.error(
                f"Failed to process {file_name}: {error}",
                extra={
                    'file_path': file_path,
                    'error_type': type(error).__name__ if error else 'Unknown'
                }
            )
            self.console_output.emit(f"✗ {file_name}: FAILED")

        # Emit any output from the importer
        if output:
            self.console_output.emit(output)

        return success

    def _run_single_import(self, file_path):
        """Run single import command - existing logic preserved."""
        try:
            # Prepare environment
            env = dict(sys.environ)
            env['PYTHONPATH'] = str(Path(sys.executable).parent / 'Lib' / 'site-packages')

            # Run the import script
            result = subprocess.run([
                sys.executable, self.script_path, file_path,
                '--db-path', self.config.get('database_path'),
                '--source-id', str(self.source_id)
            ], capture_output=True, text=True, env=env, timeout=300)

            return result.returncode == 0, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            return False, "", "Import timed out after 5 minutes"
        except Exception as e:
            return False, "", str(e)

    def _finalize_processing(self):
        """Enhanced finalization with detailed summary."""
        elapsed = time.time() - self.start_time if self.start_time else 0

        summary = (
            f"Import completed: {self.processed_count} successful, "
            f"{self.failed_count} failed, {self.retry_count} retries "
            f"(elapsed: {elapsed:.1f}s)"
        )

        # Log final statistics
        self.ingestion_logger.info(
            "Import session completed",
            extra={
                'session_id': getattr(self, 'current_session_id', 'unknown'),
                'total_files': self.total_items,
                'processed': self.processed_count,
                'failed': self.failed_count,
                'retries': self.retry_count,
                'elapsed_time': elapsed
            }
        )

        return summary

    def run(self):
        """Enhanced run method with session management."""
        # Start import session logging
        session_id = f"import_{self.source_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.current_session_id = session_id

        self.ingestion_logger.info(
            f"Starting import session: {session_id}",
            extra={'session_id': session_id, 'total_files': self.total_items}
        )

        self.import_session_started.emit(session_id)

        # Run the resilient processing
        super().run()


class ImportLogger:
    """Enhanced import logger using the new logging system."""

    def __init__(self, config_manager):
        self.config = config_manager
        self.logging_manager = EnhancedLoggingManager(config_manager)
        self.ingestion_logger = self.logging_manager.get_logger('ingestion')

        self.current_session_id = None
        self.session_start_time = None

    def start_import_session(self, source_name, files):
        """Start a new import session."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_session_id = f"{source_name}_{timestamp}"
        self.session_start_time = time.time()

        self.ingestion_logger.info(
            f"Import session started: {self.current_session_id}",
            extra={
                'session_id': self.current_session_id,
                'source_name': source_name,
                'file_count': len(files),
                'operation_type': 'session_start'
            }
        )

        return self.current_session_id

    def log_message(self, level, message, **context):
        """Log a message with context."""
        logger_method = getattr(self.ingestion_logger, level, self.ingestion_logger.info)

        # Add session context
        extra = context.copy()
        if self.current_session_id:
            extra['session_id'] = self.current_session_id

        logger_method(message, extra=extra)

    def end_import_session(self, success_count, error_count):
        """End the current import session."""
        if self.current_session_id and self.session_start_time:
            elapsed = time.time() - self.session_start_time

            self.ingestion_logger.info(
                f"Import session ended: {self.current_session_id}",
                extra={
                    'session_id': self.current_session_id,
                    'success_count': success_count,
                    'error_count': error_count,
                    'elapsed_time': elapsed,
                    'operation_type': 'session_end'
                }
            )


class EnhancedImporterApp(QWidget):
    """Enhanced importer GUI with Work Item 2 resilience features."""

    def __init__(self, config_manager):
        super().__init__()
        self.config = config_manager

        # Initialize enhanced logging
        self.logging_manager = EnhancedLoggingManager(config_manager)
        self.logger = ImportLogger(config_manager)

        # Initialize database manager
        self.db_manager = DatabaseManager(config_manager.get('database_path'))

        self.init_ui()
        self.load_sources()

    def init_ui(self):
        """Initialize the enhanced UI."""
        self.setWindowTitle('Enhanced ROM Curator Importer')
        self.setGeometry(100, 100, 1000, 700)

        layout = QVBoxLayout(self)

        # Source selection
        source_group = QGroupBox("Import Source")
        source_layout = QHBoxLayout()

        self.source_combo = QComboBox()
        self.source_combo.currentIndexChanged.connect(self.on_source_changed)
        source_layout.addWidget(QLabel("Source:"))
        source_layout.addWidget(self.source_combo)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_sources)
        source_layout.addWidget(self.refresh_btn)

        source_group.setLayout(source_layout)
        layout.addWidget(source_group)

        # File selection
        file_group = QGroupBox("Files to Import")
        file_layout = QVBoxLayout()

        file_controls = QHBoxLayout()
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.MultiSelection)

        self.add_files_btn = QPushButton("Add Files...")
        self.add_files_btn.clicked.connect(self.add_files)
        file_controls.addWidget(self.add_files_btn)

        self.clear_files_btn = QPushButton("Clear")
        self.clear_files_btn.clicked.connect(self.clear_files)
        file_controls.addWidget(self.clear_files_btn)

        file_layout.addLayout(file_controls)
        file_layout.addWidget(self.file_list)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Progress and control
        progress_group = QGroupBox("Import Progress")
        progress_layout = QVBoxLayout()

        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)

        # Control buttons
        controls_layout = QHBoxLayout()

        self.start_btn = QPushButton("Start Import")
        self.start_btn.clicked.connect(self.start_import)
        self.start_btn.setEnabled(False)
        controls_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_import)
        self.stop_btn.setEnabled(False)
        controls_layout.addWidget(self.stop_btn)

        self.pause_btn = QPushButton("Pause/Resume")
        self.pause_btn.clicked.connect(self.pause_resume_import)
        self.pause_btn.setEnabled(False)
        controls_layout.addWidget(self.pause_btn)

        progress_layout.addLayout(controls_layout)

        # Status label
        self.status_label = QLabel("Ready")
        progress_layout.addWidget(self.status_label)

        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        # Console output
        console_group = QGroupBox("Console Output")
        console_layout = QVBoxLayout()

        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setMaximumHeight(300)
        console_layout.addWidget(self.console_output)

        console_group.setLayout(console_layout)
        layout.addWidget(console_group)

        self.worker_thread = None

    def load_sources(self):
        """Load available import sources."""
        try:
            conn = self.db_manager.connect()
            cursor = conn.cursor()

            cursor.execute("SELECT source_id, name FROM metadata_source WHERE importer_script IS NOT NULL")
            sources = cursor.fetchall()

            self.source_combo.clear()
            self.source_combo.addItem("-- Select Source --", None)

            for source_id, name in sources:
                self.source_combo.addItem(name, source_id)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load sources: {e}")

    def on_source_changed(self):
        """Handle source selection change."""
        source_id = self.source_combo.currentData()
        self.start_btn.setEnabled(source_id is not None and self.file_list.count() > 0)

    def add_files(self):
        """Add files to import list."""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Files to Import",
            "", "All Files (*.*)"
        )

        if files:
            for file_path in files:
                self.file_list.addItem(file_path)

            self.start_btn.setEnabled(self.source_combo.currentData() is not None)

    def clear_files(self):
        """Clear the file list."""
        self.file_list.clear()
        self.start_btn.setEnabled(False)

    def start_import(self):
        """Start the import process with enhanced resilience."""
        if self.worker_thread and self.worker_thread.isRunning():
            return

        source_id = self.source_combo.currentData()
        if not source_id:
            QMessageBox.warning(self, "Error", "Please select an import source.")
            return

        # Get selected files
        files = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.isSelected():
                files.append(item.text())

        if not files:
            # If no files selected, import all
            files = [self.file_list.item(i).text() for i in range(self.file_list.count())]

        if not files:
            QMessageBox.warning(self, "Error", "Please add files to import.")
            return

        # Get script path for source
        try:
            conn = self.db_manager.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT importer_script FROM metadata_source WHERE source_id = ?", (source_id,))
            result = cursor.fetchone()

            if not result or not result[0]:
                QMessageBox.critical(self, "Error", "No import script configured for this source.")
                return

            script_path = result[0]

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to get script path: {e}")
            return

        # Create and start worker thread
        self.worker_thread = EnhancedImportWorkerThread(
            self.config, source_id, script_path, files, self.logger
        )

        # Connect signals
        self.worker_thread.progress_updated.connect(self.update_progress)
        self.worker_thread.console_output.connect(self.add_console_output)
        self.worker_thread.operation_completed.connect(self.import_completed)
        self.worker_thread.phase_changed.connect(self.phase_changed)
        self.worker_thread.error_occurred.connect(self.handle_error)
        self.worker_thread.retry_attempted.connect(self.handle_retry)
        self.worker_thread.import_session_started.connect(self.import_session_started)

        # Update UI state
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.pause_btn.setEnabled(True)
        self.status_label.setText("Starting import...")

        # Clear console
        self.console_output.clear()

        # Start the worker
        self.worker_thread.start()

    def stop_import(self):
        """Stop the import process."""
        if self.worker_thread:
            self.worker_thread.stop()

    def pause_resume_import(self):
        """Pause or resume the import process."""
        if self.worker_thread:
            if self.worker_thread.is_paused:
                self.worker_thread.resume()
                self.pause_btn.setText("Pause")
            else:
                self.worker_thread.pause()
                self.pause_btn.setText("Resume")

    def update_progress(self, current, total, message):
        """Update progress bar."""
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
        self.status_label.setText(message)

    def add_console_output(self, text):
        """Add text to console output."""
        self.console_output.append(text)
        # Auto-scroll to bottom
        cursor = self.console_output.textCursor()
        cursor.movePosition(cursor.End)
        self.console_output.setTextCursor(cursor)

    def import_completed(self, success, summary):
        """Handle import completion."""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100 if success else 0)

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("Pause/Resume")

        if success:
            self.status_label.setText("Import completed successfully")
            QMessageBox.information(self, "Success", f"Import completed!\n\n{summary}")
        else:
            self.status_label.setText("Import failed")
            QMessageBox.critical(self, "Error", f"Import failed!\n\n{summary}")

        self.worker_thread = None

    def phase_changed(self, phase_name, description):
        """Handle phase changes."""
        self.add_console_output(f"\n--- Phase: {phase_name} ---")
        self.add_console_output(description)

    def handle_error(self, error_msg, classification, is_recoverable):
        """Handle errors from worker thread."""
        self.add_console_output(f"ERROR ({classification}): {error_msg}")
        if not is_recoverable:
            QMessageBox.warning(self, "Non-recoverable Error",
                              f"A non-recoverable error occurred:\n\n{error_msg}\n\n"
                              "The import process will continue with remaining files.")

    def handle_retry(self, error_msg, attempt, delay):
        """Handle retry attempts."""
        self.add_console_output(f"RETRY {attempt}: {error_msg} (waiting {delay:.1f}s)")

    def import_session_started(self, session_id):
        """Handle import session start."""
        self.add_console_output(f"Import session started: {session_id}")

    def closeEvent(self, event):
        """Handle window close."""
        if self.worker_thread and self.worker_thread.isRunning():
            reply = QMessageBox.question(
                self, "Confirm Exit",
                "An import is currently running. Stop it and exit?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.worker_thread.stop()
                self.worker_thread.wait(5000)  # Wait up to 5 seconds
            else:
                event.ignore()
                return

        event.accept()


# Example usage
if __name__ == "__main__":
    # Mock config for demonstration
    class MockConfig:
        def get(self, key, default=None):
            configs = {
                'database_path': './database/RomCurator.db',
                'log_directory': './logs',
                'log_level': 'INFO'
            }
            return configs.get(key, default)

    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    window = EnhancedImporterApp(MockConfig())
    window.show()

    sys.exit(app.exec_())
