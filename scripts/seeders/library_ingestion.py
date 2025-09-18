"""
Library File Ingestion Importer for ROM Curator

This importer handles scanning and ingesting files from library directories,
including ROM files, archives, and metadata extraction. It follows the
BaseImporter pattern and integrates with the existing database schema.

Features:
- File discovery and classification
- Hash calculation (SHA1, CRC32, MD5, SHA256)
- Archive expansion and member file processing
- Platform detection from file paths and extensions
- Metadata extraction and storage
- Progress reporting and cancellation support
"""

import argparse
import hashlib
import logging
import os
import sqlite3
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import fnmatch

try:
    from .base_importer import BaseImporter, DatabaseHandler
except ImportError:
    from base_importer import BaseImporter, DatabaseHandler

# Import extension registry manager
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from extension_registry_manager import ExtensionRegistryManager


class LibraryIngestionImporter(BaseImporter):
    """Library file ingestion importer that processes files from configured directories."""
    
    def __init__(self, db_path: str, config: Dict[str, Any] = None):
        super().__init__(db_path)
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        
        # Load config if not provided
        if config is None:
            config = self._load_config()
        
        self.config = config
        self.ingestion_settings = self.config.get('ingestion_settings', {})
        self.library_roots = self.ingestion_settings.get('library_roots', [])
        self.batch_size = self.ingestion_settings.get('batch_size', 100)
        self.enable_validation = self.ingestion_settings.get('enable_validation', True)
        self.enable_archive_expansion = self.ingestion_settings.get('enable_archive_expansion', True)
        # Only use hash algorithms that exist in the current database schema
        self.hash_algorithms = self.ingestion_settings.get('hash_algorithms', ['sha1', 'crc32', 'md5'])
        self.max_file_size_mb = self.ingestion_settings.get('max_file_size_mb', 1024)
        self.exclude_patterns = self.ingestion_settings.get('exclude_patterns', [])
        self.enable_platform_detection = self.ingestion_settings.get('enable_platform_detection', True)
        self.enable_metadata_extraction = self.ingestion_settings.get('enable_metadata_extraction', True)
        
        # Initialize extension registry manager
        self.extension_registry = ExtensionRegistryManager(db_path)
        
        # Load supported file extensions from registry
        self.supported_extensions = self._load_supported_extensions()
        
        # Statistics tracking
        self.stats = {
            'files_discovered': 0,
            'files_processed': 0,
            'files_hashed': 0,
            'files_matched': 0,
            'files_pending_review': 0,
            'archives_expanded': 0,
            'errors': 0
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from project root."""
        import json
        from pathlib import Path
        
        # Look for config.json in the project root (two levels up from this script)
        script_dir = Path(__file__).parent
        project_root = script_dir.parent.parent
        config_file = project_root / 'config.json'
        
        config = {}
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load config file {config_file}: {e}")
                print("Using default configuration values.")
        else:
            print(f"Warning: Config file not found at {config_file}")
            print("Using default configuration values.")
        
        return config
    
    def _load_supported_extensions(self) -> Dict[str, List[str]]:
        """Load supported file extensions from the extension registry."""
        try:
            # Get all active extensions
            extensions = self.extension_registry.get_extensions(active_only=True)
            
            # Group by type
            supported = {
                'rom': [],
                'archive': [],
                'save': [],
                'patch': []
            }
            
            for ext in extensions:
                ext_name = ext['extension']
                
                if ext['is_rom']:
                    supported['rom'].append(ext_name)
                if ext['is_archive']:
                    supported['archive'].append(ext_name)
                if ext['is_save']:
                    supported['save'].append(ext_name)
                if ext['is_patch']:
                    supported['patch'].append(ext_name)
            
            self.logger.info(f"Loaded {len(extensions)} supported extensions from registry")
            return supported
            
        except Exception as e:
            self.logger.warning(f"Failed to load extensions from registry: {e}")
            # Fallback to config-based extensions
            return self.ingestion_settings.get('file_extensions', {
                'rom': ['.rom', '.bin', '.nes', '.sfc', '.smd', '.gb', '.gba', '.nds'],
                'archive': ['.zip', '.7z', '.rar', '.tar', '.gz'],
                'save': ['.sav', '.srm', '.state'],
                'patch': ['.ips', '.ups', '.bps', '.xdelta']
            })
    
    def get_file_type_description(self):
        return "Library File Ingestion"
    
    def handle_existing_import(self, file_path, file_hash):
        """
        Override to handle directories for library ingestion.
        For library ingestion, we don't check existing imports by file hash
        since we're processing directories, not individual files.
        """
        # For library ingestion, we always process the directory
        # The individual file processing will handle duplicate detection
        return False
    
    def process_files(self, source_id, file_paths):
        """
        Override the base process_files method to handle directories for library ingestion.
        """
        for file_path_str in file_paths:
            file_path = Path(file_path_str)
            print(f"\n--- Processing {self.get_file_type_description()} directory: {file_path.name} ---")

            # For library ingestion, we create a custom import log entry
            log_id = self._start_library_import_log(source_id, file_path)
            
            try:
                # Process the directory for file ingestion
                records_processed, notes = self.process_single_file(file_path, log_id, source_id)
                
                self.db.finish_import_log(log_id, 'completed', records_processed, notes)
                print(f"--- Finished processing {file_path.name} ---")
                
            except Exception as e:
                error_message = f"Critical error: {e}. All changes for this file have been rolled back."
                print(error_message)
                self.db.finish_import_log(log_id, 'failed', 0, error_message)

        print(f"\nAll {self.get_file_type_description()} directories processed.")
    
    def _start_library_import_log(self, source_id: int, file_path: Path) -> int:
        """Create a custom import log entry for library ingestion."""
        try:
            cursor = self.db.conn.cursor()
            # Use a dummy hash for directories
            file_hash = f"directory_{file_path.name}_{hash(str(file_path))}"
            cursor.execute(
                """
                INSERT INTO import_log (source_id, file_name, file_hash, status)
                VALUES (?, ?, ?, 'running')
                """,
                (source_id, file_path.name, file_hash)
            )
            self.db.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"Error creating import log entry: {e}")
            raise
    
    def create_argument_parser(self):
        """Create argument parser for CLI usage."""
        parser = argparse.ArgumentParser(description='Library File Ingestion Importer')
        parser.add_argument('--source_id', type=int, required=True, help='Metadata source ID')
        parser.add_argument('--db_path', type=str, required=True, help='Database path')
        parser.add_argument('--files', nargs='+', help='Library root directories to scan')
        parser.add_argument('--batch_size', type=int, default=100, help='Batch size for processing')
        parser.add_argument('--enable_validation', action='store_true', default=True, help='Enable file validation')
        parser.add_argument('--enable_archive_expansion', action='store_true', default=True, help='Enable archive expansion')
        parser.add_argument('--hash_algorithms', nargs='+', default=['sha1', 'crc32', 'md5', 'sha256'], 
                          help='Hash algorithms to use')
        parser.add_argument('--max_file_size_mb', type=int, default=1024, help='Maximum file size in MB')
        parser.add_argument('--exclude_patterns', nargs='+', default=[], help='File patterns to exclude')
        return parser
    
    def process_single_file(self, file_path: Path, log_id: int, source_id: int) -> Tuple[int, str]:
        """
        Process a single library root directory for file ingestion.
        This method is called by the base importer for each directory.
        """
        try:
            # Override library roots if provided via CLI
            if hasattr(self, '_cli_library_roots') and self._cli_library_roots:
                self.library_roots = self._cli_library_roots
            else:
                # Use the file_path as a single library root
                self.library_roots = [str(file_path)]
            
            if not self.library_roots:
                return 0, "No library roots configured"
            
            # Validate that all library roots exist
            valid_roots = []
            for root_path in self.library_roots:
                root_path = Path(root_path)
                if root_path.exists() and root_path.is_dir():
                    valid_roots.append(root_path)
                else:
                    print(f"Warning: Library root does not exist or is not a directory: {root_path}")
            
            if not valid_roots:
                return 0, "No valid library roots found"
            
            self.library_roots = [str(r) for r in valid_roots]
            
            # Process all library roots
            total_processed = 0
            notes_parts = []
            
            for root_path in self.library_roots:
                root_path = Path(root_path)
                if not root_path.exists():
                    notes_parts.append(f"Library root not found: {root_path}")
                    continue
                
                if not root_path.is_dir():
                    notes_parts.append(f"Library root is not a directory: {root_path}")
                    continue
                
                # Discover files in this root
                discovered_files = self._discover_files(root_path)
                self.stats['files_discovered'] += len(discovered_files)
                
                # Process files in batches
                for i in range(0, len(discovered_files), self.batch_size):
                    batch = discovered_files[i:i + self.batch_size]
                    batch_processed = self._process_file_batch(batch, log_id, source_id)
                    total_processed += batch_processed
                    
                    # Report progress
                    print(f"Processed batch {i//self.batch_size + 1}: {batch_processed} files")
            
            # Generate summary
            summary = self._generate_summary()
            notes_parts.append(summary)
            
            return total_processed, "; ".join(notes_parts)
            
        except Exception as e:
            error_msg = f"Error processing library ingestion: {e}"
            print(error_msg)
            return 0, error_msg
    
    def _discover_files(self, root_path: Path) -> List[Path]:
        """Discover files in the library root directory."""
        discovered_files = []
        
        try:
            for file_path in root_path.rglob('*'):
                if file_path.is_file():
                    # Check file size
                    file_size_mb = file_path.stat().st_size / (1024 * 1024)
                    if file_size_mb > self.max_file_size_mb:
                        print(f"Skipping large file: {file_path} ({file_size_mb:.1f} MB)")
                        continue
                    
                    # Check exclude patterns
                    if self._should_exclude_file(file_path):
                        continue
                    
                    # Check if file matches supported extensions
                    if self._is_supported_file(file_path):
                        discovered_files.append(file_path)
        
        except PermissionError as e:
            print(f"Permission denied accessing {root_path}: {e}")
        except Exception as e:
            print(f"Error discovering files in {root_path}: {e}")
        
        return discovered_files
    
    def _should_exclude_file(self, file_path: Path) -> bool:
        """Check if file should be excluded based on patterns."""
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(file_path.name.lower(), pattern.lower()):
                return True
        return False
    
    def _is_supported_file(self, file_path: Path) -> bool:
        """Check if file is supported based on extensions."""
        file_ext = file_path.suffix.lower()
        
        # Use extension registry to detect file type
        if file_type_info := self.extension_registry.detect_file_type(file_path.name):
            # File is recognized by registry
            return True
        
        # Check if extension is in our supported lists (fallback)
        # Check ROM extensions
        rom_extensions = self.supported_extensions.get('rom', [])
        if file_ext in rom_extensions:
            return True
        
        # Check archive extensions
        if self.enable_archive_expansion:
            archive_extensions = self.supported_extensions.get('archive', [])
            if file_ext in archive_extensions:
                return True
        
        # If not recognized, record as unknown extension
        if file_ext:
            self.extension_registry.record_unknown_extension(file_ext)
            self.logger.info(f"Unknown extension encountered: {file_ext} in {file_path}")
        
        return False
    
    def _process_file_batch(self, file_paths: List[Path], log_id: int, source_id: int) -> int:
        """Process a batch of files."""
        processed_count = 0
        
        for file_path in file_paths:
            try:
                # Calculate hashes
                hashes = self._calculate_file_hashes(file_path)
                if not hashes:
                    continue
                
                self.stats['files_hashed'] += 1
                
                # Check if file already exists in database
                existing_rom_id = self._find_existing_rom_file(hashes)
                
                if existing_rom_id:
                    # File already exists, update discovery record
                    self._update_file_discovery(file_path, existing_rom_id, log_id)
                    self.stats['files_matched'] += 1
                else:
                    # New file, create ROM file record
                    rom_id = self._create_rom_file_record(file_path, hashes, log_id)
                    if rom_id:
                        self._create_file_discovery_record(file_path, rom_id, log_id)
                        self.stats['files_pending_review'] += 1
                
                # Handle archive expansion if enabled
                if self.enable_archive_expansion and self._is_archive_file(file_path):
                    self._expand_archive(file_path, log_id, source_id)
                    self.stats['archives_expanded'] += 1
                
                processed_count += 1
                self.stats['files_processed'] += 1
                
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
                self.stats['errors'] += 1
        
        return processed_count
    
    def _calculate_file_hashes(self, file_path: Path) -> Dict[str, str]:
        """Calculate hashes for a file using configured algorithms."""
        hashes = {}
        
        try:
            # Check if file exists and is readable
            if not file_path.exists():
                print(f"File does not exist: {file_path}")
                return {}
            
            if not file_path.is_file():
                print(f"Path is not a file: {file_path}")
                return {}
            
            # Check file size before processing
            file_size = file_path.stat().st_size
            if file_size == 0:
                print(f"File is empty: {file_path}")
                return {}
            
            with open(file_path, 'rb') as f:
                # Read file in chunks for memory efficiency
                chunk_size = 8192
                
                # Initialize hash objects
                hash_objects = {}
                for algo in self.hash_algorithms:
                    if algo.lower() == 'sha1':
                        hash_objects['sha1'] = hashlib.sha1()
                    elif algo.lower() == 'crc32':
                        import zlib
                        hash_objects['crc32'] = zlib.crc32(b'')
                    elif algo.lower() == 'md5':
                        hash_objects['md5'] = hashlib.md5()
                    elif algo.lower() == 'sha256':
                        hash_objects['sha256'] = hashlib.sha256()
                
                # Process file in chunks
                bytes_read = 0
                while chunk := f.read(chunk_size):
                    bytes_read += len(chunk)
                    for hash_obj in hash_objects.values():
                        if isinstance(hash_obj, int):  # CRC32
                            hash_obj = zlib.crc32(chunk, hash_obj)
                        else:
                            hash_obj.update(chunk)
                
                # Verify we read the entire file
                if bytes_read != file_size:
                    print(f"Warning: Only read {bytes_read} of {file_size} bytes from {file_path}")
                
                # Get final hash values
                for algo, hash_obj in hash_objects.items():
                    if algo == 'crc32':
                        hashes[algo] = format(hash_obj & 0xffffffff, '08x')
                    else:
                        hashes[algo] = hash_obj.hexdigest()
        
        except PermissionError as e:
            print(f"Permission denied reading file {file_path}: {e}")
            return {}
        except OSError as e:
            print(f"OS error reading file {file_path}: {e}")
            return {}
        except Exception as e:
            print(f"Error calculating hashes for {file_path}: {e}")
            return {}
        
        return hashes
    
    def _find_existing_rom_file(self, hashes: Dict[str, str]) -> Optional[int]:
        """Find existing ROM file by hash."""
        try:
            cursor = self.db.conn.cursor()
            
            # Try to find by SHA1 first (most common)
            if 'sha1' in hashes and hashes['sha1']:
                cursor.execute("SELECT rom_id FROM rom_file WHERE sha1 = ?", (hashes['sha1'],))
                row = cursor.fetchone()
                if row:
                    return row['rom_id']
            
            # Try other hash algorithms that exist in the schema
            for algo, hash_value in hashes.items():
                if algo == 'sha1' or not hash_value:
                    continue
                
                column_name = algo.lower()
                if column_name in ['crc32', 'md5']:
                    cursor.execute(f"SELECT rom_id FROM rom_file WHERE {column_name} = ?", (hash_value,))
                    row = cursor.fetchone()
                    if row:
                        return row['rom_id']
            
            return None
            
        except Exception as e:
            print(f"Error finding existing ROM file: {e}")
            return None
    
    def _create_rom_file_record(self, file_path: Path, hashes: Dict[str, str], log_id: int) -> Optional[int]:
        """Create a new ROM file record in the database."""
        try:
            cursor = self.db.conn.cursor()
            
            # Get file stats
            stat = file_path.stat()
            file_size = stat.st_size
            modified_time = datetime.fromtimestamp(stat.st_mtime).isoformat()
            
            # Validate required hashes
            if not hashes.get('sha1'):
                print(f"Warning: No SHA1 hash available for {file_path}")
                return None
            
            # Detect platform if enabled
            platform_id = None
            if self.enable_platform_detection:
                platform_id = self._detect_platform(file_path)
            
            # Insert ROM file record (using existing schema)
            cursor.execute("""
                INSERT INTO rom_file (
                    sha1, md5, crc32, size_bytes, filename
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                hashes.get('sha1', ''),
                hashes.get('md5', ''),
                hashes.get('crc32', ''),
                file_size,
                file_path.name
            ))
            
            rom_id = cursor.lastrowid
            self.db.conn.commit()
            
            return rom_id
            
        except sqlite3.IntegrityError as e:
            print(f"Database integrity error creating ROM file record for {file_path}: {e}")
            self.db.conn.rollback()
            return None
        except Exception as e:
            print(f"Error creating ROM file record for {file_path}: {e}")
            self.db.conn.rollback()
            return None
    
    def _detect_platform(self, file_path: Path) -> Optional[int]:
        """Detect platform from file path and extension using extension registry."""
        try:
            file_ext = file_path.suffix.lower()
            
            # PRIMARY: Try to get platform from extension registry first
            if file_ext and (platform_id := self._get_platform_from_extension_registry(file_ext)):
                self.logger.debug(f"Platform detected from extension registry: {file_ext} -> Platform ID {platform_id}")
                return platform_id
            
            # SECONDARY: Fallback to path-based detection for unmapped extensions
            path_parts = [part.lower() for part in file_path.parts]
            
            # Platform detection rules for path-based detection
            platform_rules = {
                'nintendo': {
                    'nes': 'Nintendo Entertainment System',
                    'snes': 'Super Nintendo Entertainment System',
                    'n64': 'Nintendo 64',
                    'gamecube': 'GameCube',
                    'wii': 'Wii',
                    'gameboy': 'Game Boy',
                    'gb': 'Game Boy',
                    'gba': 'Game Boy Advance',
                    'nds': 'Nintendo DS'
                },
                'sega': {
                    'mastersystem': 'Sega Master System',
                    'megadrive': 'Sega Mega Drive',
                    'genesis': 'Sega Genesis',
                    'saturn': 'Sega Saturn',
                    'dreamcast': 'Sega Dreamcast'
                },
                'sony': {
                    'playstation': 'PlayStation',
                    'ps1': 'PlayStation',
                    'ps2': 'PlayStation 2',
                    'ps3': 'PlayStation 3',
                    'psp': 'PlayStation Portable'
                }
            }
            
            # Check path parts for platform indicators
            for manufacturer, platforms in platform_rules.items():
                if manufacturer in ' '.join(path_parts):
                    for platform_key, platform_name in platforms.items():
                        if platform_key in ' '.join(path_parts):
                            platform_id = self._get_or_create_platform(platform_name)
                            self.logger.debug(f"Platform detected from path: {platform_name} -> Platform ID {platform_id}")
                            return platform_id
            
            # TERTIARY: Final fallback to hardcoded extension mapping
            ext_platform_map = {
                '.nes': 'Nintendo Entertainment System',
                '.sfc': 'Super Nintendo Entertainment System',
                '.n64': 'Nintendo 64',
                '.gb': 'Game Boy',
                '.gba': 'Game Boy Advance',
                '.nds': 'Nintendo DS',
                '.smd': 'Sega Mega Drive',
                '.iso': 'PlayStation'  # Generic ISO, could be any platform
            }
            
            if file_ext in ext_platform_map:
                platform_id = self._get_or_create_platform(ext_platform_map[file_ext])
                self.logger.debug(f"Platform detected from hardcoded mapping: {file_ext} -> {ext_platform_map[file_ext]} -> Platform ID {platform_id}")
                return platform_id
            
            self.logger.debug(f"No platform detected for {file_path} (extension: {file_ext})")
            
        except Exception as e:
            self.logger.error(f"Error detecting platform for {file_path}: {e}")
        
        return None
    
    def _get_platform_from_extension_registry(self, file_ext: str) -> Optional[int]:
        """Get platform ID from extension registry for the given file extension."""
        try:
            # Get the extension info from registry
            if not (extension_info := self.extension_registry.get_extension_by_name(file_ext)):
                return None

            # Get platform mappings for this extension
            if not (platform_mappings := self.extension_registry.get_platforms_for_extension(extension_info['extension_id'])):
                return None
            
            # Prefer primary mappings, then highest confidence
            primary_mappings = [m for m in platform_mappings if m.get('is_primary', False)]
            if primary_mappings:
                # Return the first primary mapping
                return primary_mappings[0]['platform_id']
            
            # If no primary mappings, return the highest confidence mapping
            best_mapping = max(platform_mappings, key=lambda m: m.get('confidence', 0.0))
            return best_mapping['platform_id']
            
        except Exception as e:
            print(f"Error getting platform from extension registry for {file_ext}: {e}")
            return None
    
    def _get_or_create_platform(self, platform_name: str) -> Optional[int]:
        """Get or create platform in database."""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT platform_id FROM platform WHERE name = ?", (platform_name,))
            row = cursor.fetchone()
            
            if row:
                return row['platform_id']
            else:
                cursor.execute("INSERT INTO platform (name) VALUES (?)", (platform_name,))
                self.db.conn.commit()
                return cursor.lastrowid
                
        except Exception as e:
            print(f"Error getting/creating platform {platform_name}: {e}")
            return None
    
    def _get_or_create_library_root(self, file_path: Path) -> int:
        """Get or create library root record for the given file path."""
        try:
            cursor = self.db.conn.cursor()
            
            # Find the library root by checking if the file path starts with any configured root
            for root_path in self.library_roots:
                root_path = Path(root_path)
                try:
                    # Check if file_path is within this root
                    relative_path = file_path.relative_to(root_path)
                    
                    # Check if this root already exists in the database
                    cursor.execute("""
                        SELECT root_id FROM library_root 
                        WHERE absolute_path = ?
                    """, (str(root_path.absolute()),))
                    
                    row = cursor.fetchone()
                    if row:
                        return row['root_id']
                    
                    # Create new library root record
                    cursor.execute("""
                        INSERT INTO library_root (absolute_path, name, created_at)
                        VALUES (?, ?, ?)
                    """, (
                        str(root_path.absolute()),
                        root_path.name,
                        datetime.now().isoformat()
                    ))
                    
                    self.db.conn.commit()
                    return cursor.lastrowid
                    
                except ValueError:
                    # file_path is not within this root, continue to next
                    continue
            
            # If no configured root matches, create a default one
            default_root_id = 1
            cursor.execute("""
                INSERT OR IGNORE INTO library_root (root_id, absolute_path, name, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                default_root_id,
                str(file_path.parent.absolute()),
                "Default Library Root",
                datetime.now().isoformat()
            ))
            
            self.db.conn.commit()
            return default_root_id
            
        except Exception as e:
            print(f"Error getting/creating library root for {file_path}: {e}")
            # Return default root_id as fallback
            return 1
    
    def _create_file_discovery_record(self, file_path: Path, rom_id: int, log_id: int):
        """Create file discovery record."""
        try:
            cursor = self.db.conn.cursor()
            
            # Get or create library root record
            root_id = self._get_or_create_library_root(file_path)
            
            cursor.execute("""
                INSERT INTO file_discovery (
                    log_id, root_id, absolute_path, relative_path, size_bytes,
                    modified_time, rom_id, promotion_state, first_seen, last_seen
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id,
                root_id,
                str(file_path.absolute()),
                str(file_path.relative_to(file_path.parents[0])),  # Simple relative path
                file_path.stat().st_size,
                datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                rom_id,
                'hashed',
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            self.db.conn.commit()
            
        except Exception as e:
            print(f"Error creating file discovery record for {file_path}: {e}")
    
    def _update_file_discovery(self, file_path: Path, rom_id: int, log_id: int):
        """Update existing file discovery record."""
        try:
            cursor = self.db.conn.cursor()
            
            cursor.execute("""
                UPDATE file_discovery 
                SET rom_id = ?, last_seen = ?, promotion_state = 'hashed'
                WHERE absolute_path = ?
            """, (rom_id, datetime.now().isoformat(), str(file_path.absolute())))
            
            if cursor.rowcount == 0:
                print(f"Warning: No file discovery record found to update for {file_path}")
            
            self.db.conn.commit()
            
        except Exception as e:
            print(f"Error updating file discovery record for {file_path}: {e}")
            self.stats['errors'] += 1
    
    def _is_archive_file(self, file_path: Path) -> bool:
        """Check if file is an archive."""
        # Use extension registry to detect archive files
        file_type_info = self.extension_registry.detect_file_type(file_path.name)
        
        if file_type_info and file_type_info.get('is_archive'):
            return True
        
        # Fallback to supported extensions list
        archive_extensions = self.supported_extensions.get('archive', [])
        return file_path.suffix.lower() in archive_extensions
    
    def _expand_archive(self, file_path: Path, log_id: int, source_id: int):
        """Expand archive and process member files."""
        try:
            # This is a placeholder for archive expansion
            # In a real implementation, this would use libraries like zipfile, py7zr, etc.
            # For now, we just log that archive expansion is not implemented
            print(f"Archive expansion not yet implemented for {file_path}")
            
            # TODO: Implement actual archive expansion
            # - Use zipfile for .zip files
            # - Use py7zr for .7z files
            # - Use rarfile for .rar files
            # - Extract member files to temporary directory
            # - Process each member file as a ROM file
            # - Create archive_member records linking parent to children
            # - Clean up temporary files
            
        except Exception as e:
            print(f"Error expanding archive {file_path}: {e}")
            self.stats['errors'] += 1
    
    def _generate_summary(self) -> str:
        """Generate processing summary."""
        return (f"Files discovered: {self.stats['files_discovered']}, "
                f"processed: {self.stats['files_processed']}, "
                f"hashed: {self.stats['files_hashed']}, "
                f"matched: {self.stats['files_matched']}, "
                f"pending review: {self.stats['files_pending_review']}, "
                f"archives expanded: {self.stats['archives_expanded']}, "
                f"errors: {self.stats['errors']}")


def main():
    """Main entry point for CLI usage."""
    import json
    from pathlib import Path
    
    # Load configuration from project root
    # Look for config.json in the project root (two levels up from this script)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    config_file = project_root / 'config.json'
    
    config = {}
    if config_file.exists():
        with open(config_file, 'r') as f:
            config = json.load(f)
    else:
        print(f"Warning: Config file not found at {config_file}")
        print("Using default configuration values.")
    
    # Create importer
    importer = LibraryIngestionImporter(config.get('database_path', './database/RomCurator.db'), config)
    
    # Create argument parser
    parser = importer.create_argument_parser()
    args = parser.parse_args()
    
    # Override settings from CLI arguments
    if args.files:
        importer._cli_library_roots = args.files
    if args.batch_size:
        importer.batch_size = args.batch_size
    if args.hash_algorithms:
        importer.hash_algorithms = args.hash_algorithms
    if args.max_file_size_mb:
        importer.max_file_size_mb = args.max_file_size_mb
    if args.exclude_patterns:
        importer.exclude_patterns = args.exclude_patterns
    
    # Run the importer
    try:
        importer.run(args)
    finally:
        importer.close()


if __name__ == '__main__':
    main()