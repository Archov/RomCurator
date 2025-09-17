"""
MobyGames JSON Importer for the Atomic Game Database (v1.6 compatible).
Refactored to use the shared BaseImporter class.
"""

import argparse
import json
import jsonschema
from pathlib import Path

try:
    from .base_importer import BaseImporter
except ImportError:
    from base_importer import BaseImporter


class MobyGamesImporter(BaseImporter):
    """MobyGames-specific importer that processes JSON catalog files."""
    
    def get_file_type_description(self):
        return "MobyGames JSON"
    
    def load_and_validate_schema(self, schema_path):
        """Loads and returns the JSON schema for validation."""
        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load schema from {schema_path}: {e}")
            return None

    def validate_data_against_schema(self, data, schema):
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

    def process_game_entry(self, cursor, game_data, log_id):
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
                platform_id = self.db.get_or_create_lookup_table(cursor, 'platform', 'name', platform_name)
                
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
                    company_id = self.db.get_or_create_lookup_table(cursor, 'company', 'name', dev_name)
                    cursor.execute("INSERT OR IGNORE INTO release_developer (release_id, company_id) VALUES (?, ?)", 
                                  (release_id, company_id))

                # Link publishers to this release
                for pub_name in game_data.get('publishers', []):
                    company_id = self.db.get_or_create_lookup_table(cursor, 'company', 'name', pub_name)
                    cursor.execute("INSERT OR IGNORE INTO release_publisher (release_id, company_id) VALUES (?, ?)", 
                                  (release_id, company_id))

                # Link genres to this release
                for genre_name in game_data.get('genres', []):
                    genre_id = self.db.get_or_create_lookup_table(cursor, 'genre', 'name', genre_name)
                    cursor.execute("INSERT OR IGNORE INTO release_genre (release_id, genre_id) VALUES (?, ?)", 
                                  (release_id, genre_id))
            
            return True

        except Exception as e:
            print(f"  - ERROR processing game '{title}': {e}")
            return False

    def process_single_file(self, file_path, log_id, source_id):
        """Process a single MobyGames JSON file."""
        # Get schema path from database
        schema_path = self.get_schema_path_from_db(source_id)
        schema = None
        if schema_path:
            schema_file = Path(schema_path)
            if schema_file.exists():
                schema = self.load_and_validate_schema(schema_file)
            else:
                print(f"Warning: Schema file not found at {schema_path}")
        
        records_processed = 0
        records_failed = 0

        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            data = json.load(f)
        
        # Validate against schema if available
        if schema:
            is_valid, validation_message = self.validate_data_against_schema(data, schema)
            if not is_valid:
                print(f"Warning: Schema validation failed for {file_path.name}, but proceeding with import anyway.")
                print(f"Validation details: {validation_message}")
                print("Note: Some valid JSON files don't strictly conform to their schemas but are still importable.")
            else:
                print(f"Schema validation passed: {validation_message}")

        print(f"Found {len(data)} game entries in the file.")
        
        with self.db.conn:
            cursor = self.db.conn.cursor()
            
            for game_entry in data:
                records_processed += 1
                if not self.process_game_entry(cursor, game_entry, log_id):
                    records_failed += 1
            
            if records_failed > 0:
                raise Exception(f"{records_failed} of {records_processed} records failed.")

        notes = f"Successfully processed {records_processed} game entries."
        return records_processed, notes

    def create_argument_parser(self):
        """Create and return the argument parser for this importer."""
        parser = argparse.ArgumentParser(description="MobyGames JSON Importer for the Atomic Game Database (v1.6 compatible).")
        parser.add_argument('--source_id', required=True, type=int, help="The source_id from the metadata_source table.")
        parser.add_argument('--db_path', required=True, help="Path to the SQLite database file.")
        parser.add_argument('--files', nargs='+', required=True, help="List of JSON files to import.")
        return parser


def main():
    """Main entry point for the MobyGames importer."""
    # Parse arguments first to get database path
    parser = argparse.ArgumentParser(description="MobyGames JSON Importer for the Atomic Game Database (v1.6 compatible).")
    parser.add_argument('--source_id', required=True, type=int, help="The source_id from the metadata_source table.")
    parser.add_argument('--db_path', required=True, help="Path to the SQLite database file.")
    parser.add_argument('--files', nargs='+', required=True, help="List of JSON files to import.")
    args = parser.parse_args()
    
    # Initialize with the actual database path
    importer = MobyGamesImporter(args.db_path)
    importer.run(args)


if __name__ == '__main__':
    main()
