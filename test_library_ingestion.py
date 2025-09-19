"""
Unit tests for Library Ingestion functionality

Tests cover:
- CLI invocation of library_ingestion.py
- GUI wiring and configuration
- Configuration persistence
- Database integration
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

from config_manager import ConfigManager
from scripts.seeders.library_ingestion import LibraryIngestionImporter


class TestLibraryIngestion(unittest.TestCase):
    """Test cases for library ingestion functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, 'test.db')
        self.config_path = os.path.join(self.test_dir, 'config.json')
        
        # Create test database
        self._create_test_database()
        
        # Create test configuration
        self._create_test_config()
        
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
    
    def _create_test_config(self):
        """Create test configuration file."""
        config = {
            "database_path": self.db_path,
            "importer_scripts_directory": "./scripts/seeders/",
            "log_directory": os.path.join(self.test_dir, "logs"),
            "log_level": "DEBUG",
            "auto_create_directories": True,
            "progress_update_interval": 100,
            "gui_settings": {
                "window_width": 1200,
                "window_height": 800,
                "theme": "dark"
            },
            "ingestion_settings": {
                "library_roots": [],
                "batch_size": 10,
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
        
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=4)
    
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
    
    def test_config_manager_defaults(self):
        """Test that ConfigManager creates proper default configuration."""
        config_manager = ConfigManager(self.config_path)
        
        # Test that ingestion settings are properly loaded
        ingestion_settings = config_manager.get('ingestion_settings')
        self.assertIsNotNone(ingestion_settings)
        self.assertEqual(ingestion_settings['batch_size'], 10)
        self.assertTrue(ingestion_settings['enable_validation'])
        self.assertTrue(ingestion_settings['enable_archive_expansion'])
        self.assertIn('sha1', ingestion_settings['hash_algorithms'])
        self.assertIn('crc32', ingestion_settings['hash_algorithms'])
        self.assertIn('md5', ingestion_settings['hash_algorithms'])
        self.assertIn('sha256', ingestion_settings['hash_algorithms'])
    
    def test_config_manager_persistence(self):
        """Test that configuration changes persist."""
        config_manager = ConfigManager(self.config_path)
        
        # Modify a setting
        config_manager.set('ingestion_settings.batch_size', 50)
        config_manager.save()
        
        # Create new config manager and verify change persisted
        config_manager2 = ConfigManager(self.config_path)
        self.assertEqual(config_manager2.get('ingestion_settings.batch_size'), 50)
    
    def test_library_ingestion_importer_initialization(self):
        """Test that LibraryIngestionImporter initializes correctly."""
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        importer = LibraryIngestionImporter(self.db_path, config)
        
        self.assertEqual(importer.batch_size, 10)
        self.assertTrue(importer.enable_validation)
        self.assertTrue(importer.enable_archive_expansion)
        self.assertIn('sha1', importer.hash_algorithms)
        self.assertEqual(importer.max_file_size_mb, 1024)
    
    def test_file_discovery(self):
        """Test file discovery functionality."""
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        importer = LibraryIngestionImporter(self.db_path, config)
        importer.library_roots = [self.rom_dir]
        
        discovered_files = importer._discover_files(Path(self.rom_dir))
        
        # Should find the 3 ROM files but not the excluded .tmp file
        self.assertEqual(len(discovered_files), 3)
        
        # Check that all discovered files are in our test files list
        discovered_paths = [str(f) for f in discovered_files]
        for test_file in self.test_files:
            self.assertIn(test_file, discovered_paths)
    
    def test_file_classification(self):
        """Test file classification based on extensions."""
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        importer = LibraryIngestionImporter(self.db_path, config)
        
        # Test ROM file classification
        rom_file = Path(self.test_files[0])  # .nes file
        self.assertTrue(importer._is_supported_file(rom_file))
        
        # Test excluded file
        excluded_file = Path(os.path.join(self.rom_dir, 'temp_file.tmp'))
        self.assertTrue(importer._should_exclude_file(excluded_file))
    
    def test_hash_calculation(self):
        """Test hash calculation functionality."""
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        importer = LibraryIngestionImporter(self.db_path, config)
        
        # Test hash calculation on a small file
        test_file = Path(self.test_files[0])
        hashes = importer._calculate_file_hashes(test_file)
        
        # Should have all configured hash algorithms
        self.assertIn('sha1', hashes)
        self.assertIn('crc32', hashes)
        self.assertIn('md5', hashes)
        self.assertIn('sha256', hashes)
        
        # All hashes should be non-empty strings
        for algo, hash_value in hashes.items():
            self.assertIsInstance(hash_value, str)
            self.assertGreater(len(hash_value), 0)
    
    def test_platform_detection(self):
        """Test platform detection from file paths."""
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        importer = LibraryIngestionImporter(self.db_path, config)
        
        # Test NES platform detection
        nes_file = Path(self.test_files[0])  # .nes file
        platform_id = importer._detect_platform(nes_file)
        self.assertIsNotNone(platform_id)
        
        # Verify platform was created in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM platform WHERE platform_id = ?", (platform_id,))
        platform_name = cursor.fetchone()[0]
        conn.close()
        
        self.assertEqual(platform_name, 'Nintendo Entertainment System')
    
    def test_cli_argument_parsing(self):
        """Test CLI argument parsing."""
        importer = LibraryIngestionImporter(self.db_path)
        parser = importer.create_argument_parser()
        
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
    
    def test_database_integration(self):
        """Test database integration for ROM file creation."""
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        importer = LibraryIngestionImporter(self.db_path, config)
        
        # Test ROM file record creation
        test_file = Path(self.test_files[0])
        hashes = importer._calculate_file_hashes(test_file)
        
        # Create import log entry first
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO import_log (source_id, file_name, file_hash, status)
            VALUES (4, 'test_import', 'test_hash', 'running')
        """)
        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Create ROM file record
        rom_id = importer._create_rom_file_record(test_file, hashes, log_id)
        
        self.assertIsNotNone(rom_id)
        
        # Verify record was created in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM rom_file WHERE rom_id = ?", (rom_id,))
        rom_record = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(rom_record)
        self.assertEqual(rom_record[1], test_file.name)  # file_name
        self.assertEqual(rom_record[2], str(test_file))  # file_path
        self.assertIsNotNone(rom_record[5])  # sha1 hash
    
    def test_import_session_summary(self):
        """Test that import session produces correct summary."""
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        importer = LibraryIngestionImporter(self.db_path, config)
        
        # Simulate some processing
        importer.stats['files_discovered'] = 10
        importer.stats['files_processed'] = 8
        importer.stats['files_hashed'] = 8
        importer.stats['files_matched'] = 3
        importer.stats['files_pending_review'] = 5
        importer.stats['archives_expanded'] = 2
        importer.stats['errors'] = 1
        
        summary = importer._generate_summary()
        
        self.assertIn('Files discovered: 10', summary)
        self.assertIn('processed: 8', summary)
        self.assertIn('hashed: 8', summary)
        self.assertIn('matched: 3', summary)
        self.assertIn('pending review: 5', summary)
        self.assertIn('archives expanded: 2', summary)
        self.assertIn('errors: 1', summary)


class TestEnhancedImporterGUI(unittest.TestCase):
    """Test cases for enhanced importer GUI integration."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, 'test.db')
        self.config_path = os.path.join(self.test_dir, 'config.json')
        
        # Create minimal test database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE metadata_source (
                source_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                importer_script TEXT,
                schema_file_path TEXT
            )
        """)
        
        cursor.execute("""
            INSERT INTO metadata_source VALUES
            (1, 'No-Intro', 'scripts/seeders/no_intro.py', NULL),
            (2, 'MobyGames', 'scripts/seeders/mobygames.py', 'schema.json'),
            (4, 'file_ingestion', 'scripts/seeders/library_ingestion.py', NULL)
        """)
        
        conn.commit()
        conn.close()
        
        # Create test configuration
        config = {
            "database_path": self.db_path,
            "importer_scripts_directory": "./scripts/seeders/",
            "log_directory": os.path.join(self.test_dir, "logs"),
            "log_level": "DEBUG",
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
        
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=4)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
    
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


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)