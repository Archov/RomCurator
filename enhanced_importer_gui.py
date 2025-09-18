"""
Enhanced Data Importer GUI with Progress Feedback and Logging

This provides a comprehensive interface for importing data with:
- Real-time progress bars
- Console output viewing
- Detailed logging to files
- Error reporting and recovery
"""

import os
import sys
import json
import sqlite3
import subprocess
import logging
import threading
import time
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

# Import existing database management
from data_importer_gui import DatabaseManager


class ImportLogger:
    """Enhanced logging system for import operations."""
    
    def __init__(self, config_manager):
        self.config = config_manager
        self.log_dir = Path(config_manager.get('log_directory'))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Current import session
        self.current_session_id = None
        self.session_log_file = None
        self.session_logger = None
    
    def start_import_session(self, source_name, files):
        """Start a new import session with dedicated logging."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_session_id = f"{source_name}_{timestamp}"
        
        # Create session-specific log file
        self.session_log_file = self.log_dir / f"import_{self.current_session_id}.log"
        
        # Create session logger
        self.session_logger = logging.getLogger(f"import_session_{self.current_session_id}")
        self.session_logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        for handler in self.session_logger.handlers[:]:
            self.session_logger.removeHandler(handler)
        
        # File handler for this session
        file_handler = logging.FileHandler(self.session_log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        self.session_logger.addHandler(file_handler)
        
        # Log session start
        self.session_logger.info(f"=== Import Session Started ===")
        self.session_logger.info(f"Source: {source_name}")
        self.session_logger.info(f"Files: {len(files)} files")
        for i, file_path in enumerate(files, 1):
            self.session_logger.info(f"  {i}. {Path(file_path).name}")
        self.session_logger.info(f"Session ID: {self.current_session_id}")
        
        return self.current_session_id
    
    def log_message(self, level, message):
        """Log a message to the current session."""
        if self.session_logger:
            getattr(self.session_logger, level.lower())(message)
    
    def end_import_session(self, success=True, summary=""):
        """End the current import session."""
        if self.session_logger:
            self.session_logger.info(f"=== Import Session Ended ===")
            self.session_logger.info(f"Success: {success}")
            if summary:
                self.session_logger.info(f"Summary: {summary}")
            
            # Close handlers
            for handler in self.session_logger.handlers[:]:
                handler.close()
                self.session_logger.removeHandler(handler)
        
        self.current_session_id = None
        self.session_log_file = None
        self.session_logger = None
    
    def get_session_log_content(self):
        """Get the content of the current session log."""
        if self.session_log_file and self.session_log_file.exists():
            try:
                with open(self.session_log_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                return f"Error reading log file: {e}"
        return "No active session log."


class ImportWorkerThread(QThread):
    """Worker thread for import operations with progress reporting."""
    
    # Signals
    progress_updated = pyqtSignal(int, int, str)  # current, total, message
    output_received = pyqtSignal(str)  # console output
    error_occurred = pyqtSignal(str)   # error message
    import_completed = pyqtSignal(bool, str)  # success, summary
    
    def __init__(self, config, source_id, script_path, files, logger):
        super().__init__()
        self.config = config
        self.source_id = source_id
        self.script_path = script_path
        self.files = files
        self.logger = logger
        self.should_stop = False
        self.current_process = None
    
    def stop(self):
        """Request the import to stop."""
        self.should_stop = True
        if self.current_process:
            try:
                self.logger.log_message("info", "Terminating running import process")
                self.current_process.terminate()
                # Give it a moment to terminate gracefully
                try:
                    self.current_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.logger.log_message("warning", "Process did not terminate gracefully, forcing kill")
                    self.current_process.kill()
            except Exception as e:
                self.logger.log_message("error", f"Error terminating process: {e}")
    
    def run(self):
        """Run the import process."""
        try:
            total_files = len(self.files)
            self.progress_updated.emit(0, total_files, "Starting import...")
            
            # Debug configuration information
            db_path = Path(self.config.get('database_path')).resolve()
            self.output_received.emit(f"Database path from config: {self.config.get('database_path')}")
            self.output_received.emit(f"Resolved database path: {db_path}")
            self.output_received.emit(f"Database exists: {db_path.exists()}")
            self.output_received.emit(f"Script path: {self.script_path}")
            self.output_received.emit(f"Source ID: {self.source_id}")
            
            # Start logging session
            session_id = self.logger.start_import_session(
                f"source_{self.source_id}", 
                self.files
            )
            
            success_count = 0
            error_count = 0
            
            for i, file_path in enumerate(self.files):
                if self.should_stop:
                    self.logger.log_message("warning", "Import stopped by user")
                    break
                
                file_name = Path(file_path).name
                self.progress_updated.emit(i, total_files, f"Processing {file_name}")
                self.output_received.emit(f"Processing file {i+1}/{total_files}: {file_name}")
                
                # Log file processing start
                self.logger.log_message("info", f"Processing file: {file_name}")
                
                # Run importer for this file
                success, output, error = self._run_single_import(file_path)
                
                if success:
                    success_count += 1
                    self.logger.log_message("info", f"Successfully processed: {file_name}")
                    self.output_received.emit(f"✓ {file_name}: Success")
                    
                    # Also log successful output for debugging
                    if output and output.strip():
                        self.logger.log_message("debug", f"Output from {file_name}:\n{output}")
                else:
                    error_count += 1
                    self.logger.log_message("error", f"Failed to process {file_name}: {error}")
                    self.output_received.emit(f"✗ {file_name}: FAILED")
                    
                    # Show more detailed error information
                    if error:
                        # Extract key error details for user display
                        error_lines = error.split('\n')
                        key_errors = []
                        for line in error_lines[:3]:  # Show first 3 error lines
                            if line.strip():
                                key_errors.append(f"    {line.strip()}")
                        
                        if key_errors:
                            self.output_received.emit(f"  Error details:")
                            for err_line in key_errors:
                                self.output_received.emit(err_line)
                    
                    # Log full error details
                    if output:
                        self.logger.log_message("error", f"Full output from failed {file_name}:\n{output}")
                    if error:
                        self.logger.log_message("error", f"Error details for {file_name}:\n{error}")
                
                # Emit any output from the importer
                if output:
                    self.output_received.emit(output)
                
                # Small delay to allow UI updates
                self.msleep(50)
            
            # Final progress update
            self.progress_updated.emit(total_files, total_files, "Import completed")
            
            # Summary with more detailed status
            total_files = len(self.files)
            if error_count == 0:
                summary = f"All {total_files} files processed successfully"
                status_msg = "✓ Import completed successfully!"
            else:
                summary = f"Processed {total_files} files: {success_count} successful, {error_count} failed"
                status_msg = f"✗ Import completed with {error_count} failures"
            
            self.output_received.emit(status_msg)
            self.logger.log_message("info", summary)
            
            # End logging session
            self.logger.end_import_session(error_count == 0, summary)
            
            # Signal completion - only report success if ALL files succeeded
            self.import_completed.emit(error_count == 0, summary)
            
        except Exception as e:
            error_msg = f"Critical import error: {e}"
            self.logger.log_message("error", error_msg)
            self.logger.end_import_session(False, error_msg)
            self.error_occurred.emit(error_msg)
    
    def _run_single_import(self, file_path):
        """Run the importer for a single file with real-time streaming and cancellation."""
        try:
            # Get database path and resolve it exactly like the original does
            db_path = Path(self.config.get('database_path')).resolve()
            
            # Check if this is the library ingestion importer
            if 'library_ingestion' in str(self.script_path):
                # For library ingestion, pass the file_path as a library root directory
                args = [
                    sys.executable,
                    str(self.script_path),
                    '--source_id', str(self.source_id),
                    '--db_path', str(db_path),
                    '--files', file_path
                ]
            else:
                # Standard importer behavior
                args = [
                    sys.executable,
                    str(self.script_path),
                    '--source_id', str(self.source_id),
                    '--db_path', str(db_path),
                    '--files', file_path
                ]
            
            # Log the exact command being executed
            command_str = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in args)
            self.logger.log_message("info", f"Executing command: {command_str}")
            
            # Emit command to console output using the worker's signal
            self.output_received.emit(f"Executing: {command_str}")
            
            # Use Popen for real-time streaming and cancellation support
            process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,  # Line buffered
                universal_newlines=True
            )
            
            # Store process reference for cancellation
            self.current_process = process
            
            # Stream output in real-time
            stdout_lines = []
            stderr_lines = []
            
            # Read output line by line with timeout
            import select
            import time
            
            timeout_seconds = 300  # 5 minute timeout per file
            start_time = time.time()
            
            # Set up Windows threading infrastructure once, outside the loop
            stdout_queue = None
            stderr_queue = None
            stdout_thread = None
            stderr_thread = None
            
            if os.name == 'nt' or not hasattr(select, 'select'):
                # Use threading for Windows and fallback
                import threading
                import queue
                
                def read_output(pipe, output_queue):
                    for line in iter(pipe.readline, ''):
                        output_queue.put(line.rstrip())
                    # Don't close the pipe here - let communicate() handle it
                
                stdout_queue = queue.Queue()
                stderr_queue = queue.Queue()
                
                stdout_thread = threading.Thread(target=read_output, args=(process.stdout, stdout_queue))
                stderr_thread = threading.Thread(target=read_output, args=(process.stderr, stderr_queue))
                
                stdout_thread.daemon = True
                stderr_thread.daemon = True
                stdout_thread.start()
                stderr_thread.start()
            
            while process.poll() is None:
                # Check for cancellation
                if self.should_stop:
                    self.logger.log_message("warning", "Import cancelled by user")
                    process.terminate()
                    try:
                        process.wait(timeout=5)  # Give it 5 seconds to terminate gracefully
                    except subprocess.TimeoutExpired:
                        process.kill()  # Force kill if it doesn't terminate
                    return False, '\n'.join(stdout_lines), "Import cancelled by user"
                
                # Check for timeout
                if time.time() - start_time > timeout_seconds:
                    self.logger.log_message("error", "Import timed out")
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    return False, '\n'.join(stdout_lines), "Import timed out (>5 minutes)"
                
                # Read available output
                try:
                    # Use select for non-blocking read (Unix/Linux only)
                    if os.name != 'nt' and hasattr(select, 'select'):
                        ready, _, _ = select.select([process.stdout, process.stderr], [], [], 0.1)
                        
                        if process.stdout in ready:
                            line = process.stdout.readline()
                            if line:
                                stdout_lines.append(line.rstrip())
                                self.output_received.emit(line.rstrip())
                                self.logger.log_message("debug", f"STDOUT: {line.rstrip()}")
                        
                        if process.stderr in ready:
                            line = process.stderr.readline()
                            if line:
                                stderr_lines.append(line.rstrip())
                                self.output_received.emit(f"STDERR: {line.rstrip()}")
                                self.logger.log_message("debug", f"STDERR: {line.rstrip()}")
                    else:
                        # Use the pre-created threads and queues for Windows
                        # Process available output from the queues
                        while not stdout_queue.empty():
                            line = stdout_queue.get_nowait()
                            stdout_lines.append(line)
                            self.output_received.emit(line)
                            self.logger.log_message("debug", f"STDOUT: {line}")
                        
                        while not stderr_queue.empty():
                            line = stderr_queue.get_nowait()
                            stderr_lines.append(line)
                            self.output_received.emit(f"STDERR: {line}")
                            self.logger.log_message("debug", f"STDERR: {line}")
                        
                        time.sleep(0.1)  # Small delay to prevent busy waiting
                        
                except Exception as e:
                    self.logger.log_message("error", f"Error reading process output: {e}")
                    break
            
            # Wait for process to complete
            return_code = process.wait()
            
            # Clear process reference
            self.current_process = None
            
            # Get any remaining output
            if os.name != 'nt' and hasattr(select, 'select'):
                # For Unix/Linux, use communicate() to get remaining output
                remaining_stdout, remaining_stderr = process.communicate()
                if remaining_stdout:
                    stdout_lines.extend(remaining_stdout.splitlines())
                    for line in remaining_stdout.splitlines():
                        self.output_received.emit(line)
                if remaining_stderr:
                    stderr_lines.extend(remaining_stderr.splitlines())
                    for line in remaining_stderr.splitlines():
                        self.output_received.emit(f"STDERR: {line}")
            else:
                # For Windows, drain any remaining output from the queues
                # Wait a moment for threads to finish reading
                if stdout_thread and stdout_thread.is_alive():
                    stdout_thread.join(timeout=1)
                if stderr_thread and stderr_thread.is_alive():
                    stderr_thread.join(timeout=1)
                
                # Drain any remaining output from queues
                while not stdout_queue.empty():
                    line = stdout_queue.get_nowait()
                    stdout_lines.append(line)
                    self.output_received.emit(line)
                
                while not stderr_queue.empty():
                    line = stderr_queue.get_nowait()
                    stderr_lines.append(line)
                    self.output_received.emit(f"STDERR: {line}")
                
                # Now it's safe to call communicate() to close pipes
                process.communicate()
            
            # Combine all output
            stdout_output = '\n'.join(stdout_lines)
            stderr_output = '\n'.join(stderr_lines)
            
            if return_code == 0:
                # Check the output for actual success indicators
                if any(phrase in stdout_output for phrase in [
                    "Critical error:",
                    "records failed",
                    "All changes for this file have been rolled back",
                    "table dat_entry_metadata has no column named",
                    "ERROR processing game"
                ]):
                    # Extract the actual error information
                    lines = stdout_output.split('\n')
                    error_lines = [line for line in lines if any(err in line for err in [
                        "Critical error:", "ERROR processing", "records failed"
                    ])]
                    
                    if error_lines:
                        error_summary = '\n'.join(error_lines[:5])  # Show first 5 errors
                        return False, stdout_output, f"Database operations failed:\n{error_summary}"
                    else:
                        return False, stdout_output, "Database operations failed (see output for details)"
                
                return True, stdout_output, None
            else:
                return False, stdout_output, stderr_output
                
        except Exception as e:
            return False, "", str(e)


class EnhancedImporterWidget(QWidget):
    """Enhanced importer widget with progress and logging."""
    
    def __init__(self, config_manager):
        super().__init__()
        self.config = config_manager
        # Get database path and resolve it exactly like the original does
        db_path = Path(config_manager.get('database_path')).resolve()
        self.db = DatabaseManager(db_path)
        self.logger = ImportLogger(config_manager)
        
        self.selected_files = []
        self.current_source_id = None
        self.current_importer_script = None
        self.import_worker = None
        
        self.init_ui()
        self.populate_sources_dropdown()
    
    def init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter)
        
        # Top panel: Import configuration
        config_panel = self._create_config_panel()
        splitter.addWidget(config_panel)
        
        # Bottom panel: Progress and output
        progress_panel = self._create_progress_panel()
        splitter.addWidget(progress_panel)
        
        # Set splitter proportions
        splitter.setSizes([300, 400])
    
    def _create_config_panel(self):
        """Create the import configuration panel."""
        panel = QGroupBox("Import Configuration")
        layout = QVBoxLayout(panel)
        
        # Source selection
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("Import Source:"))
        
        self.source_combo = QComboBox()
        self.source_combo.currentIndexChanged.connect(self.on_source_changed)
        source_layout.addWidget(self.source_combo, 1)
        
        manage_btn = QPushButton("Manage Sources...")
        manage_btn.clicked.connect(self.manage_sources)
        source_layout.addWidget(manage_btn)
        
        layout.addLayout(source_layout)
        
        # File selection
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("Files to Import:"))
        
        self.select_btn = QPushButton("Select Files...")
        self.select_btn.clicked.connect(self.select_files)
        file_layout.addWidget(self.select_btn)
        
        layout.addLayout(file_layout)
        
        # Selected files list
        self.files_list = QListWidget()
        self.files_list.setMaximumHeight(100)
        layout.addWidget(self.files_list)
        
        # Already imported files section
        imported_label = QLabel("Already Imported for this Source:")
        layout.addWidget(imported_label)
        
        self.imported_list = QListWidget()
        self.imported_list.setMaximumHeight(100)
        layout.addWidget(self.imported_list)
        
        # Import options
        options_layout = QHBoxLayout()
        
        self.stop_on_error_cb = QCheckBox("Stop on first error")
        self.stop_on_error_cb.setChecked(False)
        options_layout.addWidget(self.stop_on_error_cb)
        
        options_layout.addStretch()
        
        # Import button
        self.import_btn = QPushButton("Start Import")
        self.import_btn.clicked.connect(self.start_import)
        self.import_btn.setStyleSheet("font-size: 14px; padding: 8px;")
        options_layout.addWidget(self.import_btn)
        
        self.stop_btn = QPushButton("Stop Import")
        self.stop_btn.clicked.connect(self.stop_import)
        self.stop_btn.setEnabled(False)
        options_layout.addWidget(self.stop_btn)
        
        layout.addLayout(options_layout)
        
        return panel
    
    def _create_progress_panel(self):
        """Create the progress and output panel."""
        panel = QGroupBox("Import Progress & Output")
        layout = QVBoxLayout(panel)
        
        # Progress bar
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("Progress:"))
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("")
        progress_layout.addWidget(self.progress_label)
        
        layout.addLayout(progress_layout)
        
        # Tabbed output
        self.output_tabs = QTabWidget()
        
        # Console output tab
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setFont(self.console_output.font())  # Monospace
        self.output_tabs.addTab(self.console_output, "Console Output")
        
        # Log viewer tab
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.output_tabs.addTab(self.log_viewer, "Detailed Log")
        
        layout.addWidget(self.output_tabs)
        
        # Output controls
        controls_layout = QHBoxLayout()
        
        clear_btn = QPushButton("Clear Output")
        clear_btn.clicked.connect(self.clear_output)
        controls_layout.addWidget(clear_btn)
        
        save_log_btn = QPushButton("Save Log...")
        save_log_btn.clicked.connect(self.save_log)
        controls_layout.addWidget(save_log_btn)
        
        controls_layout.addStretch()
        
        # Auto-scroll checkbox
        self.auto_scroll_cb = QCheckBox("Auto-scroll")
        self.auto_scroll_cb.setChecked(True)
        controls_layout.addWidget(self.auto_scroll_cb)
        
        layout.addLayout(controls_layout)
        
        return panel
    
    def populate_sources_dropdown(self):
        """Populate the sources dropdown."""
        self.source_combo.clear()
        sources = self.db.get_metadata_sources()
        
        if not sources:
            self.source_combo.addItem("No sources configured. Please add one.", None)
        else:
            for source_row in sources:
                source_id, name, script_path = source_row[:3]
                self.source_combo.addItem(name, (source_id, script_path))
    
    def on_source_changed(self, index):
        """Handle source selection change."""
        data = self.source_combo.itemData(index)
        if data:
            self.current_source_id, self.current_importer_script = data
            self.update_imported_files_list()
            
            # Update button text based on importer type
            if 'library_ingestion' in str(self.current_importer_script):
                self.select_btn.setText("Select Library Directory...")
            else:
                self.select_btn.setText("Select Files...")
        else:
            self.current_source_id = None
            self.current_importer_script = None
            self.imported_list.clear()
            self.select_btn.setText("Select Files...")
    
    def update_imported_files_list(self):
        """Update the list of already imported files for the current source."""
        self.imported_list.clear()
        if self.current_source_id:
            files = self.db.get_imported_files_for_source(self.current_source_id)
            self.imported_list.addItems(files)
    
    def select_files(self):
        """Open file selection dialog."""
        # Check if this is the library ingestion importer
        if self.current_importer_script and 'library_ingestion' in str(self.current_importer_script):
            # For library ingestion, select directories
            directory = QFileDialog.getExistingDirectory(
                self, "Select Library Root Directory", ""
            )
            
            if directory:
                self.selected_files = [directory]
                self.files_list.clear()
                self.files_list.addItems([Path(directory).name])
        else:
            # Standard file selection for other importers
            file_filter = "All Files (*)"
            
            # Determine file filter based on source schema
            if self.current_source_id:
                sources = self.db.get_metadata_sources()
                for source_row in sources:
                    if source_row[0] == self.current_source_id and len(source_row) > 3 and source_row[3]:
                        schema_path = source_row[3].lower()
                        if schema_path.endswith('.json'):
                            file_filter = "JSON Files (*.json);;All Files (*)"
                        elif schema_path.endswith('.xsd'):
                            file_filter = "DAT Files (*.dat);;XML Files (*.xml);;All Files (*)"
                        break
            
            files, _ = QFileDialog.getOpenFileNames(
                self, "Select Source Data Files", "", file_filter
            )
            
            if files:
                self.selected_files = files
                self.files_list.clear()
                self.files_list.addItems([Path(f).name for f in files])
    
    def start_import(self):
        """Start the import process."""
        if not self.current_importer_script:
            QMessageBox.warning(self, "Warning", "Please select a valid import source.")
            return
        
        if not self.selected_files:
            QMessageBox.warning(self, "Warning", "Please select files to import.")
            return
        
        script_path = Path(self.current_importer_script)
        if not script_path.exists():
            QMessageBox.critical(
                self, "Error", 
                f"Importer script not found at:\n{script_path}"
            )
            return
        
        # Clear previous output
        self.clear_output()
        
        # Setup UI for import
        self.import_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(self.selected_files))
        self.progress_bar.setValue(0)
        
        # Create and start worker thread
        self.import_worker = ImportWorkerThread(
            self.config, 
            self.current_source_id,
            script_path,
            self.selected_files,
            self.logger
        )
        
        # Connect signals
        self.import_worker.progress_updated.connect(self.update_progress)
        self.import_worker.output_received.connect(self.add_console_output)
        self.import_worker.error_occurred.connect(self.handle_error)
        self.import_worker.import_completed.connect(self.import_finished)
        
        # Start the import
        self.import_worker.start()
        
        # Start log viewer update timer
        self.log_update_timer = QTimer()
        self.log_update_timer.timeout.connect(self.update_log_viewer)
        self.log_update_timer.start(1000)  # Update every second
    
    def stop_import(self):
        """Stop the current import."""
        if self.import_worker:
            self.import_worker.stop()
            self.add_console_output("Import stop requested...")
    
    def update_progress(self, current, total, message):
        """Update the progress bar and message."""
        self.progress_bar.setValue(current)
        self.progress_label.setText(message)
    
    def add_console_output(self, text):
        """Add text to the console output."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.console_output.append(f"[{timestamp}] {text}")
        
        if self.auto_scroll_cb.isChecked():
            # Scroll to bottom
            scrollbar = self.console_output.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def update_log_viewer(self):
        """Update the log viewer with current session log."""
        log_content = self.logger.get_session_log_content()
        if log_content != self.log_viewer.toPlainText():
            self.log_viewer.setPlainText(log_content)
            
            if self.auto_scroll_cb.isChecked():
                scrollbar = self.log_viewer.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
    
    def handle_error(self, error_msg):
        """Handle import errors."""
        self.add_console_output(f"ERROR: {error_msg}")
        QMessageBox.critical(self, "Import Error", f"Import failed:\n{error_msg}")
    
    def import_finished(self, success, summary):
        """Handle import completion."""
        # Stop the log update timer
        if hasattr(self, 'log_update_timer'):
            self.log_update_timer.stop()
        
        # Update final log content
        self.update_log_viewer()
        
        # Reset UI
        self.import_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        
        # Show completion message
        if success:
            self.add_console_output(f"✓ Import completed successfully!")
            self.add_console_output(f"Summary: {summary}")
            QMessageBox.information(
                self, "Import Complete", 
                f"Import completed successfully!\n\n{summary}"
            )
        else:
            self.add_console_output(f"✗ Import completed with errors.")
            self.add_console_output(f"Summary: {summary}")
            
            # Parse the summary to get failure count
            if "failed" in summary.lower():
                try:
                    parts = summary.split(", ")
                    failed_part = [p for p in parts if "failed" in p][0]
                    failed_count = failed_part.split()[0]
                    message = (
                        f"Import completed with {failed_count} file(s) failing to import properly.\n\n"
                        f"{summary}\n\n"
                        "Common causes:\n"
                        "• Database schema issues (run Tools → Database → Setup Matching System)\n"
                        "• Corrupted DAT files\n"
                        "• Permission issues\n\n"
                        "Check the detailed log and console output for specific error details."
                    )
                except:
                    message = f"Import completed with errors:\n\n{summary}\n\nCheck the detailed log for more information."
            else:
                message = f"Import completed with errors:\n\n{summary}\n\nCheck the detailed log for more information."
            
            QMessageBox.warning(self, "Import Issues", message)
        
        # Clear worker reference
        self.import_worker = None
        
        # Refresh the imported files list
        self.update_imported_files_list()
    
    def clear_output(self):
        """Clear all output displays."""
        self.console_output.clear()
        self.log_viewer.clear()
    
    def save_log(self):
        """Save the current log to a file."""
        if not self.logger.session_log_file:
            QMessageBox.information(
                self, "No Log", 
                "No active import session to save."
            )
            return
        
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Import Log", 
            f"import_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            "Log Files (*.log);;Text Files (*.txt);;All Files (*)"
        )
        
        if save_path:
            try:
                import shutil
                shutil.copy2(self.logger.session_log_file, save_path)
                QMessageBox.information(
                    self, "Log Saved", 
                    f"Log saved to:\n{save_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Save Error", 
                    f"Failed to save log:\n{e}"
                )
    
    def manage_sources(self):
        """Open source management dialog."""
        # Import here to avoid circular imports
        from data_importer_gui import SourceManagerDialog
        
        sources = self.db.get_metadata_sources()
        source_names = [s[1] for s in sources]
        
        # Create the full source management interface (copied from original data_importer_gui.py)
        menu = QDialog(self)
        menu_layout = QVBoxLayout()
        menu.setWindowTitle("Manage Sources")
        menu.setMinimumSize(500, 400)
        
        add_btn = QPushButton("Add New Source...")
        add_btn.clicked.connect(lambda: self.open_source_dialog(menu))
        
        edit_btn = QPushButton("Edit Selected...")
        delete_btn = QPushButton("Delete Selected")
        
        list_widget = QListWidget()
        list_widget.addItems(source_names)
        
        edit_btn.clicked.connect(lambda: self.open_source_dialog(menu, list_widget.currentRow(), sources))
        delete_btn.clicked.connect(lambda: self.delete_source(menu, list_widget.currentRow(), sources))
        
        menu_layout.addWidget(add_btn)
        menu_layout.addWidget(list_widget)
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        menu_layout.addLayout(btn_layout)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(menu.accept)
        menu_layout.addWidget(close_btn)
        
        menu.setLayout(menu_layout)
        menu.exec_()
        
        # Refresh the sources dropdown after management
        self.populate_sources_dropdown()
    
    def open_source_dialog(self, parent_menu, index=-1, sources=None):
        """Open source add/edit dialog."""
        from data_importer_gui import SourceManagerDialog
        
        source_data = sources[index] if index != -1 and sources else None
        dialog = SourceManagerDialog(self.db, self.config, source_data, self)
        if dialog.exec_():
            parent_menu.close()
    
    def delete_source(self, parent_menu, index, sources):
        """Delete a source."""
        if index == -1:
            QMessageBox.information(self, "Info", "Please select a source to delete.")
            return

        source_row = sources[index]
        source_id, name = source_row[0], source_row[1]
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete the source '{name}'?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if not self.db.delete_metadata_source(source_id):
                QMessageBox.critical(
                    self, "Error", 
                    f"Could not delete '{name}'. It is currently associated with existing import logs."
                )
            else:
                parent_menu.close()


# For compatibility with the main application
class ImporterApp(EnhancedImporterWidget):
    """Compatibility wrapper for the main application."""
    
    def __init__(self, config_manager=None):
        if not config_manager:
            from rom_curator_main import ConfigManager
            config_manager = ConfigManager()
        
        super().__init__(config_manager)
        self.setWindowTitle('ROM Curator - Enhanced Data Importer')


def main():
    """Main entry point for standalone testing."""
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    
    # Load configuration
    from rom_curator_main import ConfigManager
    config = ConfigManager()
    
    window = ImporterApp(config)
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
