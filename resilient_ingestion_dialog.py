#!/usr/bin/env python3
"""
Resilient Ingestion Dialog - Work Item 2 Complete Implementation

Provides a comprehensive UI for library ingestion with:
- Resilience controls (pause/resume/stop)
- Error handling and classification display
- Checkpoint recovery
- Real-time progress and phase tracking
- Performance monitoring
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QProgressBar, QTextEdit, QListWidget,
    QGroupBox, QCheckBox, QComboBox, QMessageBox, QFileDialog,
    QSplitter, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QSpinBox, QFormLayout, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon
import qdarkstyle

from resilient_worker import ResilientWorkerThread
from enhanced_logging import ErrorClassification, classify_error


class MockIngestionWorker(ResilientWorkerThread):
    """Mock worker for demonstration - simulates ingestion operations."""

    def __init__(self, config_manager, items):
        super().__init__(config_manager, "demo_ingestion", items)

    def _process_item(self, item):
        """Simulate processing an item."""
        import time
        time.sleep(0.1)  # Simulate work

        # Simulate occasional errors for demonstration
        if item % 50 == 0:  # Every 50th item has a 20% chance of error
            import random
            if random.random() < 0.2:
                raise FileNotFoundError(f"Mock file not found: {item}")

        return f"Processed item {item}"

    def _finalize_processing(self):
        """Return summary."""
        return f"Demo completed: {self.processed_count} processed, {self.failed_count} failed"


class ErrorDisplayWidget(QWidget):
    """Widget for displaying errors with classification."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize the error display UI."""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("🚨 Error Summary")
        header.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(header)

        # Error statistics
        stats_layout = QHBoxLayout()

        self.total_errors_label = QLabel("Total: 0")
        self.total_errors_label.setStyleSheet("color: red; font-weight: bold;")

        self.transient_errors_label = QLabel("Transient: 0")
        self.transient_errors_label.setStyleSheet("color: orange;")

        self.permanent_errors_label = QLabel("Permanent: 0")
        self.permanent_errors_label.setStyleSheet("color: red;")

        stats_layout.addWidget(self.total_errors_label)
        stats_layout.addWidget(self.transient_errors_label)
        stats_layout.addWidget(self.permanent_errors_label)
        stats_layout.addStretch()

        layout.addLayout(stats_layout)

        # Error list
        self.error_table = QTableWidget()
        self.error_table.setColumnCount(4)
        self.error_table.setHorizontalHeaderLabels([
            "Time", "Error Type", "Classification", "Message"
        ])
        self.error_table.horizontalHeader().setStretchLastSection(True)
        self.error_table.setAlternatingRowColors(True)
        self.error_table.setMaximumHeight(200)

        layout.addWidget(self.error_table)

    def add_error(self, message, classification, timestamp=None):
        """Add an error to the display."""
        if timestamp is None:
            timestamp = datetime.now().strftime("%H:%M:%S")

        row = self.error_table.rowCount()
        self.error_table.insertRow(row)

        # Time
        self.error_table.setItem(row, 0, QTableWidgetItem(timestamp))

        # Error type
        error_type = type(message).__name__ if hasattr(message, '__class__') else "Unknown"
        self.error_table.setItem(row, 1, QTableWidgetItem(error_type))

        # Classification
        class_item = QTableWidgetItem(classification.value)
        if classification == ErrorClassification.TRANSIENT_IO:
            class_item.setBackground(Qt.yellow)
        elif classification == ErrorClassification.TRANSIENT_SYSTEM:
            class_item.setBackground(Qt.orange)
        else:
            class_item.setBackground(Qt.red)
        self.error_table.setItem(row, 2, class_item)

        # Message
        self.error_table.setItem(row, 3, QTableWidgetItem(str(message)))

        # Update statistics
        self._update_statistics()

    def _update_statistics(self):
        """Update error statistics."""
        total = self.error_table.rowCount()
        transient = 0
        permanent = 0

        for row in range(total):
            class_item = self.error_table.item(row, 2)
            if class_item:
                classification = class_item.text()
                if "transient" in classification.lower():
                    transient += 1
                else:
                    permanent += 1

        self.total_errors_label.setText(f"Total: {total}")
        self.transient_errors_label.setText(f"Transient: {transient}")
        self.permanent_errors_label.setText(f"Permanent: {permanent}")

    def clear_errors(self):
        """Clear all errors."""
        self.error_table.setRowCount(0)
        self._update_statistics()


class ResilienceControlsWidget(QWidget):
    """Widget for resilience controls (pause/resume/stop)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.init_ui()

    def init_ui(self):
        """Initialize the resilience controls UI."""
        layout = QHBoxLayout(self)

        # Status indicator
        self.status_label = QLabel("⏹️ Ready")
        self.status_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Control buttons
        self.start_btn = QPushButton("▶️ Start")
        self.start_btn.clicked.connect(self.start_operation)
        layout.addWidget(self.start_btn)

        self.pause_btn = QPushButton("⏸️ Pause")
        self.pause_btn.clicked.connect(self.pause_resume_operation)
        self.pause_btn.setEnabled(False)
        layout.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("⏹️ Stop")
        self.stop_btn.clicked.connect(self.stop_operation)
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn)

        # Resilience settings
        layout.addStretch()
        layout.addWidget(QLabel("Resilience:"))

        self.retry_check = QCheckBox("Auto-retry")
        self.retry_check.setChecked(True)
        layout.addWidget(self.retry_check)

        self.checkpoint_check = QCheckBox("Checkpoints")
        self.checkpoint_check.setChecked(True)
        layout.addWidget(self.checkpoint_check)

    def set_worker(self, worker):
        """Set the worker thread to control."""
        self.worker = worker
        self._update_button_states()

    def start_operation(self):
        """Start the operation."""
        if self.worker and not self.worker.isRunning():
            self.worker.start()
            self._update_button_states()

    def pause_resume_operation(self):
        """Pause or resume the operation."""
        if not self.worker:
            return

        if self.worker.is_paused:
            self.worker.resume()
            self.pause_btn.setText("⏸️ Pause")
        else:
            self.worker.pause()
            self.pause_btn.setText("▶️ Resume")

    def stop_operation(self):
        """Stop the operation."""
        if self.worker:
            self.worker.stop()

    def _update_button_states(self):
        """Update button states based on worker status."""
        if not self.worker:
            self.start_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            self.status_label.setText("⏹️ Ready")
            return

        running = self.worker.isRunning()
        paused = getattr(self.worker, 'is_paused', False)

        self.start_btn.setEnabled(not running)
        self.pause_btn.setEnabled(running)
        self.stop_btn.setEnabled(running)

        if not running:
            self.status_label.setText("⏹️ Stopped")
        elif paused:
            self.status_label.setText("⏸️ Paused")
        else:
            self.status_label.setText("▶️ Running")


class ProgressDisplayWidget(QWidget):
    """Enhanced progress display with phase tracking."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize the progress display UI."""
        layout = QVBoxLayout(self)

        # Main progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        # Progress details
        details_layout = QHBoxLayout()

        self.current_phase_label = QLabel("Phase: Initializing")
        self.current_phase_label.setFont(QFont("Arial", 10))

        self.items_processed_label = QLabel("Items: 0/0")
        self.items_processed_label.setFont(QFont("Arial", 10))

        self.elapsed_time_label = QLabel("Time: 0:00")
        self.elapsed_time_label.setFont(QFont("Arial", 10))

        details_layout.addWidget(self.current_phase_label)
        details_layout.addStretch()
        details_layout.addWidget(self.items_processed_label)
        details_layout.addWidget(self.elapsed_time_label)

        layout.addLayout(details_layout)

        # Performance indicator
        self.performance_label = QLabel("Performance: -- items/sec")
        self.performance_label.setFont(QFont("Arial", 9))
        self.performance_label.setStyleSheet("color: #888;")
        layout.addWidget(self.performance_label)

    def update_progress(self, current, total, message=""):
        """Update progress display."""
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
            self.items_processed_label.setText(f"Items: {current}/{total}")
        else:
            self.progress_bar.setRange(0, 0)  # Indeterminate
            self.items_processed_label.setText("Items: --/--")

    def update_phase(self, phase_name, description):
        """Update current phase."""
        self.current_phase_label.setText(f"Phase: {phase_name}")
        if description:
            self.current_phase_label.setToolTip(description)

    def update_elapsed_time(self, elapsed_seconds):
        """Update elapsed time display."""
        minutes = int(elapsed_seconds // 60)
        seconds = int(elapsed_seconds % 60)
        self.elapsed_time_label.setText("02d")

    def update_performance(self, items_per_second):
        """Update performance indicator."""
        if items_per_second > 0:
            self.performance_label.setText(".1f")
        else:
            self.performance_label.setText("Performance: -- items/sec")


class ResilientIngestionDialog(QDialog):
    """Complete resilient ingestion dialog with all Work Item 2 features."""

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.worker = None
        self.start_time = None

        self.init_ui()
        self.setup_connections()

        # Apply dark theme
        self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    def init_ui(self):
        """Initialize the comprehensive UI."""
        self.setWindowTitle("Resilient Library Ingestion - Work Item 2")
        self.setGeometry(100, 100, 1200, 800)

        layout = QVBoxLayout(self)

        # Create tab widget for organization
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)

        # Main ingestion tab
        main_tab = QWidget()
        tab_widget.addTab(main_tab, "📁 Ingestion")

        # Configuration tab
        config_tab = QWidget()
        tab_widget.addTab(config_tab, "⚙️ Configuration")

        # Monitoring tab
        monitor_tab = QWidget()
        tab_widget.addTab(monitor_tab, "📊 Monitoring")

        # Setup each tab
        self.setup_main_tab(main_tab)
        self.setup_config_tab(config_tab)
        self.setup_monitor_tab(monitor_tab)

        # Bottom button row
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

    def setup_main_tab(self, tab):
        """Setup the main ingestion tab."""
        layout = QVBoxLayout(tab)

        # Resilience controls at the top
        resilience_group = QGroupBox("Resilience Controls")
        resilience_layout = QVBoxLayout(resilience_group)
        self.resilience_controls = ResilienceControlsWidget()
        resilience_layout.addWidget(self.resilience_controls)
        layout.addWidget(resilience_group)

        # Progress display
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        self.progress_display = ProgressDisplayWidget()
        progress_layout.addWidget(self.progress_display)
        layout.addWidget(progress_group)

        # Splitter for console and errors
        splitter = QSplitter(Qt.Vertical)

        # Console output
        console_group = QGroupBox("Console Output")
        console_layout = QVBoxLayout(console_group)
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setFontFamily("Consolas")
        self.console_output.setFontPointSize(9)
        self.console_output.setMaximumHeight(300)
        console_layout.addWidget(self.console_output)
        splitter.addWidget(console_group)

        # Error display
        error_group = QGroupBox("Error Summary")
        error_layout = QVBoxLayout(error_group)
        self.error_display = ErrorDisplayWidget()
        error_layout.addWidget(self.error_display)
        splitter.addWidget(error_group)

        layout.addWidget(splitter)

    def setup_config_tab(self, tab):
        """Setup the configuration tab."""
        layout = QVBoxLayout(tab)

        # Library selection
        library_group = QGroupBox("Library Configuration")
        library_layout = QFormLayout(library_group)

        self.library_path_edit = QLineEdit()
        self.library_path_edit.setText(str(Path.home() / "ROMs"))  # Default
        library_layout.addRow("Library Path:", self.library_path_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_library_path)
        library_layout.addRow("", browse_btn)

        layout.addWidget(library_group)

        # Processing options
        options_group = QGroupBox("Processing Options")
        options_layout = QVBoxLayout(options_group)

        self.hash_check = QCheckBox("Calculate file hashes")
        self.hash_check.setChecked(True)
        options_layout.addWidget(self.hash_check)

        self.archive_check = QCheckBox("Process archives")
        self.archive_check.setChecked(True)
        options_layout.addWidget(self.archive_check)

        self.metadata_check = QCheckBox("Extract metadata")
        self.metadata_check.setChecked(True)
        options_layout.addWidget(self.metadata_check)

        layout.addWidget(options_group)

        # Resilience settings
        resilience_group = QGroupBox("Resilience Settings")
        resilience_layout = QFormLayout(resilience_group)

        self.max_retries_spin = QSpinBox()
        self.max_retries_spin.setRange(1, 10)
        self.max_retries_spin.setValue(3)
        resilience_layout.addRow("Max Retries:", self.max_retries_spin)

        self.retry_delay_spin = QSpinBox()
        self.retry_delay_spin.setRange(10, 300)
        self.retry_delay_spin.setValue(30)
        resilience_layout.addRow("Retry Delay (sec):", self.retry_delay_spin)

        layout.addWidget(resilience_group)

        layout.addStretch()

    def setup_monitor_tab(self, tab):
        """Setup the monitoring tab."""
        layout = QVBoxLayout(tab)

        # Current status
        status_group = QGroupBox("Current Status")
        status_layout = QVBoxLayout(status_group)

        self.status_table = QTableWidget()
        self.status_table.setColumnCount(2)
        self.status_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.status_table.horizontalHeader().setStretchLastSection(True)
        self.status_table.setAlternatingRowColors(True)

        # Add status items
        status_items = [
            ("Status", "Ready"),
            ("Items Processed", "0"),
            ("Items Failed", "0"),
            ("Retry Count", "0"),
            ("Current Phase", "None"),
            ("Elapsed Time", "0:00"),
            ("Estimated Completion", "--"),
        ]

        self.status_table.setRowCount(len(status_items))
        for i, (metric, value) in enumerate(status_items):
            self.status_table.setItem(i, 0, QTableWidgetItem(metric))
            self.status_table.setItem(i, 1, QTableWidgetItem(value))

        status_layout.addWidget(self.status_table)
        layout.addWidget(status_group)

        # Performance metrics
        perf_group = QGroupBox("Performance Metrics")
        perf_layout = QVBoxLayout(perf_group)

        self.perf_table = QTableWidget()
        self.perf_table.setColumnCount(3)
        self.perf_table.setHorizontalHeaderLabels(["Operation", "Avg Duration", "Items/sec"])
        self.perf_table.horizontalHeader().setStretchLastSection(True)
        self.perf_table.setAlternatingRowColors(True)

        perf_layout.addWidget(self.perf_table)
        layout.addWidget(perf_group)

        # Refresh button
        refresh_btn = QPushButton("Refresh Metrics")
        refresh_btn.clicked.connect(self.refresh_monitoring)
        layout.addWidget(refresh_btn)

        layout.addStretch()

    def setup_connections(self):
        """Setup signal connections."""
        # Update timer for monitoring
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_status_display)
        self.update_timer.start(1000)  # Update every second

    def browse_library_path(self):
        """Browse for library path."""
        path = QFileDialog.getExistingDirectory(self, "Select Library Directory")
        if path:
            self.library_path_edit.setText(path)

    def start_ingestion(self):
        """Start the ingestion process."""
        if self.worker and self.worker.isRunning():
            return

        # Get library path
        library_path = Path(self.library_path_edit.text())
        if not library_path.exists():
            QMessageBox.warning(self, "Invalid Path",
                              f"Library path does not exist:\n{library_path}")
            return

        # Create mock items for demonstration
        items = list(range(1, 101))  # Simulate 100 items

        # Create worker
        self.worker = MockIngestionWorker(self.config, items)

        # Configure retry policy
        from enhanced_logging import RetryPolicy
        retry_policy = RetryPolicy(
            max_attempts=self.max_retries_spin.value(),
            initial_delay=self.retry_delay_spin.value()
        )
        self.worker.set_retry_policy(retry_policy)

        # Connect signals
        self.worker.progress_updated.connect(self.progress_display.update_progress)
        self.worker.phase_changed.connect(self.progress_display.update_phase)
        self.worker.operation_completed.connect(self.ingestion_completed)
        self.worker.error_occurred.connect(self.handle_worker_error)
        self.worker.retry_attempted.connect(self.handle_worker_retry)

        # Set worker in controls
        self.resilience_controls.set_worker(self.worker)

        # Clear previous state
        self.error_display.clear_errors()
        self.console_output.clear()
        self.start_time = datetime.now()

        # Start worker
        self.worker.start()

        self.add_console_message("🚀 Starting resilient ingestion process...")

    def stop_ingestion(self):
        """Stop the ingestion process."""
        if self.worker:
            self.worker.stop()
            self.add_console_message("🛑 Ingestion stopped by user")

    def pause_resume_ingestion(self):
        """Pause or resume ingestion."""
        if self.worker:
            if self.worker.is_paused:
                self.worker.resume()
                self.add_console_message("▶️ Ingestion resumed")
            else:
                self.worker.pause()
                self.add_console_message("⏸️ Ingestion paused")

    def handle_worker_error(self, error_msg, classification, is_recoverable):
        """Handle errors from worker thread."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.error_display.add_error(error_msg, ErrorClassification(classification), timestamp)

        if is_recoverable:
            self.add_console_message(f"⚠️ Recoverable error: {error_msg}")
        else:
            self.add_console_message(f"❌ Permanent error: {error_msg}")

    def handle_worker_retry(self, error_msg, attempt, delay):
        """Handle retry attempts."""
        self.add_console_message(f"🔄 Retry {attempt} in {delay}s: {error_msg}")

    def ingestion_completed(self, success, summary):
        """Handle ingestion completion."""
        elapsed = datetime.now() - self.start_time if self.start_time else None

        if success:
            self.add_console_message(f"✅ Ingestion completed successfully!")
            self.add_console_message(f"📊 Summary: {summary}")
            if elapsed:
                self.add_console_message(f"⏱️ Total time: {elapsed.total_seconds():.1f}s")
        else:
            self.add_console_message(f"❌ Ingestion failed!")
            self.add_console_message(f"📊 Summary: {summary}")

        self.resilience_controls._update_button_states()

    def add_console_message(self, message):
        """Add a message to the console output."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.console_output.append(f"[{timestamp}] {message}")

        # Auto-scroll to bottom
        cursor = self.console_output.textCursor()
        cursor.movePosition(cursor.End)
        self.console_output.setTextCursor(cursor)

    def update_status_display(self):
        """Update the status display in monitoring tab."""
        if not self.worker:
            return

        # Update status table
        status_data = self.worker.get_progress_summary()

        updates = [
            ("Status", "Running" if self.worker.isRunning() else "Stopped"),
            ("Items Processed", str(status_data.get('processed_count', 0))),
            ("Items Failed", str(status_data.get('failed_count', 0))),
            ("Retry Count", str(status_data.get('retry_count', 0))),
            ("Current Phase", status_data.get('current_phase', 'Unknown')),
            ("Elapsed Time", ".1f"),
        ]

        for i, (metric, value) in enumerate(updates):
            if i < self.status_table.rowCount():
                self.status_table.item(i, 1).setText(value)

        # Update progress display
        if self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            self.progress_display.update_elapsed_time(elapsed)

            # Calculate performance
            processed = status_data.get('processed_count', 0)
            if elapsed > 0 and processed > 0:
                items_per_sec = processed / elapsed
                self.progress_display.update_performance(items_per_sec)

    def refresh_monitoring(self):
        """Refresh monitoring data."""
        try:
            from enhanced_logging import EnhancedLoggingManager
            logging_manager = EnhancedLoggingManager(self.config)
            summary = logging_manager.get_performance_summary()

            # Update performance table
            self.perf_table.setRowCount(len(summary))

            for i, (operation, stats) in enumerate(summary.items()):
                self.perf_table.setItem(i, 0, QTableWidgetItem(operation))
                self.perf_table.setItem(i, 1, QTableWidgetItem(".2f"))
                self.perf_table.setItem(i, 2, QTableWidgetItem(".1f"))

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to refresh monitoring data:\n{e}")

    def closeEvent(self, event):
        """Handle dialog close."""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "Confirm Exit",
                "Ingestion is currently running. Stop it and exit?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.worker.stop()
                self.worker.wait(5000)  # Wait up to 5 seconds
            else:
                event.ignore()
                return

        event.accept()


# Test function for standalone execution
if __name__ == "__main__":
    from rom_curator_main import ConfigManager

    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    config = ConfigManager()
    dialog = ResilientIngestionDialog(config)
    dialog.show()

    sys.exit(app.exec_())
