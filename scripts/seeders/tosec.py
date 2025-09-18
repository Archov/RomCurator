"""
TOSEC DAT XML Importer for the Atomic Game Database (v1.6 compatible).
Refactored to use the shared BaseImporter class and XML utilities.
"""

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    from .base_importer import BaseImporter
    from .xml_utils import (
        load_dtd_schema, 
        validate_xml_against_schema,
        handle_schema_validation_warning,
        process_dat_rom_entry
    )
except ImportError:
    from .base_importer import BaseImporter
    from .xml_utils import (
        load_dtd_schema, 
        validate_xml_against_schema,
        handle_schema_validation_warning,
        process_dat_rom_entry
    )


class TosecImporter(BaseImporter):
    """TOSEC DAT importer that processes XML DAT files."""
    
    def get_file_type_description(self):
        return "TOSEC DAT"
    
    def extract_platform_from_tosec_header(self, header_element):
        """Extract platform name from TOSEC DAT header information."""
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

    def extract_platform_from_filename(self, filename):
        """Extract platform information from TOSEC DAT filename as fallback."""
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

    def process_game_entry(self, cursor, game_element, log_id, platform_id):
        """Processes a single game element from the TOSEC DAT XML."""
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
                crc32 = rom_elem.get('crc')  # TOSEC uses 'crc' instead of 'crc32'
                md5 = rom_elem.get('md5')

                if sha1 or crc32 or md5:
                    if process_dat_rom_entry(cursor, log_id, platform_id, game_name, sha1, crc32, md5, None, is_clone, clone_of, "tosec"):
                        processed_files += 1
                else:
                    print(f"  - Warning: ROM in game '{game_name}' missing all hash values, skipping.")
            
            # TOSEC may also have disk elements for some platforms
            disks = game_element.findall('disk')
            for disk_elem in disks:
                sha1 = disk_elem.get('sha1')
                crc32 = disk_elem.get('crc')  # TOSEC uses 'crc' instead of 'crc32'
                md5 = disk_elem.get('md5')

                if sha1 or crc32 or md5:
                    if process_dat_rom_entry(cursor, log_id, platform_id, game_name, sha1, crc32, md5, None, is_clone, clone_of, "tosec"):
                        processed_files += 1
                else:
                    print(f"  - Warning: Disk in game '{game_name}' missing all hash values, skipping.")
            
            if processed_files == 0:
                print(f"  - Warning: Game '{game_name}' had no valid ROM/disk files to process.")
                return False
            
            return True

        except Exception as e:
            print(f"  - ERROR processing game '{game_name}': {e}")
            return False

    def process_single_file(self, file_path, log_id, source_id):
        """Process a single TOSEC DAT file."""
        records_processed = 0
        records_failed = 0

        # Get DTD schema path from database configuration
        schema_path = self.get_schema_path_from_db(source_id)
        dtd_schema = None
        
        if schema_path:
            schema_file = Path(schema_path)
            if schema_file.exists():
                dtd_schema = load_dtd_schema(schema_file)
                if dtd_schema is None:
                    raise Exception(f"Failed to load DTD schema from {schema_path}")
            else:
                raise Exception(f"DTD schema file specified but not found at {schema_path}")
        else:
            print("No DTD schema configured, proceeding without validation")
            
        # Validate against DTD schema if available
        if dtd_schema:
            is_valid, validation_message = validate_xml_against_schema(file_path, dtd_schema, "DTD")
            handle_schema_validation_warning(file_path, is_valid, validation_message, "DTD")

        # Parse the XML DAT file
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Extract platform information from header or filename
        header = root.find('header')
        if header is not None:
            platform_name = self.extract_platform_from_tosec_header(header)
        else:
            platform_name = self.extract_platform_from_filename(file_path.stem)
        
        print(f"Detected platform: {platform_name}")
        
        # Get games from the datafile
        games = root.findall('game')
        print(f"Found {len(games)} game entries in the TOSEC DAT file.")
        
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
        parser = argparse.ArgumentParser(description="TOSEC DAT Importer for the Atomic Game Database (v1.6 compatible).")
        parser.add_argument('--source_id', required=True, type=int, help="The source_id from the metadata_source table.")
        parser.add_argument('--db_path', required=True, help="Path to the SQLite database file.")
        parser.add_argument('--files', nargs='+', required=True, help="List of TOSEC DAT files to import.")
        return parser


def main():
    """Main entry point for the TOSEC importer."""
    # Parse arguments first to get database path
    parser = argparse.ArgumentParser(description="TOSEC DAT Importer for the Atomic Game Database (v1.6 compatible).")
    parser.add_argument('--source_id', required=True, type=int, help="The source_id from the metadata_source table.")
    parser.add_argument('--db_path', required=True, help="Path to the SQLite database file.")
    parser.add_argument('--files', nargs='+', required=True, help="List of TOSEC DAT files to import.")
    args = parser.parse_args()
    
    # Initialize with the actual database path
    importer = TosecImporter(args.db_path)
    importer.run(args)


if __name__ == '__main__':
    main()
