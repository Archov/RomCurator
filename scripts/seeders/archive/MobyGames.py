import argparse
import json
import sqlite3
import hashlib
import jsonschema
from pathlib import Path
from datetime import datetime

# This script is designed to import MobyGames JSON catalog format into the v1.6 database schema.

class DatabaseHandler:
    """A dedicated handler for all database operations within the script."""
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

    @staticmethod
    def calculate_file_hash(file_path):
        """Calculates the SHA256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

def load_and_validate_schema(schema_path):
    """Loads and returns the JSON schema for validation."""
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load schema from {schema_path}: {e}")
        return None

def validate_data_against_schema(data, schema):
    """Validates JSON data against the provided schema."""
    if not schema:
        return True, "No schema provided - skipping validation"
    
    try:
        jsonschema.validate(data, schema)
        return True, "Data validation successful"
    except jsonschema.ValidationError as e:
        return False, f"Schema validation error: {e.message}"
    except Exception as e:
        return False, f"Unexpected validation error: {e}"

def process_game_entry(db, cursor, game_data, log_id):
    """Processes a single game object from the MobyGames JSON within a transaction."""
    title = game_data.get('title')
    if not title:
        print(f"  - Skipping entry with missing Title.")
        return False

    try:
        # Get or create atomic game unit
        cursor.execute("SELECT atomic_id FROM atomic_game_unit WHERE lower(canonical_title) = ?", (title.lower(),))
        atomic_row = cursor.fetchone()
        if atomic_row:
            atomic_id = atomic_row['atomic_id']
        else:
            cursor.execute("INSERT INTO atomic_game_unit (canonical_title) VALUES (?)", (title,))
            atomic_id = cursor.lastrowid

        # Store core metadata
        release_date = game_data.get('release_date', '')
        cursor.execute("""
            INSERT OR REPLACE INTO atomic_core_metadata (atomic_id, log_id, release_date)
            VALUES (?, ?, ?)
        """, (atomic_id, log_id, release_date))

        # Store extension metadata
        moby_score = game_data.get('moby_score')
        moby_url = game_data.get('moby_url', '')
        moby_id = game_data.get('id')
        
        # Store MobyGames specific metadata
        if moby_score is not None:
            cursor.execute("""
                INSERT OR REPLACE INTO atomic_metadata_extension (atomic_id, log_id, key, value)
                VALUES (?, ?, 'moby_score', ?)
            """, (atomic_id, log_id, str(moby_score)))
        
        if moby_url:
            cursor.execute("""
                INSERT OR REPLACE INTO atomic_metadata_extension (atomic_id, log_id, key, value)
                VALUES (?, ?, 'moby_url', ?)
            """, (atomic_id, log_id, moby_url))
        
        if moby_id:
            cursor.execute("""
                INSERT OR REPLACE INTO atomic_metadata_extension (atomic_id, log_id, key, value)
                VALUES (?, ?, 'moby_id', ?)
            """, (atomic_id, log_id, str(moby_id)))

        # Process each platform as a separate game release
        platforms = game_data.get('platforms', [])
        for platform_name in platforms:
            # Get or create platform
            platform_id = db.get_or_create_lookup_table(cursor, 'platform', 'name', platform_name)
            
            # Create or get game release for this platform
            cursor.execute("""
                SELECT release_id FROM game_release 
                WHERE atomic_id = ? AND platform_id = ? AND release_title = ?
            """, (atomic_id, platform_id, title))
            
            release_row = cursor.fetchone()
            if release_row:
                release_id = release_row['release_id']
            else:
                cursor.execute("""
                    INSERT INTO game_release (atomic_id, platform_id, release_title)
                    VALUES (?, ?, ?)
                """, (atomic_id, platform_id, title))
                release_id = cursor.lastrowid

            # Link developers to this release
            for dev_name in game_data.get('developers', []):
                company_id = db.get_or_create_lookup_table(cursor, 'company', 'name', dev_name)
                cursor.execute("INSERT OR IGNORE INTO release_developer (release_id, company_id) VALUES (?, ?)", 
                              (release_id, company_id))

            # Link publishers to this release
            for pub_name in game_data.get('publishers', []):
                company_id = db.get_or_create_lookup_table(cursor, 'company', 'name', pub_name)
                cursor.execute("INSERT OR IGNORE INTO release_publisher (release_id, company_id) VALUES (?, ?)", 
                              (release_id, company_id))

            # Link genres to this release
            for genre_name in game_data.get('genres', []):
                genre_id = db.get_or_create_lookup_table(cursor, 'genre', 'name', genre_name)
                cursor.execute("INSERT OR IGNORE INTO release_genre (release_id, genre_id) VALUES (?, ?)", 
                              (release_id, genre_id))
        
        return True

    except Exception as e:
        print(f"  - ERROR processing game '{title}': {e}")
        return False

def get_schema_path_from_db(db, source_id):
    """Retrieves the schema file path for a given source from the database."""
    cursor = db.conn.cursor()
    cursor.execute("SELECT schema_file_path FROM metadata_source WHERE source_id = ?", (source_id,))
    row = cursor.fetchone()
    return row['schema_file_path'] if row and row['schema_file_path'] else None

def main(args):
    db = DatabaseHandler(args.db_path)
    
    # Get schema path from database
    schema_path = get_schema_path_from_db(db, args.source_id)
    schema = None
    if schema_path:
        schema_file = Path(schema_path)
        if schema_file.exists():
            schema = load_and_validate_schema(schema_file)
        else:
            print(f"Warning: Schema file not found at {schema_path}")
    
    for file_path_str in args.files:
        file_path = Path(file_path_str)
        print(f"\n--- Processing file: {file_path.name} ---")

        file_hash = db.calculate_file_hash(file_path)
        existing_import = db.check_file_hash(file_hash)
        if existing_import:
            log_id, status = existing_import
            if status == 'completed':
                print(f"Skipping '{file_path.name}': This file has already been successfully imported (log_id: {log_id}).")
                continue
            elif status == 'failed':
                print(f"File '{file_path.name}' was previously imported but failed (log_id: {log_id}). Deleting failed record and retrying...")
                cursor = db.conn.cursor()
                cursor.execute("DELETE FROM import_log WHERE log_id = ?", (log_id,))
                db.conn.commit()
            elif status == 'running':
                print(f"File '{file_path.name}' appears to be currently importing (log_id: {log_id}). Deleting stuck record and retrying...")
                cursor = db.conn.cursor()
                cursor.execute("DELETE FROM import_log WHERE log_id = ?", (log_id,))
                db.conn.commit()

        log_id, _ = db.start_import_log(args.source_id, file_path)
        
        records_processed = 0
        records_failed = 0

        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                data = json.load(f)
            
            # Validate against schema if available
            if schema:
                is_valid, validation_message = validate_data_against_schema(data, schema)
                if not is_valid:
                    raise ValueError(f"Schema validation failed: {validation_message}")
                print(f"Schema validation passed: {validation_message}")

            print(f"Found {len(data)} game entries in the file.")
            
            with db.conn:
                cursor = db.conn.cursor()
                
                for game_entry in data:
                    records_processed += 1
                    if not process_game_entry(db, cursor, game_entry, log_id):
                        records_failed += 1
                
                if records_failed > 0:
                    raise sqlite3.DataError(f"{records_failed} of {records_processed} records failed.")

            notes = f"Successfully processed {records_processed} game entries."
            db.finish_import_log(log_id, 'completed', records_processed, notes)
            print(f"--- Finished processing {file_path.name} ---")

        except Exception as e:
            error_message = f"Critical error: {e}. All changes for this file have been rolled back."
            print(error_message)
            db.finish_import_log(log_id, 'failed', records_processed, error_message)

    db.close()
    print("\nAll files processed.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="MobyGames JSON Importer for the Atomic Game Database (v1.6 compatible).")
    parser.add_argument('--source_id', required=True, type=int, help="The source_id from the metadata_source table.")
    parser.add_argument('--db_path', required=True, help="Path to the SQLite database file.")
    parser.add_argument('--files', nargs='+', required=True, help="List of JSON files to import.")
    
    args = parser.parse_args()
    main(args)
