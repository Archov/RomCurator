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
    
    def test_import_partial_overwrite(self):
        """Test import with partial overlap - only matching entities should be overwritten."""
        # Create initial data
        cat1_id = self.manager.create_category("Category 1", "Original 1", 1, True)
        cat2_id = self.manager.create_category("Category 2", "Original 2", 2, True)
        ext1_id = self.manager.create_extension(".ext1", cat1_id, "Extension 1", None, True, False, True, False, False)
        ext2_id = self.manager.create_extension(".ext2", cat2_id, "Extension 2", None, True, False, True, False, False)
        
        # Create import data with partial overlap
        self.export_file = "/tmp/test_partial_overwrite.json"
        export_data = {
            'metadata': {'export_date': '2025-01-01', 'version': '1.0', 'format': 'json'},
            'categories': [
                {'name': 'Category 1', 'description': 'Updated Category 1', 'sort_order': 10, 'is_active': True},  # Overwrite existing
                {'name': 'Category 3', 'description': 'New Category 3', 'sort_order': 3, 'is_active': True}  # New category
            ],
            'extensions': [
                {'extension': '.ext1', 'category_id': 1, 'description': 'Updated Extension 1', 'is_active': True, 'is_rom': True, 'is_archive': False, 'is_save': False, 'is_patch': False},  # Overwrite existing
                {'extension': '.ext3', 'category_id': 1, 'description': 'New Extension 3', 'is_active': True, 'is_rom': True, 'is_archive': False, 'is_save': False, 'is_patch': False}  # New extension
            ],
            'mappings': [],
            'unknown_extensions': []
        }
        
        with open(self.export_file, 'w') as f:
            json.dump(export_data, f)
        
        # Import with overwrite
        results = self.manager.import_extensions(self.export_file, "json", overwrite=True)
        self.assertTrue(results['success'])
        self.assertEqual(results['categories_imported'], 2)  # 1 updated + 1 new
        self.assertEqual(results['extensions_imported'], 2)  # 1 updated + 1 new
        
        # Verify partial overwrite results
        categories = self.manager.get_categories()
        self.assertEqual(len(categories), 3)  # Original 2 + 1 new
        
        # Find specific categories
        cat1 = next(c for c in categories if c['name'] == 'Category 1')
        cat2 = next(c for c in categories if c['name'] == 'Category 2')
        cat3 = next(c for c in categories if c['name'] == 'Category 3')
        
        # Category 1 should be updated
        self.assertEqual(cat1['description'], 'Updated Category 1')
        self.assertEqual(cat1['sort_order'], 10)
        
        # Category 2 should remain unchanged
        self.assertEqual(cat2['description'], 'Original 2')
        self.assertEqual(cat2['sort_order'], 2)
        
        # Category 3 should be new
        self.assertEqual(cat3['description'], 'New Category 3')
        self.assertEqual(cat3['sort_order'], 3)
        
        # Verify extensions
        extensions = self.manager.get_extensions()
        self.assertEqual(len(extensions), 3)  # Original 2 + 1 new
        
        # Find specific extensions
        ext1 = next(e for e in extensions if e['extension'] == '.ext1')
        ext2 = next(e for e in extensions if e['extension'] == '.ext2')
        ext3 = next(e for e in extensions if e['extension'] == '.ext3')
        
        # Extension 1 should be updated
        self.assertEqual(ext1['description'], 'Updated Extension 1')
        
        # Extension 2 should remain unchanged
        self.assertEqual(ext2['description'], 'Extension 2')
        
        # Extension 3 should be new
        self.assertEqual(ext3['description'], 'New Extension 3')

    def test_import_resolves_foreign_keys_by_name(self):
        """Test that import resolves foreign keys using natural keys when IDs differ."""
        existing_category_id = self.manager.create_category("Existing Category", "Original", 1, True)
        self.manager.create_category("Secondary Category", "Secondary", 2, True)
        existing_platform_id = self._create_test_platform("Existing Platform")

        self.export_file = "/tmp/test_foreign_key_import.json"
        export_data = {
            'metadata': {'export_date': '2025-01-01', 'version': '1.0', 'format': 'json'},
            'categories': [
                {'name': 'Existing Category', 'description': 'Updated Description', 'sort_order': 10, 'is_active': True}
            ],
            'extensions': [
                {
                    'extension': '.fx',
                    'category_id': 999,
                    'category_name': 'Existing Category',
                    'description': 'FX Extension',
                    'is_active': True,
                    'is_rom': True,
                    'is_archive': False,
                    'is_save': False,
                    'is_patch': False
                }
            ],
            'mappings': [
                {
                    'platform_id': 555,
                    'platform_name': 'Existing Platform',
                    'extension_id': 777,
                    'extension': '.fx',
                    'is_primary': True,
                    'confidence': 0.95
                },
                {
                    'platform_name': 'Created Platform',
                    'extension': '.fx',
                    'is_primary': False,
                    'confidence': 0.5
                }
            ],
            'unknown_extensions': [
                {
                    'extension': '.mystery',
                    'file_count': 2,
                    'status': 'pending',
                    'suggested_category_id': 123,
                    'suggested_category': 'Existing Category',
                    'suggested_platform_id': 456,
                    'suggested_platform': 'Existing Platform',
                    'notes': 'Needs review'
                }
            ]
        }

        with open(self.export_file, 'w') as f:
            json.dump(export_data, f)

        results = self.manager.import_extensions(self.export_file, "json", overwrite=True)
        self.assertTrue(results['success'])

        extension = self.manager.get_extension_by_name('.fx')
        self.assertIsNotNone(extension)
        self.assertEqual(extension['category_id'], existing_category_id)

        mappings = self.manager.get_platform_extensions(extension_id=extension['extension_id'])
        self.assertEqual(len(mappings), 2)
        self.assertTrue(any(m['platform_id'] == existing_platform_id for m in mappings))
        self.assertTrue(any(m['platform_name'] == 'Created Platform' for m in mappings))

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT platform_id FROM platform WHERE name = ?", ("Created Platform",))
        created_platform_row = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(created_platform_row)

        unknown_entries = self.manager.get_unknown_extensions()
        self.assertTrue(any(ue['extension'] == '.mystery' for ue in unknown_entries))
        mystery_entry = next(ue for ue in unknown_entries if ue['extension'] == '.mystery')
        self.assertEqual(mystery_entry['suggested_category_id'], existing_category_id)
        self.assertEqual(mystery_entry['suggested_platform_id'], existing_platform_id)

    def test_csv_import_not_implemented(self):
        """Test that importing a CSV file raises the correct error and does not import data."""
        csv_path = self._create_test_csv_file()
        
        try:
            # Attempt to import CSV and expect error in results
            results = self.manager.import_extensions(csv_path, "csv")
            self.assertFalse(results['success'])
            self.assertGreater(len(results['errors']), 0)
            self.assertTrue(any("Unsupported import format: csv" in error for error in results['errors']))
            self.assertTrue(any("Only 'json' is currently supported" in error for error in results['errors']))

            # Ensure no data was imported
            categories = self.manager.get_categories()
            self.assertEqual(len(categories), 0)
        finally:
            os.remove(csv_path)
    
    def _create_test_csv_file(self):
        """Helper method to create a test CSV file."""
        csv_content = "id,name,description\n1,Test Category,Test Description"
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w') as temp_csv:
            temp_csv.write(csv_content)
            return temp_csv.name
    
    def test_import_json_malformed(self):
        """Test import error handling for malformed JSON."""
        malformed_json = '{"metadata": {"export_date": "2025-01-01", "version": "1.0", "format": "json"}, "categories": [}'  # Invalid JSON
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
            tmp.write(malformed_json)
            tmp_path = tmp.name

        try:
            results = self.manager.import_extensions(tmp_path, "json")
            self.assertFalse(results['success'])
            self.assertGreater(len(results['errors']), 0)
            # Check that no data was imported
            categories = self.manager.get_categories()
            self.assertEqual(len(categories), 0)
        finally:
            os.remove(tmp_path)
    
    def test_import_json_missing_fields(self):
        """Test import error handling for missing required fields."""
        missing_fields_json = '{"metadata": {"export_date": "2025-01-01", "version": "1.0", "format": "json"}}'  # Missing categories, extensions, etc.
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
            tmp.write(missing_fields_json)
            tmp_path = tmp.name

        try:
            results = self.manager.import_extensions(tmp_path, "json")
            # Should succeed but import nothing
            self.assertTrue(results['success'])
            self.assertEqual(results['categories_imported'], 0)
            self.assertEqual(results['extensions_imported'], 0)
        finally:
            os.remove(tmp_path)
    
    def test_import_json_extra_fields(self):
        """Test import with extra/unknown fields in JSON."""
        extra_fields_json = '''{
            "metadata": {"export_date": "2025-01-01", "version": "1.0", "format": "json"},
            "categories": [{"name": "Test Category", "description": "Test", "sort_order": 1, "is_active": true, "extra_field": "should_be_ignored"}],
            "extensions": [{"extension": ".test", "category_id": 1, "description": "Test Extension", "is_active": true, "is_rom": true, "is_archive": false, "is_save": false, "is_patch": false, "unknown_field": "should_be_ignored"}],
            "mappings": [],
            "unknown_extensions": [],
            "extra_section": "should_be_ignored"
        }'''
        
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
            tmp.write(extra_fields_json)
            tmp_path = tmp.name

        try:
            results = self.manager.import_extensions(tmp_path, "json")
            # Should succeed and ignore extra fields
            self.assertTrue(results['success'])
            self.assertEqual(results['categories_imported'], 1)
            self.assertEqual(results['extensions_imported'], 1)
            
            # Verify data was imported correctly (extra fields ignored)
            categories = self.manager.get_categories()
            self.assertEqual(len(categories), 1)
            self.assertEqual(categories[0]['name'], 'Test Category')
            self.assertEqual(categories[0]['description'], 'Test')
            
            extensions = self.manager.get_extensions()
            self.assertEqual(len(extensions), 1)
            self.assertEqual(extensions[0]['extension'], '.test')
            self.assertEqual(extensions[0]['description'], 'Test Extension')
        finally:
            os.remove(tmp_path)
    
    def test_export_csv_functionality(self):
        """Test CSV export functionality and verify correct formatting and data completeness."""
        # Create test data
        self._create_csv_test_data()
        
        # Export to CSV
        self.export_file = "/tmp/test_export.csv"
        success = self.manager.export_extensions(self.export_file, "csv")
        self.assertTrue(success)
        self.assertTrue(os.path.exists(self.export_file))
        
        # Verify export content
        content = self._read_csv_export_content()
        
        # Check that all sections are present
        self._verify_csv_sections_present(content)
        
        # Check specific data is present
        self._verify_csv_data_present(content)
        
        # Verify CSV structure
        self._verify_csv_structure(content)
    
    def _create_csv_test_data(self):
        """Helper method to create test data for CSV export tests."""
        cat_id = self.manager.create_category("Test Category", "Test Description", 1, True)
        ext_id = self.manager.create_extension(".test", cat_id, "Test Extension", "application/octet-stream", True, False, True, False, False)
        platform_id = self._create_test_platform("Test Platform")
        mapping_id = self.manager.create_platform_extension(platform_id, ext_id, True, 0.9)
        unknown_id = self.manager.record_unknown_extension(".unknown", 3)
    
    def _read_csv_export_content(self):
        """Helper method to read CSV export content."""
        with open(self.export_file, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _verify_csv_sections_present(self, content):
        """Helper method to verify CSV sections are present."""
        self.assertIn('CATEGORIES', content)
        self.assertIn('EXTENSIONS', content)
        self.assertIn('PLATFORM MAPPINGS', content)
        self.assertIn('UNKNOWN EXTENSIONS', content)
    
    def _verify_csv_data_present(self, content):
        """Helper method to verify specific data is present in CSV."""
        self.assertIn('Test Category', content)
        self.assertIn('.test', content)
        self.assertIn('Test Platform', content)
        self.assertIn('.unknown', content)
    
    def _verify_csv_structure(self, content):
        """Helper method to verify CSV structure and headers."""
        lines = content.strip().split('\n')
        
        # Find section boundaries
        categories_start = next(i for i, line in enumerate(lines) if line.strip() == 'CATEGORIES')
        extensions_start = next(i for i, line in enumerate(lines) if line.strip() == 'EXTENSIONS')
        mappings_start = next(i for i, line in enumerate(lines) if line.strip() == 'PLATFORM MAPPINGS')
        unknown_start = next(i for i, line in enumerate(lines) if line.strip() == 'UNKNOWN EXTENSIONS')
        
        # Verify categories section
        cat_header_line = lines[categories_start + 1]
        self.assertIn('category_id', cat_header_line)
        self.assertIn('name', cat_header_line)
        self.assertIn('description', cat_header_line)
        
        # Verify extensions section
        ext_header_line = lines[extensions_start + 1]
        self.assertIn('extension_id', ext_header_line)
        self.assertIn('extension', ext_header_line)
        self.assertIn('is_rom', ext_header_line)
        
        # Verify mappings section
        map_header_line = lines[mappings_start + 1]
        self.assertIn('platform_extension_id', map_header_line)
        self.assertIn('platform_name', map_header_line)
        self.assertIn('is_primary', map_header_line)
        self.assertIn('confidence', map_header_line)
        
        # Verify unknown extensions section
        unknown_header_line = lines[unknown_start + 1]
        self.assertIn('unknown_extension_id', unknown_header_line)
        self.assertIn('extension', unknown_header_line)
        self.assertIn('file_count', unknown_header_line)
        self.assertIn('status', unknown_header_line)


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
        self._test_unknown_extension_filtering('pending', '.pending')
        self._test_unknown_extension_filtering('approved', '.approved')
        self._test_unknown_extension_filtering('rejected', '.rejected')
        self._test_unknown_extension_filtering('ignored', '.ignored')
    
    def _test_unknown_extension_filtering(self, status: str, expected_extension: str):
        """Helper method to test unknown extension filtering by status."""
        extensions = self.manager.get_unknown_extensions(status=status)
        self.assertEqual(len(extensions), 1)
        self.assertEqual(extensions[0]['extension'], expected_extension)
    
    def test_unknown_extension_approval_failure_missing_category(self):
        """Test unknown extension approval failure when category is missing."""
        # Record unknown extension
        unknown_id = self.manager.record_unknown_extension(".newrom", 10)
        
        # Try to approve with non-existent category
        success = self.manager.approve_unknown_extension(unknown_id, 999, None, "Test approval")
        self.assertFalse(success)
        
        # Check that extension was not created
        extensions = self.manager.get_extensions()
        self.assertEqual(len(extensions), 0)
        
        # Check that unknown extension status was not changed
        unknown_exts = self.manager.get_unknown_extensions()
        self.assertEqual(unknown_exts[0]['status'], 'pending')
    
    def test_unknown_extension_approval_failure_missing_platform(self):
        """Test unknown extension approval failure when platform is missing."""
        # Record unknown extension
        unknown_id = self.manager.record_unknown_extension(".newrom", 10)
        
        # Create category but use non-existent platform
        cat_id = self.manager.create_category("New ROM Files", "New ROM format", 1, True)
        
        # Try to approve with non-existent platform
        success = self.manager.approve_unknown_extension(unknown_id, cat_id, 999, "Test approval")
        self.assertFalse(success)
        
        # Check that extension was not created
        extensions = self.manager.get_extensions()
        self.assertEqual(len(extensions), 0)
        
        # Check that unknown extension status was not changed
        unknown_exts = self.manager.get_unknown_extensions()
        self.assertEqual(unknown_exts[0]['status'], 'pending')


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
    
    def test_file_type_detection_case_insensitive(self):
        """Test file type detection is case-insensitive for extensions."""
        # Create test data
        cat_id = self.manager.create_category("ROM Files", "Game ROM files", 1, True)
        ext_id = self.manager.create_extension(".nes", cat_id, "NES ROM", None, True, False, True, False, False)
        
        # Test various case combinations
        test_extensions = ['.NES', '.NeS', '.nes', '.Nes']
        expected_type = 'NES ROM'
        
        for ext in test_extensions:
            file_info = self.manager.detect_file_type(f"game{ext}")
            self.assertIsNotNone(file_info, f"Failed for extension: {ext}")
            self.assertEqual(file_info['extension'], '.nes')  # Should normalize to lowercase
            self.assertEqual(file_info['description'], expected_type)
    
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
    
    def test_platform_detection_equal_confidence(self):
        """Test platform detection when multiple mappings have equal confidence and none are primary."""
        # Create test data
        cat_id = self.manager.create_category("ROM Files", "Game ROM files", 1, True)
        ext_id = self.manager.create_extension(".multi", cat_id, "Multi-platform ROM", None, True, False, True, False, False)
        
        # Create multiple platforms with equal confidence
        platform1_id = self._create_test_platform("Platform A")
        platform2_id = self._create_test_platform("Platform B")
        platform3_id = self._create_test_platform("Platform C")
        
        # Create mappings with equal confidence, none primary
        mapping1_id = self.manager.create_platform_extension(platform1_id, ext_id, False, 0.8)
        mapping2_id = self.manager.create_platform_extension(platform2_id, ext_id, False, 0.8)
        mapping3_id = self.manager.create_platform_extension(platform3_id, ext_id, False, 0.8)
        
        # Test platform detection - should return one of the equal confidence mappings
        platform_mappings = self.manager.get_platforms_for_extension(ext_id)
        self.assertEqual(len(platform_mappings), 3)
        
        # All mappings should have equal confidence
        confidences = [m['confidence'] for m in platform_mappings]
        self.assertTrue(all(c == 0.8 for c in confidences))
        
        # None should be primary
        primary_mappings = [m for m in platform_mappings if m['is_primary']]
        self.assertEqual(len(primary_mappings), 0)
        
        # The selection should be consistent (first one with highest confidence)
        best_mapping = max(platform_mappings, key=lambda m: m['confidence'])
        self.assertEqual(best_mapping['confidence'], 0.8)
        self.assertIn(best_mapping['platform_id'], [platform1_id, platform2_id, platform3_id])
    
    def test_platform_detection_zero_confidence(self):
        """Test platform detection when all confidence values are zero or missing."""
        # Create test data
        cat_id = self.manager.create_category("ROM Files", "Game ROM files", 1, True)
        ext_id = self.manager.create_extension(".zero", cat_id, "Zero confidence ROM", None, True, False, True, False, False)
        
        # Create multiple platforms with zero confidence
        platform1_id = self._create_test_platform("Platform A")
        platform2_id = self._create_test_platform("Platform B")
        platform3_id = self._create_test_platform("Platform C")
        
        # Create mappings with zero confidence, none primary
        mapping1_id = self.manager.create_platform_extension(platform1_id, ext_id, False, 0.0)
        mapping2_id = self.manager.create_platform_extension(platform2_id, ext_id, False, 0.0)
        mapping3_id = self.manager.create_platform_extension(platform3_id, ext_id, False, 0.0)
        
        # Test platform detection - should return one of the zero confidence mappings
        platform_mappings = self.manager.get_platforms_for_extension(ext_id)
        self.assertEqual(len(platform_mappings), 3)
        
        # All mappings should have zero confidence
        confidences = [m['confidence'] for m in platform_mappings]
        self.assertTrue(all(c == 0.0 for c in confidences))
        
        # None should be primary
        primary_mappings = [m for m in platform_mappings if m['is_primary']]
        self.assertEqual(len(primary_mappings), 0)
        
        # The selection should still work (first one with highest confidence, which is 0.0)
        best_mapping = max(platform_mappings, key=lambda m: m['confidence'])
        self.assertEqual(best_mapping['confidence'], 0.0)
        self.assertIn(best_mapping['platform_id'], [platform1_id, platform2_id, platform3_id])
    
    def test_platform_detection_multiple_primary(self):
        """Test platform detection when multiple mappings are set as primary."""
        # Create test data
        cat_id = self.manager.create_category("ROM Files", "Game ROM files", 1, True)
        ext_id = self.manager.create_extension(".multi", cat_id, "Multi Platform Extension", None, True, False, True, False, False)
        
        # Create platforms
        platform1_id = self._create_test_platform("Primary Platform 1")
        platform2_id = self._create_test_platform("Primary Platform 2")
        platform3_id = self._create_test_platform("Non-Primary Platform")
        
        # Create multiple primary mappings
        self.manager.create_platform_extension(platform1_id, ext_id, True, 0.9)
        self.manager.create_platform_extension(platform2_id, ext_id, True, 0.8)
        self.manager.create_platform_extension(platform3_id, ext_id, False, 0.7)
        
        # Test platform detection - should return the first primary mapping
        platform_mappings = self.manager.get_platforms_for_extension(ext_id)
        self.assertEqual(len(platform_mappings), 3)
        
        # Find primary mappings
        primary_mappings = [m for m in platform_mappings if m['is_primary']]
        self.assertEqual(len(primary_mappings), 2)
        
        # Should return one of the primary platforms (first one found)
        primary_platform_ids = [m['platform_id'] for m in primary_mappings]
        self.assertIn(platform1_id, primary_platform_ids)
        self.assertIn(platform2_id, primary_platform_ids)
        self.assertNotIn(platform3_id, primary_platform_ids)
    
    def test_platform_detection_missing_confidence(self):
        """Test platform detection when confidence field is missing from mappings."""
        # Create test data
        cat_id = self.manager.create_category("ROM Files", "Game ROM files", 1, True)
        ext_id = self.manager.create_extension(".missing", cat_id, "Missing Confidence ROM", None, True, False, True, False, False)
        
        # Create platform
        platform_id = self._create_test_platform("Test Platform")
        
        # Create mapping without confidence field (should use default 1.0)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO platform_extension (platform_id, extension_id, is_primary)
            VALUES (?, ?, ?)
        """, (platform_id, ext_id, False))
        conn.commit()
        conn.close()
        
        # Test platform detection
        platform_mappings = self.manager.get_platforms_for_extension(ext_id)
        self.assertEqual(len(platform_mappings), 1)
        self.assertEqual(platform_mappings[0]['platform_id'], platform_id)
        self.assertEqual(platform_mappings[0]['confidence'], 1.0)  # Should use default
        self.assertFalse(platform_mappings[0]['is_primary'])
    
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