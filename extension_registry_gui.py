"""
Extension Registry GUI for ROM Curator

This module provides a PyQt5-based GUI for managing file extensions, categories,
platform mappings, and unknown extension handling.

Features:
- Category management (CRUD operations)
- Extension management (CRUD operations)
- Platform mapping management
- Unknown extension approval workflow
- Import/export functionality (JSON/CSV)
- Real-time filtering and search
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QTableWidget,
    QTableWidgetItem, QPushButton, QLineEdit, QComboBox, QCheckBox,
    QTextEdit, QGroupBox, QFormLayout, QLabel, QMessageBox, QHeaderView,
    QSplitter, QListWidget, QListWidgetItem, QDialogButtonBox, QSpinBox,
    QFileDialog, QProgressBar, QStatusBar
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt5.QtGui import QFont, QIcon

from extension_registry_manager import ExtensionRegistryManager


class ExtensionRegistryDialog(QDialog):
    """Main dialog for extension registry management."""
    
    def __init__(self, db_path: str, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.manager = ExtensionRegistryManager(db_path)
        self.current_category_id = None
        self.current_extension_id = None
        self.current_mapping_id = None
        
        self.setWindowTitle("Extension Registry Manager")
        self.setModal(True)
        self.resize(1200, 800)
        
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.create_categories_tab()
        self.create_extensions_tab()
        self.create_mappings_tab()
        self.create_unknown_tab()
        self.create_import_export_tab()
        
        # Status bar
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def create_categories_tab(self):
        """Create the categories management tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Categories list
        categories_group = QGroupBox("File Type Categories")
        categories_layout = QVBoxLayout(categories_group)
        
        # Categories table
        self.categories_table = QTableWidget()
        self.categories_table.setColumnCount(5)
        self.categories_table.setHorizontalHeaderLabels([
            "ID", "Name", "Description", "Sort Order", "Active"
        ])
        self.categories_table.horizontalHeader().setStretchLastSection(True)
        self.categories_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.categories_table.itemSelectionChanged.connect(self.on_category_selected)
        categories_layout.addWidget(self.categories_table)
        
        # Category buttons
        category_buttons_layout = QHBoxLayout()
        self.add_category_btn = QPushButton("➕ Add Category")
        self.add_category_btn.clicked.connect(self.add_category)
        self.update_category_btn = QPushButton("✏️ Update Category")
        self.update_category_btn.clicked.connect(self.update_category)
        self.update_category_btn.setEnabled(False)
        self.delete_category_btn = QPushButton("🗑️ Delete Category")
        self.delete_category_btn.clicked.connect(self.delete_category)
        self.delete_category_btn.setEnabled(False)
        
        category_buttons_layout.addWidget(self.add_category_btn)
        category_buttons_layout.addWidget(self.update_category_btn)
        category_buttons_layout.addWidget(self.delete_category_btn)
        category_buttons_layout.addStretch()
        categories_layout.addLayout(category_buttons_layout)
        
        layout.addWidget(categories_group)
        
        # Category form
        form_group = QGroupBox("Category Details")
        form_layout = QFormLayout(form_group)
        
        self.category_name_edit = QLineEdit()
        self.category_name_edit.setPlaceholderText("e.g., Nintendo ROMs")
        form_layout.addRow("Name:", self.category_name_edit)
        
        self.category_description_edit = QTextEdit()
        self.category_description_edit.setMaximumHeight(80)
        self.category_description_edit.setPlaceholderText("Description of this category")
        form_layout.addRow("Description:", self.category_description_edit)
        
        self.category_sort_order_edit = QSpinBox()
        self.category_sort_order_edit.setRange(0, 9999)
        self.category_sort_order_edit.setValue(0)
        form_layout.addRow("Sort Order:", self.category_sort_order_edit)
        
        self.category_active_check = QCheckBox("Active")
        self.category_active_check.setChecked(True)
        form_layout.addRow("", self.category_active_check)
        
        layout.addWidget(form_group)
        
        self.tab_widget.addTab(tab, "📁 Categories")
    
    def create_extensions_tab(self):
        """Create the extensions management tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Extensions list
        extensions_group = QGroupBox("File Extensions")
        extensions_layout = QVBoxLayout(extensions_group)
        
        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        self.extension_filter_edit = QLineEdit()
        self.extension_filter_edit.setPlaceholderText("Search extensions...")
        self.extension_filter_edit.textChanged.connect(self.filter_extensions)
        filter_layout.addWidget(self.extension_filter_edit)
        
        self.category_filter_combo = QComboBox()
        self.category_filter_combo.addItem("All Categories", None)
        self.category_filter_combo.currentTextChanged.connect(self.filter_extensions)
        filter_layout.addWidget(QLabel("Category:"))
        filter_layout.addWidget(self.category_filter_combo)
        filter_layout.addStretch()
        extensions_layout.addLayout(filter_layout)
        
        # Extensions table
        self.extensions_table = QTableWidget()
        self.extensions_table.setColumnCount(8)
        self.extensions_table.setHorizontalHeaderLabels([
            "ID", "Extension", "Category", "Description", "ROM", "Archive", "Save", "Patch"
        ])
        self.extensions_table.horizontalHeader().setStretchLastSection(True)
        self.extensions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.extensions_table.itemSelectionChanged.connect(self.on_extension_selected)
        extensions_layout.addWidget(self.extensions_table)
        
        # Extension buttons
        extension_buttons_layout = QHBoxLayout()
        self.add_extension_btn = QPushButton("➕ Add Extension")
        self.add_extension_btn.clicked.connect(self.add_extension)
        self.update_extension_btn = QPushButton("✏️ Update Extension")
        self.update_extension_btn.clicked.connect(self.update_extension)
        self.update_extension_btn.setEnabled(False)
        self.delete_extension_btn = QPushButton("🗑️ Delete Extension")
        self.delete_extension_btn.clicked.connect(self.delete_extension)
        self.delete_extension_btn.setEnabled(False)
        
        extension_buttons_layout.addWidget(self.add_extension_btn)
        extension_buttons_layout.addWidget(self.update_extension_btn)
        extension_buttons_layout.addWidget(self.delete_extension_btn)
        extension_buttons_layout.addStretch()
        extensions_layout.addLayout(extension_buttons_layout)
        
        layout.addWidget(extensions_group)
        
        # Extension form
        form_group = QGroupBox("Extension Details")
        form_layout = QFormLayout(form_group)
        
        self.extension_edit = QLineEdit()
        self.extension_edit.setPlaceholderText("e.g., .rom")
        form_layout.addRow("Extension:", self.extension_edit)
        
        self.extension_category_combo = QComboBox()
        form_layout.addRow("Category:", self.extension_category_combo)
        
        self.extension_description_edit = QLineEdit()
        self.extension_description_edit.setPlaceholderText("Description")
        form_layout.addRow("Description:", self.extension_description_edit)
        
        self.extension_mime_edit = QLineEdit()
        self.extension_mime_edit.setPlaceholderText("MIME type")
        form_layout.addRow("MIME Type:", self.extension_mime_edit)
        
        # Type checkboxes
        type_layout = QHBoxLayout()
        self.extension_rom_check = QCheckBox("ROM")
        self.extension_archive_check = QCheckBox("Archive")
        self.extension_save_check = QCheckBox("Save")
        self.extension_patch_check = QCheckBox("Patch")
        type_layout.addWidget(self.extension_rom_check)
        type_layout.addWidget(self.extension_archive_check)
        type_layout.addWidget(self.extension_save_check)
        type_layout.addWidget(self.extension_patch_check)
        form_layout.addRow("Types:", type_layout)
        
        layout.addWidget(form_group)
        
        self.tab_widget.addTab(tab, "📄 Extensions")
    
    def create_mappings_tab(self):
        """Create the platform mappings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Mappings list
        mappings_group = QGroupBox("Platform Mappings")
        mappings_layout = QVBoxLayout(mappings_group)
        
        # Mappings table
        self.mappings_table = QTableWidget()
        self.mappings_table.setColumnCount(6)
        self.mappings_table.setHorizontalHeaderLabels([
            "ID", "Platform", "Extension", "Primary", "Confidence", "Actions"
        ])
        self.mappings_table.horizontalHeader().setStretchLastSection(True)
        self.mappings_table.setSelectionBehavior(QTableWidget.SelectRows)
        mappings_layout.addWidget(self.mappings_table)
        
        # Mapping buttons
        mapping_buttons_layout = QHBoxLayout()
        self.add_mapping_btn = QPushButton("➕ Add Mapping")
        self.add_mapping_btn.clicked.connect(self.add_mapping)
        self.delete_mapping_btn = QPushButton("🗑️ Delete Mapping")
        self.delete_mapping_btn.clicked.connect(self.delete_mapping)
        self.delete_mapping_btn.setEnabled(False)
        mapping_buttons_layout.addWidget(self.add_mapping_btn)
        mapping_buttons_layout.addWidget(self.delete_mapping_btn)
        mapping_buttons_layout.addStretch()
        mappings_layout.addLayout(mapping_buttons_layout)
        
        layout.addWidget(mappings_group)
        
        # Mapping form
        form_group = QGroupBox("Platform Mapping Details")
        form_layout = QFormLayout(form_group)
        
        self.mapping_platform_combo = QComboBox()
        form_layout.addRow("Platform:", self.mapping_platform_combo)
        
        self.mapping_extension_combo = QComboBox()
        form_layout.addRow("Extension:", self.mapping_extension_combo)
        
        self.mapping_primary_check = QCheckBox("Primary Mapping")
        form_layout.addRow("", self.mapping_primary_check)
        
        self.mapping_confidence_spin = QSpinBox()
        self.mapping_confidence_spin.setRange(0, 100)
        self.mapping_confidence_spin.setValue(100)
        self.mapping_confidence_spin.setSuffix("%")
        form_layout.addRow("Confidence:", self.mapping_confidence_spin)
        
        layout.addWidget(form_group)
        
        self.tab_widget.addTab(tab, "🔗 Mappings")
    
    def create_unknown_tab(self):
        """Create the unknown extensions tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Unknown extensions list
        unknown_group = QGroupBox("Unknown Extensions")
        unknown_layout = QVBoxLayout(unknown_group)
        
        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Status:"))
        self.unknown_status_combo = QComboBox()
        self.unknown_status_combo.addItems(["All", "Pending", "Approved", "Rejected", "Ignored"])
        self.unknown_status_combo.currentTextChanged.connect(self.filter_unknown_extensions)
        filter_layout.addWidget(self.unknown_status_combo)
        filter_layout.addStretch()
        unknown_layout.addLayout(filter_layout)
        
        # Unknown extensions table
        self.unknown_table = QTableWidget()
        self.unknown_table.setColumnCount(7)
        self.unknown_table.setHorizontalHeaderLabels([
            "Extension", "Count", "Status", "Suggested Category", "Suggested Platform", "Notes", "Actions"
        ])
        self.unknown_table.horizontalHeader().setStretchLastSection(True)
        self.unknown_table.setSelectionBehavior(QTableWidget.SelectRows)
        unknown_layout.addWidget(self.unknown_table)
        
        # Unknown extension buttons
        unknown_buttons_layout = QHBoxLayout()
        self.approve_unknown_btn = QPushButton("✅ Approve")
        self.approve_unknown_btn.clicked.connect(self.approve_unknown)
        self.approve_unknown_btn.setEnabled(False)
        self.reject_unknown_btn = QPushButton("❌ Reject")
        self.reject_unknown_btn.clicked.connect(self.reject_unknown)
        self.reject_unknown_btn.setEnabled(False)
        self.ignore_unknown_btn = QPushButton("🚫 Ignore")
        self.ignore_unknown_btn.clicked.connect(self.ignore_unknown)
        self.ignore_unknown_btn.setEnabled(False)
        
        unknown_buttons_layout.addWidget(self.approve_unknown_btn)
        unknown_buttons_layout.addWidget(self.reject_unknown_btn)
        unknown_buttons_layout.addWidget(self.ignore_unknown_btn)
        unknown_buttons_layout.addStretch()
        unknown_layout.addLayout(unknown_buttons_layout)
        
        layout.addWidget(unknown_group)
        
        self.tab_widget.addTab(tab, "❓ Unknown")
    
    def create_import_export_tab(self):
        """Create the import/export tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Export section
        export_group = QGroupBox("Export Extension Registry")
        export_layout = QVBoxLayout(export_group)
        
        export_buttons_layout = QHBoxLayout()
        self.export_json_btn = QPushButton("📄 Export JSON")
        self.export_json_btn.clicked.connect(lambda: self.export_data('json'))
        export_buttons_layout.addWidget(self.export_json_btn)
        
        self.export_csv_btn = QPushButton("📊 Export CSV")
        self.export_csv_btn.clicked.connect(lambda: self.export_data('csv'))
        export_buttons_layout.addWidget(self.export_csv_btn)
        export_buttons_layout.addStretch()
        export_layout.addLayout(export_buttons_layout)
        
        layout.addWidget(export_group)
        
        # Import section
        import_group = QGroupBox("Import Extension Registry")
        import_layout = QVBoxLayout(import_group)
        
        import_buttons_layout = QHBoxLayout()
        self.import_json_btn = QPushButton("📄 Import JSON")
        self.import_json_btn.clicked.connect(lambda: self.import_data('json'))
        import_buttons_layout.addWidget(self.import_json_btn)
        
        self.import_csv_btn = QPushButton("📊 Import CSV")
        self.import_csv_btn.clicked.connect(lambda: self.import_data('csv'))
        import_buttons_layout.addWidget(self.import_csv_btn)
        import_buttons_layout.addStretch()
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
        
        self.tab_widget.addTab(tab, "📤 Import/Export")
    
    def load_data(self):
        """Load all data into the interface."""
        self.load_categories()
        self.load_extensions()
        self.load_mappings()
        self.load_unknown_extensions()
        self.update_status("Data loaded successfully")
    
    def load_categories(self):
        """Load categories into the table."""
        try:
            categories = self.manager.get_categories()
            self.categories_table.setRowCount(len(categories))
            
            for row, category in enumerate(categories):
                self.categories_table.setItem(row, 0, QTableWidgetItem(str(category['category_id'])))
                self.categories_table.setItem(row, 1, QTableWidgetItem(category['name']))
                self.categories_table.setItem(row, 2, QTableWidgetItem(category['description'] or ''))
                self.categories_table.setItem(row, 3, QTableWidgetItem(str(category['sort_order'])))
                self.categories_table.setItem(row, 4, QTableWidgetItem('Yes' if category['is_active'] else 'No'))
            
            # Update category combo boxes
            self.category_filter_combo.clear()
            self.category_filter_combo.addItem("All Categories", None)
            self.extension_category_combo.clear()
            
            for category in categories:
                self.category_filter_combo.addItem(category['name'], category['category_id'])
                self.extension_category_combo.addItem(category['name'], category['category_id'])
            
        except Exception as e:
            self.update_status(f"Error loading categories: {e}")
    
    def load_extensions(self):
        """Load extensions into the table."""
        try:
            extensions = self.manager.get_extensions()
            self.extensions_table.setRowCount(len(extensions))
            
            for row, extension in enumerate(extensions):
                self.extensions_table.setItem(row, 0, QTableWidgetItem(str(extension['extension_id'])))
                self.extensions_table.setItem(row, 1, QTableWidgetItem(extension['extension']))
                self.extensions_table.setItem(row, 2, QTableWidgetItem(extension['category_name']))
                self.extensions_table.setItem(row, 3, QTableWidgetItem(extension['description'] or ''))
                self.extensions_table.setItem(row, 4, QTableWidgetItem('Yes' if extension['is_rom'] else 'No'))
                self.extensions_table.setItem(row, 5, QTableWidgetItem('Yes' if extension['is_archive'] else 'No'))
                self.extensions_table.setItem(row, 6, QTableWidgetItem('Yes' if extension['is_save'] else 'No'))
                self.extensions_table.setItem(row, 7, QTableWidgetItem('Yes' if extension['is_patch'] else 'No'))
            
        except Exception as e:
            self.update_status(f"Error loading extensions: {e}")
    
    def load_mappings(self):
        """Load platform mappings into the table."""
        try:
            with self.manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT pe.*, p.name as platform_name, fe.extension
                    FROM platform_extension pe
                    JOIN platform p ON pe.platform_id = p.platform_id
                    JOIN file_extension fe ON pe.extension_id = fe.extension_id
                    ORDER BY p.name, fe.extension
                """)
                mappings = [dict(row) for row in cursor.fetchall()]
            
            self.mappings_table.setRowCount(len(mappings))
            
            for row, mapping in enumerate(mappings):
                self.mappings_table.setItem(row, 0, QTableWidgetItem(str(mapping['platform_extension_id'])))
                self.mappings_table.setItem(row, 1, QTableWidgetItem(mapping['platform_name']))
                self.mappings_table.setItem(row, 2, QTableWidgetItem(mapping['extension']))
                self.mappings_table.setItem(row, 3, QTableWidgetItem('Yes' if mapping['is_primary'] else 'No'))
                self.mappings_table.setItem(row, 4, QTableWidgetItem(f"{mapping['confidence']:.1f}"))
                
                # Add delete button
                delete_btn = QPushButton("Delete")
                delete_btn.clicked.connect(lambda checked, mid=mapping['platform_extension_id']: self.delete_mapping(mid))
                self.mappings_table.setCellWidget(row, 5, delete_btn)
            
            # Update platform and extension combo boxes
            self.mapping_platform_combo.clear()
            self.mapping_extension_combo.clear()
            
            # Load platforms
            cursor.execute("SELECT platform_id, name FROM platform ORDER BY name")
            platforms = cursor.fetchall()
            for platform in platforms:
                self.mapping_platform_combo.addItem(platform['name'], platform['platform_id'])
            
            # Load extensions
            extensions = self.manager.get_extensions(active_only=True)
            for extension in extensions:
                self.mapping_extension_combo.addItem(extension['extension'], extension['extension_id'])
            
        except Exception as e:
            self.update_status(f"Error loading mappings: {e}")
    
    def load_unknown_extensions(self):
        """Load unknown extensions into the table."""
        try:
            unknown_extensions = self.manager.get_unknown_extensions()
            self.unknown_table.setRowCount(len(unknown_extensions))
            
            for row, unknown in enumerate(unknown_extensions):
                self.unknown_table.setItem(row, 0, QTableWidgetItem(unknown['extension']))
                self.unknown_table.setItem(row, 1, QTableWidgetItem(str(unknown['file_count'])))
                self.unknown_table.setItem(row, 2, QTableWidgetItem(unknown['status']))
                self.unknown_table.setItem(row, 3, QTableWidgetItem(unknown['suggested_category'] or ''))
                self.unknown_table.setItem(row, 4, QTableWidgetItem(unknown['suggested_platform'] or ''))
                self.unknown_table.setItem(row, 5, QTableWidgetItem(unknown['notes'] or ''))
                
                # Add action buttons
                action_layout = QHBoxLayout()
                approve_btn = QPushButton("Approve")
                approve_btn.clicked.connect(lambda checked, uid=unknown['unknown_extension_id']: self.approve_unknown(uid))
                reject_btn = QPushButton("Reject")
                reject_btn.clicked.connect(lambda checked, uid=unknown['unknown_extension_id']: self.reject_unknown(uid))
                ignore_btn = QPushButton("Ignore")
                ignore_btn.clicked.connect(lambda checked, uid=unknown['unknown_extension_id']: self.ignore_unknown(uid))
                
                action_layout.addWidget(approve_btn)
                action_layout.addWidget(reject_btn)
                action_layout.addWidget(ignore_btn)
                
                action_widget = QWidget()
                action_widget.setLayout(action_layout)
                self.unknown_table.setCellWidget(row, 6, action_widget)
            
        except Exception as e:
            self.update_status(f"Error loading unknown extensions: {e}")
    
    def filter_extensions(self):
        """Filter extensions based on search criteria."""
        # This is a placeholder - in a real implementation, you would filter the table
        pass
    
    def filter_unknown_extensions(self):
        """Filter unknown extensions by status."""
        # This is a placeholder - in a real implementation, you would filter the table
        pass
    
    def on_category_selected(self):
        """Handle category selection."""
        current_row = self.categories_table.currentRow()
        if current_row >= 0:
            category_id = int(self.categories_table.item(current_row, 0).text())
            category = self.manager.get_category(category_id)
            if category:
                self.current_category_id = category_id
                self.category_name_edit.setText(category['name'])
                self.category_description_edit.setPlainText(category['description'] or "")
                self.category_sort_order_edit.setValue(category['sort_order'])
                self.category_active_check.setChecked(bool(category['is_active']))
                self.update_category_btn.setEnabled(True)
                self.delete_category_btn.setEnabled(True)
    
    def on_extension_selected(self):
        """Handle extension selection in the table."""
        current_row = self.extensions_table.currentRow()
        if current_row >= 0:
            # Enable/disable action buttons based on selection
            pass  # Implementation can be added here if needed
    
    def add_category(self):
        """Add a new category."""
        dialog = self._create_form_dialog("Add Category")
        layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()
        
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("e.g., Nintendo ROMs")
        form_layout.addRow("Name:", name_edit)
        
        description_edit = QTextEdit()
        description_edit.setMaximumHeight(80)
        description_edit.setPlaceholderText("Description")
        form_layout.addRow("Description:", description_edit)
        
        sort_order_spin = QSpinBox()
        sort_order_spin.setRange(0, 9999)
        sort_order_spin.setValue(0)
        form_layout.addRow("Sort Order:", sort_order_spin)
        
        active_check = QCheckBox("Active")
        active_check.setChecked(True)
        form_layout.addRow("", active_check)
        
        layout.addLayout(form_layout)
        self._add_dialog_buttons(dialog, layout)
        
        if dialog.exec_() == QDialog.Accepted:
            try:
                self.manager.create_category(
                    name=name_edit.text().strip(),
                    description=description_edit.toPlainText().strip() or None,
                    sort_order=sort_order_spin.value(),
                    is_active=active_check.isChecked()
                )
                self.load_categories()
                self._show_success_message("Success", "Category added successfully.")
            except Exception as e:
                self._show_error_message("Error", f"Failed to add category: {e}")
    
    def update_category(self):
        """Update the selected category."""
        if not self.current_category_id:
            self._show_warning_message("Warning", "Please select a category to update.")
            return
        
        try:
            success = self.manager.update_category(
                self.current_category_id,
                name=self.category_name_edit.text().strip(),
                description=self.category_description_edit.toPlainText().strip() or None,
                sort_order=self.category_sort_order_edit.value(),
                is_active=self.category_active_check.isChecked()
            )
            
            if success:
                self.load_categories()
                self._show_success_message("Success", "Category updated successfully.")
            else:
                self._show_warning_message("Warning", "Failed to update category.")
        except Exception as e:
            self._show_error_message("Error", f"Failed to update category: {e}")
    
    def delete_category(self):
        """Delete the selected category."""
        if not self.current_category_id:
            self._show_warning_message("Warning", "Please select a category to delete.")
            return
        
        if self._confirm_action("Confirm Delete", "Are you sure you want to delete this category?"):
            try:
                if self.manager.delete_category(self.current_category_id):
                    self.load_categories()
                    self.clear_category_form()
                    self._show_success_message("Success", "Category deleted successfully.")
                else:
                    self._show_warning_message("Warning", "Failed to delete category.")
            except Exception as e:
                self._show_error_message("Error", f"Failed to delete category: {e}")
    
    def clear_category_form(self):
        """Clear the category form."""
        self.category_name_edit.clear()
        self.category_description_edit.clear()
        self.category_sort_order_edit.setValue(0)
        self.category_active_check.setChecked(True)
        self.update_category_btn.setEnabled(False)
        self.delete_category_btn.setEnabled(False)
        self.current_category_id = None
    
    def add_extension(self):
        """Add a new file extension."""
        dialog = self._create_form_dialog("Add Extension")
        layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()
        
        extension_edit = QLineEdit()
        extension_edit.setPlaceholderText("e.g., .rom")
        form_layout.addRow("Extension:", extension_edit)
        
        category_combo = QComboBox()
        categories = self.manager.get_categories(active_only=True)
        for category in categories:
            category_combo.addItem(category['name'], category['category_id'])
        form_layout.addRow("Category:", category_combo)
        
        description_edit = QLineEdit()
        form_layout.addRow("Description:", description_edit)
        
        mime_edit = QLineEdit()
        form_layout.addRow("MIME Type:", mime_edit)
        
        is_rom_check = QCheckBox("ROM")
        is_archive_check = QCheckBox("Archive")
        is_save_check = QCheckBox("Save")
        is_patch_check = QCheckBox("Patch")
        form_layout.addRow("Types:", is_rom_check)
        form_layout.addRow("", is_archive_check)
        form_layout.addRow("", is_save_check)
        form_layout.addRow("", is_patch_check)
        
        layout.addLayout(form_layout)
        self._add_dialog_buttons(dialog, layout)
        
        if dialog.exec_() == QDialog.Accepted:
            extension = extension_edit.text().strip()
            if not extension.startswith('.'):
                extension = '.' + extension
            
            category_id = category_combo.currentData()
            description = description_edit.text().strip() or None
            mime_type = mime_edit.text().strip() or None
            
            try:
                self.manager.create_extension(
                    extension=extension,
                    category_id=category_id,
                    description=description,
                    mime_type=mime_type,
                    is_rom=is_rom_check.isChecked(),
                    is_archive=is_archive_check.isChecked(),
                    is_save=is_save_check.isChecked(),
                    is_patch=is_patch_check.isChecked()
                )
                self.load_extensions()
                self._show_success_message("Success", f"Extension {extension} added successfully.")
            except Exception as e:
                self._show_error_message("Error", f"Failed to add extension: {e}")
    
    def update_extension(self):
        """Update the selected extension."""
        # Implementation for updating extensions
        pass
    
    def delete_extension(self):
        """Delete the selected extension."""
        # Implementation for deleting extensions
        pass
    
    def add_mapping(self):
        """Add a new platform mapping."""
        platform_id = self.mapping_platform_combo.currentData()
        extension_id = self.mapping_extension_combo.currentData()
        
        if not platform_id or not extension_id:
            QMessageBox.warning(self, "Warning", "Please select both platform and extension.")
            return
        
        try:
            self.manager.add_platform_mapping(
                platform_id=platform_id,
                extension_id=extension_id,
                is_primary=self.mapping_primary_check.isChecked(),
                confidence=self.mapping_confidence_spin.value() / 100.0
            )
            self.load_mappings()
            QMessageBox.information(self, "Success", "Platform mapping added successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add mapping: {e}")
    
    def delete_mapping(self, mapping_id: int):
        """Delete a platform mapping."""
        reply = QMessageBox.question(
            self, "Confirm Delete", 
            "Are you sure you want to delete this mapping?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if self.manager.delete_platform_mapping(mapping_id):
                    self.load_mappings()
                    QMessageBox.information(self, "Success", "Mapping deleted successfully.")
                else:
                    QMessageBox.warning(self, "Warning", "Failed to delete mapping.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete mapping: {e}")
    
    def approve_unknown(self, unknown_id: int = None):
        """Approve an unknown extension."""
        if unknown_id is None:
            # Get selected unknown extension
            current_row = self.unknown_table.currentRow()
            if current_row < 0:
                QMessageBox.warning(self, "Warning", "Please select an unknown extension to approve.")
                return
            unknown_id = self.unknown_table.item(current_row, 0).data(Qt.UserRole)
        
        # Show approval dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Approve Unknown Extension")
        dialog.setModal(True)
        dialog.resize(400, 300)
        
        layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()
        
        category_combo = QComboBox()
        categories = self.manager.get_categories(active_only=True)
        for category in categories:
            category_combo.addItem(category['name'], category['category_id'])
        form_layout.addRow("Category:", category_combo)
        
        platform_combo = QComboBox()
        platform_combo.addItem("No Platform", None)
        # Load platforms
        with self.manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT platform_id, name FROM platform ORDER BY name")
            platforms = cursor.fetchall()
            for platform in platforms:
                platform_combo.addItem(platform['name'], platform['platform_id'])
        form_layout.addRow("Platform:", platform_combo)
        
        notes_edit = QTextEdit()
        notes_edit.setMaximumHeight(80)
        form_layout.addRow("Notes:", notes_edit)
        
        layout.addLayout(form_layout)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            try:
                success = self.manager.approve_unknown_extension(
                    unknown_id=unknown_id,
                    category_id=category_combo.currentData(),
                    platform_id=platform_combo.currentData(),
                    notes=notes_edit.toPlainText().strip() or None
                )
                
                if success:
                    self.load_unknown_extensions()
                    self.load_extensions()
                    QMessageBox.information(self, "Success", "Unknown extension approved successfully.")
                else:
                    QMessageBox.warning(self, "Warning", "Failed to approve unknown extension.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to approve unknown extension: {e}")
    
    def reject_unknown(self, unknown_id: int = None):
        """Reject an unknown extension."""
        if unknown_id is None:
            current_row = self.unknown_table.currentRow()
            if current_row < 0:
                QMessageBox.warning(self, "Warning", "Please select an unknown extension to reject.")
                return
            unknown_id = self.unknown_table.item(current_row, 0).data(Qt.UserRole)
        
        try:
            if self.manager.update_unknown_extension(unknown_id, status='rejected'):
                self.load_unknown_extensions()
                QMessageBox.information(self, "Success", "Unknown extension rejected.")
            else:
                QMessageBox.warning(self, "Warning", "Failed to reject unknown extension.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to reject unknown extension: {e}")
    
    def ignore_unknown(self, unknown_id: int = None):
        """Ignore an unknown extension."""
        if unknown_id is None:
            current_row = self.unknown_table.currentRow()
            if current_row < 0:
                QMessageBox.warning(self, "Warning", "Please select an unknown extension to ignore.")
                return
            unknown_id = self.unknown_table.item(current_row, 0).data(Qt.UserRole)
        
        try:
            if self.manager.update_unknown_extension(unknown_id, status='ignored'):
                self.load_unknown_extensions()
                QMessageBox.information(self, "Success", "Unknown extension ignored.")
            else:
                QMessageBox.warning(self, "Warning", "Failed to ignore unknown extension.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to ignore unknown extension: {e}")
    
    def export_data(self, format: str):
        """Export extension registry data."""
        file_filter = "JSON files (*.json)" if format == 'json' else "CSV files (*.csv)"
        file_path, _ = QFileDialog.getSaveFileName(
            self, f"Export Extension Registry ({format.upper()})", 
            f"extension_registry.{format}", file_filter
        )
        
        if not file_path:
            return
        
        try:
            success = self.manager.export_extensions(file_path, format)
            if success:
                self.status_text.append(f"✅ Export successful: {file_path}")
                self._show_success_message("Export Successful", f"Extension registry exported to:\n{file_path}")
            else:
                self.status_text.append(f"❌ Export failed: {file_path}")
                self._show_error_message("Export Failed", "Failed to export extension registry.")
        except Exception as e:
            self.status_text.append(f"❌ Export error: {e}")
            self._show_error_message("Export Error", f"Export failed: {e}")
    
    def import_data(self, format: str):
        """Import extension registry data."""
        file_filter = "JSON files (*.json)" if format == 'json' else "CSV files (*.csv)"
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Import Extension Registry ({format.upper()})", 
            "", file_filter
        )
        
        if not file_path:
            return
        
        try:
            overwrite = self.overwrite_check.isChecked()
            results = self.manager.import_extensions(file_path, format, overwrite)
            
            if results['success']:
                self._log_import_success(file_path, results)
                self.load_data()
                self._show_import_success_message(results)
            else:
                self._log_import_failure(file_path, results)
                self._show_import_error_message(results)
        except Exception as e:
            self.status_text.append(f"❌ Import error: {e}")
            self._show_error_message("Import Error", f"Import failed: {e}")
    
    def _log_import_success(self, file_path: str, results: dict):
        """Log successful import to status text."""
        self.status_text.append(f"✅ Import successful: {file_path}")
        self.status_text.append(f"   Categories: {results['categories_imported']}")
        self.status_text.append(f"   Extensions: {results['extensions_imported']}")
        self.status_text.append(f"   Mappings: {results['mappings_imported']}")
        self.status_text.append(f"   Unknown: {results['unknown_imported']}")
    
    def _log_import_failure(self, file_path: str, results: dict):
        """Log failed import to status text."""
        self.status_text.append(f"❌ Import failed: {file_path}")
    
    def _show_import_success_message(self, results: dict):
        """Show import success message dialog."""
        message = (
            f"Import completed successfully!\n\n"
            f"Categories: {results['categories_imported']}\n"
            f"Extensions: {results['extensions_imported']}\n"
            f"Mappings: {results['mappings_imported']}\n"
            f"Unknown: {results['unknown_imported']}"
        )
        self._show_success_message("Import Successful", message)
    
    def _show_import_error_message(self, results: dict):
        """Show import error message dialog."""
        error_msg = "\n".join(results['errors'][:5])  # Show first 5 errors
        if len(results['errors']) > 5:
            error_msg += f"\n... and {len(results['errors']) - 5} more errors"
        self._show_error_message("Import Failed", f"Import failed:\n{error_msg}")
    
    def update_status(self, message: str):
        """Update the status bar message."""
        self.status_bar.showMessage(message)
    
    def _create_form_dialog(self, title: str, width: int = 400, height: int = 300) -> QDialog:
        """Create a standard form dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setModal(True)
        dialog.resize(width, height)
        return dialog
    
    def _create_form_layout(self, dialog: QDialog) -> QFormLayout:
        """Create a standard form layout for a dialog."""
        layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()
        layout.addLayout(form_layout)
        return form_layout
    
    def _add_dialog_buttons(self, dialog: QDialog, layout: QVBoxLayout) -> QDialogButtonBox:
        """Add standard OK/Cancel buttons to a dialog."""
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        return buttons
    
    def _show_success_message(self, title: str, message: str):
        """Show a success message dialog."""
        QMessageBox.information(self, title, message)
    
    def _show_error_message(self, title: str, message: str):
        """Show an error message dialog."""
        QMessageBox.critical(self, title, message)
    
    def _show_warning_message(self, title: str, message: str):
        """Show a warning message dialog."""
        QMessageBox.warning(self, title, message)
    
    def _confirm_action(self, title: str, message: str) -> bool:
        """Show a confirmation dialog and return True if user confirms."""
        reply = QMessageBox.question(
            self, title, message,
            QMessageBox.Yes | QMessageBox.No
        )
        return reply == QMessageBox.Yes