"""
No-Intro DAT XML Importer for the Atomic Game Database (v1.6 compatible).
Refactored to use the shared BaseImporter class and XML utilities.
"""

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    from .base_importer import BaseImporter
    from .xml_utils import (
        extract_schema_url_from_dat, 
        download_and_cache_schema,
        load_xsd_schema, 
        validate_xml_against_schema,
        handle_schema_validation_warning,
        process_dat_rom_entry
    )
except ImportError:
    from base_importer import BaseImporter
    from xml_utils import (
        extract_schema_url_from_dat, 
        download_and_cache_schema,
        load_xsd_schema, 
        validate_xml_against_schema,
        handle_schema_validation_warning,
        process_dat_rom_entry
    )


class NoIntroImporter(BaseImporter):
    """No-Intro DAT importer that processes XML DAT files."""
    
    def get_file_type_description(self):
        return "No-Intro DAT"
    
    def extract_platform_from_source_name(self, source_name):
        """Extract platform name from No-Intro DAT file naming conventions."""
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

    def process_game_entry(self, cursor, game_element, log_id, platform_id):
        """Processes a single game element from the No-Intro DAT XML."""
        game_name = game_element.get('name')
        if not game_name:
            print(f"  - Skipping game entry with missing name attribute.")
            return False

        try:
            # Extract clone information - handle both 'cloneof' and 'cloneofid' attributes
            clone_of = game_element.get('cloneof', '') or game_element.get('cloneofid', '')
            is_clone = 1 if clone_of else 0
            
            processed_files = 0
            
            # Check for direct <rom> elements (NO-INTRO format)
            roms = game_element.findall('rom')
            for rom_elem in roms:
                sha1 = rom_elem.get('sha1')
                if sha1 and process_dat_rom_entry(cursor, log_id, platform_id, game_name, sha1, is_clone, clone_of):
                    processed_files += 1
                elif not sha1:
                    print(f"  - Warning: ROM in game '{game_name}' missing SHA1, skipping.")
            
            # Also check for source/file structure (alternative DAT format)
            sources = game_element.findall('source')
            for source in sources:
                files = source.findall('file')
                for file_elem in files:
                    sha1 = file_elem.get('sha1')
                    if sha1 and process_dat_rom_entry(cursor, log_id, platform_id, game_name, sha1, is_clone, clone_of):
                        processed_files += 1
                    elif not sha1:
                        print(f"  - Warning: File in game '{game_name}' missing SHA1, skipping.")
            
            # Also process release elements if they exist (scene releases)
            releases = game_element.findall('release')
            for release in releases:
                files = release.findall('file')
                for file_elem in files:
                    sha1 = file_elem.get('sha1')
                    if sha1 and process_dat_rom_entry(cursor, log_id, platform_id, game_name, sha1, is_clone, clone_of):
                        processed_files += 1
            
            if processed_files == 0:
                print(f"  - Warning: Game '{game_name}' had no valid ROM files to process.")
                return False
            
            return True

        except Exception as e:
            print(f"  - ERROR processing game '{game_name}': {e}")
            return False

    def process_single_file(self, file_path, log_id, source_id):
        """Process a single No-Intro DAT file."""
        records_processed = 0
        records_failed = 0

        # Try to get schema URL from the DAT file itself
        schema_url = extract_schema_url_from_dat(file_path)
        schema = None
        
        if schema_url:
            print(f"Found embedded schema URL: {schema_url}")
            # Download and cache the schema
            cached_schema_path = download_and_cache_schema(schema_url)
            if cached_schema_path:
                schema = load_xsd_schema(cached_schema_path)
                if schema is None:
                    raise Exception(f"Failed to load downloaded schema from {schema_url}")
            else:
                print("Warning: Could not download embedded schema, proceeding without validation")
        else:
            # Fallback to database-configured schema if no embedded schema found
            schema_path = self.get_schema_path_from_db(source_id)
            if schema_path:
                schema_file = Path(schema_path)
                if schema_file.exists():
                    schema = load_xsd_schema(schema_file)
                    if schema is None:
                        raise Exception(f"Failed to load schema from {schema_path}")
                else:
                    raise Exception(f"Schema file specified but not found at {schema_path}")
            
        # Validate against schema if available
        if schema:
            is_valid, validation_message = validate_xml_against_schema(file_path, schema, "XSD")
            handle_schema_validation_warning(file_path, is_valid, validation_message, "XSD")

        # Parse the XML DAT file
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Extract platform information from filename or header
        platform_name = self.extract_platform_from_source_name(file_path.stem)
        print(f"Detected platform: {platform_name}")
        
        # Get games from the datafile
        games = root.findall('game')
        print(f"Found {len(games)} game entries in the DAT file.")
        
        with self.db.conn:
            cursor = self.db.conn.cursor()
            
            # Get or create platform
            platform_id = self.db.get_or_create_platform(cursor, platform_name)
            
            for game_element in games:
                records_processed += 1
                if not self.process_game_entry(cursor, game_element, log_id, platform_id):
                    records_failed += 1
            
            if records_failed > 0:
                raise Exception(f"{records_failed} of {records_processed} records failed.")

        notes = f"Successfully processed {records_processed} game entries for platform '{platform_name}'."
        return records_processed, notes

    def create_argument_parser(self):
        """Create and return the argument parser for this importer."""
        parser = argparse.ArgumentParser(description="No-Intro DAT Importer for the Atomic Game Database (v1.6 compatible).")
        parser.add_argument('--source_id', required=True, type=int, help="The source_id from the metadata_source table.")
        parser.add_argument('--db_path', required=True, help="Path to the SQLite database file.")
        parser.add_argument('--files', nargs='+', required=True, help="List of DAT files to import.")
        return parser


def main():
    """Main entry point for the No-Intro importer."""
    importer = NoIntroImporter(None)  # db_path will be set from args
    parser = importer.create_argument_parser()
    args = parser.parse_args()
    
    # Initialize with the actual database path
    importer = NoIntroImporter(args.db_path)
    importer.run(args)


if __name__ == '__main__':
    main()
