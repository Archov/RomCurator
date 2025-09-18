"""
ROM Curator - Main Application Entry Point

This is the single entry point for all ROM Curator functionality.
Provides a unified interface with menu options for all tools and workflows.
"""

import sys
import json
import logging
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QMenuBar, QStatusBar, QAction, QMessageBox, QLabel, QPushButton,
    QGroupBox, QTextEdit, QSplashScreen, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont, QIcon
import qdarkstyle

# Import our modules
from enhanced_importer_gui import ImporterApp
from curation_gui import CurationMainWindow
from platform_linking_gui import PlatformLinkingDialog
from extension_registry_gui import ExtensionRegistryDialog

# Import enhanced logging system (Work Item 2)
from enhanced_logging import EnhancedLoggingManager

# Import resilient worker components (Work Item 2)
from resilient_worker import ResilientWorkerThread


class ConfigManager:
    """Centralized configuration management."""
    
    def __init__(self, config_file='config.json'):
        self.config_file = Path(config_file)
        self.config = self.load_config()
        
    def load_config(self):
        """Load configuration from JSON file."""
        if not self.config_file.exists():
            # Create default config
            default_config = {
                "database_path": "./database/RomCurator.db",
                "importer_scripts_directory": "./scripts/seeders/",
                "log_directory": "./logs/",
                "log_level": "INFO",
                "auto_create_directories": True,
                "progress_update_interval": 100,
                "gui_settings": {
                    "window_width": 1200,
                    "window_height": 800,
                    "theme": "dark"
                },
                "ingestion_settings": {
                    "library_roots": [],
                    "batch_size": 100,
                    "enable_validation": True,
                    "enable_archive_expansion": True,
                    "hash_algorithms": ["sha1", "crc32", "md5", "sha256"],
                    "file_extensions": {
                        "rom": [".rom", ".bin", ".smd", ".sfc", ".nes", ".gb", ".gba", ".nds", ".iso", ".img"],
                        "archive": [".zip", ".7z", ".rar", ".tar", ".gz"]
                    },
                    "max_file_size_mb": 1024,
                    "exclude_patterns": ["*.tmp", "*.temp", "*.bak", "*.backup"],
                    "enable_platform_detection": True,
                    "enable_metadata_extraction": True
                }
            }
            
            try:
                with open(self.config_file, 'w') as f:
                    json.dump(default_config, f, indent=4)
                return default_config
            except IOError as e:
                raise SystemExit(f"FATAL: Could not create config file: {e}")
        
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            raise SystemExit(f"FATAL: Could not read config file: {e}")
    
    def get(self, key, default=None):
        """Get configuration value with optional default."""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key, value):
        """Set configuration value."""
        keys = key.split('.')
        config_ref = self.config
        
        for k in keys[:-1]:
            if k not in config_ref:
                config_ref[k] = {}
            config_ref = config_ref[k]
        
        config_ref[keys[-1]] = value
    
    def save(self):
        """Save current configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except IOError as e:
            logging.error(f"Could not save config file: {e}")
    
    def ensure_directories(self):
        """Create required directories if they don't exist."""
        if self.get('auto_create_directories', True):
            dirs_to_create = [
                Path(self.get('database_path')).parent,
                Path(self.get('log_directory')),
                Path(self.get('importer_scripts_directory'))
            ]
            
            for directory in dirs_to_create:
                directory.mkdir(parents=True, exist_ok=True)


class LoggingManager:
    """Enhanced centralized logging management using Work Item 2 framework."""

    def __init__(self, config_manager):
        self.config = config_manager
        self.enhanced_logging = EnhancedLoggingManager(config_manager)

        # Keep backward compatibility by exposing loggers
        self.root_logger = self.enhanced_logging.root_logger
        self.ingestion_logger = self.enhanced_logging.ingestion_logger
        self.archive_logger = self.enhanced_logging.archive_logger
        self.organizer_logger = self.enhanced_logging.organizer_logger

    def get_logger(self, name: str = None):
        """Get a logger by name (backward compatibility)."""
        if name:
            return self.enhanced_logging.get_logger(name)
        return self.root_logger

    def log_performance_metric(self, operation: str, duration: float, item_count: int = 1):
        """Log performance metrics."""
        return self.enhanced_logging.log_performance_metric(operation, duration, item_count)

    def get_performance_summary(self):
        """Get performance summary."""
        return self.enhanced_logging.get_performance_summary()


class WelcomeWidget(QWidget):
    """Welcome screen widget for the main application."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """Initialize the welcome screen UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("ROM Curator")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Transform chaos into control")
        subtitle_font = QFont()
        subtitle_font.setPointSize(14)
        subtitle_font.setItalic(True)
        subtitle.setFont(subtitle_font)
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(30)
        
        # Description
        description = QTextEdit()
        description.setReadOnly(True)
        description.setMaximumHeight(200)
        description.setHtml("""
        <p><strong>ROM Curator</strong> helps you organize and manage your game library by:</p>
        <ul>
        <li><strong>Importing metadata</strong> from sources like MobyGames for rich game information</li>
        <li><strong>Processing DAT files</strong> from No-Intro, TOSEC, and other preservation groups</li>
        <li><strong>Intelligent matching</strong> between metadata and ROMs for verified collections</li>
        <li><strong>1G1R curation</strong> for clean, organized libraries</li>
        <li><strong>Device-specific exports</strong> for MiSTer, EverDrive, RetroArch, and more</li>
        </ul>
        <p>Use the <strong>File menu</strong> to access import tools, curation interfaces, and other features.</p>
        """)
        layout.addWidget(description)
        
        layout.addStretch()


class RomCuratorMainWindow(QMainWindow):
    """Main application window with unified interface."""
    
    def __init__(self):
        super().__init__()
        
        # Initialize configuration and logging
        self.config = ConfigManager()
        self.config.ensure_directories()
        self.logging_manager = LoggingManager(self.config)
        
        # Apply dark theme to main window
        self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        
        # Initialize UI
        self.init_ui()
        
        # Check database status
        self.check_database_status()
        
        logging.info("ROM Curator main application started")
    
    def init_ui(self):
        """Initialize the main UI."""
        # Window settings
        width = self.config.get('gui_settings.window_width', 1200)
        height = self.config.get('gui_settings.window_height', 800)
        self.setWindowTitle('ROM Curator - Game Library Management')
        self.setGeometry(100, 100, width, height)
        
        # Central widget
        self.welcome_widget = WelcomeWidget()
        self.setCentralWidget(self.welcome_widget)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Add progress bar to status bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        self.status_bar.showMessage("Ready")
    
    def create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu('&File')
        
        # Import submenu
        import_menu = file_menu.addMenu('&Import Data')

        import_action = QAction('&Metadata && DAT Importer...', self)
        import_action.setStatusTip('Import game metadata and DAT files')
        import_action.triggered.connect(self.open_data_importer)
        import_menu.addAction(import_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('E&xit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.setStatusTip('Exit application')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools Menu
        tools_menu = menubar.addMenu('&Tools')

        # Library submenu (Work Item 2 - Resilient Ingestion)
        library_menu = tools_menu.addMenu('&Library')

        ingestion_action = QAction('&Scan && Ingest Files...', self)
        ingestion_action.setStatusTip('Scan library directories and ingest files with resilience features')
        ingestion_action.triggered.connect(self.open_resilient_ingestion)
        library_menu.addAction(ingestion_action)

        tools_menu.addSeparator()

        # Curation submenu
        curation_menu = tools_menu.addMenu('&Curation')

        curation_action = QAction('&DAT-Metadata Matching...', self)
        curation_action.setStatusTip('Review and curate metadata-DAT matches')
        curation_action.triggered.connect(self.open_curation_interface)
        curation_menu.addAction(curation_action)

        tools_menu.addSeparator()

        # Database tools
        db_menu = tools_menu.addMenu('&Database')

        platform_linking_action = QAction('&Platform Linking...', self)
        platform_linking_action.setStatusTip('Manage platform links for accurate matching')
        platform_linking_action.triggered.connect(self.open_platform_linking)
        db_menu.addAction(platform_linking_action)
        
        extension_registry_action = QAction('&Extension Registry...', self)
        extension_registry_action.setStatusTip('Manage file extensions and platform mappings')
        extension_registry_action.triggered.connect(self.open_extension_registry)
        db_menu.addAction(extension_registry_action)
        
        # View Menu
        view_menu = menubar.addMenu('&View')

        logs_action = QAction('&View Logs...', self)
        logs_action.setStatusTip('View application logs')
        logs_action.triggered.connect(self.view_logs)
        view_menu.addAction(logs_action)

        # Enhanced logging options (Work Item 2)
        logs_menu = view_menu.addMenu('&Logs')

        ingestion_logs_action = QAction('&Ingestion Logs...', self)
        ingestion_logs_action.setStatusTip('View ingestion-specific logs with filtering')
        ingestion_logs_action.triggered.connect(self.view_ingestion_logs)
        logs_menu.addAction(ingestion_logs_action)

        archive_logs_action = QAction('&Archive Logs...', self)
        archive_logs_action.setStatusTip('View archive processing logs')
        archive_logs_action.triggered.connect(self.view_archive_logs)
        logs_menu.addAction(archive_logs_action)

        organizer_logs_action = QAction('&Organizer Logs...', self)
        organizer_logs_action.setStatusTip('View file organization logs')
        organizer_logs_action.triggered.connect(self.view_organizer_logs)
        logs_menu.addAction(organizer_logs_action)

        performance_logs_action = QAction('&Performance Metrics...', self)
        performance_logs_action.setStatusTip('View performance metrics and statistics')
        performance_logs_action.triggered.connect(self.view_performance_metrics)
        logs_menu.addAction(performance_logs_action)

        view_menu.addSeparator()

        checkpoint_recovery_action = QAction('&Checkpoint Recovery...', self)
        checkpoint_recovery_action.setStatusTip('Manage and recover from processing checkpoints')
        checkpoint_recovery_action.triggered.connect(self.manage_checkpoints)
        view_menu.addAction(checkpoint_recovery_action)
        
        # Help Menu
        help_menu = menubar.addMenu('&Help')
        
        guide_action = QAction('&Matching Guide...', self)
        guide_action.setStatusTip('Open metadata-DAT matching guide')
        guide_action.triggered.connect(self.show_matching_guide)
        help_menu.addAction(guide_action)
        
        help_menu.addSeparator()
        
        about_action = QAction('&About...', self)
        about_action.setStatusTip('About ROM Curator')
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def check_database_status(self):
        """Check if the database exists and is properly configured."""
        db_path = Path(self.config.get('database_path'))
        
        if not db_path.exists():
            self.status_bar.showMessage(f"Database not found: {db_path}")
            QMessageBox.warning(
                self, "Database Not Found",
                f"Database file not found at:\n{db_path}\n\n"
                "Please create the database using the schema creation script."
            )
        else:
            # TODO: Add actual database schema checking
            self.status_bar.showMessage(f"Database ready: {db_path}")
    
    def open_data_importer(self):
        """Open the data importer interface."""
        try:
            # Create importer window with our configuration
            self.importer_window = ImporterApp(self.config)
            self.importer_window.show()
            
            # Connect progress signals if available
            if hasattr(self.importer_window, 'progress_signal'):
                self.importer_window.progress_signal.connect(self.update_progress)
            
            logging.info("Data importer opened")
            
        except Exception as e:
            logging.error(f"Failed to open data importer: {e}")
            QMessageBox.critical(
                self, "Error",
                f"Failed to open data importer:\n{e}"
            )
    
    def open_curation_interface(self):
        """Open the curation interface."""
        try:
            db_path = self.config.get('database_path')
            
            # Check if database exists
            if not Path(db_path).exists():
                QMessageBox.warning(
                    self, "Database Required",
                    "Please import some data first using File → Import Data."
                )
                return
            
            self.curation_window = CurationMainWindow(db_path, self.config)
            self.curation_window.show()
            
            logging.info("Curation interface opened")
            
        except Exception as e:
            logging.error(f"Failed to open curation interface: {e}")
            QMessageBox.critical(
                self, "Error",
                f"Failed to open curation interface:\n{e}"
            )
    
    def open_platform_linking(self):
        """Open the platform linking dialog."""
        try:
            db_path = self.config.get('database_path')
            
            # Check if database exists
            if not Path(db_path).exists():
                QMessageBox.warning(
                    self, "Database Required",
                    "Please import some data first using File → Import Data."
                )
                return
            
            # Check if platform_links table exists (v1.8+)
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='platform_links'
            """)
            
            if not cursor.fetchone():
                QMessageBox.warning(
                    self, "Schema Update Required",
                    "Platform linking requires database schema v1.8 or later.\n"
                    "Please ensure your database is up to date."
                )
                conn.close()
                return
            
            conn.close()
            
            self.platform_linking_dialog = PlatformLinkingDialog(db_path, self)
            self.platform_linking_dialog.show()
            
            logging.info("Platform linking dialog opened")
            
        except Exception as e:
            logging.error(f"Failed to open platform linking dialog: {e}")
            QMessageBox.critical(
                self, "Error",
                f"Failed to open platform linking dialog:\n{e}"
            )
    
    def open_extension_registry(self):
        """Open the extension registry dialog."""
        try:
            db_path = self.config.get('database_path')
            
            # Check if database exists
            if not Path(db_path).exists():
                QMessageBox.warning(
                    self, "Database Required",
                    "Please import some data first using File → Import Data."
                )
                return
            
            # Check if extension registry tables exist (v1.10+)
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='file_type_category'
            """)
            
            if not cursor.fetchone():
                QMessageBox.warning(
                    self, "Schema Update Required",
                    "Extension registry requires database schema v1.10 or later.\n"
                    "Please ensure your database is up to date."
                )
                conn.close()
                return
            
            conn.close()
            
            self.extension_registry_dialog = ExtensionRegistryDialog(db_path, self)
            self.extension_registry_dialog.show()
            
            logging.info("Extension registry dialog opened")
            
        except Exception as e:
            logging.error(f"Failed to open extension registry dialog: {e}")
            QMessageBox.critical(
                self, "Error",
                f"Failed to open extension registry dialog:\n{e}"
            )
    
    def _setup_complete(self):
        """Handle setup completion."""
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("Matching system setup complete")
        
        QMessageBox.information(
            self, "Setup Complete",
            "Matching system has been set up successfully!\n\n"
            "You can now import data and use the curation interface."
        )
    
    
    def view_logs(self):
        """Open log viewer window."""
        try:
            from log_viewer import LogViewerWindow
            self.log_viewer = LogViewerWindow(self.config)
            self.log_viewer.show()

        except Exception as e:
            # Simple fallback log viewer
            log_file = Path(self.config.get('log_directory')) / 'rom_curator.log'
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    log_dialog = QMessageBox(self)
                    log_dialog.setWindowTitle("Application Logs")
                    log_dialog.setText("Recent log entries:")
                    log_dialog.setDetailedText(content)
                    log_dialog.exec_()
                except Exception as read_error:
                    QMessageBox.warning(self, "Error", f"Could not read log file:\n{read_error}")
            else:
                QMessageBox.information(self, "Logs", "No log file found.")

    # Work Item 2: Enhanced Logging UI Methods
    def view_ingestion_logs(self):
        """View ingestion-specific logs with filtering."""
        self._view_enhanced_logs('ingestion', 'Ingestion Logs')

    def view_archive_logs(self):
        """View archive processing logs."""
        self._view_enhanced_logs('ingestion.archive', 'Archive Processing Logs')

    def view_organizer_logs(self):
        """View file organization logs."""
        self._view_enhanced_logs('ingestion.organizer', 'File Organization Logs')

    def _view_enhanced_logs(self, logger_name, title):
        """View enhanced logs with filtering capabilities."""
        try:
            log_dir = Path(self.config.get('log_directory'))

            # Map logger names to log files
            log_file_map = {
                'ingestion': 'ingestion.log',
                'ingestion.archive': 'archive.log',
                'ingestion.organizer': 'organizer.log'
            }

            log_file = log_dir / log_file_map.get(logger_name, 'rom_curator.log')

            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Create enhanced log viewer dialog
                from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QComboBox, QLabel, QCheckBox
                from PyQt5.QtCore import Qt

                dialog = QDialog(self)
                dialog.setWindowTitle(title)
                dialog.setGeometry(200, 200, 900, 600)

                layout = QVBoxLayout(dialog)

                # Filter controls
                filter_layout = QHBoxLayout()

                filter_layout.addWidget(QLabel("Filter:"))
                self.filter_combo = QComboBox()
                self.filter_combo.addItems(['All', 'INFO', 'WARNING', 'ERROR', 'DEBUG'])
                filter_layout.addWidget(self.filter_combo)

                self.show_context_check = QCheckBox("Show Context")
                self.show_context_check.setChecked(True)
                filter_layout.addWidget(self.show_context_check)

                refresh_btn = QPushButton("Refresh")
                refresh_btn.clicked.connect(lambda: self._refresh_log_view(self.log_view, log_file, dialog))
                filter_layout.addWidget(refresh_btn)

                filter_layout.addStretch()
                layout.addLayout(filter_layout)

                # Log display
                self.log_view = QTextEdit()
                self.log_view.setReadOnly(True)
                self.log_view.setFontFamily("Consolas")
                self.log_view.setFontPointSize(9)
                layout.addWidget(self.log_view)

                # Button row
                button_layout = QHBoxLayout()
                button_layout.addStretch()

                close_btn = QPushButton("Close")
                close_btn.clicked.connect(dialog.accept)
                button_layout.addWidget(close_btn)

                layout.addLayout(button_layout)

                # Load initial content
                self._refresh_log_view(self.log_view, log_file, dialog)

                dialog.exec_()
            else:
                QMessageBox.information(self, title, f"No {logger_name} log file found.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open log viewer:\n{e}")

    def _refresh_log_view(self, log_view, log_file, dialog):
        """Refresh the log view with current content and filters."""
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Apply filters
            filter_level = self.filter_combo.currentText()
            show_context = self.show_context_check.isChecked()

            lines = content.split('\n')
            filtered_lines = []

            for line in lines:
                if not line.strip():
                    continue

                # Apply level filter
                if filter_level != 'All':
                    if f'[{filter_level}]' not in line:
                        continue

                # Apply context filter
                if not show_context and '|' in line:
                    # Remove context part (everything after |)
                    line = line.split('|')[0].strip()

                filtered_lines.append(line)

            log_view.setText('\n'.join(filtered_lines[-1000:]))  # Show last 1000 lines

        except Exception as e:
            log_view.setText(f"Error loading log file: {e}")

    def view_performance_metrics(self):
        """View performance metrics and statistics."""
        try:
            # Get performance summary from logging manager
            summary = self.logging_manager.get_performance_summary()

            if not summary:
                QMessageBox.information(self, "Performance Metrics",
                                      "No performance metrics available.\n\n"
                                      "Run some ingestion operations to collect metrics.")
                return

            # Create performance dialog
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout

            dialog = QDialog(self)
            dialog.setWindowTitle("Performance Metrics")
            dialog.setGeometry(200, 200, 700, 500)

            layout = QVBoxLayout(dialog)

            metrics_text = QTextEdit()
            metrics_text.setReadOnly(True)
            metrics_text.setFontFamily("Consolas")
            metrics_text.setFontPointSize(9)

            # Format performance data
            content = "📊 PERFORMANCE METRICS SUMMARY\n"
            content += "=" * 50 + "\n\n"

            for operation, stats in summary.items():
                content += f"🔧 Operation: {operation}\n"
                content += f"   Executions: {stats['count']}\n"
                content += f"   Avg Duration: {stats['avg_duration']:.2f}s\n"
                content += f"   Min Duration: {stats['min_duration']:.2f}s\n"
                content += f"   Max Duration: {stats['max_duration']:.2f}s\n"
                content += f"   Avg Rate: {stats['avg_rate']:.1f} items/sec\n"
                content += f"   Total Items: {stats['total_items']}\n"
                content += "\n"

            metrics_text.setText(content)
            layout.addWidget(metrics_text)

            # Button row
            button_layout = QHBoxLayout()
            button_layout.addStretch()

            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.accept)
            button_layout.addWidget(close_btn)

            layout.addLayout(button_layout)

            dialog.exec_()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load performance metrics:\n{e}")

    def manage_checkpoints(self):
        """Manage and recover from processing checkpoints."""
        try:
            from pathlib import Path
            import json
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QListWidget, QPushButton, QHBoxLayout, QLabel, QMessageBox

            log_dir = Path(self.config.get('log_directory'))
            checkpoint_files = list(log_dir.glob('*_checkpoint.json'))

            if not checkpoint_files:
                QMessageBox.information(self, "Checkpoint Recovery",
                                      "No checkpoint files found.\n\n"
                                      "Checkpoint files are created during long-running operations.")
                return

            # Create checkpoint management dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Checkpoint Recovery")
            dialog.setGeometry(200, 200, 600, 400)

            layout = QVBoxLayout(dialog)

            layout.addWidget(QLabel("Available Checkpoints:"))

            checkpoint_list = QListWidget()

            for cp_file in checkpoint_files:
                try:
                    with open(cp_file, 'r', encoding='utf-8') as f:
                        cp_data = json.load(f)

                    operation = cp_data.get('operation_name', 'Unknown')
                    index = cp_data.get('current_index', 0)
                    total = cp_data.get('total_items', '?')
                    timestamp = cp_data.get('timestamp', 'Unknown')

                    display_text = f"{operation} - {index}/{total} items - {timestamp[:19]}"
                    checkpoint_list.addItem(display_text)

                    # Store file path in item data
                    checkpoint_list.item(checkpoint_list.count() - 1).setData(Qt.UserRole, str(cp_file))

                except Exception as e:
                    checkpoint_list.addItem(f"Invalid checkpoint: {cp_file.name} (Error: {e})")

            layout.addWidget(checkpoint_list)

            # Button row
            button_layout = QHBoxLayout()

            delete_btn = QPushButton("Delete Selected")
            delete_btn.clicked.connect(lambda: self._delete_checkpoint(checkpoint_list, dialog))
            button_layout.addWidget(delete_btn)

            delete_all_btn = QPushButton("Delete All")
            delete_all_btn.clicked.connect(lambda: self._delete_all_checkpoints(checkpoint_list, dialog))
            button_layout.addWidget(delete_all_btn)

            button_layout.addStretch()

            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.accept)
            button_layout.addWidget(close_btn)

            layout.addLayout(button_layout)

            dialog.exec_()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to manage checkpoints:\n{e}")

    def _delete_checkpoint(self, checkpoint_list, dialog):
        """Delete selected checkpoint."""
        current_item = checkpoint_list.currentItem()
        if not current_item:
            QMessageBox.warning(dialog, "Warning", "Please select a checkpoint to delete.")
            return

        cp_file = current_item.data(Qt.UserRole)
        if cp_file:
            try:
                Path(cp_file).unlink()
                checkpoint_list.takeItem(checkpoint_list.currentRow())
                QMessageBox.information(dialog, "Success", "Checkpoint deleted successfully.")
            except Exception as e:
                QMessageBox.critical(dialog, "Error", f"Failed to delete checkpoint:\n{e}")

    def _delete_all_checkpoints(self, checkpoint_list, dialog):
        """Delete all checkpoints."""
        reply = QMessageBox.question(dialog, "Confirm",
                                   "Are you sure you want to delete all checkpoints?\n\n"
                                   "This action cannot be undone.",
                                   QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            deleted = 0
            errors = 0

            for i in range(checkpoint_list.count()):
                item = checkpoint_list.item(i)
                cp_file = item.data(Qt.UserRole)
                if cp_file:
                    try:
                        Path(cp_file).unlink()
                        deleted += 1
                    except Exception:
                        errors += 1

            checkpoint_list.clear()

            if errors > 0:
                QMessageBox.warning(dialog, "Partial Success",
                                  f"Deleted {deleted} checkpoints, {errors} failed.")
            else:
                QMessageBox.information(dialog, "Success",
                                      f"All {deleted} checkpoints deleted successfully.")

    def open_resilient_ingestion(self):
        """Open the library file ingestion interface."""
        try:
            # Use the enhanced importer with library ingestion support
            from enhanced_importer_gui import ImporterApp
            
            # Create the enhanced importer window
            self.ingestion_dialog = ImporterApp(self.config)
            self.ingestion_dialog.show()
            
            # Set the window title to indicate this is for library ingestion
            self.ingestion_dialog.setWindowTitle('ROM Curator - Library File Ingestion')
            
            # Connect progress signals if available
            if hasattr(self.ingestion_dialog, 'progress_signal'):
                self.ingestion_dialog.progress_signal.connect(self.update_progress)
            
            self.logging_manager.root_logger.info("Library file ingestion dialog opened")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open library ingestion:\n{e}")
    
    def show_matching_guide(self):
        """Show the matching guide."""
        guide_file = Path('METADATA_DAT_MATCHING_GUIDE.md')
        if guide_file.exists():
            try:
                with open(guide_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                guide_dialog = QMessageBox(self)
                guide_dialog.setWindowTitle("Metadata-DAT Matching Guide")
                guide_dialog.setText("Matching System Guide")
                guide_dialog.setDetailedText(content)
                guide_dialog.exec_()
                
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not read guide file:\n{e}")
        else:
            QMessageBox.information(
                self, "Guide",
                "Matching guide not found. Please check the documentation."
            )
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self, "About ROM Curator",
            """
            <h3>ROM Curator</h3>
            <p><strong>Transform chaos into control</strong></p>
            <p>A comprehensive tool for organizing and managing game libraries using 
            validated metadata and DAT files from preservation groups.</p>
            <p><strong>Features:</strong></p>
            <ul>
            <li>Metadata import from MobyGames and other sources</li>
            <li>DAT file processing (No-Intro, TOSEC, GoodTools)</li>
            <li>Intelligent metadata-ROM matching</li>
            <li>1G1R library curation</li>
            <li>Device-specific exports</li>
            </ul>
            <p>Version: 1.7 (Enhanced Matching)</p>
            """
        )
    
    def update_progress(self, current, total, message=""):
        """Update the global progress bar."""
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
            self.progress_bar.setVisible(True)
        else:
            self.progress_bar.setRange(0, 0)  # Indeterminate
            self.progress_bar.setVisible(True)
        
        if message:
            self.status_bar.showMessage(message)
    
    def hide_progress(self):
        """Hide the progress bar."""
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("Ready")
    
    def closeEvent(self, event):
        """Handle application close."""
        # Save configuration
        self.config.save()
        
        # Log shutdown
        logging.info("ROM Curator application closing")
        
        # Accept the close event
        event.accept()


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("ROM Curator")
    app.setApplicationVersion("1.7")
    app.setOrganizationName("ROM Curator Project")
    
    # Apply dark theme
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    
    # Create and show main window
    main_window = RomCuratorMainWindow()
    main_window.show()
    
    # Run application
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
