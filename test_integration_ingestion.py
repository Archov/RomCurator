"""
Integration tests for Library Ingestion functionality

Tests cover:
- Real CLI invocation of library_ingestion.py
- Cancellation and resume flows
- End-to-end ingestion workflows
- Error handling and recovery
"""

import unittest
import tempfile
import shutil
import json
import sqlite3
import time
import threading
import subprocess
import signal
import os
import sys
from pathlib import Path
from unittest.mock import patch, Mock

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))


class TestCLIIntegration(unittest.TestCase):
    """Integration tests for CLI invocation and cancellation flows."""
    
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
        
        cursor.execute("""
            CREATE TABLE library_root (
                root_id INTEGER PRIMARY KEY,
                absolute_path TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
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
                "hash_algorithms": ["sha1", "crc32", "md5"],
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
    
    def test_cli_invocation_success(self):
        """Test successful CLI invocation of library_ingestion.py."""
        # Run the CLI command
        result = subprocess.run([
            sys.executable,
            'scripts/seeders/library_ingestion.py',
            '--source_id', '4',
            '--db_path', self.db_path,
            '--files', self.rom_dir,
            '--batch_size', '10'
        ], capture_output=True, text=True, timeout=30)
        
        # Verify successful execution
        self.assertEqual(result.returncode, 0, f"CLI failed with stderr: {result.stderr}")
        
        # Verify output contains expected information
        self.assertIn("Processing Library File Ingestion directory", result.stdout)
        self.assertIn("Processed batch", result.stdout)
        self.assertIn("Files discovered", result.stdout)
        
        # Verify database was updated
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check that import log was created
        cursor.execute("SELECT COUNT(*) FROM import_log WHERE source_id = 4")
        log_count = cursor.fetchone()[0]
        self.assertGreater(log_count, 0, "No import log entries were created")
        
        # Check that ROM files were created
        cursor.execute("SELECT COUNT(*) FROM rom_file")
        rom_count = cursor.fetchone()[0]
        self.assertGreater(rom_count, 0, "No ROM files were created")
        
        conn.close()
    
    def test_cli_invocation_with_invalid_source_id(self):
        """Test CLI invocation with invalid source ID."""
        result = subprocess.run([
            sys.executable,
            'scripts/seeders/library_ingestion.py',
            '--source_id', '999',  # Invalid source ID
            '--db_path', self.db_path,
            '--files', self.rom_dir
        ], capture_output=True, text=True, timeout=30)
        
        # Should fail with foreign key constraint error
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FOREIGN KEY constraint failed", result.stderr)
    
    def test_cli_invocation_with_nonexistent_directory(self):
        """Test CLI invocation with nonexistent directory."""
        result = subprocess.run([
            sys.executable,
            'scripts/seeders/library_ingestion.py',
            '--source_id', '4',
            '--db_path', self.db_path,
            '--files', '/nonexistent/directory'
        ], capture_output=True, text=True, timeout=30)
        
        # Should complete but with warnings
        self.assertEqual(result.returncode, 0)
        self.assertIn("Library root not found", result.stdout)
    
    def test_cli_invocation_with_custom_parameters(self):
        """Test CLI invocation with custom parameters."""
        result = subprocess.run([
            sys.executable,
            'scripts/seeders/library_ingestion.py',
            '--source_id', '4',
            '--db_path', self.db_path,
            '--files', self.rom_dir,
            '--batch_size', '5',
            '--hash_algorithms', 'sha1', 'md5',
            '--max_file_size_mb', '512'
        ], capture_output=True, text=True, timeout=30)
        
        # Should succeed
        self.assertEqual(result.returncode, 0)
        self.assertIn("Processing Library File Ingestion directory", result.stdout)
    
    def test_cli_help_output(self):
        """Test CLI help output."""
        result = subprocess.run([
            sys.executable,
            'scripts/seeders/library_ingestion.py',
            '--help'
        ], capture_output=True, text=True, timeout=10)
        
        # Should succeed and show help
        self.assertEqual(result.returncode, 0)
        self.assertIn("Library File Ingestion Importer", result.stdout)
        self.assertIn("--source_id", result.stdout)
        self.assertIn("--db_path", result.stdout)
        self.assertIn("--files", result.stdout)
    
    def test_cli_missing_required_arguments(self):
        """Test CLI with missing required arguments."""
        result = subprocess.run([
            sys.executable,
            'scripts/seeders/library_ingestion.py'
        ], capture_output=True, text=True, timeout=10)
        
        # Should fail with argument error
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required", result.stderr.lower())


class TestCancellationFlows(unittest.TestCase):
    """Test cancellation and resume flows."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, 'test.db')
        
        # Create test database
        self._create_test_database()
        
        # Create test library with many files
        self._create_large_test_library()
    
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
        
        cursor.execute("""
            CREATE TABLE library_root (
                root_id INTEGER PRIMARY KEY,
                absolute_path TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        
        # Insert test metadata source
        cursor.execute("""
            INSERT INTO metadata_source (source_id, name, importer_script)
            VALUES (4, 'file_ingestion', 'scripts/seeders/library_ingestion.py')
        """)
        
        conn.commit()
        conn.close()
    
    def _create_large_test_library(self):
        """Create a test library with many files for testing cancellation."""
        self.rom_dir = os.path.join(self.test_dir, 'test_library')
        os.makedirs(self.rom_dir, exist_ok=True)
        
        # Create many test files
        for i in range(20):
            file_path = os.path.join(self.rom_dir, f'test_game_{i:03d}.nes')
            with open(file_path, 'wb') as f:
                f.write(b'NES\x1a' + b'\x00' * (1000 + i * 100))  # Varying sizes
    
    def test_process_cancellation(self):
        """Test that a running process can be cancelled."""
        # Start the process
        process = subprocess.Popen([
            sys.executable,
            'scripts/seeders/library_ingestion.py',
            '--source_id', '4',
            '--db_path', self.db_path,
            '--files', self.rom_dir,
            '--batch_size', '5'  # Small batch size to ensure it takes time
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Let it run for a moment
        time.sleep(1)
        
        # Check if it's still running
        if process.poll() is None:
            # Process is still running, terminate it
            process.terminate()
            
            # Wait for it to terminate
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't terminate
                process.kill()
                process.wait()
            
            # Verify it was terminated
            self.assertIsNotNone(process.returncode)
            self.assertNotEqual(process.returncode, 0)
        else:
            # Process completed quickly, which is also fine
            self.assertIsNotNone(process.returncode)
    
    def test_resume_after_cancellation(self):
        """Test that ingestion can be resumed after cancellation."""
        # First run - should complete successfully
        result1 = subprocess.run([
            sys.executable,
            'scripts/seeders/library_ingestion.py',
            '--source_id', '4',
            '--db_path', self.db_path,
            '--files', self.rom_dir,
            '--batch_size', '10'
        ], capture_output=True, text=True, timeout=30)
        
        # Should succeed
        self.assertEqual(result1.returncode, 0)
        
        # Count files processed in first run
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM rom_file")
        first_run_count = cursor.fetchone()[0]
        conn.close()
        
        # Second run - should handle duplicates gracefully
        result2 = subprocess.run([
            sys.executable,
            'scripts/seeders/library_ingestion.py',
            '--source_id', '4',
            '--db_path', self.db_path,
            '--files', self.rom_dir,
            '--batch_size', '10'
        ], capture_output=True, text=True, timeout=30)
        
        # Should succeed
        self.assertEqual(result2.returncode, 0)
        
        # Count files processed in second run
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM rom_file")
        second_run_count = cursor.fetchone()[0]
        conn.close()
        
        # Should have the same number of files (duplicates handled)
        self.assertEqual(first_run_count, second_run_count)
    
    def test_error_recovery(self):
        """Test that the system recovers from errors gracefully."""
        # Create a file that will cause an error (empty file)
        error_file = os.path.join(self.rom_dir, 'error_file.nes')
        with open(error_file, 'w') as f:
            f.write('')  # Empty file
        
        # Run ingestion
        result = subprocess.run([
            sys.executable,
            'scripts/seeders/library_ingestion.py',
            '--source_id', '4',
            '--db_path', self.db_path,
            '--files', self.rom_dir,
            '--batch_size', '10'
        ], capture_output=True, text=True, timeout=30)
        
        # Should complete (not crash) even with errors
        self.assertEqual(result.returncode, 0)
        
        # Should have processed some files successfully
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM rom_file")
        rom_count = cursor.fetchone()[0]
        conn.close()
        
        self.assertGreater(rom_count, 0, "No files were processed successfully")


class TestEndToEndWorkflow(unittest.TestCase):
    """Test complete end-to-end ingestion workflow."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, 'test.db')
        
        # Create test database
        self._create_test_database()
        
        # Create test library
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
        
        cursor.execute("""
            CREATE TABLE library_root (
                root_id INTEGER PRIMARY KEY,
                absolute_path TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
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
        """Create a test library structure with sample files."""
        # Create test ROM files
        self.rom_dir = os.path.join(self.test_dir, 'test_library')
        os.makedirs(self.rom_dir, exist_ok=True)
        
        # Create subdirectories for different platforms
        nes_dir = os.path.join(self.rom_dir, 'nes')
        snes_dir = os.path.join(self.rom_dir, 'snes')
        
        os.makedirs(nes_dir, exist_ok=True)
        os.makedirs(snes_dir, exist_ok=True)
        
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
    
    def test_complete_ingestion_workflow(self):
        """Test complete ingestion workflow from start to finish."""
        # Run the complete ingestion
        result = subprocess.run([
            sys.executable,
            'scripts/seeders/library_ingestion.py',
            '--source_id', '4',
            '--db_path', self.db_path,
            '--files', self.rom_dir,
            '--batch_size', '10'
        ], capture_output=True, text=True, timeout=30)
        
        # Verify successful execution
        self.assertEqual(result.returncode, 0, f"CLI failed with stderr: {result.stderr}")
        
        # Verify database state
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check import log
        cursor.execute("SELECT * FROM import_log WHERE source_id = 4")
        import_logs = cursor.fetchall()
        self.assertGreater(len(import_logs), 0, "No import log entries created")
        
        # Check ROM files
        cursor.execute("SELECT * FROM rom_file")
        rom_files = cursor.fetchall()
        self.assertGreater(len(rom_files), 0, "No ROM files created")
        
        # Check file discovery records
        cursor.execute("SELECT * FROM file_discovery")
        discovery_records = cursor.fetchall()
        self.assertGreater(len(discovery_records), 0, "No file discovery records created")
        
        # Verify data integrity
        for rom_file in rom_files:
            self.assertIsNotNone(rom_file[5])  # sha1 should not be None
            self.assertGreater(rom_file[3], 0)  # size_bytes should be > 0
        
        conn.close()
        
        # Verify output contains expected information
        self.assertIn("Files discovered", result.stdout)
        self.assertIn("processed", result.stdout)
        self.assertIn("hashed", result.stdout)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)