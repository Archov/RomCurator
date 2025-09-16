import argparse
import sqlite3
import hashlib
import xml.etree.ElementTree as ET
import lxml.etree as etree
from pathlib import Path
from datetime import datetime

# This script is designed to import TOSEC DAT XML files into the v1.6 database schema.

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

def load_and_validate_schema(schema_path):
    """Loads and returns the DTD schema for validation."""
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            dtd_doc = etree.DTD(f)
            return dtd_doc
    except Exception as e:
        print(f"Warning: Could not load DTD schema from {schema_path}: {e}")
        return None

def validate_xml_against_schema(xml_file_path, dtd_schema):
    """Validates XML file against the provided DTD schema."""
    if not dtd_schema:
        return True, "No DTD schema provided - skipping validation"
    
    try:
        xml_doc = etree.parse(str(xml_file_path))
        if dtd_schema.validate(xml_doc):
            return True, "DTD validation successful"
        else:
            # DTD validation failed - collect all errors
            error_messages = []
            for error in dtd_schema.error_log:
                error_messages.append(f"Line {error.line}: {error.message}")
            
            # If there are many errors, truncate the list
            if len(error_messages) > 10:
                shown_errors = error_messages[:10]
                shown_errors.append(f"... and {len(error_messages) - 10} more errors")
                error_summary = "\n".join(shown_errors)
            else:
                error_summary = "\n".join(error_messages)
            
            return False, f"DTD validation failed with {len(error_messages)} errors:\n{error_summary}"
    except Exception as e:
        return False, f"Unexpected DTD validation error: {e}"

def extract_platform_from_tosec_header(header_element):
    """
    Extracts platform name from TOSEC DAT header information.
    TOSEC format: header name is "Platform Name - Category"
    """
    if header_element is None:
        return "Unknown Platform"
    
    # Check the header name first - TOSEC format is "Platform Name - Category"
    name_elem = header_element.find('name')
    if name_elem is not None and name_elem.text:
        header_name = name_elem.text.strip()
        
        # TOSEC naming follows "Platform Name - Category" (e.g., "Psion Series 5 - Applications")
        if " - " in header_name:
            platform_part = header_name.split(" - ")[0].strip()
            return platform_part
        else:
            # If no separator, the entire name might be the platform
            return header_name
    
    # Fallback to description if name doesn't provide clear platform info
    desc_elem = header_element.find('description')
    if desc_elem is not None and desc_elem.text:
        description = desc_elem.text.strip()
        # Description format: "Platform Name - Category (TOSEC-vYYYY-MM-DD)"
        if " - " in description and "(TOSEC" in description:
            platform_part = description.split(" - ")[0].strip()
            return platform_part
    
    return "Unknown Platform"

def extract_platform_from_filename(filename):
    """
    Extracts platform information from TOSEC DAT filename as fallback.
    TOSEC files typically start with platform name.
    """
    # Common TOSEC platform patterns in filenames
    platform_mappings = {
        'amiga': 'Amiga',
        'amstrad': 'Amstrad CPC',
        'apple': 'Apple II',
        'atari': 'Atari',
        'commodore': 'Commodore 64',
        'c64': 'Commodore 64',
        'msdos': 'MS-DOS',
        'pc': 'PC',
        'zx': 'ZX Spectrum',
        'spectrum': 'ZX Spectrum',
        'nes': 'Nintendo Entertainment System',
        'snes': 'Super Nintendo Entertainment System',
        'gameboy': 'Game Boy',
        'genesis': 'Sega Genesis',
        'megadrive': 'Sega Mega Drive',
        'mastersystem': 'Sega Master System',
        'dreamcast': 'Sega Dreamcast',
        'psx': 'Sony PlayStation',
        'playstation': 'Sony PlayStation',
        'psion': 'Psion Series 5',
    }
    
    filename_lower = filename.lower()
    for key, platform in platform_mappings.items():
        if key in filename_lower:
            return platform
    
    # Try to extract platform from start of filename before " - "
    # Many TOSEC files follow "Platform Name - Category (TOSEC-vDATE).dat"
    if " - " in filename:
        potential_platform = filename.split(" - ")[0].strip()
        return potential_platform
    
    # If no pattern matches, return filename without extension
    return Path(filename).stem.replace("(TOSEC", "").strip()

def process_game_entry(db, cursor, game_element, log_id, platform_id):
    """Processes a single game element from the TOSEC DAT XML within a transaction."""
    game_name = game_element.get('name')
    if not game_name:
        print(f"  - Skipping game entry with missing name attribute.")
        return False

    try:
        # TOSEC typically doesn't use clone relationships in the same way as No-Intro
        # but we'll check for any clone attributes just in case
        clone_of = game_element.get('cloneof', '') or game_element.get('cloneofid', '')
        is_clone = 1 if clone_of else 0
        
        processed_files = 0
        
        # Process ROM elements - TOSEC structure is similar to No-Intro
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
        
        # TOSEC may also have disk elements for some platforms
        disks = game_element.findall('disk')
        for disk_elem in disks:
            sha1 = disk_elem.get('sha1')
            if not sha1:
                print(f"  - Warning: Disk in game '{game_name}' missing SHA1, skipping.")
                continue
            
            # Insert disk entries as ROM entries in dat_entry table
            cursor.execute("""
                INSERT OR IGNORE INTO dat_entry (
                    log_id, platform_id, release_title, rom_sha1, is_clone, clone_of
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (log_id, platform_id, game_name, sha1.lower(), is_clone, clone_of))
            
            processed_files += 1
        
        if processed_files == 0:
            print(f"  - Warning: Game '{game_name}' had no valid ROM/disk files to process.")
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
        print(f"\n--- Processing TOSEC DAT file: {file_path.name} ---")

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
            # Get DTD schema path from database configuration
            schema_path = get_schema_path_from_db(db, args.source_id)
            dtd_schema = None
            
            if schema_path:
                schema_file = Path(schema_path)
                if schema_file.exists():
                    dtd_schema = load_and_validate_schema(schema_file)
                    if dtd_schema is None:
                        error_message = f"Error: Failed to load DTD schema from {schema_path}"
                        print(error_message)
                        db.finish_import_log(log_id, 'failed', 0, error_message)
                        continue
                else:
                    error_message = f"Error: DTD schema file specified but not found at {schema_path}"
                    print(error_message)
                    print("Import aborted. Please check the schema file path in the metadata source configuration.")
                    db.finish_import_log(log_id, 'failed', 0, error_message)
                    continue
            else:
                print("No DTD schema configured, proceeding without validation")
                
            # Validate against DTD schema if available
            if dtd_schema:
                is_valid, validation_message = validate_xml_against_schema(file_path, dtd_schema)
                if not is_valid:
                    print(f"Warning: DTD schema validation failed for {file_path.name}, but proceeding with import anyway.")
                    print(f"Validation details: {validation_message}")
                    print("Note: Many valid DAT files don't strictly conform to their schemas but are still importable.")
                else:
                    print(f"DTD schema validation passed: {validation_message}")

            # Parse the XML DAT file
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Extract platform information from header or filename
            header = root.find('header')
            if header is not None:
                platform_name = extract_platform_from_tosec_header(header)
            else:
                platform_name = extract_platform_from_filename(file_path.stem)
            
            print(f"Detected platform: {platform_name}")
            
            # Get games from the datafile
            games = root.findall('game')
            print(f"Found {len(games)} game entries in the TOSEC DAT file.")
            
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
    print("\nAll TOSEC DAT files processed.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="TOSEC DAT Importer for the Atomic Game Database (v1.6 compatible).")
    parser.add_argument('--source_id', required=True, type=int, help="The source_id from the metadata_source table.")
    parser.add_argument('--db_path', required=True, help="Path to the SQLite database file.")
    parser.add_argument('--files', nargs='+', required=True, help="List of TOSEC DAT files to import.")
    
    args = parser.parse_args()
    main(args)
