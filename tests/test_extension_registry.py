#!/usr/bin/env python3
"""
Extension Registry Test Suite

This test suite provides comprehensive coverage for the Extension Registry functionality
as specified in Work Item 4, including:
- CRUD operations for all registry entities
- Data persistence and integrity
- Unknown extension handling and approval workflow
- Import/export functionality
- Platform detection integration

This replaces the deleted test_extension_registry.py and provides the required
automated UI/service-layer test coverage.
"""

import unittest
import tempfile
import os
import json
import sqlite3
from pathlib import Path
import sys

# Add the workspace to Python path
sys.path.append('/workspace')

from extension_registry_manager import ExtensionRegistryManager


class TestExtensionRegistryCRUD(unittest.TestCase):
    """Test CRUD operations for extension registry entities."""
    
    def setUp(self):
        """Set up test database and manager."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        # Create database with required tables
        self._create_test_database()
        
        self.manager = ExtensionRegistryManager(self.db_path)
    
    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def _create_test_database(self):
        """Create test database with required tables."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Create file_type_category table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS file_type_category (
                category_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                sort_order INTEGER DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT 1
            )
        """)
        
        # Create file_extension table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS file_extension (
                extension_id INTEGER PRIMARY KEY,
                extension TEXT NOT NULL UNIQUE,
                category_id INTEGER NOT NULL REFERENCES file_type_category(category_id),
                description TEXT,
                mime_type TEXT,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                is_archive BOOLEAN NOT NULL DEFAULT 0,
                is_rom BOOLEAN NOT NULL DEFAULT 0,
                is_save BOOLEAN NOT NULL DEFAULT 0,
                is_patch BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create platform table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS platform (
                platform_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            )
        """)
        
        # Create platform_extension table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS platform_extension (
                platform_extension_id INTEGER PRIMARY KEY,
                platform_id INTEGER NOT NULL REFERENCES platform(platform_id),
                extension_id INTEGER NOT NULL REFERENCES file_extension(extension_id),
                is_primary BOOLEAN NOT NULL DEFAULT 0,
                confidence REAL NOT NULL DEFAULT 1.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(platform_id, extension_id)
            )
        """)
        
        # Create unknown_extension table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS unknown_extension (
                unknown_extension_id INTEGER PRIMARY KEY,
                extension TEXT NOT NULL UNIQUE,
                file_count INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'pending',
                suggested_category_id INTEGER REFERENCES file_type_category(category_id),
                suggested_platform_id INTEGER REFERENCES platform(platform_id),
                notes TEXT,
                first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _create_test_platform(self, name):
        """Helper to create a test platform."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO platform (name) VALUES (?)", (name,))
        platform_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return platform_id
    
    def test_category_crud_operations(self):
        """Test complete category CRUD operations."""
        # Create
        cat_id = self.manager.create_category("ROM Files", "Game ROM files", 1, True)
        self.assertIsInstance(cat_id, int)
        self.assertGreater(cat_id, 0)
        
        # Read
        category = self.manager.get_category(cat_id)
        self.assertIsNotNone(category)
        self.assertEqual(category['name'], "ROM Files")
        self.assertEqual(category['description'], "Game ROM files")
        self.assertEqual(category['sort_order'], 1)
        self.assertTrue(category['is_active'])
        
        # Update
        success = self.manager.update_category(cat_id, name="Updated ROM Files", description="Updated description")
        self.assertTrue(success)
        
        updated_category = self.manager.get_category(cat_id)
        self.assertEqual(updated_category['name'], "Updated ROM Files")
        self.assertEqual(updated_category['description'], "Updated description")
        
        # Delete (soft delete)
        success = self.manager.delete_category(cat_id)
        self.assertTrue(success)
        
        deleted_category = self.manager.get_category(cat_id)
        self.assertFalse(deleted_category['is_active'])
    
    def test_extension_crud_operations(self):
        """Test complete extension CRUD operations."""
        # Create category first
        cat_id = self.manager.create_category("ROM Files", "Game ROM files", 1, True)
        
        # Create extension
        ext_id = self.manager.create_extension(
            ".nes", cat_id, "Nintendo Entertainment System ROM",
            "application/octet-stream", True, False, True, False, False
        )
        self.assertIsInstance(ext_id, int)
        self.assertGreater(ext_id, 0)
        
        # Read
        extension = self.manager.get_extension(ext_id)
        self.assertIsNotNone(extension)
        self.assertEqual(extension['extension'], ".nes")
        self.assertEqual(extension['category_id'], cat_id)
        self.assertTrue(extension['is_rom'])
        self.assertFalse(extension['is_archive'])
        
        # Update
        success = self.manager.update_extension(ext_id, description="Updated NES ROM")
        self.assertTrue(success)
        
        updated_extension = self.manager.get_extension(ext_id)
        self.assertEqual(updated_extension['description'], "Updated NES ROM")
        
        # Delete (soft delete)
        success = self.manager.delete_extension(ext_id)
        self.assertTrue(success)
        
        deleted_extension = self.manager.get_extension(ext_id)
        self.assertFalse(deleted_extension['is_active'])
    
    def test_platform_extension_crud_operations(self):
        """Test complete platform-extension mapping CRUD operations."""
        # Create category and extension
        cat_id = self.manager.create_category("ROM Files", "Game ROM files", 1, True)
        ext_id = self.manager.create_extension(".nes", cat_id, "NES ROM", None, True, False, True, False, False)
        
        # Create platform
        platform_id = self._create_test_platform("Nintendo Entertainment System")
        
        # Create mapping
        mapping_id = self.manager.create_platform_extension(platform_id, ext_id, True, 1.0)
        self.assertIsInstance(mapping_id, int)
        self.assertGreater(mapping_id, 0)
        
        # Read mappings
        mappings = self.manager.get_platform_extensions(platform_id=platform_id)
        self.assertEqual(len(mappings), 1)
        self.assertEqual(mappings[0]['platform_id'], platform_id)
        self.assertEqual(mappings[0]['extension_id'], ext_id)
        self.assertTrue(mappings[0]['is_primary'])
        self.assertEqual(mappings[0]['confidence'], 1.0)
        
        # Update mapping
        success = self.manager.update_platform_extension(mapping_id, is_primary=False, confidence=0.8)
        self.assertTrue(success)
        
        updated_mappings = self.manager.get_platform_extensions(platform_id=platform_id)
        self.assertFalse(updated_mappings[0]['is_primary'])
        self.assertEqual(updated_mappings[0]['confidence'], 0.8)
        
        # Delete mapping
        success = self.manager.delete_platform_extension(mapping_id)
        self.assertTrue(success)
        
        remaining_mappings = self.manager.get_platform_extensions(platform_id=platform_id)
        self.assertEqual(len(remaining_mappings), 0)
    
    def test_unknown_extension_crud_operations(self):
        """Test complete unknown extension CRUD operations."""
        # Record unknown extension
        unknown_id = self.manager.record_unknown_extension(".unknown", 5)
        self.assertIsInstance(unknown_id, int)
        self.assertGreater(unknown_id, 0)
        
        # Read unknown extensions
        unknown_exts = self.manager.get_unknown_extensions()
        self.assertEqual(len(unknown_exts), 1)
        self.assertEqual(unknown_exts[0]['extension'], ".unknown")
        self.assertEqual(unknown_exts[0]['file_count'], 5)
        self.assertEqual(unknown_exts[0]['status'], 'pending')
        
        # Update unknown extension
        success = self.manager.update_unknown_extension(unknown_id, status='approved', notes='Test approval')
        self.assertTrue(success)
        
        updated_unknown = self.manager.get_unknown_extensions()[0]
        self.assertEqual(updated_unknown['status'], 'approved')
        self.assertEqual(updated_unknown['notes'], 'Test approval')
        
        # Test status filtering
        pending = self.manager.get_unknown_extensions(status='pending')
        self.assertEqual(len(pending), 0)
        
        approved = self.manager.get_unknown_extensions(status='approved')
        self.assertEqual(len(approved), 1)


class TestExtensionRegistryPersistence(unittest.TestCase):
    """Test data persistence and integrity."""
    
    def setUp(self):
        """Set up test database and manager."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        # Create database with required tables
        self._create_test_database()
        
        self.manager = ExtensionRegistryManager(self.db_path)
    
    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def _create_test_database(self):
        """Create test database with required tables."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Create required tables (same as above)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS file_type_category (
                category_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                sort_order INTEGER DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT 1
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS file_extension (
                extension_id INTEGER PRIMARY KEY,
                extension TEXT NOT NULL UNIQUE,
                category_id INTEGER NOT NULL REFERENCES file_type_category(category_id),
                description TEXT,
                mime_type TEXT,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                is_archive BOOLEAN NOT NULL DEFAULT 0,
                is_rom BOOLEAN NOT NULL DEFAULT 0,
                is_save BOOLEAN NOT NULL DEFAULT 0,
                is_patch BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS platform (
                platform_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS platform_extension (
                platform_extension_id INTEGER PRIMARY KEY,
                platform_id INTEGER NOT NULL REFERENCES platform(platform_id),
                extension_id INTEGER NOT NULL REFERENCES file_extension(extension_id),
                is_primary BOOLEAN NOT NULL DEFAULT 0,
                confidence REAL NOT NULL DEFAULT 1.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(platform_id, extension_id)
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS unknown_extension (
                unknown_extension_id INTEGER PRIMARY KEY,
                extension TEXT NOT NULL UNIQUE,
                file_count INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'pending',
                suggested_category_id INTEGER REFERENCES file_type_category(category_id),
                suggested_platform_id INTEGER REFERENCES platform(platform_id),
                notes TEXT,
                first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def test_data_persistence_across_sessions(self):
        """Test that data persists across manager instances."""
        # Create some data
        cat_id = self.manager.create_category("Test Category", "Test", 1, True)
        ext_id = self.manager.create_extension(".test", cat_id, "Test Extension", None, True, False, True, False, False)
        
        # Create new manager instance
        new_manager = ExtensionRegistryManager(self.db_path)
        
        # Verify data persists
        categories = new_manager.get_categories()
        self.assertEqual(len(categories), 1)
        self.assertEqual(categories[0]['name'], "Test Category")
        
        extensions = new_manager.get_extensions()
        self.assertEqual(len(extensions), 1)
        self.assertEqual(extensions[0]['extension'], ".test")
    
    def test_foreign_key_constraint_enforcement(self):
        """Test foreign key constraint enforcement."""
        # Try to create extension with non-existent category
        with self.assertRaises(sqlite3.IntegrityError):
            self.manager.create_extension(".test", 999, "Test", None, True, False, True, False, False)
        
        # Try to create platform mapping with non-existent platform
        cat_id = self.manager.create_category("Test", "Test", 1, True)
        ext_id = self.manager.create_extension(".test", cat_id, "Test", None, True, False, True, False, False)
        
        with self.assertRaises(sqlite3.IntegrityError):
            self.manager.create_platform_extension(999, ext_id, True, 1.0)
    
    def test_unique_constraint_enforcement(self):
        """Test unique constraint enforcement."""
        # Create category
        self.manager.create_category("Test Category", "Test", 1, True)
        
        # Try to create duplicate category
        with self.assertRaises(sqlite3.IntegrityError):
            self.manager.create_category("Test Category", "Test", 1, True)
        
        # Create extension
        cat_id = self.manager.create_category("Test Category 2", "Test", 1, True)
        self.manager.create_extension(".test", cat_id, "Test", None, True, False, True, False, False)
        
        # Try to create duplicate extension
        with self.assertRaises(sqlite3.IntegrityError):
            self.manager.create_extension(".test", cat_id, "Test", None, True, False, True, False, False)


class TestImportExport(unittest.TestCase):
    """Test import/export functionality."""
    
    def setUp(self):
        """Set up test database and manager."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        # Create database with required tables
        self._create_test_database()
        
        self.manager = ExtensionRegistryManager(self.db_path)
    
    def tearDown(self):
        """Clean up test database and files."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        if hasattr(self, 'export_file') and os.path.exists(self.export_file):
            os.unlink(self.export_file)
    
    def _create_test_database(self):
        """Create test database with required tables."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Create required tables (same as above)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS file_type_category (
                category_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                sort_order INTEGER DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT 1
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS file_extension (
                extension_id INTEGER PRIMARY KEY,
                extension TEXT NOT NULL UNIQUE,
                category_id INTEGER NOT NULL REFERENCES file_type_category(category_id),
                description TEXT,
                mime_type TEXT,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                is_archive BOOLEAN NOT NULL DEFAULT 0,
                is_rom BOOLEAN NOT NULL DEFAULT 0,
                is_save BOOLEAN NOT NULL DEFAULT 0,
                is_patch BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS platform (
                platform_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS platform_extension (
                platform_extension_id INTEGER PRIMARY KEY,
                platform_id INTEGER NOT NULL REFERENCES platform(platform_id),
                extension_id INTEGER NOT NULL REFERENCES file_extension(extension_id),
                is_primary BOOLEAN NOT NULL DEFAULT 0,
                confidence REAL NOT NULL DEFAULT 1.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(platform_id, extension_id)
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS unknown_extension (
                unknown_extension_id INTEGER PRIMARY KEY,
                extension TEXT NOT NULL UNIQUE,
                file_count INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'pending',
                suggested_category_id INTEGER REFERENCES file_type_category(category_id),
                suggested_platform_id INTEGER REFERENCES platform(platform_id),
                notes TEXT,
                first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _create_test_platform(self, name):
        """Helper to create a test platform."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO platform (name) VALUES (?)", (name,))
        platform_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return platform_id
    
    def test_export_json_functionality(self):
        """Test JSON export functionality."""
        # Create test data
        cat_id = self.manager.create_category("Test Category", "Test", 1, True)
        ext_id = self.manager.create_extension(".test", cat_id, "Test Extension", None, True, False, True, False, False)
        platform_id = self._create_test_platform("Test Platform")
        mapping_id = self.manager.create_platform_extension(platform_id, ext_id, True, 1.0)
        unknown_id = self.manager.record_unknown_extension(".unknown", 3)
        
        # Export to JSON
        self.export_file = "/tmp/test_export.json"
        success = self.manager.export_extensions(self.export_file, "json")
        self.assertTrue(success)
        self.assertTrue(os.path.exists(self.export_file))
        
        # Verify export content
        with open(self.export_file, 'r') as f:
            data = json.load(f)
        
        self.assertIn('metadata', data)
        self.assertIn('categories', data)
        self.assertIn('extensions', data)
        self.assertIn('mappings', data)
        self.assertIn('unknown_extensions', data)
        
        self.assertEqual(len(data['categories']), 1)
        self.assertEqual(len(data['extensions']), 1)
        self.assertEqual(len(data['mappings']), 1)
        self.assertEqual(len(data['unknown_extensions']), 1)
        
        # Verify specific data
        self.assertEqual(data['categories'][0]['name'], "Test Category")
        self.assertEqual(data['extensions'][0]['extension'], ".test")
        self.assertEqual(data['mappings'][0]['platform_id'], platform_id)
        self.assertEqual(data['unknown_extensions'][0]['extension'], ".unknown")
    
    def test_import_json_functionality(self):
        """Test JSON import functionality."""
        # Create export data
        self.export_file = "/tmp/test_export.json"
        export_data = {
            'metadata': {'export_date': '2025-01-01', 'version': '1.0', 'format': 'json'},
            'categories': [{'name': 'Imported Category', 'description': 'Imported', 'sort_order': 1, 'is_active': True}],
            'extensions': [{'extension': '.imported', 'category_id': 1, 'description': 'Imported Extension', 'is_active': True, 'is_rom': True, 'is_archive': False, 'is_save': False, 'is_patch': False}],
            'mappings': [],
            'unknown_extensions': []
        }
        
        with open(self.export_file, 'w') as f:
            json.dump(export_data, f)
        
        # Import data
        results = self.manager.import_extensions(self.export_file, "json", overwrite=False)
        self.assertTrue(results['success'])
        self.assertEqual(results['categories_imported'], 1)
        self.assertEqual(results['extensions_imported'], 1)
        
        # Verify imported data
        categories = self.manager.get_categories()
        self.assertEqual(len(categories), 1)
        self.assertEqual(categories[0]['name'], 'Imported Category')
        
        extensions = self.manager.get_extensions()
        self.assertEqual(len(extensions), 1)
        self.assertEqual(extensions[0]['extension'], '.imported')
    
    def test_import_with_overwrite_option(self):
        """Test import with overwrite option."""
        # Create initial data
        cat_id = self.manager.create_category("Original Category", "Original", 1, True)
        ext_id = self.manager.create_extension(".original", cat_id, "Original Extension", None, True, False, True, False, False)
        
        # Create import data with same names but different descriptions
        self.export_file = "/tmp/test_export.json"
        export_data = {
            'metadata': {'export_date': '2025-01-01', 'version': '1.0', 'format': 'json'},
            'categories': [{'name': 'Original Category', 'description': 'Updated Description', 'sort_order': 2, 'is_active': True}],
            'extensions': [{'extension': '.original', 'category_id': 1, 'description': 'Updated Extension', 'is_active': True, 'is_rom': True, 'is_archive': False, 'is_save': False, 'is_patch': False}],
            'mappings': [],
            'unknown_extensions': []
        }
        
        with open(self.export_file, 'w') as f:
            json.dump(export_data, f)
        
        # Import with overwrite
        results = self.manager.import_extensions(self.export_file, "json", overwrite=True)
        self.assertTrue(results['success'])
        
        # Verify data was updated
        categories = self.manager.get_categories()
        self.assertEqual(categories[0]['description'], 'Updated Description')
        self.assertEqual(categories[0]['sort_order'], 2)
        
        extensions = self.manager.get_extensions()
        self.assertEqual(extensions[0]['description'], 'Updated Extension')


class TestUnknownExtensionHandling(unittest.TestCase):
    """Test unknown extension handling and approval workflow."""
    
    def setUp(self):
        """Set up test database and manager."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        # Create database with required tables
        self._create_test_database()
        
        self.manager = ExtensionRegistryManager(self.db_path)
    
    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def _create_test_database(self):
        """Create test database with required tables."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Create required tables (same as above)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS file_type_category (
                category_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                sort_order INTEGER DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT 1
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS file_extension (
                extension_id INTEGER PRIMARY KEY,
                extension TEXT NOT NULL UNIQUE,
                category_id INTEGER NOT NULL REFERENCES file_type_category(category_id),
                description TEXT,
                mime_type TEXT,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                is_archive BOOLEAN NOT NULL DEFAULT 0,
                is_rom BOOLEAN NOT NULL DEFAULT 0,
                is_save BOOLEAN NOT NULL DEFAULT 0,
                is_patch BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS platform (
                platform_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS platform_extension (
                platform_extension_id INTEGER PRIMARY KEY,
                platform_id INTEGER NOT NULL REFERENCES platform(platform_id),
                extension_id INTEGER NOT NULL REFERENCES file_extension(extension_id),
                is_primary BOOLEAN NOT NULL DEFAULT 0,
                confidence REAL NOT NULL DEFAULT 1.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(platform_id, extension_id)
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS unknown_extension (
                unknown_extension_id INTEGER PRIMARY KEY,
                extension TEXT NOT NULL UNIQUE,
                file_count INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'pending',
                suggested_category_id INTEGER REFERENCES file_type_category(category_id),
                suggested_platform_id INTEGER REFERENCES platform(platform_id),
                notes TEXT,
                first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _create_test_platform(self, name):
        """Helper to create a test platform."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO platform (name) VALUES (?)", (name,))
        platform_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return platform_id
    
    def test_unknown_extension_recording(self):
        """Test recording of unknown extensions."""
        # Record unknown extension
        unknown_id = self.manager.record_unknown_extension(".unknown", 5)
        self.assertIsInstance(unknown_id, int)
        self.assertGreater(unknown_id, 0)
        
        # Read unknown extensions
        unknown_exts = self.manager.get_unknown_extensions()
        self.assertEqual(len(unknown_exts), 1)
        self.assertEqual(unknown_exts[0]['extension'], ".unknown")
        self.assertEqual(unknown_exts[0]['file_count'], 5)
        self.assertEqual(unknown_exts[0]['status'], 'pending')
        
        # Record same extension again (should update count)
        unknown_id2 = self.manager.record_unknown_extension(".unknown", 3)
        self.assertEqual(unknown_id, unknown_id2)  # Same ID
        
        updated_unknown = self.manager.get_unknown_extensions()[0]
        self.assertEqual(updated_unknown['file_count'], 8)  # 5 + 3
    
    def test_unknown_extension_approval_workflow(self):
        """Test complete unknown extension approval workflow."""
        # Record unknown extension
        unknown_id = self.manager.record_unknown_extension(".newrom", 10)
        
        # Create category and platform for approval
        cat_id = self.manager.create_category("New ROM Files", "New ROM format", 1, True)
        platform_id = self._create_test_platform("New Platform")
        
        # Approve unknown extension
        success = self.manager.approve_unknown_extension(unknown_id, cat_id, platform_id, "Auto-approved new format")
        self.assertTrue(success)
        
        # Check that extension was created
        extensions = self.manager.get_extensions()
        self.assertEqual(len(extensions), 1)
        self.assertEqual(extensions[0]['extension'], ".newrom")
        self.assertEqual(extensions[0]['category_id'], cat_id)
        self.assertTrue(extensions[0]['is_rom'])
        
        # Check that platform mapping was created
        mappings = self.manager.get_platform_extensions(platform_id=platform_id)
        self.assertEqual(len(mappings), 1)
        self.assertEqual(mappings[0]['extension'], ".newrom")
        self.assertTrue(mappings[0]['is_primary'])
        self.assertEqual(mappings[0]['confidence'], 1.0)
        
        # Check that unknown extension status was updated
        unknown_exts = self.manager.get_unknown_extensions()
        self.assertEqual(unknown_exts[0]['status'], 'approved')
        self.assertEqual(unknown_exts[0]['suggested_category_id'], cat_id)
        self.assertEqual(unknown_exts[0]['suggested_platform_id'], platform_id)
        self.assertEqual(unknown_exts[0]['notes'], "Auto-approved new format")
    
    def test_unknown_extension_rejection(self):
        """Test unknown extension rejection."""
        # Record unknown extension
        unknown_id = self.manager.record_unknown_extension(".junk", 1)
        
        # Reject unknown extension
        success = self.manager.reject_unknown_extension(unknown_id, "Not a valid ROM format")
        self.assertTrue(success)
        
        # Check status
        unknown_exts = self.manager.get_unknown_extensions()
        self.assertEqual(unknown_exts[0]['status'], 'rejected')
        self.assertEqual(unknown_exts[0]['notes'], "Not a valid ROM format")
        
        # Check that no extension was created
        extensions = self.manager.get_extensions()
        self.assertEqual(len(extensions), 0)
    
    def test_unknown_extension_ignoring(self):
        """Test unknown extension ignoring."""
        # Record unknown extension
        unknown_id = self.manager.record_unknown_extension(".temp", 1)
        
        # Ignore unknown extension
        success = self.manager.ignore_unknown_extension(unknown_id, "Temporary file")
        self.assertTrue(success)
        
        # Check status
        unknown_exts = self.manager.get_unknown_extensions()
        self.assertEqual(unknown_exts[0]['status'], 'ignored')
        self.assertEqual(unknown_exts[0]['notes'], "Temporary file")
        
        # Check that no extension was created
        extensions = self.manager.get_extensions()
        self.assertEqual(len(extensions), 0)
    
    def test_unknown_extension_status_filtering(self):
        """Test filtering unknown extensions by status."""
        # Create multiple unknown extensions with different statuses
        unknown1 = self.manager.record_unknown_extension(".pending", 1)
        unknown2 = self.manager.record_unknown_extension(".approved", 1)
        unknown3 = self.manager.record_unknown_extension(".rejected", 1)
        unknown4 = self.manager.record_unknown_extension(".ignored", 1)
        
        # Update statuses
        self.manager.update_unknown_extension(unknown2, status='approved')
        self.manager.update_unknown_extension(unknown3, status='rejected')
        self.manager.update_unknown_extension(unknown4, status='ignored')
        
        # Test filtering
        pending = self.manager.get_unknown_extensions(status='pending')
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]['extension'], '.pending')
        
        approved = self.manager.get_unknown_extensions(status='approved')
        self.assertEqual(len(approved), 1)
        self.assertEqual(approved[0]['extension'], '.approved')
        
        rejected = self.manager.get_unknown_extensions(status='rejected')
        self.assertEqual(len(rejected), 1)
        self.assertEqual(rejected[0]['extension'], '.rejected')
        
        ignored = self.manager.get_unknown_extensions(status='ignored')
        self.assertEqual(len(ignored), 1)
        self.assertEqual(ignored[0]['extension'], '.ignored')


class TestPlatformDetectionIntegration(unittest.TestCase):
    """Test platform detection integration with extension registry."""
    
    def setUp(self):
        """Set up test database and manager."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        # Create database with required tables
        self._create_test_database()
        
        self.manager = ExtensionRegistryManager(self.db_path)
    
    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def _create_test_database(self):
        """Create test database with required tables."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Create required tables (same as above)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS file_type_category (
                category_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                sort_order INTEGER DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT 1
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS file_extension (
                extension_id INTEGER PRIMARY KEY,
                extension TEXT NOT NULL UNIQUE,
                category_id INTEGER NOT NULL REFERENCES file_type_category(category_id),
                description TEXT,
                mime_type TEXT,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                is_archive BOOLEAN NOT NULL DEFAULT 0,
                is_rom BOOLEAN NOT NULL DEFAULT 0,
                is_save BOOLEAN NOT NULL DEFAULT 0,
                is_patch BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS platform (
                platform_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS platform_extension (
                platform_extension_id INTEGER PRIMARY KEY,
                platform_id INTEGER NOT NULL REFERENCES platform(platform_id),
                extension_id INTEGER NOT NULL REFERENCES file_extension(extension_id),
                is_primary BOOLEAN NOT NULL DEFAULT 0,
                confidence REAL NOT NULL DEFAULT 1.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(platform_id, extension_id)
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS unknown_extension (
                unknown_extension_id INTEGER PRIMARY KEY,
                extension TEXT NOT NULL UNIQUE,
                file_count INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'pending',
                suggested_category_id INTEGER REFERENCES file_type_category(category_id),
                suggested_platform_id INTEGER REFERENCES platform(platform_id),
                notes TEXT,
                first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _create_test_platform(self, name):
        """Helper to create a test platform."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO platform (name) VALUES (?)", (name,))
        platform_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return platform_id
    
    def test_file_type_detection_with_registry(self):
        """Test file type detection using extension registry."""
        # Create test data
        cat_id = self.manager.create_category("ROM Files", "Game ROM files", 1, True)
        ext_id = self.manager.create_extension(".nes", cat_id, "NES ROM", None, True, False, True, False, False)
        
        # Test detection
        file_info = self.manager.detect_file_type("test.nes")
        self.assertIsNotNone(file_info)
        self.assertEqual(file_info['extension'], ".nes")
        self.assertEqual(file_info['category_name'], "ROM Files")
        self.assertTrue(file_info['is_rom'])
        
        # Test unknown file
        file_info = self.manager.detect_file_type("test.unknown")
        self.assertIsNone(file_info)
        
        # Check that unknown was recorded
        unknown_exts = self.manager.get_unknown_extensions()
        self.assertEqual(len(unknown_exts), 1)
        self.assertEqual(unknown_exts[0]['extension'], ".unknown")
    
    def test_platform_detection_from_extension_registry(self):
        """Test platform detection using extension registry data."""
        # Create test data
        cat_id = self.manager.create_category("ROM Files", "Game ROM files", 1, True)
        ext_id = self.manager.create_extension(".nes", cat_id, "NES ROM", None, True, False, True, False, False)
        platform_id = self._create_test_platform("Nintendo Entertainment System")
        
        # Create platform mapping
        mapping_id = self.manager.create_platform_extension(platform_id, ext_id, True, 1.0)
        
        # Test platform detection
        platform_mappings = self.manager.get_platforms_for_extension(ext_id)
        self.assertEqual(len(platform_mappings), 1)
        self.assertEqual(platform_mappings[0]['platform_id'], platform_id)
        self.assertTrue(platform_mappings[0]['is_primary'])
        self.assertEqual(platform_mappings[0]['confidence'], 1.0)
    
    def test_platform_detection_priority_handling(self):
        """Test that platform detection prioritizes primary mappings."""
        # Create test data
        cat_id = self.manager.create_category("ROM Files", "Game ROM files", 1, True)
        ext_id = self.manager.create_extension(".iso", cat_id, "ISO Image", None, True, False, True, False, False)
        
        # Create multiple platform mappings
        platform1_id = self._create_test_platform("Primary Platform")
        platform2_id = self._create_test_platform("Secondary Platform")
        
        # Create primary mapping
        mapping1_id = self.manager.create_platform_extension(platform1_id, ext_id, True, 1.0)
        # Create secondary mapping
        mapping2_id = self.manager.create_platform_extension(platform2_id, ext_id, False, 0.8)
        
        # Test platform detection - should prefer primary
        platform_mappings = self.manager.get_platforms_for_extension(ext_id)
        self.assertEqual(len(platform_mappings), 2)
        
        # Find primary mapping
        primary_mapping = next((m for m in platform_mappings if m['is_primary']), None)
        self.assertIsNotNone(primary_mapping)
        self.assertEqual(primary_mapping['platform_id'], platform1_id)
    
    def test_extension_registry_summary(self):
        """Test extension registry summary functionality."""
        # Create test data
        cat_id = self.manager.create_category("ROM Files", "Game ROM files", 1, True)
        ext_id = self.manager.create_extension(".nes", cat_id, "NES ROM", None, True, False, True, False, False)
        platform_id = self._create_test_platform("Nintendo Entertainment System")
        mapping_id = self.manager.create_platform_extension(platform_id, ext_id, True, 1.0)
        unknown_id = self.manager.record_unknown_extension(".unknown", 5)
        
        # Get summary
        summary = self.manager.get_extension_registry_summary()
        
        # Verify summary structure
        self.assertIn('categories', summary)
        self.assertIn('extensions', summary)
        self.assertIn('mappings', summary)
        self.assertIn('unknown', summary)
        
        # Verify counts
        self.assertEqual(summary['categories']['total_categories'], 1)
        self.assertEqual(summary['categories']['active_categories'], 1)
        self.assertEqual(summary['extensions']['total_extensions'], 1)
        self.assertEqual(summary['extensions']['active_extensions'], 1)
        self.assertEqual(summary['extensions']['rom_extensions'], 1)
        self.assertEqual(summary['mappings']['total_mappings'], 1)
        self.assertEqual(summary['mappings']['primary_mappings'], 1)
        self.assertEqual(summary['unknown']['total_unknown'], 1)
        self.assertEqual(summary['unknown']['pending_unknown'], 1)


def run_extension_registry_tests():
    """Run the complete extension registry test suite."""
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestExtensionRegistryCRUD))
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestExtensionRegistryPersistence))
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestImportExport))
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestUnknownExtensionHandling))
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestPlatformDetectionIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_extension_registry_tests()
    sys.exit(0 if success else 1)