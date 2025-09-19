import sys
import json
import sqlite3
import subprocess
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QPushButton, QFileDialog, QListWidget, QMessageBox, QInputDialog,
    QLabel, QLineEdit, QDialog, QDialogButtonBox, QFormLayout, QAbstractItemView
)
# Import the new, final theme library
import qdarkstyle


# --- Configuration Loader ---
CONFIG_FILE = Path('config.json')

def load_config():
    """Loads configuration from a JSON file."""
    if not CONFIG_FILE.exists():
        # Create a default config if one doesn't exist
        default_config = {
            "database_path": "../database/atomic_games.sqlite",
            "importer_scripts_directory": "./scripts/seeders/"
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(default_config, f, indent=4)
            return default_config
        except IOError as e:
            # This is a critical failure, we can't run without a config.
            raise SystemExit(f"FATAL: Could not create default config file at {CONFIG_FILE.resolve()}: {e}")

    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        raise SystemExit(f"FATAL: Could not read or parse config file at {CONFIG_FILE.resolve()}: {e}")

# Load configuration at startup
config = load_config()
DATABASE_FILE = Path(config.get("database_path", "../database/atomic_games.sqlite"))
IMPORTER_SCRIPTS_DIR = Path(config.get("importer_scripts_directory", "./scripts/seeders/"))


# --- Database Helper Class ---
class DatabaseManager:
    """Handles all database interactions."""
    def __init__(self, db_file):
        self.db_file = db_file
        if not self.db_file.parent.exists():
            self.db_file.parent.mkdir(parents=True)

    def get_connection(self):
        try:
            return sqlite3.connect(self.db_file)
        except sqlite3.Error as e:
            QMessageBox.critical(None, "Database Connection Error", f"Could not connect to database at:\n{self.db_file.resolve()}\n\nError: {e}")
            return None
            
    def check_schema(self):
        """Checks if a key table exists to determine if DB is initialized."""
        conn = self.get_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='metadata_source';")
            if cursor.fetchone() is None:
                conn.close()
                return False
        except sqlite3.Error:
            conn.close()
            return False
        conn.close()
        return True

    def get_metadata_sources(self):
        """Fetches all metadata sources from the database."""
        conn = self.get_connection()
        if not conn: return []
        cursor = conn.cursor()
        cursor.execute("SELECT source_id, name, importer_script, schema_file_path FROM metadata_source ORDER BY name")
        sources = cursor.fetchall()
        conn.close()
        return sources

    def get_imported_files_for_source(self, source_id):
        """Fetches all imported file names for a given source."""
        conn = self.get_connection()
        if not conn: return []
        cursor = conn.cursor()
        cursor.execute("SELECT file_name FROM import_log WHERE source_id = ? ORDER BY import_timestamp DESC", (source_id,))
        files = cursor.fetchall()
        conn.close()
        return [f[0] for f in files]

    def add_metadata_source(self, name, script_path, schema_path=None):
        """Adds a new metadata source."""
        conn = self.get_connection()
        if not conn: return False
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO metadata_source (name, importer_script, schema_file_path) VALUES (?, ?, ?)", 
                          (name, script_path, schema_path))
            conn.commit()
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
        return True

    def update_metadata_source(self, source_id, name, script_path, schema_path=None):
        """Updates an existing metadata source."""
        conn = self.get_connection()
        if not conn: return
        cursor = conn.cursor()
        cursor.execute("UPDATE metadata_source SET name = ?, importer_script = ?, schema_file_path = ? WHERE source_id = ?", 
                      (name, script_path, schema_path, source_id))
        conn.commit()
        conn.close()

    def delete_metadata_source(self, source_id):
        """Deletes a metadata source."""
        conn = self.get_connection()
        if not conn: return False
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM import_log WHERE source_id = ?", (source_id,))
        count = cursor.fetchone()[0]
        if count > 0:
            conn.close()
            return False # Cannot delete source if it has associated imports
        
        cursor.execute("DELETE FROM metadata_source WHERE source_id = ?", (source_id,))
        conn.commit()
        conn.close()
        return True


# --- Dialog for Managing Sources ---
class SourceManagerDialog(QDialog):
    """A dialog to add, edit, or delete metadata sources."""
    def __init__(self, db_manager, config_manager, source_data=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.config = config_manager
        self.source_data = source_data # (source_id, name, script_path, schema_path)

        self.setWindowTitle("Manage Metadata Source")
        
        layout = QFormLayout(self)
        
        self.name_input = QLineEdit(self.source_data[1] if self.source_data else "")
        self.script_path_input = QLineEdit(self.source_data[2] if self.source_data else "")
        self.schema_path_input = QLineEdit(self.source_data[3] if self.source_data and len(self.source_data) > 3 and self.source_data[3] else "")
        
        script_button = QPushButton("Browse...")
        script_button.clicked.connect(self.browse_for_script)
        
        schema_button = QPushButton("Browse...")
        schema_button.clicked.connect(self.browse_for_schema)

        layout.addRow("Source Name:", self.name_input)
        
        script_layout = QHBoxLayout()
        script_layout.addWidget(self.script_path_input)
        script_layout.addWidget(script_button)
        layout.addRow("Importer Script:", script_layout)
        
        schema_layout = QHBoxLayout()
        schema_layout.addWidget(self.schema_path_input)
        schema_layout.addWidget(schema_button)
        layout.addRow("Schema File (Optional):", schema_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def browse_for_script(self):
        initial_dir = str(Path(self.config.get('importer_scripts_directory')).resolve())
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Importer Script", initial_dir, "Python Files (*.py)")
        if file_path:
            try:
                base_path = Path.cwd()
                relative_path = Path(file_path).relative_to(base_path)
                self.script_path_input.setText(str(relative_path).replace('\\', '/'))
            except ValueError:
                self.script_path_input.setText(file_path)
    
    def browse_for_schema(self):
        initial_dir = str(Path.cwd())
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Schema File", initial_dir, "All Files (*);;JSON Files (*.json);;XSD Files (*.xsd);;XML Files (*.xml)")
        if file_path:
            try:
                base_path = Path.cwd()
                relative_path = Path(file_path).relative_to(base_path)
                self.schema_path_input.setText(str(relative_path).replace('\\', '/'))
            except ValueError:
                self.schema_path_input.setText(file_path)

    def accept(self):
        name = self.name_input.text().strip()
        script = self.script_path_input.text().strip()
        schema = self.schema_path_input.text().strip() or None
        
        if not name or not script:
            QMessageBox.warning(self, "Input Error", "Both name and script path are required.")
            return

        if self.source_data: # Editing existing
            self.db_manager.update_metadata_source(self.source_data[0], name, script, schema)
        else: # Adding new
            if not self.db_manager.add_metadata_source(name, script, schema):
                QMessageBox.critical(self, "Database Error", f"A source with the name '{name}' already exists.")
                return

        super().accept()

# --- Main Application Window ---
class ImporterApp(QWidget):
    def __init__(self, config_manager=None):
        """Initialize the importer application window.
        
        If a ConfigManager instance is provided it will be used; otherwise a ConfigManager is imported from
        config_manager and instantiated. The constructor reads the configured database path, creates a
        DatabaseManager for that path, initializes internal state (selected files, current source id and
        importer script), builds the UI, and populates the sources dropdown.

        Parameters:
            config_manager (ConfigManager, optional): An existing ConfigManager instance. If None, a new one is created. Defaults to None.
        """
        super().__init__()
        
        # Use provided config or load default
        if config_manager:
            self.config = config_manager
        else:
            from config_manager import ConfigManager
            self.config = ConfigManager()
        
        # Get paths from config
        db_path = self.config.get('database_path')
        self.db = DatabaseManager(Path(db_path))
        
        self.selected_files = []
        self.current_source_id = None
        self.current_importer_script = None
        
        self.init_ui()
        self.populate_sources_dropdown()

    def init_ui(self):
        self.setWindowTitle('Atomic Game DB - Data Importer')
        self.setGeometry(300, 300, 700, 500)

        main_layout = QVBoxLayout()
        source_layout = QHBoxLayout()
        source_label = QLabel("Import Source:")
        self.source_combo = QComboBox()
        self.source_combo.currentIndexChanged.connect(self.on_source_changed)
        manage_button = QPushButton("Manage Sources...")
        manage_button.clicked.connect(self.manage_sources)
        source_layout.addWidget(source_label)
        source_layout.addWidget(self.source_combo, 1)
        source_layout.addWidget(manage_button)
        main_layout.addLayout(source_layout)

        file_selection_layout = QHBoxLayout()
        self.file_list_widget = QListWidget()
        self.file_list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        select_files_button = QPushButton("Select Files...")
        select_files_button.clicked.connect(self.select_files)
        file_selection_layout.addWidget(QLabel("Files to Import:"))
        file_selection_layout.addWidget(select_files_button)
        main_layout.addLayout(file_selection_layout)
        main_layout.addWidget(self.file_list_widget)

        imported_label = QLabel("Already Imported for this Source:")
        self.imported_list_widget = QListWidget()
        main_layout.addWidget(imported_label)
        main_layout.addWidget(self.imported_list_widget)

        self.import_button = QPushButton("Run Importer")
        self.import_button.clicked.connect(self.run_importer)
        self.import_button.setStyleSheet("font-size: 16px; padding: 10px;")
        main_layout.addWidget(self.import_button)

        self.setLayout(main_layout)

    def populate_sources_dropdown(self):
        """Fetches sources from DB and populates the dropdown."""
        self.source_combo.clear()
        sources = self.db.get_metadata_sources()
        if not sources:
            self.source_combo.addItem("No sources configured. Please add one.", None)
        else:
            for source_row in sources:
                source_id, name, script_path = source_row[:3]  # Handle both 3 and 4 column results
                self.source_combo.addItem(name, (source_id, script_path))

    def on_source_changed(self, index):
        data = self.source_combo.itemData(index)
        if data:
            self.current_source_id, self.current_importer_script = data
            self.update_imported_files_list()
        else:
            self.current_source_id = None
            self.current_importer_script = None
            self.imported_list_widget.clear()

    def update_imported_files_list(self):
        self.imported_list_widget.clear()
        if self.current_source_id:
            files = self.db.get_imported_files_for_source(self.current_source_id)
            self.imported_list_widget.addItems(files)

    def select_files(self):
        # Determine file filter based on schema file extension
        file_filter = "All Files (*)"
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
        
        files, _ = QFileDialog.getOpenFileNames(self, "Select Source Data Files", "", file_filter)
        if files:
            self.selected_files = files
            self.file_list_widget.clear()
            self.file_list_widget.addItems([Path(f).name for f in self.selected_files])

    def manage_sources(self):
        sources = self.db.get_metadata_sources()
        source_names = [s[1] for s in sources]
        
        menu = QDialog(self)
        menu_layout = QVBoxLayout()
        menu.setWindowTitle("Manage Sources")
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
        menu.setLayout(menu_layout)
        menu.exec_()
        self.populate_sources_dropdown()

    def open_source_dialog(self, parent_menu, index=-1, sources=None):
        source_data = sources[index] if index != -1 and sources else None
        dialog = SourceManagerDialog(self.db, self.config, source_data, self)
        if dialog.exec_():
            parent_menu.close()

    def delete_source(self, parent_menu, index, sources):
        if index == -1:
            QMessageBox.information(self, "Info", "Please select a source to delete.")
            return

        source_row = sources[index]
        source_id, name = source_row[0], source_row[1]
        reply = QMessageBox.question(self, "Confirm Deletion",
                                     f"Are you sure you want to delete the source '{name}'?\nThis cannot be undone.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            if not self.db.delete_metadata_source(source_id):
                 QMessageBox.critical(self, "Error", f"Could not delete '{name}'. It is currently associated with existing import logs.")
            else:
                parent_menu.close()

    def run_importer(self):
        if not self.current_importer_script:
            QMessageBox.warning(self, "Warning", "Please select a valid import source.")
            return
        if not self.selected_files:
            QMessageBox.warning(self, "Warning", "Please select one or more files to import.")
            return

        script_path = Path(self.current_importer_script).resolve()
        if not script_path.exists():
            QMessageBox.critical(self, "Error", f"Importer script not found at:\n{script_path}")
            return
            
        print(f"Running importer: {script_path}")
        print(f"Source ID: {self.current_source_id}")
        print(f"Files: {self.selected_files}")

        try:
            # Pass configuration via environment or temporary config
            db_path = self.config.get('database_path')
            args = [
                sys.executable,
                str(script_path),
                '--source_id', str(self.current_source_id),
                '--db_path', str(Path(db_path).resolve()),
                '--files'
            ] + self.selected_files
            
            result = subprocess.run(args, capture_output=True, text=True, check=True, encoding='utf-8')
            
            QMessageBox.information(self, "Success", f"Importer finished successfully.\n\nOutput:\n{result.stdout}")
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Importer Failed", f"The importer script failed.\n\nError:\n{e.stderr}")
        except Exception as e:
             QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

        self.update_imported_files_list()
        self.file_list_widget.clear()
        self.selected_files = []


def main():
    app = QApplication(sys.argv)
    
    # Apply the qdarkstyle theme. This is simple and reliable.
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    
    ex = ImporterApp()

    # We still need the schema check
    if not ex.db.check_schema():
        QMessageBox.critical(None, "Database Not Initialized",
                             "The database file appears to be empty or missing tables.\n\n"
                             "Please initialize it by running the schema creation script "
                             "against your database file.")
        sys.exit(1)

    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

