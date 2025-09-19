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
        
        # Import/Export tab
        import_export_tab = self.create_import_export_tab()
        tab_widget.addTab(import_export_tab, "📤 Import/Export")
        
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
        self.extensions_table.setColumnCount(7)
        self.extensions_table.setHorizontalHeaderLabels([
            "Extension", "Category", "Description", "Type", "Active", "Created", "Actions"
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
    
    def create_import_export_tab(self):
        """Create the import/export tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Export section
        export_group = self._create_button_group("Export Extension Registry", [
            ("📄 Export JSON", lambda: self.export_data('json')),
            ("📊 Export CSV", lambda: self.export_data('csv'))
        ])
        layout.addWidget(export_group)
        
        # Import section
        import_group = QGroupBox("Import Extension Registry")
        import_layout = QVBoxLayout(import_group)
        
        import_buttons_layout = self._create_button_layout([
            ("📄 Import JSON", lambda: self.import_data('json'))
        ])
        import_layout.addLayout(import_buttons_layout)
        
        # Import options
        options_layout = QHBoxLayout()
        
        self.overwrite_check = QCheckBox("Overwrite existing entries")
        options_layout.addWidget(self.overwrite_check)
        
        options_layout.addStretch()
        import_layout.addLayout(options_layout)
        
        layout.addWidget(import_group)
        
        # Status area
        status_group = QGroupBox("Import/Export Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(150)
        self.status_text.setFont(QFont("Consolas", 9))
        status_layout.addWidget(self.status_text)
        
        layout.addWidget(status_group)
        
        return tab
    
    def _create_button_group(self, title: str, buttons: List[Tuple[str, callable]]) -> QGroupBox:
        """Create a group box with buttons."""
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        
        button_layout = self._create_button_layout(buttons)
        layout.addLayout(button_layout)
        
        return group
    
    def _create_button_layout(self, buttons: List[Tuple[str, callable]]) -> QHBoxLayout:
        """Create a horizontal layout with buttons."""
        layout = QHBoxLayout()
        
        for text, callback in buttons:
            button = QPushButton(text)
            button.clicked.connect(callback)
            layout.addWidget(button)
        
        layout.addStretch()
        return layout
    
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
            if ext['treat_as_archive']:
                types.append("Archive")
            if ext['treat_as_disc']:
                types.append("Disc")
            if ext['treat_as_auxiliary']:
                types.append("Auxiliary")
            type_text = ", ".join(types) if types else "ROM"
            self.extensions_table.setItem(row, 3, QTableWidgetItem(type_text))
            
            # Active
            active_icon = "✅" if ext['is_active'] else "❌"
            self.extensions_table.setItem(row, 4, QTableWidgetItem(active_icon))
            
            # Created
            created = ext['created_at'][:10] if ext['created_at'] else ""
            self.extensions_table.setItem(row, 5, QTableWidgetItem(created))
            
            # Actions
            actions_btn = QPushButton("Edit")
            actions_btn.clicked.connect(lambda checked, ext_id=ext['extension']: self.edit_extension(ext_id))
            self.extensions_table.setCellWidget(row, 6, actions_btn)
    
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
    
    # =============================================================================
    # MISSING GUI METHODS - IMPLEMENTATION
    # =============================================================================
    
    def add_extension(self):
        """Add a new file extension."""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QCheckBox, QPushButton, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Extension")
        dialog.setModal(True)
        dialog.resize(400, 300)
        
        layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()
        
        # Extension input
        extension_edit = QLineEdit()
        extension_edit.setPlaceholderText("e.g., .rom")
        form_layout.addRow("Extension:", extension_edit)
        
        # Category selection
        category_combo = QComboBox()
        categories = self.manager.get_categories(active_only=True)
        for category in categories:
            category_combo.addItem(category['name'], category['category_id'])
        form_layout.addRow("Category:", category_combo)
        
        # Description
        description_edit = QLineEdit()
        form_layout.addRow("Description:", description_edit)
        
        # Type checkboxes
        treat_as_archive_check = QCheckBox("Archive")
        treat_as_disc_check = QCheckBox("Disc")
        treat_as_auxiliary_check = QCheckBox("Auxiliary")
        
        form_layout.addRow("Types:", treat_as_archive_check)
        form_layout.addRow("", treat_as_disc_check)
        form_layout.addRow("", treat_as_auxiliary_check)
        
        layout.addLayout(form_layout)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            extension = extension_edit.text().strip()
            if not extension.startswith('.'):
                extension = f'.{extension}'
            
            category_id = category_combo.currentData()
            description = description_edit.text().strip() or None
            
            try:
                self.manager.create_extension(
                    extension=extension,
                    category_id=category_id,
                    description=description,
                    is_active=True,
                    treat_as_archive=treat_as_archive_check.isChecked(),
                    treat_as_disc=treat_as_disc_check.isChecked(),
                    treat_as_auxiliary=treat_as_auxiliary_check.isChecked()
                )
                self.load_extensions()
                QMessageBox.information(self, "Success", f"Extension {extension} added successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add extension: {e}")
    
    def filter_extensions(self):
        """Filter extensions based on search and category."""
        search_text = self.extension_search.text().lower()
        category_filter = self.category_filter.currentText()
        
        for row in range(self.extensions_table.rowCount()):
            should_show = True
            
            # Check search text
            if search_text:
                extension = self.extensions_table.item(row, 0).text().lower()
                description = self.extensions_table.item(row, 2).text().lower()
                if search_text not in extension and search_text not in description:
                    should_show = False
            
            # Check category filter
            if category_filter != "All Categories":
                category = self.extensions_table.item(row, 1).text()
                if category != category_filter:
                    should_show = False
            
            self.extensions_table.setRowHidden(row, not should_show)
    
    def add_mapping(self):
        """Add a new platform-extension mapping."""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QComboBox, QDoubleSpinBox, QCheckBox, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Platform Mapping")
        dialog.setModal(True)
        dialog.resize(400, 200)
        
        layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()
        
        # Platform selection
        platform_combo = QComboBox()
        with self.manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT platform_id, name FROM platform ORDER BY name")
            platforms = cursor.fetchall()
            for platform in platforms:
                platform_combo.addItem(platform['name'], platform['platform_id'])
        form_layout.addRow("Platform:", platform_combo)
        
        # Extension selection
        extension_combo = QComboBox()
        extensions = self.manager.get_extensions(active_only=True)
        for ext in extensions:
            display_text = f"{ext['extension']} ({ext['category_name']})"
            extension_combo.addItem(display_text, ext['extension_id'])
        form_layout.addRow("Extension:", extension_combo)
        
        # Primary checkbox
        is_primary_check = QCheckBox("Primary")
        form_layout.addRow("", is_primary_check)
        
        # Confidence
        confidence_spin = QDoubleSpinBox()
        confidence_spin.setRange(0.0, 1.0)
        confidence_spin.setSingleStep(0.1)
        confidence_spin.setValue(1.0)
        form_layout.addRow("Confidence:", confidence_spin)
        
        layout.addLayout(form_layout)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            platform_id = platform_combo.currentData()
            extension_id = extension_combo.currentData()
            is_primary = is_primary_check.isChecked()
            confidence = confidence_spin.value()
            
            try:
                self.manager.create_platform_extension(
                    platform_id=platform_id,
                    extension_id=extension_id,
                    is_primary=is_primary,
                    confidence=confidence
                )
                self.load_mappings()
                QMessageBox.information(self, "Success", "Platform mapping added successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add mapping: {e}")
    
    def on_extension_selected(self):
        """Handle extension selection in the table."""
        current_row = self.extensions_table.currentRow()
        # Enable/disable action buttons based on selection
        # Implementation can be added here if needed
    
    def delete_mapping(self, mapping_id: int):
        """Delete a platform-extension mapping."""
        reply = QMessageBox.question(
            self, "Confirm Delete", 
            "Are you sure you want to delete this platform mapping?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if self.manager.delete_platform_extension(mapping_id):
                    self.load_mappings()
                    QMessageBox.information(self, "Success", "Platform mapping deleted successfully.")
                else:
                    QMessageBox.warning(self, "Warning", "Failed to delete platform mapping.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete mapping: {e}")
    
    def filter_extensions(self):
        """Filter extensions based on search text and category."""
        search_text = self.extension_search.text().lower()
        category_filter = self.category_filter.currentText()
        
        # Get all extensions
        extensions = self.manager.get_extensions()
        
        # Filter based on search text
        if search_text:
            extensions = [ext for ext in extensions if 
                         search_text in ext['extension'].lower() or 
                         (ext['description'] and search_text in ext['description'].lower())]
        
        # Filter based on category
        if category_filter != "All Categories":
            extensions = [ext for ext in extensions if ext['category_name'] == category_filter]
        
        self.populate_extensions_table(extensions)
    
    def add_extension(self):
        """Show dialog to add a new extension."""
        dialog = ExtensionDialog(self.manager)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_extensions()
    
    def on_extension_selected(self):
        """Handle extension selection in the table."""
        current_row = self.extensions_table.currentRow()
        if current_row >= 0:
            extension_item = self.extensions_table.item(current_row, 0)
            if extension_item:
                extension = extension_item.text()
                # Update details panel if it exists
                self.update_extension_details(extension)
    
    def add_mapping(self):
        """Show dialog to add a new platform-extension mapping."""
        dialog = PlatformMappingDialog(self.manager)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_mappings()
    
    def on_mapping_selected(self):
        """Handle mapping selection in the table."""
        current_row = self.mappings_table.currentRow()
        if current_row >= 0:
            # Update details panel if it exists
            pass
    
    def on_unknown_selected(self):
        """Handle unknown extension selection in the table."""
        current_row = self.unknown_table.currentRow()
        if current_row >= 0:
            # Update details panel if it exists
            pass
    
    def update_extension_details(self, extension: str):
        """Update the extension details panel."""
        # This would update a details panel if one exists
        pass

    def approve_unknown(self, unknown_id: int):
        """Approve an unknown extension."""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QComboBox, QLineEdit, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Approve Unknown Extension")
        dialog.setModal(True)
        dialog.resize(400, 200)
        
        layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()
        
        # Get unknown extension details
        unknown_exts = self.manager.get_unknown_extensions()
        unknown_ext = next((ext for ext in unknown_exts if ext['unknown_extension_id'] == unknown_id), None)
        
        if not unknown_ext:
            QMessageBox.warning(self, "Error", "Unknown extension not found.")
            return
        
        # Show extension name
        ext_label = QLineEdit(unknown_ext['extension'])
        ext_label.setReadOnly(True)
        form_layout.addRow("Extension:", ext_label)
        
        # Category selection
        category_combo = QComboBox()
        categories = self.manager.get_categories(active_only=True)
        for category in categories:
            category_combo.addItem(category['name'], category['category_id'])
        form_layout.addRow("Category:", category_combo)
        
        # Platform selection (optional)
        platform_combo = QComboBox()
        platform_combo.addItem("No Platform", None)
        with self.manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT platform_id, name FROM platform ORDER BY name")
            platforms = cursor.fetchall()
            for platform in platforms:
                platform_combo.addItem(platform['name'], platform['platform_id'])
        form_layout.addRow("Platform (optional):", platform_combo)
        
        # Notes
        notes_edit = QLineEdit()
        form_layout.addRow("Notes:", notes_edit)
        
        layout.addLayout(form_layout)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            category_id = category_combo.currentData()
            platform_id = platform_combo.currentData()
            notes = notes_edit.text().strip() or None
            
            try:
                if self.manager.approve_unknown_extension(unknown_id, category_id, platform_id, notes):
                    self.load_unknown_extensions()
                    self.load_extensions()
                    self.load_mappings()
                    QMessageBox.information(self, "Success", "Unknown extension approved and added to registry.")
                else:
                    QMessageBox.warning(self, "Warning", "Failed to approve unknown extension.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to approve extension: {e}")
    
    def reject_unknown(self, unknown_id: int):
        """Reject an unknown extension."""
        reply = QMessageBox.question(
            self, "Confirm Reject", 
            "Are you sure you want to reject this unknown extension?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if self.manager.reject_unknown_extension(unknown_id, "Rejected by user"):
                    self.load_unknown_extensions()
                    QMessageBox.information(self, "Success", "Unknown extension rejected.")
                else:
                    QMessageBox.warning(self, "Warning", "Failed to reject unknown extension.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to reject extension: {e}")
    
    def ignore_unknown(self, unknown_id: int):
        """Ignore an unknown extension."""
        reply = QMessageBox.question(
            self, "Confirm Ignore", 
            "Are you sure you want to ignore this unknown extension?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if self.manager.ignore_unknown_extension(unknown_id, "Ignored by user"):
                    self.load_unknown_extensions()
                    QMessageBox.information(self, "Success", "Unknown extension ignored.")
                else:
                    QMessageBox.warning(self, "Warning", "Failed to ignore unknown extension.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to ignore extension: {e}")
    
    def filter_categories(self):
        """Filter categories based on search text."""
        search_text = self.category_search.text().lower()
        
        for i in range(self.categories_list.count()):
            item = self.categories_list.item(i)
            item_text = item.text().lower()
            should_show = search_text in item_text
            item.setHidden(not should_show)
    
    def filter_mappings(self):
        """Filter platform mappings based on platform selection."""
        platform_filter = self.platform_filter.currentText()
        
        for row in range(self.mappings_table.rowCount()):
            if platform_filter == "All Platforms":
                self.mappings_table.setRowHidden(row, False)
            else:
                platform = self.mappings_table.item(row, 0).text()
                should_show = platform == platform_filter
                self.mappings_table.setRowHidden(row, not should_show)
    
    def filter_unknown(self):
        """Filter unknown extensions based on search and status."""
        search_text = self.unknown_search.text().lower()
        status_filter = self.status_filter.currentText()
        
        for row in range(self.unknown_table.rowCount()):
            should_show = True
            
            # Check search text
            if search_text:
                extension = self.unknown_table.item(row, 0).text().lower()
                if search_text not in extension:
                    should_show = False
            
            # Check status filter
            if status_filter != "All Status":
                status = self.unknown_table.item(row, 2).text()
                if status_filter.lower() not in status.lower():
                    should_show = False
            
            self.unknown_table.setRowHidden(row, not should_show)
    
    def add_category(self):
        """Add a new file type category."""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit, QSpinBox, QCheckBox, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Category")
        dialog.setModal(True)
        dialog.resize(400, 300)
        
        layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()
        
        # Name
        name_edit = QLineEdit()
        form_layout.addRow("Name:", name_edit)
        
        # Description
        description_edit = QTextEdit()
        description_edit.setMaximumHeight(80)
        form_layout.addRow("Description:", description_edit)
        
        # Sort order
        sort_order_spin = QSpinBox()
        sort_order_spin.setRange(0, 9999)
        sort_order_spin.setValue(0)
        form_layout.addRow("Sort Order:", sort_order_spin)
        
        # Active checkbox
        active_check = QCheckBox("Active")
        active_check.setChecked(True)
        form_layout.addRow("", active_check)
        
        layout.addLayout(form_layout)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            name = name_edit.text().strip()
            description = description_edit.toPlainText().strip() or None
            sort_order = sort_order_spin.value()
            is_active = active_check.isChecked()
            
            if not name:
                QMessageBox.warning(self, "Warning", "Name is required.")
                return
            
            try:
                self.manager.create_category(name, description, sort_order, is_active)
                self.load_categories()
                QMessageBox.information(self, "Success", f"Category '{name}' added successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add category: {e}")
    
    def on_category_selected(self, item):
        """Handle category selection."""
        if not item:
            return
            
        if not (category_id := item.data(Qt.UserRole)):
            return
            
        if not (category := self.manager.get_category(category_id)):
            return
            
        self._populate_category_form(category_id, category)
    
    def _populate_category_form(self, category_id: int, category: Dict[str, Any]):
        """Populate the category form with data."""
        self.current_category_id = category_id
        self.category_name_edit.setText(category['name'])
        self.category_description_edit.setPlainText(category['description'] or "")
        self.category_sort_order_edit.setText(str(category['sort_order']))
        self.category_active_check.setChecked(bool(category['is_active']))

        # Enable update/delete buttons
        self.update_category_btn.setEnabled(True)
        self.delete_category_btn.setEnabled(True)
    
    def update_category(self):
        """Update the selected category."""
        if not self.current_category_id:
            QMessageBox.warning(self, "Warning", "Please select a category to update.")
            return
        
        name = self.category_name_edit.text().strip()
        description = self.category_description_edit.toPlainText().strip() or None
        sort_order = int(self.category_sort_order_edit.text() or 0)
        is_active = self.category_active_check.isChecked()
        
        if not name:
            QMessageBox.warning(self, "Warning", "Name is required.")
            return
        
        try:
            if self.manager.update_category(
                self.current_category_id,
                name=name,
                description=description,
                sort_order=sort_order,
                is_active=is_active
            ):
                self.load_categories()
                QMessageBox.information(self, "Success", "Category updated successfully.")
            else:
                QMessageBox.warning(self, "Warning", "Failed to update category.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update category: {e}")
    
    def delete_category(self):
        """Delete the selected category."""
        if not self.current_category_id:
            QMessageBox.warning(self, "Warning", "Please select a category to delete.")
            return
        
        reply = QMessageBox.question(
            self, "Confirm Delete", 
            "Are you sure you want to delete this category?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if self.manager.delete_category(self.current_category_id):
                    self.load_categories()
                    self._clear_category_form()
                    QMessageBox.information(self, "Success", "Category deleted successfully.")
                else:
                    QMessageBox.warning(self, "Warning", "Failed to delete category.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete category: {e}")
    
    def _clear_category_form(self):
        """Clear the category form."""
        self.category_name_edit.clear()
        self.category_description_edit.clear()
        self.category_sort_order_edit.setText("0")
        self.category_active_check.setChecked(True)
        self.update_category_btn.setEnabled(False)
        self.delete_category_btn.setEnabled(False)
        self.current_category_id = None
    
    def edit_extension(self, extension_id: int):
        """Edit an extension."""
        extension = self.manager.get_extension(extension_id)
        if not extension:
            QMessageBox.warning(self, "Warning", "Extension not found.")
            return
        
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QCheckBox, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Extension")
        dialog.setModal(True)
        dialog.resize(400, 300)
        
        layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()
        
        # Extension (read-only)
        extension_edit = QLineEdit(extension['extension'])
        extension_edit.setReadOnly(True)
        form_layout.addRow("Extension:", extension_edit)
        
        # Category selection
        category_combo = QComboBox()
        categories = self.manager.get_categories(active_only=False)
        for category in categories:
            category_combo.addItem(category['name'], category['category_id'])
            if category['category_id'] == extension['category_id']:
                category_combo.setCurrentIndex(category_combo.count() - 1)
        form_layout.addRow("Category:", category_combo)
        
        # Description
        description_edit = QLineEdit(extension['description'] or "")
        form_layout.addRow("Description:", description_edit)
        
        # MIME type
        mime_edit = QLineEdit(extension['mime_type'] or "")
        form_layout.addRow("MIME Type:", mime_edit)
        
        # Type checkboxes
        is_rom_check = QCheckBox("ROM")
        is_rom_check.setChecked(bool(extension['is_rom']))
        is_archive_check = QCheckBox("Archive")
        is_archive_check.setChecked(bool(extension['is_archive']))
        is_save_check = QCheckBox("Save")
        is_save_check.setChecked(bool(extension['is_save']))
        is_patch_check = QCheckBox("Patch")
        is_patch_check.setChecked(bool(extension['is_patch']))
        
        form_layout.addRow("Types:", is_rom_check)
        form_layout.addRow("", is_archive_check)
        form_layout.addRow("", is_save_check)
        form_layout.addRow("", is_patch_check)
        
        # Active checkbox
        active_check = QCheckBox("Active")
        active_check.setChecked(bool(extension['is_active']))
        form_layout.addRow("", active_check)
        
        layout.addLayout(form_layout)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            category_id = category_combo.currentData()
            description = description_edit.text().strip() or None
            mime_type = mime_edit.text().strip() or None
            
            try:
                if self.manager.update_extension(
                    extension_id,
                    category_id=category_id,
                    description=description,
                    mime_type=mime_type,
                    is_rom=is_rom_check.isChecked(),
                    is_archive=is_archive_check.isChecked(),
                    is_save=is_save_check.isChecked(),
                    is_patch=is_patch_check.isChecked(),
                    is_active=active_check.isChecked()
                ):
                    self.load_extensions()
                    QMessageBox.information(self, "Success", "Extension updated successfully.")
                else:
                    QMessageBox.warning(self, "Warning", "Failed to update extension.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update extension: {e}")
    
    def export_data(self, format: str):
        """Export extension registry data."""
        from PyQt5.QtWidgets import QFileDialog
        
        # Get save file path
        file_filter = "JSON files (*.json)" if format == 'json' else "CSV files (*.csv)"
        file_path, _ = QFileDialog.getSaveFileName(
            self, f"Export Extension Registry ({format.upper()})", 
            f"extension_registry.{format}", file_filter
        )
        
        if not file_path:
            return
        
        try:
            if success := self.manager.export_extensions(file_path, format):
                self.status_text.append(f"✅ Export successful: {file_path}")
                QMessageBox.information(self, "Export Successful", f"Extension registry exported to:\n{file_path}")
            else:
                self.status_text.append(f"❌ Export failed: {file_path}")
                QMessageBox.critical(self, "Export Failed", "Failed to export extension registry.")
        except Exception as e:
            self.status_text.append(f"❌ Export error: {e}")
            QMessageBox.critical(self, "Export Error", f"Export failed: {e}")
    
    def import_data(self, format: str):
        """Import extension registry data."""
        from PyQt5.QtWidgets import QFileDialog
        
        if format != 'json':
            self.status_text.append("⚠️ Import cancelled: Only JSON imports are supported.")
            QMessageBox.warning(
                self,
                "Unsupported Import Format",
                "Only JSON import is currently supported."
            )
            return

        # Get file path
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Extension Registry (JSON)",
            "", "JSON files (*.json)"
        )
        
        if not file_path:
            return
        
        try:
            overwrite = self.overwrite_check.isChecked()
            results = self.manager.import_extensions(file_path, format, overwrite)
            
            if results['success']:
                self._handle_import_success(file_path, results)
            else:
                self._handle_import_failure(file_path, results)
                
        except Exception as e:
            self.status_text.append(f"❌ Import error: {e}")
            QMessageBox.critical(self, "Import Error", f"Import failed: {e}")
    
    def _handle_import_success(self, file_path: str, results: Dict[str, Any]):
        """Handle successful import."""
        self.status_text.append(f"✅ Import successful: {file_path}")
        self.status_text.append(f"   Categories: {results['categories_imported']}")
        self.status_text.append(f"   Extensions: {results['extensions_imported']}")
        self.status_text.append(f"   Mappings: {results['mappings_imported']}")
        self.status_text.append(f"   Unknown: {results['unknown_imported']}")

        # Refresh all data
        self.load_data()

        success_message = (
            "Import completed successfully!\n\n"
            f"Categories: {results['categories_imported']}\n"
            f"Extensions: {results['extensions_imported']}\n"
            f"Mappings: {results['mappings_imported']}\n"
            f"Unknown: {results['unknown_imported']}"
        )
        QMessageBox.information(self, "Import Successful", success_message)
    
    def _handle_import_failure(self, file_path: str, results: Dict[str, Any]):
        """Handle failed import."""
        self.status_text.append(f"❌ Import failed: {file_path}")
        error_msg = "\n".join(results['errors'][:5])  # Show first 5 errors
        if len(results['errors']) > 5:
            error_msg += f"\n... and {len(results['errors']) - 5} more errors"
        QMessageBox.critical(self, "Import Failed", f"Import failed:\n{error_msg}")

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