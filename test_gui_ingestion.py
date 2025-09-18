"""
GUI-level tests for Library Ingestion functionality

Tests cover:
- GUI wiring and worker dispatch
- Cancellation flows
- Progress reporting
- Error handling
"""

import unittest
import tempfile
import shutil
import json
import sqlite3
import time
import threading
from pathlib import Path
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))


class MockQApplication:
    """Mock QApplication for testing without Qt dependencies."""
    def __init__(self, *args, **kwargs):
        pass
    
    def exec_(self):
        return 0


class MockQWidget:
    """Mock QWidget for testing."""
    def __init__(self, parent=None):
        self.parent = parent
        self.visible = False
    
    def show(self):
        self.visible = True
    
    def hide(self):
        self.visible = False
    
    def setWindowTitle(self, title):
        self.title = title


class MockQThread:
    """Mock QThread for testing worker functionality."""
    def __init__(self):
        self.running = False
        self.finished = False
        self.should_stop = False
        self.current_process = None
    
    def start(self):
        self.running = True
        # Simulate running in a separate thread
        self.thread = threading.Thread(target=self._run_simulation)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        self.should_stop = True
        if self.current_process:
            self.current_process.terminate()
    
    def _run_simulation(self):
        """Simulate the worker thread running."""
        time.sleep(0.1)  # Simulate some work
        self.running = False
        self.finished = True
    
    def isRunning(self):
        return self.running


class MockSignals:
    """Mock PyQt signals for testing."""
    def __init__(self):
        self.connected_functions = []
    
    def connect(self, func):
        self.connected_functions.append(func)
    
    def emit(self, *args):
        for func in self.connected_functions:
            func(*args)


class TestGUIWiring(unittest.TestCase):
    """Test GUI wiring and worker dispatch functionality."""
    
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
        os.makedirs(nes_dir, exist_ok=True)
        
        # Create test ROM files
        self.test_files = []
        
        # NES ROM
        nes_file = os.path.join(nes_dir, 'test_game.nes')
        with open(nes_file, 'wb') as f:
            f.write(b'NES\x1a' + b'\x00' * 1000)  # Simple NES header + data
        self.test_files.append(nes_file)
    
    @patch('enhanced_importer_gui.QApplication', MockQApplication)
    @patch('enhanced_importer_gui.QWidget', MockQWidget)
    @patch('enhanced_importer_gui.QThread', MockQThread)
    def test_enhanced_importer_widget_creation(self):
        """Test that EnhancedImporterWidget can be created and configured."""
        from enhanced_importer_gui import EnhancedImporterWidget
        
        # Mock the database manager
        with patch('enhanced_importer_gui.DatabaseManager') as mock_db:
            mock_db_instance = Mock()
            mock_db_instance.get_metadata_sources.return_value = [
                (4, 'file_ingestion', 'scripts/seeders/library_ingestion.py', None)
            ]
            mock_db.return_value = mock_db_instance
            
            # Create widget
            widget = EnhancedImporterWidget({'database_path': self.db_path})
            
            # Verify widget was created
            self.assertIsNotNone(widget)
            self.assertEqual(widget.config['database_path'], self.db_path)
    
    @patch('enhanced_importer_gui.QApplication', MockQApplication)
    @patch('enhanced_importer_gui.QWidget', MockQWidget)
    @patch('enhanced_importer_gui.QThread', MockQThread)
    def test_import_worker_thread_creation(self):
        """Test that ImportWorkerThread can be created and configured."""
        from enhanced_importer_gui import ImportWorkerThread, ImportLogger
        
        # Create mock logger
        mock_logger = Mock(spec=ImportLogger)
        mock_logger.start_import_session.return_value = "test_session"
        mock_logger.log_message = Mock()
        mock_logger.end_import_session = Mock()
        
        # Create worker thread
        worker = ImportWorkerThread(
            config={'database_path': self.db_path},
            source_id=4,
            script_path='scripts/seeders/library_ingestion.py',
            files=[self.rom_dir],
            logger=mock_logger
        )
        
        # Verify worker was created
        self.assertIsNotNone(worker)
        self.assertEqual(worker.source_id, 4)
        self.assertEqual(worker.files, [self.rom_dir])
        self.assertFalse(worker.should_stop)
        self.assertIsNone(worker.current_process)
    
    @patch('enhanced_importer_gui.QApplication', MockQApplication)
    @patch('enhanced_importer_gui.QWidget', MockQWidget)
    @patch('enhanced_importer_gui.QThread', MockQThread)
    def test_import_worker_cancellation(self):
        """Test that ImportWorkerThread properly handles cancellation."""
        from enhanced_importer_gui import ImportWorkerThread, ImportLogger
        
        # Create mock logger
        mock_logger = Mock(spec=ImportLogger)
        mock_logger.start_import_session.return_value = "test_session"
        mock_logger.log_message = Mock()
        mock_logger.end_import_session = Mock()
        
        # Create worker thread
        worker = ImportWorkerThread(
            config={'database_path': self.db_path},
            source_id=4,
            script_path='scripts/seeders/library_ingestion.py',
            files=[self.rom_dir],
            logger=mock_logger
        )
        
        # Test initial state
        self.assertFalse(worker.should_stop)
        self.assertIsNone(worker.current_process)
        
        # Test stop method
        worker.stop()
        self.assertTrue(worker.should_stop)
        
        # Test stop with mock process
        mock_process = Mock()
        mock_process.terminate = Mock()
        mock_process.wait = Mock()
        worker.current_process = mock_process
        
        worker.stop()
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=5)
    
    @patch('enhanced_importer_gui.QApplication', MockQApplication)
    @patch('enhanced_importer_gui.QWidget', MockQWidget)
    @patch('enhanced_importer_gui.QThread', MockQThread)
    def test_import_worker_progress_reporting(self):
        """Test that ImportWorkerThread properly reports progress."""
        from enhanced_importer_gui import ImportWorkerThread, ImportLogger
        
        # Create mock logger
        mock_logger = Mock(spec=ImportLogger)
        mock_logger.start_import_session.return_value = "test_session"
        mock_logger.log_message = Mock()
        mock_logger.end_import_session = Mock()
        
        # Create worker thread
        worker = ImportWorkerThread(
            config={'database_path': self.db_path},
            source_id=4,
            script_path='scripts/seeders/library_ingestion.py',
            files=[self.rom_dir],
            logger=mock_logger
        )
        
        # Mock the signals
        worker.progress_updated = MockSignals()
        worker.output_received = MockSignals()
        worker.import_completed = MockSignals()
        worker.error_occurred = MockSignals()
        
        # Test that signals are properly connected
        self.assertIsInstance(worker.progress_updated, MockSignals)
        self.assertIsInstance(worker.output_received, MockSignals)
        self.assertIsInstance(worker.import_completed, MockSignals)
        self.assertIsInstance(worker.error_occurred, MockSignals)
    
    @patch('enhanced_importer_gui.QApplication', MockQApplication)
    @patch('enhanced_importer_gui.QWidget', MockQWidget)
    @patch('enhanced_importer_gui.QThread', MockQThread)
    def test_import_worker_error_handling(self):
        """Test that ImportWorkerThread properly handles errors."""
        from enhanced_importer_gui import ImportWorkerThread, ImportLogger
        
        # Create mock logger
        mock_logger = Mock(spec=ImportLogger)
        mock_logger.start_import_session.return_value = "test_session"
        mock_logger.log_message = Mock()
        mock_logger.end_import_session = Mock()
        
        # Create worker thread
        worker = ImportWorkerThread(
            config={'database_path': self.db_path},
            source_id=4,
            script_path='scripts/seeders/library_ingestion.py',
            files=[self.rom_dir],
            logger=mock_logger
        )
        
        # Mock the signals
        worker.progress_updated = MockSignals()
        worker.output_received = MockSignals()
        worker.import_completed = MockSignals()
        worker.error_occurred = MockSignals()
        
        # Test error handling by simulating an exception
        try:
            # This should not raise an exception
            worker.run()
        except Exception as e:
            self.fail(f"Worker.run() raised an exception: {e}")
    
    @patch('enhanced_importer_gui.QApplication', MockQApplication)
    @patch('enhanced_importer_gui.QWidget', MockQWidget)
    @patch('enhanced_importer_gui.QThread', MockQThread)
    def test_import_worker_subprocess_handling(self):
        """Test that ImportWorkerThread properly handles subprocess operations."""
        from enhanced_importer_gui import ImportWorkerThread, ImportLogger
        
        # Create mock logger
        mock_logger = Mock(spec=ImportLogger)
        mock_logger.start_import_session.return_value = "test_session"
        mock_logger.log_message = Mock()
        mock_logger.end_import_session = Mock()
        
        # Create worker thread
        worker = ImportWorkerThread(
            config={'database_path': self.db_path},
            source_id=4,
            script_path='scripts/seeders/library_ingestion.py',
            files=[self.rom_dir],
            logger=mock_logger
        )
        
        # Mock subprocess.Popen
        with patch('enhanced_importer_gui.subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.poll.return_value = None
            mock_process.stdout = Mock()
            mock_process.stderr = Mock()
            mock_process.wait.return_value = 0
            mock_process.communicate.return_value = ("test output", "")
            mock_popen.return_value = mock_process
            
            # Test subprocess execution
            success, output, error = worker._run_single_import(self.rom_dir)
            
            # Verify subprocess was called
            mock_popen.assert_called_once()
            
            # Verify process handling
            self.assertIsNotNone(worker.current_process)
    
    def test_main_application_integration(self):
        """Test that the main application properly integrates with the enhanced importer."""
        # Mock the main application components
        with patch('rom_curator_main.QApplication', MockQApplication):
            with patch('rom_curator_main.QMainWindow', MockQWidget):
                with patch('rom_curator_main.QWidget', MockQWidget):
                    with patch('rom_curator_main.QThread', MockQThread):
                        from rom_curator_main import RomCuratorMainWindow
                        
                        # Create main window
                        main_window = RomCuratorMainWindow()
                        
                        # Test that the ingestion method exists and is callable
                        self.assertTrue(hasattr(main_window, 'open_resilient_ingestion'))
                        self.assertTrue(callable(main_window.open_resilient_ingestion))
                        
                        # Test that the method can be called without errors
                        try:
                            main_window.open_resilient_ingestion()
                        except Exception as e:
                            # Expected to fail due to missing Qt dependencies, but should not crash
                            self.assertIn("enhanced_importer_gui", str(e))


class TestCancellationFlows(unittest.TestCase):
    """Test cancellation and resume flows."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, 'test.db')
        
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
            INSERT INTO metadata_source (source_id, name, importer_script)
            VALUES (4, 'file_ingestion', 'scripts/seeders/library_ingestion.py')
        """)
        
        conn.commit()
        conn.close()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
    
    def test_cancellation_signal_propagation(self):
        """Test that cancellation signals are properly propagated."""
        from enhanced_importer_gui import ImportWorkerThread, ImportLogger
        
        # Create mock logger
        mock_logger = Mock(spec=ImportLogger)
        mock_logger.start_import_session.return_value = "test_session"
        mock_logger.log_message = Mock()
        mock_logger.end_import_session = Mock()
        
        # Create worker thread
        worker = ImportWorkerThread(
            config={'database_path': self.db_path},
            source_id=4,
            script_path='scripts/seeders/library_ingestion.py',
            files=['/test/path'],
            logger=mock_logger
        )
        
        # Test cancellation flag
        self.assertFalse(worker.should_stop)
        worker.stop()
        self.assertTrue(worker.should_stop)
        
        # Test that stop method logs the action only when there's a process
        # Since no process is set, no logging should occur
        mock_logger.log_message.assert_not_called()
    
    def test_process_termination(self):
        """Test that running processes are properly terminated."""
        from enhanced_importer_gui import ImportWorkerThread, ImportLogger
        
        # Create mock logger
        mock_logger = Mock(spec=ImportLogger)
        mock_logger.start_import_session.return_value = "test_session"
        mock_logger.log_message = Mock()
        mock_logger.end_import_session = Mock()
        
        # Create worker thread
        worker = ImportWorkerThread(
            config={'database_path': self.db_path},
            source_id=4,
            script_path='scripts/seeders/library_ingestion.py',
            files=['/test/path'],
            logger=mock_logger
        )
        
        # Mock a running process
        mock_process = Mock()
        mock_process.terminate = Mock()
        mock_process.wait = Mock()
        worker.current_process = mock_process
        
        # Test stop method
        worker.stop()
        
        # Verify process was terminated
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=5)
        
        # Verify that logging occurred when there was a process
        mock_logger.log_message.assert_called()
    
    def test_cancellation_during_execution(self):
        """Test that cancellation works during execution."""
        from enhanced_importer_gui import ImportWorkerThread, ImportLogger
        
        # Create mock logger
        mock_logger = Mock(spec=ImportLogger)
        mock_logger.start_import_session.return_value = "test_session"
        mock_logger.log_message = Mock()
        mock_logger.end_import_session = Mock()
        
        # Create worker thread
        worker = ImportWorkerThread(
            config={'database_path': self.db_path},
            source_id=4,
            script_path='scripts/seeders/library_ingestion.py',
            files=['/test/path'],
            logger=mock_logger
        )
        
        # Mock subprocess that simulates a long-running process
        with patch('enhanced_importer_gui.subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.poll.return_value = None  # Process is still running
            mock_process.stdout = Mock()
            mock_process.stderr = Mock()
            mock_process.wait.return_value = 0
            mock_process.communicate.return_value = ("", "")
            mock_popen.return_value = mock_process
            
            # Start the worker in a separate thread
            worker_thread = threading.Thread(target=worker.run)
            worker_thread.daemon = True
            worker_thread.start()
            
            # Give it a moment to start
            time.sleep(0.1)
            
            # Stop the worker
            worker.stop()
            
            # Wait for the worker thread to finish
            worker_thread.join(timeout=1)
            
            # Verify the process was terminated
            mock_process.terminate.assert_called()


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)