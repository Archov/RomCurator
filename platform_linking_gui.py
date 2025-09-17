#!/usr/bin/env python3
"""
Platform Linking GUI v2 - Simplified Atomic vs Alias Management

This provides a clean interface for managing platform relationships where
one platform is the "atomic" (canonical) platform and others are "aliases".
"""

import sys
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QLineEdit, QComboBox, QGroupBox,
    QAbstractItemView, QMessageBox, QCheckBox, QSplitter, QWidget
)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QFont, QMouseEvent


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


class PlatformAliasDialog(QDialog):
    """Dialog for selecting platforms to add as aliases."""
    
    def __init__(self, available_platforms: List[Dict], parent=None):
        super().__init__(parent)
        self.available_platforms = available_platforms
        self.selected_platforms = []
        
        self.setWindowTitle("Add Platform Aliases")
        self.setModal(True)
        self.resize(500, 400)
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the dialog UI."""
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel("Select platforms to add as aliases:")
        instructions.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(instructions)
        
        # Search filter
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Filter:"))
        self.search_edit = QLineEdit()
        self.search_edit.textChanged.connect(self.filter_platforms)
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)
        
        # Platform list (multi-select)
        self.platform_list = QListWidget()
        self.platform_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.populate_platform_list()
        layout.addWidget(self.platform_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept_selection)
        self.ok_btn.setEnabled(False)
        button_layout.addWidget(self.ok_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Connect selection changes
        self.platform_list.itemSelectionChanged.connect(self.on_selection_changed)
        
    def populate_platform_list(self):
        """Populate the platform list."""
        self.platform_list.clear()
        
        for platform in self.available_platforms:
            item = QListWidgetItem(platform['name'])
            item.setData(Qt.UserRole, platform['platform_id'])
            self.platform_list.addItem(item)
            
    def filter_platforms(self):
        """Filter platforms based on search text."""
        search_text = self.search_edit.text().lower()
        
        for i in range(self.platform_list.count()):
            item = self.platform_list.item(i)
            platform_name = item.text().lower()
            item.setHidden(search_text not in platform_name)
            
    def on_selection_changed(self):
        """Handle selection changes."""
        selected_items = self.platform_list.selectedItems()
        self.ok_btn.setEnabled(len(selected_items) > 0)
        
    def accept_selection(self):
        """Accept the selected platforms."""
        selected_items = self.platform_list.selectedItems()
        self.selected_platforms = [
            {
                'platform_id': item.data(Qt.UserRole),
                'name': item.text()
            }
            for item in selected_items
        ]
        self.accept()


class PlatformLinkingDialog(QDialog):
    """Simplified platform linking dialog for atomic vs alias management."""
    
    def __init__(self, db_path: str, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.current_platform_id = None
        
        self.setWindowTitle("Platform Linking Manager v2")
        self.setModal(True)
        self.resize(1000, 494)
        self.setMinimumWidth(1000)
        
        # Make frameless to avoid white Windows title bar
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        
        # Inherit parent's stylesheet if available
        if parent and hasattr(parent, 'styleSheet'):
            self.setStyleSheet(parent.styleSheet())
        
        self.init_ui()
        self.load_platforms()
        
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        
        # Custom title bar
        title_bar = self.create_title_bar()
        layout.addWidget(title_bar)
        
        # Legend above the containers - compact
        legend = QLabel(
            "Manage platform relationships: ⚛️ = Atomic (canonical), 👓 = Alias, ⚪ = Unlinked"
        )
        legend.setWordWrap(True)
        legend.setFont(QFont("Arial", 14, QFont.Bold))
        legend.setStyleSheet("color: #666; margin: 0px 0px;")
        #legend.setFixedHeight(legend.sizeHint().height())  # Fixed height, won't grow
        layout.addWidget(legend)
        
        # Main content splitter - this will grow/shrink with window
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - All platforms (List A)
        left_group = QGroupBox("All Platforms")
        left_layout = QVBoxLayout()
        
        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Atomic", "Alias", "Unlinked"])
        self.filter_combo.currentTextChanged.connect(self.filter_platforms)
        filter_layout.addWidget(self.filter_combo)
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search platforms...")
        self.search_edit.textChanged.connect(self.filter_platforms)
        filter_layout.addWidget(self.search_edit)
        
        left_layout.addLayout(filter_layout)
        
        # Platform list (List A) - will grow with window
        self.platform_list = QListWidget()
        self.platform_list.itemClicked.connect(self.on_platform_selected)
        self.platform_list.setAlternatingRowColors(True)
        left_layout.addWidget(self.platform_list)
        
        left_group.setLayout(left_layout)
        splitter.addWidget(left_group)
        
        # Right panel - Current links (List B)
        right_group = QGroupBox("Current Links")
        right_layout = QVBoxLayout()
        
        # Search box for List B
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search links:"))
        self.links_search_edit = QLineEdit()
        self.links_search_edit.setPlaceholderText("Search linked platforms...")
        self.links_search_edit.textChanged.connect(self.filter_links)
        search_layout.addWidget(self.links_search_edit)
        right_layout.addLayout(search_layout)
        
        # Links list (List B) - will grow with window
        self.links_list = QListWidget()
        self.links_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.links_list.setAlternatingRowColors(True)
        right_layout.addWidget(self.links_list)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ Add Aliases")
        self.add_btn.clicked.connect(self.add_aliases)
        self.add_btn.setEnabled(False)
        button_layout.addWidget(self.add_btn)
        
        self.remove_btn = QPushButton("🗑️ Remove")
        self.remove_btn.clicked.connect(self.remove_links)
        self.remove_btn.setEnabled(False)
        button_layout.addWidget(self.remove_btn)
        
        self.atomic_btn = QPushButton("⚛️ Make Atomic")
        self.atomic_btn.clicked.connect(self.make_atomic)
        self.atomic_btn.setEnabled(False)
        button_layout.addWidget(self.atomic_btn)
        
        
        right_layout.addLayout(button_layout)
        
        right_group.setLayout(right_layout)
        splitter.addWidget(right_group)
        
        splitter.setSizes([500, 500])
        layout.addWidget(splitter, 1)  # Stretch factor 1 - will grow/shrink
        
        # Bottom buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_data)
        bottom_layout.addWidget(self.refresh_btn)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(self.close_btn)
        
        layout.addLayout(bottom_layout)
        
        self.setLayout(layout)
        
        # Connect selection changes
        self.links_list.itemSelectionChanged.connect(self.on_links_selection_changed)
        
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
        title_label = QLabel("Platform Linking Manager v2")
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
        
    def load_platforms(self):
        """Load all platforms and their link status."""
        cursor = self.conn.cursor()
        
        # Get all platforms with their link status
        cursor.execute("""
            SELECT 
                p.platform_id,
                p.name,
                CASE WHEN EXISTS (
                    SELECT 1 FROM platform_links pl 
                    WHERE pl.atomic_platform_id = p.platform_id
                ) THEN 'atomic'
                WHEN EXISTS (
                    SELECT 1 FROM platform_links pl 
                    WHERE pl.dat_platform_id = p.platform_id
                ) THEN 'alias'
                ELSE 'unlinked'
                END as link_status
            FROM platform p
            ORDER BY p.name
        """)
        
        self.platforms = cursor.fetchall()
        self.populate_platform_list()
        
    def populate_platform_list(self, platforms=None):
        """Populate the platform list with status indicators."""
        if platforms is None:
            platforms = self.platforms
            
        self.platform_list.clear()
        
        for platform in platforms:
            status = platform['link_status']
            
            # Choose emoji based on status
            if status == 'atomic':
                emoji = '⚛️'
            elif status == 'alias':
                emoji = '👓'
            else:  # unlinked
                emoji = '⚪'
                
            item_text = f"{emoji} {platform['name']}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, platform['platform_id'])
            item.setData(Qt.UserRole + 1, platform['link_status'])
            self.platform_list.addItem(item)
            
    def filter_platforms(self):
        """Filter platforms based on filter combo and search text."""
        filter_type = self.filter_combo.currentText()
        search_text = self.search_edit.text().lower()
        
        filtered_platforms = []
        for platform in self.platforms:
            # Apply type filter
            if filter_type != "All" and platform['link_status'] != filter_type.lower():
                continue
                
            # Apply text filter
            if search_text and search_text not in platform['name'].lower():
                continue
                
            filtered_platforms.append(platform)
            
        self.populate_platform_list(filtered_platforms)
        
    def filter_links(self):
        """Filter the links list based on search text."""
        search_text = self.links_search_edit.text().lower()
        
        for i in range(self.links_list.count()):
            item = self.links_list.item(i)
            if item:
                item_text = item.text().lower()
                item.setHidden(search_text and search_text not in item_text)
        
    def on_platform_selected(self, item):
        """Handle platform selection in List A."""
        self.current_platform_id = item.data(Qt.UserRole)
        platform_name = item.text().split(' ', 1)[1]  # Remove emoji
        link_status = item.data(Qt.UserRole + 1)
        
        # Load and display current links
        self.load_current_links()
        
        # Enable/disable buttons based on selection
        self.add_btn.setEnabled(True)
        self.atomic_btn.setEnabled(True)
        
    def load_current_links(self):
        """Load current links for the selected platform."""
        if not self.current_platform_id:
            return
            
        cursor = self.conn.cursor()
        
        # First, find the atomic platform for this group
        atomic_platform_id = self.get_atomic_platform_id(self.current_platform_id)
        
        # Get ALL platforms in this group EXCEPT the selected one
        cursor.execute("""
            SELECT 
                p.platform_id,
                p.name,
                CASE WHEN p.platform_id = ? THEN 'atomic'
                     ELSE 'alias'
                END as role
            FROM platform p
            WHERE p.platform_id != ?
              AND (p.platform_id = ? 
                   OR p.platform_id IN (
                       SELECT dat_platform_id FROM platform_links 
                       WHERE atomic_platform_id = ?
                   )
                   OR p.platform_id IN (
                       SELECT atomic_platform_id FROM platform_links 
                       WHERE dat_platform_id = ?
                   ))
            ORDER BY 
                CASE WHEN p.platform_id = ? THEN 0 ELSE 1 END,
                p.name
        """, (atomic_platform_id, self.current_platform_id, atomic_platform_id, 
              atomic_platform_id, atomic_platform_id, atomic_platform_id))
        
        links = cursor.fetchall()
        
        self.links_list.clear()
        
        if not links:
            self.links_list.addItem("No links found")
            self.remove_btn.setEnabled(False)
            return
            
        for link in links:
            role = link['role']
            emoji = '⚛️' if role == 'atomic' else '👓'
            item_text = f"{emoji} {link['name']}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, link['platform_id'])
            item.setData(Qt.UserRole + 1, role)
            self.links_list.addItem(item)
            
        self.remove_btn.setEnabled(True)
        
    def on_links_selection_changed(self):
        """Handle selection changes in links list."""
        selected_items = self.links_list.selectedItems()
        self.remove_btn.setEnabled(len(selected_items) > 0)
        
    def add_aliases(self):
        """Add aliases to the current platform."""
        if not self.current_platform_id:
            return
            
        # Get available platforms (completely unlinked platforms only)
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT p.platform_id, p.name
            FROM platform p
            WHERE p.platform_id != ?
            AND p.platform_id NOT IN (
                SELECT atomic_platform_id FROM platform_links
                UNION
                SELECT dat_platform_id FROM platform_links
            )
            ORDER BY p.name
        """, (self.current_platform_id,))
        
        available_platforms = [dict(row) for row in cursor.fetchall()]
        
        if not available_platforms:
            QMessageBox.information(
                self, "No Available Platforms",
                "All platforms are already linked to this platform."
            )
            return
            
        # Open alias selection dialog
        dialog = PlatformAliasDialog(available_platforms, self)
        if dialog.exec_() == QDialog.Accepted:
            self.create_links(dialog.selected_platforms)
            
    def create_links(self, selected_platforms: List[Dict]):
        """Create links between platforms."""
        if not selected_platforms:
            return
            
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("BEGIN TRANSACTION")
            
            for platform in selected_platforms:
                # Determine which is atomic and which is alias
                # If current platform is already atomic, new platforms become aliases
                # If current platform is alias, find its atomic platform
                # If current platform is unlinked, it becomes atomic
                
                current_status = self.get_platform_status(self.current_platform_id)
                
                if current_status == 'unlinked':
                    # Current platform becomes atomic, new platform becomes alias
                    atomic_id = self.current_platform_id
                    alias_id = platform['platform_id']
                else:
                    # Find the atomic platform for this group
                    atomic_id = self.get_atomic_platform_id(self.current_platform_id)
                    alias_id = platform['platform_id']
                
                # Create the link
                cursor.execute("""
                    INSERT OR IGNORE INTO platform_links 
                    (atomic_platform_id, dat_platform_id, confidence)
                    VALUES (?, ?, 1.0)
                """, (atomic_id, alias_id))
            
            cursor.execute("COMMIT")
            self.refresh_data()
            
            QMessageBox.information(
                self, "Links Created",
                f"Created {len(selected_platforms)} platform links."
            )
            
        except Exception as e:
            cursor.execute("ROLLBACK")
            QMessageBox.critical(
                self, "Error",
                f"Failed to create links: {e}"
            )
            
    def remove_links(self):
        """Remove selected links. If removing an atomic platform, first make the selected item from List A the new atomic."""
        selected_items = self.links_list.selectedItems()
        if not selected_items:
            return
            
        cursor = self.conn.cursor()
        
        # Check if any of the selected items are atomic platforms
        atomic_platforms_to_remove = []
        for item in selected_items:
            platform_id = item.data(Qt.UserRole)
            role = item.data(Qt.UserRole + 1)
            if role == 'atomic':
                atomic_platforms_to_remove.append(platform_id)
        
        # If we're removing atomic platforms, first make the selected item from List A the new atomic
        if atomic_platforms_to_remove:
            if not self.current_platform_id:
                QMessageBox.information(
                    self, "No Selection",
                    "Please select a platform from the platform list to become the new atomic."
                )
                return
                
            # Get all platforms in the current group
            current_atomic_id = self.get_atomic_platform_id(self.current_platform_id)
            all_platforms = self.get_all_platforms_in_group(current_atomic_id)
            
            # Make the selected item from List A the new atomic for all platforms in the group
            other_platforms = [pid for pid in all_platforms if pid != self.current_platform_id]
            
            # Delete ALL existing links for this group
            cursor.execute("""
                DELETE FROM platform_links
                WHERE atomic_platform_id IN ({})
                   OR dat_platform_id IN ({})
            """.format(','.join('?' * len(all_platforms)), 
                       ','.join('?' * len(all_platforms))), 
                       all_platforms + all_platforms)
            
            # Create new links with the selected platform as atomic
            for platform_id in other_platforms:
                cursor.execute("""
                    INSERT INTO platform_links 
                    (atomic_platform_id, dat_platform_id, confidence)
                    VALUES (?, ?, 1.0)
                """, (self.current_platform_id, platform_id))
        
        # Now remove the specific links for the selected items
        for item in selected_items:
            platform_id = item.data(Qt.UserRole)
            
            # Remove the link between the selected platform and the item from List A
            cursor.execute("""
                DELETE FROM platform_links
                WHERE (atomic_platform_id = ? AND dat_platform_id = ?)
                   OR (atomic_platform_id = ? AND dat_platform_id = ?)
            """, (self.current_platform_id, platform_id,
                  platform_id, self.current_platform_id))
        
        cursor.execute("COMMIT")
        self.refresh_data()
        
        if atomic_platforms_to_remove:
            QMessageBox.information(
                self, "Atomic Platform Removed",
                f"Removed atomic platform(s) and made the selected platform the new atomic."
            )
        else:
            QMessageBox.information(
                self, "Links Removed",
                f"Removed {len(selected_items)} platform links."
            )
            
    def make_atomic(self):
        """Make the selected platform from List B the atomic platform for its group."""
        # Get the selected item from List B (links list)
        current_item = self.links_list.currentItem()
        if not current_item:
            QMessageBox.information(
                self, "No Selection",
                "Please select a platform from the links list to make atomic."
            )
            return
            
        # Get the platform ID from the selected item
        selected_platform_id = current_item.data(Qt.UserRole)
        if not selected_platform_id:
            QMessageBox.information(
                self, "Invalid Selection",
                "Please select a valid platform from the links list."
            )
            return
            
        # Get all platforms in the current group (including the selected one)
        cursor = self.conn.cursor()
        atomic_platform_id = self.get_atomic_platform_id(self.current_platform_id)
        
        # Get ALL platforms in this group using a recursive approach
        all_platforms = self.get_all_platforms_in_group(atomic_platform_id)
        
        if len(all_platforms) <= 1:
            QMessageBox.information(
                self, "No Links",
                "This platform has no links to make atomic."
            )
            return
            
        # Remove the selected platform from the list of platforms to link to
        other_platforms = [pid for pid in all_platforms if pid != selected_platform_id]
        
        # Get the selected platform name for the dialog
        selected_platform_name = current_item.text().split(' ', 1)[1]  # Remove emoji
        
        reply = QMessageBox.question(
            self, "Make Atomic",
            f"Make '{selected_platform_name}' atomic for {len(other_platforms)} linked platforms?\n\n"
            f"This will change the atomic platform for the entire group.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
            
        try:
            cursor.execute("BEGIN TRANSACTION")
            
            # Delete ALL existing links for this group
            cursor.execute("""
                DELETE FROM platform_links
                WHERE atomic_platform_id IN ({})
                   OR dat_platform_id IN ({})
            """.format(','.join('?' * len(all_platforms)), 
                       ','.join('?' * len(all_platforms))), 
                       all_platforms + all_platforms)
            
            # Create new links with selected platform as atomic
            for platform_id in other_platforms:
                cursor.execute("""
                    INSERT INTO platform_links 
                    (atomic_platform_id, dat_platform_id, confidence)
                    VALUES (?, ?, 1.0)
                """, (selected_platform_id, platform_id))
            
            cursor.execute("COMMIT")
            
            # Force a complete refresh of the GUI
            self.refresh_data()
            
            QMessageBox.information(
                self, "Platform Made Atomic",
                f"'{selected_platform_name}' is now atomic for {len(other_platforms)} linked platforms.\n\n"
                f"All links in this group have been updated."
            )
            
        except Exception as e:
            cursor.execute("ROLLBACK")
            QMessageBox.critical(
                self, "Error",
                f"Failed to make platform atomic: {e}"
            )
            
    def get_platform_status(self, platform_id: int) -> str:
        """Get the link status of a platform."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                CASE WHEN EXISTS (
                    SELECT 1 FROM platform_links WHERE atomic_platform_id = ?
                ) THEN 'atomic'
                WHEN EXISTS (
                    SELECT 1 FROM platform_links WHERE dat_platform_id = ?
                ) THEN 'alias'
                ELSE 'unlinked'
                END as status
        """, (platform_id, platform_id))
        
        result = cursor.fetchone()
        return result['status'] if result else 'unlinked'
        
    def get_atomic_platform_id(self, platform_id: int) -> int:
        """Get the atomic platform ID for a given platform."""
        cursor = self.conn.cursor()
        
        # Check if it's already atomic
        cursor.execute("""
            SELECT atomic_platform_id FROM platform_links WHERE atomic_platform_id = ?
        """, (platform_id,))
        
        result = cursor.fetchone()
        if result:
            return platform_id
            
        # Find its atomic platform
        cursor.execute("""
            SELECT atomic_platform_id FROM platform_links WHERE dat_platform_id = ?
        """, (platform_id,))
        
        result = cursor.fetchone()
        return result['atomic_platform_id'] if result else platform_id
        
    def get_all_platforms_in_group(self, atomic_platform_id: int) -> List[int]:
        """Get all platforms in the same group as the given atomic platform."""
        cursor = self.conn.cursor()
        visited = set()
        to_visit = {atomic_platform_id}
        all_platforms = set()
        
        while to_visit:
            current_id = to_visit.pop()
            if current_id in visited:
                continue
                
            visited.add(current_id)
            all_platforms.add(current_id)
            
            # Find all platforms linked to this one (both directions)
            cursor.execute("""
                SELECT dat_platform_id FROM platform_links WHERE atomic_platform_id = ?
                UNION
                SELECT atomic_platform_id FROM platform_links WHERE dat_platform_id = ?
            """, (current_id, current_id))
            
            linked_platforms = [row['dat_platform_id'] for row in cursor.fetchall()]
            
            for platform_id in linked_platforms:
                if platform_id not in visited:
                    to_visit.add(platform_id)
        
        return list(all_platforms)
        
    def refresh_data(self):
        """Refresh all data from database."""
        # Remember current filter selection
        current_filter = self.filter_combo.currentText()
        current_search = self.search_edit.text()
        
        self.load_platforms()
        
        # Restore filter selection and reapply filtering
        self.filter_combo.setCurrentText(current_filter)
        self.search_edit.setText(current_search)
        self.filter_platforms()
        
        if self.current_platform_id:
            self.load_current_links()
        
    def closeEvent(self, event):
        """Handle dialog close event."""
        self.conn.close()
        event.accept()


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Test the dialog
    dialog = PlatformLinkingDialog('database/RomCurator.db')
    dialog.show()
    
    sys.exit(app.exec_())
