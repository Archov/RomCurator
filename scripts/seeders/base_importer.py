"""
Base importer class for the Atomic Game Database.
Contains shared functionality across all importer types to reduce code duplication.
"""

import argparse
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
from abc import ABC, abstractmethod


class DatabaseHandler:
    """A dedicated handler for all database operations within importer scripts."""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        if self.conn:
            self.conn.close()

    def check_file_hash(self, file_hash):
        """Checks if a file with this hash has already been processed and returns the status."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT log_id, status FROM import_log WHERE file_hash = ?",
            (file_hash,)
        )
        result = cursor.fetchone()
        return result if result else None

    def start_import_log(self, source_id, file_path):
        """Creates a new log entry for an import process."""
        cursor = self.conn.cursor()
        file_hash = self.calculate_file_hash(file_path)
        cursor.execute(
            """
            INSERT INTO import_log (source_id, file_name, file_hash, status)
            VALUES (?, ?, ?, 'running')
            """,
            (source_id, file_path.name, file_hash)
        )
        self.conn.commit()
        return cursor.lastrowid, file_hash

    def finish_import_log(self, log_id, status, records_processed=0, notes=""):
        """Updates a log entry to mark it as completed or failed."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE import_log
            SET status = ?, records_processed = ?, notes = ?, import_timestamp = ?
            WHERE log_id = ?
            """,
            (status, records_processed, notes, datetime.now().isoformat(), log_id)
        )
        self.conn.commit()

    def get_or_create_lookup_table(self, cursor, table, name_column, value):
        """Gets the ID of a row in a lookup table if it exists, otherwise creates it."""
        id_column = f"{table}_id"
        if table == 'region':
            id_column = 'region_code'
            name_column = 'region_code'
            
        cursor.execute(f"SELECT {id_column} FROM {table} WHERE lower({name_column}) = ?", (value.lower(),))
        row = cursor.fetchone()
        if row:
            return row[id_column]
        else:
            if table == 'region':
                cursor.execute(f"INSERT INTO {table} (region_code, name) VALUES (?, ?)", (value, value))
            else:
                cursor.execute(f"INSERT INTO {table} ({name_column}) VALUES (?)", (value,))
            return cursor.lastrowid

    def get_or_create_platform(self, cursor, platform_name):
        """Gets the ID of a platform if it exists, otherwise creates it."""
        cursor.execute("SELECT platform_id FROM platform WHERE lower(name) = ?", (platform_name.lower(),))
        row = cursor.fetchone()
        if row:
            return row['platform_id']
        else:
            cursor.execute("INSERT INTO platform (name) VALUES (?)", (platform_name,))
            return cursor.lastrowid

    @staticmethod
    def calculate_file_hash(file_path):
        """Calculates the SHA256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()


class BaseImporter(ABC):
    """Base class for all data importers with common functionality."""
    
    def __init__(self, db_path):
        self.db = DatabaseHandler(db_path)
    
    def close(self):
        """Clean up database connection."""
        self.db.close()
    
    def get_schema_path_from_db(self, source_id):
        """Retrieves the schema file path for a given source from the database."""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT schema_file_path FROM metadata_source WHERE source_id = ?", (source_id,))
        row = cursor.fetchone()
        return row['schema_file_path'] if row and row['schema_file_path'] else None
    
    def handle_existing_import(self, file_path, file_hash):
        """
        Handle cases where a file has been previously imported.
        Returns True if the file should be skipped, False if it should be processed.
        """
        existing_import = self.db.check_file_hash(file_hash)
        if existing_import:
            log_id, status = existing_import
            if status == 'completed':
                print(f"Skipping '{file_path.name}': This file has already been successfully imported (log_id: {log_id}).")
                return True
            elif status == 'failed':
                print(f"File '{file_path.name}' was previously imported but failed (log_id: {log_id}). Deleting failed record and retrying...")
                cursor = self.db.conn.cursor()
                cursor.execute("DELETE FROM import_log WHERE log_id = ?", (log_id,))
                self.db.conn.commit()
            elif status == 'running':
                print(f"File '{file_path.name}' appears to be currently importing (log_id: {log_id}). Deleting stuck record and retrying...")
                cursor = self.db.conn.cursor()
                cursor.execute("DELETE FROM import_log WHERE log_id = ?", (log_id,))
                self.db.conn.commit()
        
        return False  # File should be processed
    
    def process_files(self, source_id, file_paths):
        """
        Main processing loop for importing multiple files.
        This handles the common pattern across all importers.
        """
        for file_path_str in file_paths:
            file_path = Path(file_path_str)
            print(f"\n--- Processing {self.get_file_type_description()} file: {file_path.name} ---")

            file_hash = self.db.calculate_file_hash(file_path)
            if self.handle_existing_import(file_path, file_hash):
                continue  # Skip this file

            log_id, _ = self.db.start_import_log(source_id, file_path)
            
            try:
                # Let the specific importer handle the file processing
                records_processed, notes = self.process_single_file(file_path, log_id, source_id)
                
                self.db.finish_import_log(log_id, 'completed', records_processed, notes)
                print(f"--- Finished processing {file_path.name} ---")
                
            except Exception as e:
                error_message = f"Critical error: {e}. All changes for this file have been rolled back."
                print(error_message)
                self.db.finish_import_log(log_id, 'failed', 0, error_message)

        print(f"\nAll {self.get_file_type_description()} files processed.")
    
    @abstractmethod
    def get_file_type_description(self):
        """Return a string describing the file type (e.g., 'DAT', 'JSON')."""
        pass
    
    @abstractmethod
    def process_single_file(self, file_path, log_id, source_id):
        """
        Process a single file and return (records_processed, notes).
        This method must be implemented by each specific importer.
        """
        pass
    
    @abstractmethod
    def create_argument_parser(self):
        """Create and return the argument parser for this importer."""
        pass
    
    def run(self, args):
        """Main entry point for running the importer."""
        try:
            self.process_files(args.source_id, args.files)
        finally:
            self.close()
