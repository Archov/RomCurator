#!/usr/bin/env python3
"""
Extension Registry GUI - PyQt management dialog for file extensions and platform mappings

This module provides a comprehensive PyQt interface for managing the extension registry system,
including file type categories, file extensions, platform mappings, and unknown extension handling.
"""

import sys
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Any

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem,
    QLineEdit, QComboBox, QCheckBox, QGroupBox, QSplitter, QWidget, QTabWidget,
    QAbstractItemView, QMessageBox, QInputDialog, QFormLayout, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QStatusBar
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt5.QtGui import QFont, QMouseEvent, QPoint

from extension_registry_manager import ExtensionRegistryManager


class DraggableTitleBar(QWidget):
    """Custom title bar that allows dragging the window."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dragging = False
        self.drag_start_position = QPoint()
    
    def mousePressEvent(self, event):
        """Handle mouse press to start dragging."""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_start_position = event.globalPos() - self.window().frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move to drag the window."""
        if event.buttons() == Qt.LeftButton and self.dragging:
            self.window().move(event.globalPos() - self.drag_start_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release to stop dragging."""
        if event.button() == Qt.LeftButton:
            self.dragging = False
            event.accept()


class ExtensionRegistryDialog(QDialog):
    """Main extension registry management dialog."""
    
    def __init__(self, db_path: str, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.manager = ExtensionRegistryManager(db_path)
        self.current_category_id = None
        self.current_extension_id = None
        
        self.setWindowTitle("Extension Registry Manager")
        self.setModal(True)
        self.resize(1200, 800)
        self.setMinimumWidth(1000)
        
        # Make frameless to avoid white Windows title bar
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        
        # Inherit parent's stylesheet if available
        if parent and hasattr(parent, 'styleSheet'):
            self.setStyleSheet(parent.styleSheet())
        
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        
        # Custom title bar
        title_bar = self.create_title_bar()
        layout.addWidget(title_bar)
        
        # Create tab widget for different sections
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # Categories tab
        categories_tab = self.create_categories_tab()
        tab_widget.addTab(categories_tab, "📁 Categories")
        
        # Extensions tab
        extensions_tab = self.create_extensions_tab()
        tab_widget.addTab(extensions_tab, "📄 Extensions")
        
        # Platform mappings tab
        mappings_tab = self.create_mappings_tab()
        tab_widget.addTab(mappings_tab, "🔗 Platform Mappings")
        
        # Unknown extensions tab
        unknown_tab = self.create_unknown_tab()
        tab_widget.addTab(unknown_tab, "❓ Unknown Extensions")
        
        # Statistics tab
        stats_tab = self.create_statistics_tab()
        tab_widget.addTab(stats_tab, "📊 Statistics")
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.refresh_all_data)
        button_layout.addWidget(self.refresh_btn)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def create_title_bar(self):
        """Create a custom title bar with close button and drag functionality."""
        title_bar = DraggableTitleBar()
        title_bar.setFixedHeight(30)
        title_bar.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border-bottom: 1px solid #555;
            }
        """)
        
        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(10, 0, 10, 0)
        
        # Title
        title_label = QLabel("Extension Registry Manager")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        layout.addWidget(title_label)
        
        # Spacer
        layout.addStretch()
        
        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 10px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        return title_bar
    
    def create_categories_tab(self):
        """Create the categories management tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Top controls
        controls_layout = QHBoxLayout()
        
        self.category_search = QLineEdit()
        self.category_search.setPlaceholderText("Search categories...")
        self.category_search.textChanged.connect(self.filter_categories)
        controls_layout.addWidget(self.category_search)
        
        self.add_category_btn = QPushButton("➕ Add Category")
        self.add_category_btn.clicked.connect(self.add_category)
        controls_layout.addWidget(self.add_category_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Categories list
        self.categories_list = QListWidget()
        self.categories_list.itemClicked.connect(self.on_category_selected)
        self.categories_list.setAlternatingRowColors(True)
        layout.addWidget(self.categories_list)
        
        # Category details
        details_group = QGroupBox("Category Details")
        details_layout = QFormLayout(details_group)
        
        self.category_name_edit = QLineEdit()
        self.category_description_edit = QTextEdit()
        self.category_description_edit.setMaximumHeight(100)
        self.category_sort_order_edit = QLineEdit()
        self.category_sort_order_edit.setText("0")
        self.category_active_check = QCheckBox("Active")
        self.category_active_check.setChecked(True)
        
        details_layout.addRow("Name:", self.category_name_edit)
        details_layout.addRow("Description:", self.category_description_edit)
        details_layout.addRow("Sort Order:", self.category_sort_order_edit)
        details_layout.addRow("", self.category_active_check)
        
        # Category action buttons
        category_buttons = QHBoxLayout()
        self.update_category_btn = QPushButton("💾 Update")
        self.update_category_btn.clicked.connect(self.update_category)
        self.update_category_btn.setEnabled(False)
        category_buttons.addWidget(self.update_category_btn)
        
        self.delete_category_btn = QPushButton("🗑️ Delete")
        self.delete_category_btn.clicked.connect(self.delete_category)
        self.delete_category_btn.setEnabled(False)
        category_buttons.addWidget(self.delete_category_btn)
        
        category_buttons.addStretch()
        details_layout.addRow("", category_buttons)
        
        layout.addWidget(details_group)
        
        return tab
    
    def create_extensions_tab(self):
        """Create the extensions management tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Top controls
        controls_layout = QHBoxLayout()
        
        self.extension_search = QLineEdit()
        self.extension_search.setPlaceholderText("Search extensions...")
        self.extension_search.textChanged.connect(self.filter_extensions)
        controls_layout.addWidget(self.extension_search)
        
        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories")
        self.category_filter.currentTextChanged.connect(self.filter_extensions)
        controls_layout.addWidget(self.category_filter)
        
        self.add_extension_btn = QPushButton("➕ Add Extension")
        self.add_extension_btn.clicked.connect(self.add_extension)
        controls_layout.addWidget(self.add_extension_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Extensions table
        self.extensions_table = QTableWidget()
        self.extensions_table.setColumnCount(8)
        self.extensions_table.setHorizontalHeaderLabels([
            "Extension", "Category", "Description", "Type", "Active", "MIME", "Created", "Actions"
        ])
        self.extensions_table.horizontalHeader().setStretchLastSection(True)
        self.extensions_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.extensions_table.itemSelectionChanged.connect(self.on_extension_selected)
        layout.addWidget(self.extensions_table)
        
        return tab
    
    def create_mappings_tab(self):
        """Create the platform mappings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Top controls
        controls_layout = QHBoxLayout()
        
        self.platform_filter = QComboBox()
        self.platform_filter.addItem("All Platforms")
        self.platform_filter.currentTextChanged.connect(self.filter_mappings)
        controls_layout.addWidget(self.platform_filter)
        
        self.add_mapping_btn = QPushButton("➕ Add Mapping")
        self.add_mapping_btn.clicked.connect(self.add_mapping)
        controls_layout.addWidget(self.add_mapping_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Mappings table
        self.mappings_table = QTableWidget()
        self.mappings_table.setColumnCount(6)
        self.mappings_table.setHorizontalHeaderLabels([
            "Platform", "Extension", "Category", "Primary", "Confidence", "Actions"
        ])
        self.mappings_table.horizontalHeader().setStretchLastSection(True)
        self.mappings_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.mappings_table)
        
        return tab
    
    def create_unknown_tab(self):
        """Create the unknown extensions tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Top controls
        controls_layout = QHBoxLayout()
        
        self.unknown_search = QLineEdit()
        self.unknown_search.setPlaceholderText("Search unknown extensions...")
        self.unknown_search.textChanged.connect(self.filter_unknown)
        controls_layout.addWidget(self.unknown_search)
        
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All Status", "Pending", "Approved", "Rejected", "Ignored"])
        self.status_filter.currentTextChanged.connect(self.filter_unknown)
        controls_layout.addWidget(self.status_filter)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Unknown extensions table
        self.unknown_table = QTableWidget()
        self.unknown_table.setColumnCount(7)
        self.unknown_table.setHorizontalHeaderLabels([
            "Extension", "File Count", "Status", "First Seen", "Suggested Category", "Suggested Platform", "Actions"
        ])
        self.unknown_table.horizontalHeader().setStretchLastSection(True)
        self.unknown_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.unknown_table)
        
        return tab
    
    def create_statistics_tab(self):
        """Create the statistics tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Statistics display
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.stats_text)
        
        # Refresh button
        refresh_stats_btn = QPushButton("🔄 Refresh Statistics")
        refresh_stats_btn.clicked.connect(self.refresh_statistics)
        layout.addWidget(refresh_stats_btn)
        
        return tab
    
    def load_data(self):
        """Load all data from the database."""
        self.load_categories()
        self.load_extensions()
        self.load_mappings()
        self.load_unknown_extensions()
        self.refresh_statistics()
    
    def load_categories(self):
        """Load categories into the list."""
        self.categories_list.clear()
        categories = self.manager.get_categories(active_only=False)
        
        for category in categories:
            status_icon = "✅" if category['is_active'] else "❌"
            item_text = f"{status_icon} {category['name']}"
            if category['description']:
                item_text += f" - {category['description']}"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, category['category_id'])
            self.categories_list.addItem(item)
        
        # Update category filter in extensions tab
        self.category_filter.clear()
        self.category_filter.addItem("All Categories")
        for category in categories:
            if category['is_active']:
                self.category_filter.addItem(category['name'])
    
    def load_extensions(self):
        """Load extensions into the table."""
        extensions = self.manager.get_extensions(active_only=False)
        
        self.extensions_table.setRowCount(len(extensions))
        
        for row, ext in enumerate(extensions):
            # Extension
            self.extensions_table.setItem(row, 0, QTableWidgetItem(ext['extension']))
            
            # Category
            self.extensions_table.setItem(row, 1, QTableWidgetItem(ext['category_name']))
            
            # Description
            desc = ext['description'] or ""
            self.extensions_table.setItem(row, 2, QTableWidgetItem(desc))
            
            # Type
            types = []
            if ext['is_rom']:
                types.append("ROM")
            if ext['is_archive']:
                types.append("Archive")
            if ext['is_save']:
                types.append("Save")
            if ext['is_patch']:
                types.append("Patch")
            type_text = ", ".join(types) if types else "Unknown"
            self.extensions_table.setItem(row, 3, QTableWidgetItem(type_text))
            
            # Active
            active_icon = "✅" if ext['is_active'] else "❌"
            self.extensions_table.setItem(row, 4, QTableWidgetItem(active_icon))
            
            # MIME type
            mime = ext['mime_type'] or ""
            self.extensions_table.setItem(row, 5, QTableWidgetItem(mime))
            
            # Created
            created = ext['created_at'][:10] if ext['created_at'] else ""
            self.extensions_table.setItem(row, 6, QTableWidgetItem(created))
            
            # Actions
            actions_btn = QPushButton("Edit")
            actions_btn.clicked.connect(lambda checked, ext_id=ext['extension_id']: self.edit_extension(ext_id))
            self.extensions_table.setCellWidget(row, 7, actions_btn)
    
    def load_mappings(self):
        """Load platform mappings into the table."""
        mappings = self.manager.get_platform_extensions()
        
        self.mappings_table.setRowCount(len(mappings))
        
        for row, mapping in enumerate(mappings):
            # Platform
            self.mappings_table.setItem(row, 0, QTableWidgetItem(mapping['platform_name']))
            
            # Extension
            self.mappings_table.setItem(row, 1, QTableWidgetItem(mapping['extension']))
            
            # Category
            self.mappings_table.setItem(row, 2, QTableWidgetItem(mapping['category_name']))
            
            # Primary
            primary_icon = "⭐" if mapping['is_primary'] else "📄"
            self.mappings_table.setItem(row, 3, QTableWidgetItem(primary_icon))
            
            # Confidence
            confidence = f"{mapping['confidence']:.2f}"
            self.mappings_table.setItem(row, 4, QTableWidgetItem(confidence))
            
            # Actions
            actions_btn = QPushButton("Delete")
            actions_btn.clicked.connect(lambda checked, map_id=mapping['platform_extension_id']: self.delete_mapping(map_id))
            self.mappings_table.setCellWidget(row, 5, actions_btn)
    
    def load_unknown_extensions(self):
        """Load unknown extensions into the table."""
        unknown = self.manager.get_unknown_extensions()
        
        self.unknown_table.setRowCount(len(unknown))
        
        for row, ext in enumerate(unknown):
            # Extension
            self.unknown_table.setItem(row, 0, QTableWidgetItem(ext['extension']))
            
            # File count
            self.unknown_table.setItem(row, 1, QTableWidgetItem(str(ext['file_count'])))
            
            # Status
            status_icon = {
                'pending': '🟡',
                'approved': '✅',
                'rejected': '❌',
                'ignored': '⚪'
            }.get(ext['status'], '❓')
            status_text = f"{status_icon} {ext['status'].title()}"
            self.unknown_table.setItem(row, 2, QTableWidgetItem(status_text))
            
            # First seen
            first_seen = ext['first_seen'][:10] if ext['first_seen'] else ""
            self.unknown_table.setItem(row, 3, QTableWidgetItem(first_seen))
            
            # Suggested category
            suggested_cat = ext['suggested_category'] or ""
            self.unknown_table.setItem(row, 4, QTableWidgetItem(suggested_cat))
            
            # Suggested platform
            suggested_plat = ext['suggested_platform'] or ""
            self.unknown_table.setItem(row, 5, QTableWidgetItem(suggested_plat))
            
            # Actions
            actions_layout = QHBoxLayout()
            approve_btn = QPushButton("✅")
            approve_btn.setToolTip("Approve")
            approve_btn.clicked.connect(lambda checked, ext_id=ext['unknown_extension_id']: self.approve_unknown(ext_id))
            actions_layout.addWidget(approve_btn)
            
            reject_btn = QPushButton("❌")
            reject_btn.setToolTip("Reject")
            reject_btn.clicked.connect(lambda checked, ext_id=ext['unknown_extension_id']: self.reject_unknown(ext_id))
            actions_layout.addWidget(reject_btn)
            
            ignore_btn = QPushButton("⚪")
            ignore_btn.setToolTip("Ignore")
            ignore_btn.clicked.connect(lambda checked, ext_id=ext['unknown_extension_id']: self.ignore_unknown(ext_id))
            actions_layout.addWidget(ignore_btn)
            
            actions_widget = QWidget()
            actions_widget.setLayout(actions_layout)
            self.unknown_table.setCellWidget(row, 6, actions_widget)
    
    def refresh_statistics(self):
        """Refresh the statistics display."""
        summary = self.manager.get_extension_registry_summary()
        
        stats_text = "📊 EXTENSION REGISTRY STATISTICS\n"
        stats_text += "=" * 50 + "\n\n"
        
        # Categories
        stats_text += "📁 CATEGORIES\n"
        stats_text += f"   Total: {summary['categories']['total_categories']}\n"
        stats_text += f"   Active: {summary['categories']['active_categories']}\n\n"
        
        # Extensions
        stats_text += "📄 EXTENSIONS\n"
        stats_text += f"   Total: {summary['extensions']['total_extensions']}\n"
        stats_text += f"   Active: {summary['extensions']['active_extensions']}\n"
        stats_text += f"   ROM: {summary['extensions']['rom_extensions']}\n"
        stats_text += f"   Archive: {summary['extensions']['archive_extensions']}\n"
        stats_text += f"   Save: {summary['extensions']['save_extensions']}\n"
        stats_text += f"   Patch: {summary['extensions']['patch_extensions']}\n\n"
        
        # Mappings
        stats_text += "🔗 PLATFORM MAPPINGS\n"
        stats_text += f"   Total: {summary['mappings']['total_mappings']}\n"
        stats_text += f"   Primary: {summary['mappings']['primary_mappings']}\n"
        stats_text += f"   Platforms: {summary['mappings']['platforms_with_mappings']}\n\n"
        
        # Unknown
        stats_text += "❓ UNKNOWN EXTENSIONS\n"
        stats_text += f"   Total: {summary['unknown']['total_unknown']}\n"
        stats_text += f"   Pending: {summary['unknown']['pending_unknown']}\n"
        stats_text += f"   Approved: {summary['unknown']['approved_unknown']}\n"
        stats_text += f"   Rejected: {summary['unknown']['rejected_unknown']}\n"
        stats_text += f"   Ignored: {summary['unknown']['ignored_unknown']}\n"
        
        self.stats_text.setText(stats_text)
    
    def refresh_all_data(self):
        """Refresh all data in all tabs."""
        self.load_data()
        QMessageBox.information(self, "Refresh Complete", "All data has been refreshed.")
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        event.accept()


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    # Test the dialog
    dialog = ExtensionRegistryDialog('database/RomCurator.db')
    dialog.show()
    
    sys.exit(app.exec_())