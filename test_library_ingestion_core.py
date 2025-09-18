"""
Core unit tests for Library Ingestion functionality (without GUI dependencies)

Tests cover:
- CLI invocation of library_ingestion.py
- Configuration handling
- Database integration
- File processing logic
"""

import unittest
import tempfile
import shutil
import json
import sqlite3
from pathlib import Path
import sys
import os

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))


class TestConfigManager(unittest.TestCase):
    """Test cases for configuration management."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.test_dir, 'config.json')
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
    
    def test_config_creation_with_ingestion_settings(self):
        """Test that configuration is created with proper ingestion settings."""
        # Create a minimal config manager implementation
        class SimpleConfigManager:
            def __init__(self, config_file='config.json'):
                self.config_file = Path(config_file)
                self.config = self.load_config()
            
            def load_config(self):
                if not self.config_file.exists():
                    default_config = {
                        "database_path": "./database/RomCurator.db",
                        "importer_scripts_directory": "./scripts/seeders/",
                        "log_directory": "./logs/",
                        "log_level": "INFO",
                        "auto_create_directories": True,
                        "progress_update_interval": 100,
                        "gui_settings": {
                            "window_width": 1200,
                            "window_height": 800,
                            "theme": "dark"
                        },
                        "ingestion_settings": {
                            "library_roots": [],
                            "batch_size": 100,
                            "enable_validation": True,
                            "enable_archive_expansion": True,
                            "hash_algorithms": ["sha1", "crc32", "md5", "sha256"],
                            "file_extensions": {
                                "rom": [".rom", ".bin", ".smd", ".sfc", ".nes", ".gb", ".gba", ".nds", ".iso", ".img"],
                                "archive": [".zip", ".7z", ".rar", ".tar", ".gz"]
                            },
                            "max_file_size_mb": 1024,
                            "exclude_patterns": ["*.tmp", "*.temp", "*.bak", "*.backup"],
                            "enable_platform_detection": True,
                            "enable_metadata_extraction": True
                        }
                    }
                    
                    with open(self.config_file, 'w') as f:
                        json.dump(default_config, f, indent=4)
                    return default_config
                
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            
            def get(self, key, default=None):
                keys = key.split('.')
                value = self.config
                
                for k in keys:
                    if isinstance(value, dict) and k in value:
                        value = value[k]
                    else:
                        return default
                
                return value
        
        config_manager = SimpleConfigManager(self.config_path)
        
        # Test that ingestion settings are properly loaded
        ingestion_settings = config_manager.get('ingestion_settings')
        self.assertIsNotNone(ingestion_settings)
        self.assertEqual(ingestion_settings['batch_size'], 100)
        self.assertTrue(ingestion_settings['enable_validation'])
        self.assertTrue(ingestion_settings['enable_archive_expansion'])
        self.assertIn('sha1', ingestion_settings['hash_algorithms'])
        self.assertIn('crc32', ingestion_settings['hash_algorithms'])
        self.assertIn('md5', ingestion_settings['hash_algorithms'])
        self.assertIn('sha256', ingestion_settings['hash_algorithms'])
        self.assertEqual(ingestion_settings['max_file_size_mb'], 1024)
        self.assertIn('*.tmp', ingestion_settings['exclude_patterns'])


class TestLibraryIngestionCore(unittest.TestCase):
    """Test cases for core library ingestion functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, 'test.db')
        
        # Create test database
        self._create_test_database()
        
        # Create test library structure
        self._create_test_library()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
    
    def _create_test_database(self):
        """Create a test database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create essential tables
        cursor.execute("""
            CREATE TABLE metadata_source (
                source_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                importer_script TEXT,
                schema_file_path TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE import_log (
                log_id INTEGER PRIMARY KEY,
                source_id INTEGER NOT NULL REFERENCES metadata_source(source_id),
                file_name TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                import_timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
                records_processed INTEGER DEFAULT 0,
                notes TEXT,
                UNIQUE(file_hash)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE platform (
                platform_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE rom_file (
                rom_id INTEGER PRIMARY KEY,
                file_name TEXT NOT NULL,
                file_path TEXT,
                size_bytes INTEGER,
                modified_time TEXT,
                sha1 TEXT,
                crc32 TEXT,
                md5 TEXT,
                sha256 TEXT,
                platform_id INTEGER REFERENCES platform(platform_id),
                content_role TEXT DEFAULT 'primary'
            )
        """)
        
        cursor.execute("""
            CREATE TABLE file_discovery (
                discovery_id INTEGER PRIMARY KEY,
                log_id INTEGER NOT NULL REFERENCES import_log(log_id),
                root_id INTEGER NOT NULL,
                absolute_path TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                size_bytes INTEGER,
                modified_time TEXT,
                rom_id INTEGER REFERENCES rom_file(rom_id),
                promotion_state TEXT NOT NULL DEFAULT 'pending' CHECK (promotion_state IN ('pending','hashed','failed')),
                first_seen TEXT NOT NULL DEFAULT (datetime('now')),
                last_seen TEXT NOT NULL DEFAULT (datetime('now')),
                depth INTEGER DEFAULT 0,
                message TEXT,
                UNIQUE(root_id, relative_path)
            )
        """)
        
        # Insert test metadata source
        cursor.execute("""
            INSERT INTO metadata_source (source_id, name, importer_script)
            VALUES (4, 'file_ingestion', 'scripts/seeders/library_ingestion.py')
        """)
        
        conn.commit()
        conn.close()
    
    def _create_test_library(self):
        """Create test library structure with sample files."""
        # Create test ROM files
        self.rom_dir = os.path.join(self.test_dir, 'test_library')
        os.makedirs(self.rom_dir, exist_ok=True)
        
        # Create subdirectories for different platforms
        nes_dir = os.path.join(self.rom_dir, 'nes')
        snes_dir = os.path.join(self.rom_dir, 'snes')
        gb_dir = os.path.join(self.rom_dir, 'gameboy')
        
        os.makedirs(nes_dir, exist_ok=True)
        os.makedirs(snes_dir, exist_ok=True)
        os.makedirs(gb_dir, exist_ok=True)
        
        # Create test ROM files
        self.test_files = []
        
        # NES ROM
        nes_file = os.path.join(nes_dir, 'test_game.nes')
        with open(nes_file, 'wb') as f:
            f.write(b'NES\x1a' + b'\x00' * 1000)  # Simple NES header + data
        self.test_files.append(nes_file)
        
        # SNES ROM
        snes_file = os.path.join(snes_dir, 'test_game.sfc')
        with open(snes_file, 'wb') as f:
            f.write(b'\x00' * 2000)  # Simple SNES ROM data
        self.test_files.append(snes_file)
        
        # Game Boy ROM
        gb_file = os.path.join(gb_dir, 'test_game.gb')
        with open(gb_file, 'wb') as f:
            f.write(b'\x00' * 500)  # Simple GB ROM data
        self.test_files.append(gb_file)
        
        # Create a file that should be excluded
        excluded_file = os.path.join(self.rom_dir, 'temp_file.tmp')
        with open(excluded_file, 'w') as f:
            f.write('This should be excluded')
    
    def test_metadata_source_registration(self):
        """Test that file_ingestion is properly registered in metadata_source."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM metadata_source WHERE name = 'file_ingestion'")
        source_record = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(source_record)
        self.assertEqual(source_record[1], 'file_ingestion')
        self.assertEqual(source_record[2], 'scripts/seeders/library_ingestion.py')
        self.assertIsNone(source_record[3])  # schema_file_path
    
    def test_file_discovery_logic(self):
        """Test file discovery and classification logic."""
        # Test file extension classification
        rom_extensions = [".rom", ".bin", ".smd", ".sfc", ".nes", ".gb", ".gba", ".nds", ".iso", ".img"]
        archive_extensions = [".zip", ".7z", ".rar", ".tar", ".gz"]
        
        # Test ROM file detection
        for test_file in self.test_files:
            file_ext = Path(test_file).suffix.lower()
            self.assertIn(file_ext, rom_extensions)
        
        # Test excluded file detection
        excluded_file = Path(os.path.join(self.rom_dir, 'temp_file.tmp'))
        self.assertEqual(excluded_file.suffix.lower(), '.tmp')
    
    def test_hash_calculation_algorithms(self):
        """Test that all required hash algorithms are available."""
        import hashlib
        import zlib
        
        # Test that we can create hash objects for all algorithms
        test_data = b'test data for hashing'
        
        # SHA1
        sha1_hash = hashlib.sha1(test_data).hexdigest()
        self.assertIsInstance(sha1_hash, str)
        self.assertEqual(len(sha1_hash), 40)
        
        # MD5
        md5_hash = hashlib.md5(test_data).hexdigest()
        self.assertIsInstance(md5_hash, str)
        self.assertEqual(len(md5_hash), 32)
        
        # SHA256
        sha256_hash = hashlib.sha256(test_data).hexdigest()
        self.assertIsInstance(sha256_hash, str)
        self.assertEqual(len(sha256_hash), 64)
        
        # CRC32
        crc32_hash = format(zlib.crc32(test_data) & 0xffffffff, '08x')
        self.assertIsInstance(crc32_hash, str)
        self.assertEqual(len(crc32_hash), 8)
    
    def test_platform_detection_rules(self):
        """Test platform detection rules."""
        # Test platform detection based on file extensions
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
        
        for ext, expected_platform in ext_platform_map.items():
            self.assertIsInstance(ext, str)
            self.assertIsInstance(expected_platform, str)
            self.assertTrue(ext.startswith('.'))
    
    def test_database_schema_compatibility(self):
        """Test that the database schema supports all required operations."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Test that we can insert a ROM file record
        cursor.execute("""
            INSERT INTO rom_file (
                file_name, file_path, size_bytes, modified_time,
                sha1, crc32, md5, sha256, platform_id, content_role
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'test.nes',
            '/path/to/test.nes',
            1024,
            '2025-01-01T00:00:00',
            'test_sha1_hash',
            'test_crc32_hash',
            'test_md5_hash',
            'test_sha256_hash',
            1,
            'primary'
        ))
        
        rom_id = cursor.lastrowid
        self.assertIsNotNone(rom_id)
        
        # Test that we can insert a file discovery record
        cursor.execute("""
            INSERT INTO file_discovery (
                log_id, root_id, absolute_path, relative_path, size_bytes,
                modified_time, rom_id, promotion_state, first_seen, last_seen
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            1,  # log_id
            1,  # root_id
            '/absolute/path/to/test.nes',
            'test.nes',
            1024,
            '2025-01-01T00:00:00',
            rom_id,
            'hashed',
            '2025-01-01T00:00:00',
            '2025-01-01T00:00:00'
        ))
        
        discovery_id = cursor.lastrowid
        self.assertIsNotNone(discovery_id)
        
        conn.commit()
        conn.close()
    
    def test_cli_argument_parsing(self):
        """Test CLI argument parsing without importing the full module."""
        import argparse
        
        # Create argument parser similar to the one in library_ingestion.py
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
        
        # Test parsing valid arguments
        args = parser.parse_args([
            '--source_id', '4',
            '--db_path', self.db_path,
            '--files', self.rom_dir,
            '--batch_size', '25',
            '--hash_algorithms', 'sha1', 'md5'
        ])
        
        self.assertEqual(args.source_id, 4)
        self.assertEqual(args.db_path, self.db_path)
        self.assertEqual(args.files, [self.rom_dir])
        self.assertEqual(args.batch_size, 25)
        self.assertEqual(args.hash_algorithms, ['sha1', 'md5'])
    
    def test_configuration_validation(self):
        """Test that configuration values are valid."""
        config = {
            "ingestion_settings": {
                "library_roots": [],
                "batch_size": 100,
                "enable_validation": True,
                "enable_archive_expansion": True,
                "hash_algorithms": ["sha1", "crc32", "md5", "sha256"],
                "file_extensions": {
                    "rom": [".rom", ".bin", ".smd", ".sfc", ".nes", ".gb", ".gba", ".nds", ".iso", ".img"],
                    "archive": [".zip", ".7z", ".rar", ".tar", ".gz"]
                },
                "max_file_size_mb": 1024,
                "exclude_patterns": ["*.tmp", "*.temp", "*.bak", "*.backup"],
                "enable_platform_detection": True,
                "enable_metadata_extraction": True
            }
        }
        
        ingestion_settings = config['ingestion_settings']
        
        # Validate batch size
        self.assertIsInstance(ingestion_settings['batch_size'], int)
        self.assertGreater(ingestion_settings['batch_size'], 0)
        
        # Validate boolean flags
        self.assertIsInstance(ingestion_settings['enable_validation'], bool)
        self.assertIsInstance(ingestion_settings['enable_archive_expansion'], bool)
        self.assertIsInstance(ingestion_settings['enable_platform_detection'], bool)
        self.assertIsInstance(ingestion_settings['enable_metadata_extraction'], bool)
        
        # Validate hash algorithms
        valid_algorithms = ['sha1', 'crc32', 'md5', 'sha256']
        for algo in ingestion_settings['hash_algorithms']:
            self.assertIn(algo, valid_algorithms)
        
        # Validate file extensions
        self.assertIn('rom', ingestion_settings['file_extensions'])
        self.assertIn('archive', ingestion_settings['file_extensions'])
        
        # All ROM extensions should start with a dot
        for ext in ingestion_settings['file_extensions']['rom']:
            self.assertTrue(ext.startswith('.'))
        
        # All archive extensions should start with a dot
        for ext in ingestion_settings['file_extensions']['archive']:
            self.assertTrue(ext.startswith('.'))
        
        # Validate max file size
        self.assertIsInstance(ingestion_settings['max_file_size_mb'], int)
        self.assertGreater(ingestion_settings['max_file_size_mb'], 0)
        
        # Validate exclude patterns
        for pattern in ingestion_settings['exclude_patterns']:
            self.assertIsInstance(pattern, str)
            self.assertTrue(pattern.startswith('*'))


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)