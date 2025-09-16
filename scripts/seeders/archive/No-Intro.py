import argparse
import sqlite3
import hashlib
import xml.etree.ElementTree as ET
import lxml.etree as etree
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

# This script is designed to import NO-INTRO DAT XML files into the v1.6 database schema.

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

def extract_schema_url_from_dat(xml_file_path):
    """Extracts the XSD schema URL from the DAT file's schemaLocation attribute."""
    try:
        # Parse just enough to get the root element and its attributes
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        
        # Look for xsi:schemaLocation attribute
        schema_location = root.get('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation')
        if schema_location:
            # schemaLocation format is "namespace_uri schema_url"
            parts = schema_location.strip().split()
            if len(parts) >= 2:
                return parts[1]  # Return the schema URL part
        
        return None
    except Exception as e:
        print(f"Warning: Could not extract schema URL from DAT file: {e}")
        return None

def download_and_cache_schema(schema_url, cache_dir=".schema_cache"):
    """Downloads an XSD schema from a URL and caches it locally."""
    try:
        # Create cache directory if it doesn't exist
        cache_path = Path(cache_dir)
        cache_path.mkdir(exist_ok=True)
        
        # Generate cache filename from URL
        parsed_url = urlparse(schema_url)
        cache_filename = f"{parsed_url.netloc}_{Path(parsed_url.path).name}"
        cache_file = cache_path / cache_filename
        
        # Check if already cached
        if cache_file.exists():
            print(f"Using cached schema: {cache_file}")
            return str(cache_file)
        
        # Download the schema
        print(f"Downloading schema from: {schema_url}")
        with urllib.request.urlopen(schema_url, timeout=30) as response:
            schema_content = response.read()
        
        # Save to cache
        with open(cache_file, 'wb') as f:
            f.write(schema_content)
        
        print(f"Schema cached to: {cache_file}")
        return str(cache_file)
        
    except urllib.error.URLError as e:
        print(f"Warning: Could not download schema from {schema_url}: {e}")
        return None
    except Exception as e:
        print(f"Warning: Error caching schema: {e}")
        return None
def load_and_validate_schema(schema_path):
    """Loads and returns the XSD schema for validation."""
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_doc = etree.parse(f)
            return etree.XMLSchema(schema_doc)
    except Exception as e:
        print(f"Warning: Could not load schema from {schema_path}: {e}")
        return None

def validate_xml_against_schema(xml_file_path, schema):
    """Validates XML file against the provided XSD schema."""
    if not schema:
        return True, "No schema provided - skipping validation"
    
    try:
        xml_doc = etree.parse(str(xml_file_path))
        if schema.validate(xml_doc):
            return True, "XML validation successful"
        else:
            # Schema validation failed - collect all errors
            error_messages = []
            for error in schema.error_log:
                error_messages.append(f"Line {error.line}: {error.message}")
            
            # If there are many errors, truncate the list
            if len(error_messages) > 10:
                shown_errors = error_messages[:10]
                shown_errors.append(f"... and {len(error_messages) - 10} more errors")
                error_summary = "\n".join(shown_errors)
            else:
                error_summary = "\n".join(error_messages)
            
            return False, f"Schema validation failed with {len(error_messages)} errors:\n{error_summary}"
    except Exception as e:
        return False, f"Unexpected validation error: {e}"

def extract_platform_from_source_name(source_name):
    """
    Attempts to extract platform name from various source naming conventions.
    This is a heuristic approach since platform info might be embedded in source names.
    """
    # Common platform mappings found in NO-INTRO DAT file names
    platform_mappings = {
        'nintendo - game boy': 'Game Boy',
        'nintendo - super nintendo entertainment system': 'Super Nintendo Entertainment System',
        'nintendo - nintendo entertainment system': 'Nintendo Entertainment System',
        'nintendo - nintendo 64': 'Nintendo 64',
        'nintendo - gamecube': 'GameCube',
        'sega - master system': 'Sega Master System',
        'sega - mega drive': 'Sega Mega Drive',
        'sega - game gear': 'Sega Game Gear',
        'sega - dreamcast': 'Sega Dreamcast',
        'sony - playstation': 'Sony PlayStation',
        'sony - playstation portable': 'PlayStation Portable',
        'atari - atari 2600': 'Atari 2600',
        'atari - atari 7800': 'Atari 7800',
    }
    
    source_lower = source_name.lower()
    for key, platform in platform_mappings.items():
        if key in source_lower:
            return platform
    
    # If no match found, try to extract from parentheses or common patterns
    if 'game boy' in source_lower:
        return 'Game Boy'
    elif 'nintendo' in source_lower and 'entertainment system' in source_lower:
        return 'Nintendo Entertainment System'
    elif 'super nintendo' in source_lower or 'snes' in source_lower:
        return 'Super Nintendo Entertainment System'
    elif 'nintendo 64' in source_lower or 'n64' in source_lower:
        return 'Nintendo 64'
    elif 'sega' in source_lower and 'master system' in source_lower:
        return 'Sega Master System'
    elif 'mega drive' in source_lower or 'genesis' in source_lower:
        return 'Sega Mega Drive'
    
    # Default fallback - return a cleaned version of the source name
    return source_name.replace(' - ', ' ').title()

def process_game_entry(db, cursor, game_element, log_id, platform_id):
    """Processes a single game element from the DAT XML within a transaction."""
    game_name = game_element.get('name')
    if not game_name:
        print(f"  - Skipping game entry with missing name attribute.")
        return False

    try:
        # Note: External ID tracking removed for schema compatibility
        
        # Extract clone information - handle both 'cloneof' and 'cloneofid' attributes
        clone_of = game_element.get('cloneof', '') or game_element.get('cloneofid', '')
        is_clone = 1 if clone_of else 0
        
        processed_files = 0
        
        # Check for direct <rom> elements (NO-INTRO format)
        roms = game_element.findall('rom')
        for rom_elem in roms:
            sha1 = rom_elem.get('sha1')
            if not sha1:
                print(f"  - Warning: ROM in game '{game_name}' missing SHA1, skipping.")
                continue
            
            # Insert into dat_entry table
            cursor.execute("""
                INSERT OR IGNORE INTO dat_entry (
                    log_id, platform_id, release_title, rom_sha1, is_clone, clone_of
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (log_id, platform_id, game_name, sha1.lower(), is_clone, clone_of))
            
            processed_files += 1
        
        # Also check for source/file structure (alternative DAT format)
        sources = game_element.findall('source')
        for source in sources:
            files = source.findall('file')
            for file_elem in files:
                sha1 = file_elem.get('sha1')
                if not sha1:
                    print(f"  - Warning: File in game '{game_name}' missing SHA1, skipping.")
                    continue
                
                # Insert into dat_entry table
                cursor.execute("""
                    INSERT OR IGNORE INTO dat_entry (
                        log_id, platform_id, release_title, rom_sha1, is_clone, clone_of
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (log_id, platform_id, game_name, sha1.lower(), is_clone, clone_of))
                
                processed_files += 1
        
        # Also process release elements if they exist (scene releases)
        releases = game_element.findall('release')
        for release in releases:
            files = release.findall('file')
            for file_elem in files:
                sha1 = file_elem.get('sha1')
                if not sha1:
                    continue
                
                # Insert release files as well
                cursor.execute("""
                    INSERT OR IGNORE INTO dat_entry (
                        log_id, platform_id, release_title, rom_sha1, is_clone, clone_of
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (log_id, platform_id, game_name, sha1.lower(), is_clone, clone_of))
                
                processed_files += 1
        
        if processed_files == 0:
            print(f"  - Warning: Game '{game_name}' had no valid ROM files to process.")
            return False
        
        return True

    except Exception as e:
        print(f"  - ERROR processing game '{game_name}': {e}")
        return False

def get_schema_path_from_db(db, source_id):
    """Retrieves the schema file path for a given source from the database."""
    cursor = db.conn.cursor()
    cursor.execute("SELECT schema_file_path FROM metadata_source WHERE source_id = ?", (source_id,))
    row = cursor.fetchone()
    return row['schema_file_path'] if row and row['schema_file_path'] else None

def main(args):
    db = DatabaseHandler(args.db_path)
    
    for file_path_str in args.files:
        file_path = Path(file_path_str)
        print(f"\n--- Processing DAT file: {file_path.name} ---")

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
            # Try to get schema URL from the DAT file itself
            schema_url = extract_schema_url_from_dat(file_path)
            schema = None
            
            if schema_url:
                print(f"Found embedded schema URL: {schema_url}")
                # Download and cache the schema
                cached_schema_path = download_and_cache_schema(schema_url)
                if cached_schema_path:
                    schema = load_and_validate_schema(cached_schema_path)
                    if schema is None:
                        error_message = f"Error: Failed to load downloaded schema from {schema_url}"
                        print(error_message)
                        db.finish_import_log(log_id, 'failed', 0, error_message)
                        continue
                else:
                    print("Warning: Could not download embedded schema, proceeding without validation")
            else:
                # Fallback to database-configured schema if no embedded schema found
                schema_path = get_schema_path_from_db(db, args.source_id)
                if schema_path:
                    schema_file = Path(schema_path)
                    if schema_file.exists():
                        schema = load_and_validate_schema(schema_file)
                        if schema is None:
                            error_message = f"Error: Failed to load schema from {schema_path}"
                            print(error_message)
                            db.finish_import_log(log_id, 'failed', 0, error_message)
                            continue
                    else:
                        error_message = f"Error: Schema file specified but not found at {schema_path}"
                        print(error_message)
                        print("Import aborted. Please check the schema file path in the metadata source configuration.")
                        db.finish_import_log(log_id, 'failed', 0, error_message)
                        continue
                
            # Validate against schema if available
            if schema:
                is_valid, validation_message = validate_xml_against_schema(file_path, schema)
                if not is_valid:
                    print(f"Warning: Schema validation failed for {file_path.name}, but proceeding with import anyway.")
                    print(f"Validation details: {validation_message}")
                    print("Note: Many valid DAT files don't strictly conform to their schemas but are still importable.")
                else:
                    print(f"Schema validation passed: {validation_message}")

            # Parse the XML DAT file
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Extract platform information from filename or header
            platform_name = extract_platform_from_source_name(file_path.stem)
            print(f"Detected platform: {platform_name}")
            
            # Get games from the datafile
            games = root.findall('game')
            print(f"Found {len(games)} game entries in the DAT file.")
            
            with db.conn:
                cursor = db.conn.cursor()
                
                # Get or create platform
                platform_id = db.get_or_create_platform(cursor, platform_name)
                
                for game_element in games:
                    records_processed += 1
                    if not process_game_entry(db, cursor, game_element, log_id, platform_id):
                        records_failed += 1
                
                if records_failed > 0:
                    raise sqlite3.DataError(f"{records_failed} of {records_processed} records failed.")

            notes = f"Successfully processed {records_processed} game entries for platform '{platform_name}'."
            db.finish_import_log(log_id, 'completed', records_processed, notes)
            print(f"--- Finished processing {file_path.name} ---")

        except Exception as e:
            error_message = f"Critical error: {e}. All changes for this file have been rolled back."
            print(error_message)
            db.finish_import_log(log_id, 'failed', records_processed, error_message)

    db.close()
    print("\nAll DAT files processed.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="NO-INTRO DAT Importer for the Atomic Game Database (v1.6 compatible).")
    parser.add_argument('--source_id', required=True, type=int, help="The source_id from the metadata_source table.")
    parser.add_argument('--db_path', required=True, help="Path to the SQLite database file.")
    parser.add_argument('--files', nargs='+', required=True, help="List of DAT files to import.")
    
    args = parser.parse_args()
    main(args)