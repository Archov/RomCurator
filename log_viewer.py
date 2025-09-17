"""
Log Viewer Window for ROM Curator

Provides a dedicated interface for viewing application logs.
"""

import sys
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit,
    QComboBox, QLabel, QMessageBox, QFileDialog, QCheckBox
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont


class LogViewerWindow(QWidget):
    """Window for viewing application logs."""
    
    def __init__(self, config_manager):
        super().__init__()
        self.config = config_manager
        self.log_dir = Path(config_manager.get('log_directory'))
        
        self.init_ui()
        self.populate_log_files()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_current_log)
        
    def init_ui(self):
        """Initialize the UI."""
        self.setWindowTitle('ROM Curator - Log Viewer')
        self.setGeometry(200, 200, 900, 600)
        
        layout = QVBoxLayout(self)
        
        # Top controls
        controls_layout = QHBoxLayout()
        
        controls_layout.addWidget(QLabel("Log File:"))
        
        self.log_combo = QComboBox()
        self.log_combo.currentTextChanged.connect(self.load_selected_log)
        controls_layout.addWidget(self.log_combo, 1)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.populate_log_files)
        controls_layout.addWidget(refresh_btn)
        
        self.auto_refresh_cb = QCheckBox("Auto-refresh (5s)")
        self.auto_refresh_cb.toggled.connect(self.toggle_auto_refresh)
        controls_layout.addWidget(self.auto_refresh_cb)
        
        layout.addLayout(controls_layout)
        
        # Log content display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        
        # Use monospace font for better log readability
        font = QFont("Consolas, Monaco, monospace")
        font.setPointSize(9)
        self.log_display.setFont(font)
        
        layout.addWidget(self.log_display)
        
        # Bottom controls
        bottom_layout = QHBoxLayout()
        
        clear_btn = QPushButton("Clear Display")
        clear_btn.clicked.connect(self.clear_display)
        bottom_layout.addWidget(clear_btn)
        
        save_btn = QPushButton("Save As...")
        save_btn.clicked.connect(self.save_log)
        bottom_layout.addWidget(save_btn)
        
        bottom_layout.addStretch()
        
        self.auto_scroll_cb = QCheckBox("Auto-scroll")
        self.auto_scroll_cb.setChecked(True)
        bottom_layout.addWidget(self.auto_scroll_cb)
        
        layout.addLayout(bottom_layout)
    
    def populate_log_files(self):
        """Populate the log files dropdown."""
        self.log_combo.clear()
        
        if not self.log_dir.exists():
            self.log_combo.addItem("No log directory found")
            return
        
        # Find all log files
        log_files = list(self.log_dir.glob("*.log"))
        
        if not log_files:
            self.log_combo.addItem("No log files found")
            return
        
        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        for log_file in log_files:
            self.log_combo.addItem(log_file.name)
    
    def load_selected_log(self, filename):
        """Load the selected log file."""
        if not filename or filename in ["No log directory found", "No log files found"]:
            self.log_display.clear()
            return
        
        log_file = self.log_dir / filename
        
        if not log_file.exists():
            self.log_display.setText(f"Log file not found: {log_file}")
            return
        
        try:
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            self.log_display.setPlainText(content)
            
            if self.auto_scroll_cb.isChecked():
                # Scroll to bottom
                scrollbar = self.log_display.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
                
        except Exception as e:
            self.log_display.setText(f"Error reading log file: {e}")
    
    def refresh_current_log(self):
        """Refresh the currently selected log."""
        current_file = self.log_combo.currentText()
        if current_file:
            self.load_selected_log(current_file)
    
    def toggle_auto_refresh(self, enabled):
        """Toggle auto-refresh timer."""
        if enabled:
            self.refresh_timer.start(5000)  # 5 seconds
        else:
            self.refresh_timer.stop()
    
    def clear_display(self):
        """Clear the log display."""
        self.log_display.clear()
    
    def save_log(self):
        """Save the current log content to a file."""
        content = self.log_display.toPlainText()
        
        if not content:
            QMessageBox.information(self, "Nothing to Save", "No log content to save.")
            return
        
        filename = self.log_combo.currentText()
        if filename:
            default_name = f"saved_{filename}"
        else:
            default_name = "log_export.txt"
        
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Log File", default_name,
            "Log Files (*.log);;Text Files (*.txt);;All Files (*)"
        )
        
        if save_path:
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                QMessageBox.information(
                    self, "Log Saved", 
                    f"Log saved to:\n{save_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Save Error", 
                    f"Failed to save log:\n{e}"
                )
    
    def closeEvent(self, event):
        """Handle window close."""
        # Stop the refresh timer
        self.refresh_timer.stop()
        event.accept()


def main():
    """Standalone entry point for testing."""
    from PyQt5.QtWidgets import QApplication
    import qdarkstyle
    
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    
    # Load configuration
    from rom_curator_main import ConfigManager
    config = ConfigManager()
    
    window = LogViewerWindow(config)
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
