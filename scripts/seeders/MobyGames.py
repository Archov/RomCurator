import argparse
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime

# This script is designed to be called by the GUI application or command line.
# It is specifically built for the v1.5 database schema.

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
        """Checks if a file with this hash has already been successfully imported."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT log_id FROM import_log WHERE file_hash = ? AND status = 'completed'",
            (file_hash,)
        )
        return cursor.fetchone() is not None

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

    def finish_import_log(self, log_id, status, notes=""):
        """Updates a log entry to mark it as completed or failed."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE import_log
            SET status = ?, notes = ?, import_timestamp = ?
            WHERE log_id = ?
            """,
            (status, notes, datetime.now().isoformat(), log_id)
        )
        self.conn.commit()

    def get_or_create(self, cursor, table, value):
        """Gets the ID of a row in a table if it exists, otherwise creates it."""
        cursor.execute(f"SELECT {table}_id FROM {table} WHERE lower(canonical_name) = ?", (value.lower(),))
        row = cursor.fetchone()
        if row:
            return row[f"{table}_id"]
        else:
            cursor.execute(f"INSERT INTO {table} (canonical_name) VALUES (?)", (value,))
            return cursor.lastrowid

    @staticmethod
    def calculate_file_hash(file_path):
        """Calculates the SHA256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

def process_game_entry(db, cursor, game_data):
    """Processes a single game object from the MobyGames JSON within a transaction."""
    title = game_data.get('title')
    if not title:
        print(f"  - Skipping entry with missing Title.")
        return False

    try:
        # Since we have no place to store Moby ID yet in v1.5, we will create a new atomic unit
        # for each title. The reconciliation step in Phase 2 will be responsible for merging duplicates.
        cursor.execute("INSERT INTO atomic_game_unit (canonical_title) VALUES (?)", (title,))
        atomic_id = cursor.lastrowid
        
        # Process relationships
        for platform_name in game_data.get('platforms', []):
            platform_id = db.get_or_create(cursor, 'platform', platform_name)
            # Create a game_release for this specific platform
            cursor.execute(
                """
                INSERT OR IGNORE INTO game_release (atomic_id, platform_id, release_title, release_date)
                VALUES (?, ?, ?, ?)
                """,
                (atomic_id, platform_id, title, game_data.get('release_date'))
            )
            # Fetch the release_id whether it was just inserted or ignored
            cursor.execute(
                "SELECT release_id FROM game_release WHERE atomic_id = ? AND platform_id = ? AND release_title = ?",
                (atomic_id, platform_id, title)
            )
            release_row = cursor.fetchone()
            if not release_row: continue
            release_id = release_row['release_id']

            # Link developers, publishers, and genres to this specific release
            for dev_name in game_data.get('developers', []):
                company_id = db.get_or_create(cursor, 'company', dev_name)
                cursor.execute("INSERT OR IGNORE INTO release_developer (release_id, company_id) VALUES (?, ?)", (release_id, company_id))
            for pub_name in game_data.get('publishers', []):
                company_id = db.get_or_create(cursor, 'company', pub_name)
                cursor.execute("INSERT OR IGNORE INTO release_publisher (release_id, company_id) VALUES (?, ?)", (release_id, company_id))
            for genre_name in game_data.get('genres', []):
                genre_id = db.get_or_create(cursor, 'genre', genre_name)
                cursor.execute("INSERT OR IGNORE INTO release_genre (release_id, genre_id) VALUES (?, ?)", (release_id, genre_id))
        
        return True

    except Exception as e:
        print(f"  - ERROR processing game '{title}': {e}")
        return False

def main(args):
    db = DatabaseHandler(args.db_path)
    
    for file_path_str in args.files:
        file_path = Path(file_path_str)
        print(f"\n--- Processing file: {file_path.name} ---")

        file_hash = db.calculate_file_hash(file_path)
        if db.check_file_hash(file_hash):
            print(f"Skipping '{file_path.name}': This file has already been successfully imported.")
            continue

        log_id, _ = db.start_import_log(args.source_id, file_path)
        
        records_processed = 0
        records_failed = 0

        try:
            with db.conn:
                cursor = db.conn.cursor()
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    data = json.load(f)
                
                print(f"Found {len(data)} game entries in the file.")
                for game_entry in data:
                    records_processed += 1
                    if not process_game_entry(db, cursor, game_entry):
                        records_failed += 1
                
                if records_failed > 0:
                    raise sqlite3.DataError(f"{records_failed} of {records_processed} records failed.")

            notes = f"Successfully processed {records_processed} game entries."
            db.finish_import_log(log_id, 'completed', notes)
            print(f"--- Finished processing {file_path.name} ---")

        except Exception as e:
            error_message = f"Critical error: {e}. All changes for this file have been rolled back."
            print(error_message)
            db.finish_import_log(log_id, 'failed', error_message)

    db.close()
    print("\nAll files processed.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="MobyGames JSON Importer for the Atomic Game Database (v1.5 compatible).")
    parser.add_argument('--source_id', required=True, type=int, help="The source_id from the metadata_source table.")
    parser.add_argument('--db_path', required=True, help="Path to the SQLite database file.")
    parser.add_argument('--files', nargs='+', required=True, help="List of JSON files to import.")
    
    args = parser.parse_args()
    main(args)

