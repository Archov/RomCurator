"""
GUI interface for manual curation of DAT-to-metadata matches.

This allows users to review and confirm potential matches between atomic games
and DAT entries that weren't automatically linked.
"""

import sys
import sqlite3
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QSplitter,
    QTextEdit, QComboBox, QSpinBox, QGroupBox, QMessageBox,
    QProgressBar, QStatusBar, QHeaderView, QAbstractItemView
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import qdarkstyle

# Add the scripts/seeders directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent / 'scripts' / 'seeders'))

from matching_engine import GameMatcher, create_dat_atomic_link_table


class MatchingWorker(QThread):
    """Worker thread for finding matches without blocking the GUI."""
    
    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(list)     # results
    error = pyqtSignal(str)         # error message
    
    def __init__(self, db_path, min_confidence=0.5, max_confidence=0.95):
        super().__init__()
        self.db_path = db_path
        self.min_confidence = min_confidence
        self.max_confidence = max_confidence
    
    def run(self):
        try:
            matcher = GameMatcher(self.db_path)
            try:
                # Get curation queue
                queue = matcher.get_manual_curation_queue(self.min_confidence, self.max_confidence)
                self.finished.emit(queue)
            finally:
                matcher.close()
        except Exception as e:
            self.error.emit(str(e))


class CurationMainWindow(QMainWindow):
    """Main window for the curation interface."""
    
    def __init__(self, db_path, config_manager=None):
        """
        Initialize the curation main window.
        
        Creates a GameMatcher for the given SQLite database path, prepares internal state for the manual curation queue, loads or creates a ConfigManager if one is not provided, builds the user interface, and begins loading the curation queue.
        
        Parameters:
            db_path (str | pathlib.Path): Path to the SQLite database file used by GameMatcher.
            config_manager (ConfigManager, optional): Preconstructed configuration manager instance. If omitted, a ConfigManager is imported and instantiated.
        
        Side effects:
            - Constructs UI widgets and starts loading the curation queue (which will spawn a background worker).
        """
        super().__init__()
        self.db_path = db_path
        self.matcher = GameMatcher(db_path)
        self.curation_queue = []
        self.current_item = None
        
        # Store config for future use
        if config_manager:
            self.config = config_manager
        else:
            from config_manager import ConfigManager
            self.config = ConfigManager()
        
        self.init_ui()
        self.load_curation_queue()
    
    def closeEvent(self, event):
        """Clean up when closing."""
        if self.matcher:
            self.matcher.close()
        event.accept()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle('DAT-Metadata Curation Interface')
        self.setGeometry(100, 100, 1400, 900)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel: Game list and controls
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel: Match details and actions
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([500, 900])
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Create progress bar (hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
    
    def create_left_panel(self):
        """Create the left panel with game list and controls."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Controls group
        controls_group = QGroupBox("Controls")
        controls_layout = QVBoxLayout(controls_group)
        
        # Confidence range controls
        confidence_layout = QHBoxLayout()
        confidence_layout.addWidget(QLabel("Min Confidence:"))
        self.min_confidence_spin = QSpinBox()
        self.min_confidence_spin.setRange(0, 100)
        self.min_confidence_spin.setValue(50)
        self.min_confidence_spin.setSuffix("%")
        confidence_layout.addWidget(self.min_confidence_spin)
        
        confidence_layout.addWidget(QLabel("Max Confidence:"))
        self.max_confidence_spin = QSpinBox()
        self.max_confidence_spin.setRange(0, 100)
        self.max_confidence_spin.setValue(95)
        self.max_confidence_spin.setSuffix("%")
        confidence_layout.addWidget(self.max_confidence_spin)
        
        controls_layout.addLayout(confidence_layout)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Refresh Queue")
        self.refresh_btn.clicked.connect(self.load_curation_queue)
        button_layout.addWidget(self.refresh_btn)
        
        self.auto_link_btn = QPushButton("Auto-Link High Confidence")
        self.auto_link_btn.clicked.connect(self.auto_link_high_confidence)
        button_layout.addWidget(self.auto_link_btn)
        
        controls_layout.addLayout(button_layout)
        layout.addWidget(controls_group)
        
        # Games table
        games_group = QGroupBox("Games Needing Curation")
        games_layout = QVBoxLayout(games_group)
        
        self.games_table = QTableWidget()
        self.games_table.setColumnCount(4)
        self.games_table.setHorizontalHeaderLabels(["Game Title", "Platforms", "Matches", "Best Match %"])
        self.games_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.games_table.itemSelectionChanged.connect(self.on_game_selected)
        
        # Auto-resize columns
        header = self.games_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        games_layout.addWidget(self.games_table)
        layout.addWidget(games_group)
        
        return panel
    
    def create_right_panel(self):
        """Create the right panel with match details."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Current game info
        game_info_group = QGroupBox("Selected Game")
        game_info_layout = QVBoxLayout(game_info_group)
        
        self.game_title_label = QLabel("No game selected")
        self.game_title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        game_info_layout.addWidget(self.game_title_label)
        
        self.game_details_text = QTextEdit()
        self.game_details_text.setMaximumHeight(100)
        self.game_details_text.setReadOnly(True)
        game_info_layout.addWidget(self.game_details_text)
        
        layout.addWidget(game_info_group)
        
        # Potential matches
        matches_group = QGroupBox("Potential DAT Matches")
        matches_layout = QVBoxLayout(matches_group)
        
        self.matches_table = QTableWidget()
        self.matches_table.setColumnCount(5)
        self.matches_table.setHorizontalHeaderLabels(["DAT Title", "Base Title", "Platform", "Confidence", "Action"])
        self.matches_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        # Auto-resize columns
        matches_header = self.matches_table.horizontalHeader()
        matches_header.setSectionResizeMode(0, QHeaderView.Stretch)
        matches_header.setSectionResizeMode(1, QHeaderView.Stretch)
        matches_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        matches_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        matches_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        matches_layout.addWidget(self.matches_table)
        layout.addWidget(matches_group)
        
        # Action buttons
        action_group = QGroupBox("Actions for Selected Game")
        action_layout = QHBoxLayout(action_group)
        
        self.skip_btn = QPushButton("Skip This Game")
        self.skip_btn.clicked.connect(self.skip_current_game)
        self.skip_btn.setEnabled(False)
        action_layout.addWidget(self.skip_btn)
        
        self.no_match_btn = QPushButton("Mark as No Match")
        self.no_match_btn.clicked.connect(self.mark_no_match)
        self.no_match_btn.setEnabled(False)
        action_layout.addWidget(self.no_match_btn)
        
        layout.addWidget(action_group)
        
        return panel
    
    def load_curation_queue(self):
        """Load the curation queue from the database."""
        self.refresh_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_bar.showMessage("Loading curation queue...")
        
        # Get confidence values
        min_conf = self.min_confidence_spin.value() / 100.0
        max_conf = self.max_confidence_spin.value() / 100.0
        
        # Start worker thread
        self.worker = MatchingWorker(self.db_path, min_conf, max_conf)
        self.worker.finished.connect(self.on_queue_loaded)
        self.worker.error.connect(self.on_queue_error)
        self.worker.start()
    
    def on_queue_loaded(self, queue):
        """Handle completion of queue loading."""
        self.curation_queue = queue
        self.populate_games_table()
        
        self.progress_bar.setVisible(False)
        self.refresh_btn.setEnabled(True)
        self.status_bar.showMessage(f"Loaded {len(queue)} games needing curation")
    
    def on_queue_error(self, error_msg):
        """Handle errors during queue loading."""
        self.progress_bar.setVisible(False)
        self.refresh_btn.setEnabled(True)
        self.status_bar.showMessage("Error loading queue")
        
        QMessageBox.critical(self, "Error", f"Failed to load curation queue:\n{error_msg}")
    
    def populate_games_table(self):
        """Populate the games table with curation queue data."""
        self.games_table.setRowCount(len(self.curation_queue))
        
        for row, item in enumerate(self.curation_queue):
            # Game title
            title_item = QTableWidgetItem(item['atomic_title'])
            title_item.setData(Qt.UserRole, item)
            self.games_table.setItem(row, 0, title_item)
            
            # Platforms (from best match)
            platform_item = QTableWidgetItem(item['best_match'].platform_name)
            self.games_table.setItem(row, 1, platform_item)
            
            # Match count
            count_item = QTableWidgetItem(str(item['match_count']))
            self.games_table.setItem(row, 2, count_item)
            
            # Best match confidence
            confidence_item = QTableWidgetItem(f"{item['best_match'].confidence:.1%}")
            self.games_table.setItem(row, 3, confidence_item)
    
    def on_game_selected(self):
        """Handle selection of a game in the list."""
        current_row = self.games_table.currentRow()
        if current_row < 0 or current_row >= len(self.curation_queue):
            self.current_item = None
            self.update_match_details(None)
            return
        
        self.current_item = self.curation_queue[current_row]
        self.update_match_details(self.current_item)
    
    def update_match_details(self, item):
        """Update the match details panel."""
        if not item:
            self.game_title_label.setText("No game selected")
            self.game_details_text.clear()
            self.matches_table.setRowCount(0)
            self.skip_btn.setEnabled(False)
            self.no_match_btn.setEnabled(False)
            return
        
        # Update game info
        self.game_title_label.setText(item['atomic_title'])
        
        # Get additional game details
        cursor = self.matcher.conn.cursor()
        cursor.execute("""
            SELECT COUNT(gr.release_id) as release_count,
                   GROUP_CONCAT(DISTINCT p.name) as platforms,
                   acm.release_date, acm.description
            FROM atomic_game_unit agu
            LEFT JOIN game_release gr ON agu.atomic_id = gr.atomic_id
            LEFT JOIN platform p ON gr.platform_id = p.platform_id
            LEFT JOIN atomic_core_metadata acm ON agu.atomic_id = acm.atomic_id
            WHERE agu.atomic_id = ?
            GROUP BY agu.atomic_id
        """, (item['atomic_id'],))
        
        details = cursor.fetchone()
        if details:
            details_text = f"Releases: {details['release_count']}\n"
            details_text += f"Platforms: {details['platforms'] or 'Unknown'}\n"
            details_text += f"Release Date: {details['release_date'] or 'Unknown'}\n"
            if details['description']:
                details_text += f"Description: {details['description'][:200]}..."
            
            self.game_details_text.setText(details_text)
        
        # Populate matches table
        matches = item['all_matches']
        self.matches_table.setRowCount(len(matches))
        
        for row, match in enumerate(matches):
            # DAT title
            dat_title_item = QTableWidgetItem(match.dat_title)
            self.matches_table.setItem(row, 0, dat_title_item)
            
            # Base title
            base_title_item = QTableWidgetItem(match.base_title)
            self.matches_table.setItem(row, 1, base_title_item)
            
            # Platform
            platform_item = QTableWidgetItem(match.platform_name)
            self.matches_table.setItem(row, 2, platform_item)
            
            # Confidence
            confidence_item = QTableWidgetItem(f"{match.confidence:.1%}")
            self.matches_table.setItem(row, 3, confidence_item)
            
            # Action button
            action_btn = QPushButton("Link This Match")
            action_btn.clicked.connect(lambda checked, m=match: self.create_link(m))
            self.matches_table.setCellWidget(row, 4, action_btn)
        
        # Enable action buttons
        self.skip_btn.setEnabled(True)
        self.no_match_btn.setEnabled(True)
    
    def create_link(self, match):
        """Create a link between atomic game and DAT entry."""
        try:
            cursor = self.matcher.conn.cursor()
            
            # Check if link already exists
            cursor.execute("""
                SELECT link_id FROM dat_atomic_link 
                WHERE atomic_id = ? AND dat_entry_id = ?
            """, (match.atomic_id, match.dat_entry_id))
            
            if cursor.fetchone():
                QMessageBox.information(self, "Info", "This link already exists.")
                return
            
            # Create the link
            cursor.execute("""
                INSERT INTO dat_atomic_link (atomic_id, dat_entry_id, confidence, match_type)
                VALUES (?, ?, ?, 'manual')
            """, (match.atomic_id, match.dat_entry_id, match.confidence))
            
            self.matcher.conn.commit()
            
            QMessageBox.information(self, "Success", f"Successfully linked '{match.atomic_title}' to '{match.base_title}'")
            
            # Remove this item from the curation queue and refresh
            self.remove_current_from_queue()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create link:\n{e}")
            self.matcher.conn.rollback()
    
    def skip_current_game(self):
        """Skip the current game (move to next)."""
        if not self.current_item:
            return
        
        self.remove_current_from_queue()
    
    def mark_no_match(self):
        """Mark the current game as having no matches."""
        if not self.current_item:
            return
        
        reply = QMessageBox.question(
            self, "Confirm No Match",
            f"Mark '{self.current_item['atomic_title']}' as having no DAT matches?\n\n"
            "This will create a record indicating no match exists.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                cursor = self.matcher.conn.cursor()
                
                # Create a special "no match" record
                cursor.execute("""
                    INSERT INTO dat_atomic_link (atomic_id, dat_entry_id, confidence, match_type)
                    VALUES (?, NULL, 0.0, 'no_match')
                """, (self.current_item['atomic_id'],))
                
                self.matcher.conn.commit()
                self.remove_current_from_queue()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to mark as no match:\n{e}")
                self.matcher.conn.rollback()
    
    def remove_current_from_queue(self):
        """Remove the current item from the queue and update display."""
        if not self.current_item:
            return
        
        # Find and remove the current item
        current_row = self.games_table.currentRow()
        if current_row >= 0:
            self.curation_queue.pop(current_row)
            self.games_table.removeRow(current_row)
            
            # Update status
            self.status_bar.showMessage(f"{len(self.curation_queue)} games remaining for curation")
            
            # Select next item if available
            if self.curation_queue and current_row < len(self.curation_queue):
                self.games_table.setCurrentRow(current_row)
            elif self.curation_queue:
                self.games_table.setCurrentRow(len(self.curation_queue) - 1)
            else:
                self.current_item = None
                self.update_match_details(None)
    
    def auto_link_high_confidence(self):
        """Automatically link all high-confidence matches."""
        reply = QMessageBox.question(
            self, "Auto-Link Confirmation",
            "Automatically create links for all matches with >95% confidence?\n\n"
            "This will create links without manual review.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                stats = self.matcher.create_automatic_links(0.95)
                
                QMessageBox.information(
                    self, "Auto-Link Complete",
                    f"Automatic linking completed:\n\n"
                    f"Created: {stats['created']} links\n"
                    f"Skipped: {stats['skipped']} (already existed)\n"
                    f"Errors: {stats['errors']}"
                )
                
                # Refresh the queue
                self.load_curation_queue()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Auto-linking failed:\n{e}")


def main():
    """Main entry point for the curation GUI."""
    import argparse
    
    parser = argparse.ArgumentParser(description="DAT-Metadata Curation GUI")
    parser.add_argument('--db_path', help="Path to the SQLite database file")
    args = parser.parse_args()
    
    # Use default database path if not provided
    if not args.db_path:
        config_file = Path('config.json')
        if config_file.exists():
            import json
            with open(config_file, 'r') as f:
                config = json.load(f)
                args.db_path = config.get('database_path', './database/RomCurator.db')
        else:
            args.db_path = './database/RomCurator.db'
    
    # Check if database exists
    if not Path(args.db_path).exists():
        print(f"Error: Database file not found at {args.db_path}")
        sys.exit(1)
    
    # Ensure the dat_atomic_link table exists
    try:
        create_dat_atomic_link_table(args.db_path)
    except Exception as e:
        print(f"Warning: Could not create/verify dat_atomic_link table: {e}")
    
    # Create and run the application
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    
    window = CurationMainWindow(args.db_path)
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
