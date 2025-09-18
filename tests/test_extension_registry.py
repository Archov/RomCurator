"""
Test suite for Extension Registry functionality.

This module provides comprehensive tests for the extension registry system,
including CRUD operations, platform mappings, unknown extension handling,
and import/export functionality.
"""

import unittest
import tempfile
import os
import json
import sqlite3
from pathlib import Path
import sys

# Add the project root to the path
sys.path.append(str(Path(__file__).parent.parent))

from extension_registry_manager import ExtensionRegistryManager


class TestExtensionRegistryManager(unittest.TestCase):
    """Test cases for ExtensionRegistryManager."""
    
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
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create extension registry tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_type_category (
                    category_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    sort_order INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_extension (
                    extension_id INTEGER PRIMARY KEY,
                    extension TEXT NOT NULL UNIQUE,
                    category_id INTEGER NOT NULL REFERENCES file_type_category(category_id),
                    description TEXT,
                    mime_type TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_rom BOOLEAN DEFAULT FALSE,
                    is_archive BOOLEAN DEFAULT FALSE,
                    is_save BOOLEAN DEFAULT FALSE,
                    is_patch BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS platform (
                    platform_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS platform_extension (
                    platform_extension_id INTEGER PRIMARY KEY,
                    platform_id INTEGER NOT NULL REFERENCES platform(platform_id),
                    extension_id INTEGER NOT NULL REFERENCES file_extension(extension_id),
                    is_primary BOOLEAN DEFAULT FALSE,
                    confidence REAL DEFAULT 1.0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(platform_id, extension_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS unknown_extension (
                    unknown_extension_id INTEGER PRIMARY KEY,
                    extension TEXT NOT NULL UNIQUE,
                    file_count INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'ignored')),
                    suggested_category_id INTEGER REFERENCES file_type_category(category_id),
                    suggested_platform_id INTEGER REFERENCES platform(platform_id),
                    notes TEXT,
                    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def test_create_category(self):
        """Test creating a new category."""
        category_id = self.manager.create_category(
            name="Test Category",
            description="Test description",
            sort_order=10,
            is_active=True
        )
        
        self.assertIsNotNone(category_id)
        self.assertGreater(category_id, 0)
        
        # Verify category was created
        category = self.manager.get_category(category_id)
        self.assertIsNotNone(category)
        self.assertEqual(category['name'], "Test Category")
        self.assertEqual(category['description'], "Test description")
        self.assertEqual(category['sort_order'], 10)
        self.assertTrue(category['is_active'])
    
    def test_create_category_duplicate(self):
        """Test creating a duplicate category fails."""
        self.manager.create_category(name="Test Category")
        
        with self.assertRaises(ValueError):
            self.manager.create_category(name="Test Category")
    
    def test_get_categories(self):
        """Test getting all categories."""
        # Create test categories
        cat1 = self.manager.create_category("Category 1", sort_order=10)
        cat2 = self.manager.create_category("Category 2", sort_order=5)
        cat3 = self.manager.create_category("Category 3", sort_order=15, is_active=False)
        
        # Get all categories
        categories = self.manager.get_categories()
        self.assertEqual(len(categories), 3)
        
        # Check sorting (by sort_order, then name)
        self.assertEqual(categories[0]['name'], "Category 2")  # sort_order=5
        self.assertEqual(categories[1]['name'], "Category 1")  # sort_order=10
        self.assertEqual(categories[2]['name'], "Category 3")  # sort_order=15
        
        # Get active categories only
        active_categories = self.manager.get_categories(active_only=True)
        self.assertEqual(len(active_categories), 2)
        self.assertTrue(all(cat['is_active'] for cat in active_categories))
    
    def test_update_category(self):
        """Test updating a category."""
        category_id = self.manager.create_category("Original Name", "Original description")
        
        # Update category
        success = self.manager.update_category(
            category_id,
            name="Updated Name",
            description="Updated description",
            sort_order=99
        )
        
        self.assertTrue(success)
        
        # Verify update
        category = self.manager.get_category(category_id)
        self.assertEqual(category['name'], "Updated Name")
        self.assertEqual(category['description'], "Updated description")
        self.assertEqual(category['sort_order'], 99)
    
    def test_delete_category(self):
        """Test deleting a category."""
        category_id = self.manager.create_category("To Delete")
        
        # Delete category
        success = self.manager.delete_category(category_id)
        self.assertTrue(success)
        
        # Verify deletion
        category = self.manager.get_category(category_id)
        self.assertIsNone(category)
    
    def test_create_extension(self):
        """Test creating a new extension."""
        category_id = self.manager.create_category("Test Category")
        
        extension_id = self.manager.create_extension(
            extension=".test",
            category_id=category_id,
            description="Test extension",
            mime_type="application/x-test",
            is_rom=True,
            is_archive=False,
            is_save=False,
            is_patch=False
        )
        
        self.assertIsNotNone(extension_id)
        self.assertGreater(extension_id, 0)
        
        # Verify extension was created
        extension = self.manager.get_extension(extension_id)
        self.assertIsNotNone(extension)
        self.assertEqual(extension['extension'], '.test')
        self.assertEqual(extension['category_id'], category_id)
        self.assertEqual(extension['description'], "Test extension")
        self.assertEqual(extension['mime_type'], "application/x-test")
        self.assertTrue(extension['is_rom'])
        self.assertFalse(extension['is_archive'])
        self.assertFalse(extension['is_save'])
        self.assertFalse(extension['is_patch'])
    
    def test_create_extension_auto_dot(self):
        """Test that extension automatically gets a dot prefix."""
        category_id = self.manager.create_category("Test Category")
        
        extension_id = self.manager.create_extension("test", category_id)
        extension = self.manager.get_extension(extension_id)
        self.assertEqual(extension['extension'], '.test')
    
    def test_get_extension_by_name(self):
        """Test getting extension by name."""
        category_id = self.manager.create_category("Test Category")
        extension_id = self.manager.create_extension(".test", category_id)
        
        extension = self.manager.get_extension_by_name(".test")
        self.assertIsNotNone(extension)
        self.assertEqual(extension['extension_id'], extension_id)
        
        # Test with extension without dot
        extension2 = self.manager.get_extension_by_name("test")
        self.assertIsNotNone(extension2)
        self.assertEqual(extension2['extension_id'], extension_id)
    
    def test_get_extensions(self):
        """Test getting extensions with filters."""
        category1 = self.manager.create_category("Category 1")
        category2 = self.manager.create_category("Category 2")
        
        ext1 = self.manager.create_extension(".ext1", category1, is_rom=True)
        ext2 = self.manager.create_extension(".ext2", category1, is_archive=True)
        ext3 = self.manager.create_extension(".ext3", category2, is_rom=True, is_active=False)
        
        # Get all extensions
        extensions = self.manager.get_extensions()
        self.assertEqual(len(extensions), 3)
        
        # Get extensions by category
        cat1_extensions = self.manager.get_extensions(category_id=category1)
        self.assertEqual(len(cat1_extensions), 2)
        
        # Get active extensions only
        active_extensions = self.manager.get_extensions(active_only=True)
        self.assertEqual(len(active_extensions), 2)
        self.assertTrue(all(ext['is_active'] for ext in active_extensions))
    
    def test_platform_mapping(self):
        """Test platform-extension mapping."""
        # Create test data
        category_id = self.manager.create_category("Test Category")
        extension_id = self.manager.create_extension(".test", category_id)
        
        # Create platform
        with self.manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO platform (name) VALUES (?)", ("Test Platform",))
            platform_id = cursor.lastrowid
            conn.commit()
        
        # Add platform mapping
        mapping_id = self.manager.add_platform_mapping(
            platform_id=platform_id,
            extension_id=extension_id,
            is_primary=True,
            confidence=0.9
        )
        
        self.assertIsNotNone(mapping_id)
        
        # Get platform mappings for extension
        mappings = self.manager.get_platforms_for_extension(extension_id)
        self.assertEqual(len(mappings), 1)
        self.assertEqual(mappings[0]['platform_id'], platform_id)
        self.assertTrue(mappings[0]['is_primary'])
        self.assertEqual(mappings[0]['confidence'], 0.9)
    
    def test_unknown_extension_recording(self):
        """Test recording unknown extensions."""
        # Record unknown extension
        unknown_id = self.manager.record_unknown_extension(".unknown", 5)
        self.assertIsNotNone(unknown_id)
        
        # Record same extension again (should update count)
        unknown_id2 = self.manager.record_unknown_extension(".unknown", 3)
        self.assertEqual(unknown_id, unknown_id2)
        
        # Verify unknown extension
        unknown_extensions = self.manager.get_unknown_extensions()
        self.assertEqual(len(unknown_extensions), 1)
        self.assertEqual(unknown_extensions[0]['extension'], '.unknown')
        self.assertEqual(unknown_extensions[0]['file_count'], 8)  # 5 + 3
        self.assertEqual(unknown_extensions[0]['status'], 'pending')
    
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
    
    def test_approve_unknown_extension(self):
        """Test approving an unknown extension."""
        # Create test data
        category_id = self.manager.create_category("Test Category")
        unknown_id = self.manager.record_unknown_extension(".unknown", 1)
        
        # Create platform
        with self.manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO platform (name) VALUES (?)", ("Test Platform",))
            platform_id = cursor.lastrowid
            conn.commit()
        
        # Approve unknown extension
        success = self.manager.approve_unknown_extension(
            unknown_id=unknown_id,
            category_id=category_id,
            platform_id=platform_id,
            notes="Test approval"
        )
        
        self.assertTrue(success)
        
        # Verify extension was created
        extension = self.manager.get_extension_by_name(".unknown")
        self.assertIsNotNone(extension)
        self.assertEqual(extension['category_id'], category_id)
        
        # Verify platform mapping was created
        mappings = self.manager.get_platforms_for_extension(extension['extension_id'])
        self.assertEqual(len(mappings), 1)
        self.assertEqual(mappings[0]['platform_id'], platform_id)
        self.assertTrue(mappings[0]['is_primary'])
        
        # Verify unknown extension status was updated
        unknown_extensions = self.manager.get_unknown_extensions(status='approved')
        self.assertEqual(len(unknown_extensions), 1)
        self.assertEqual(unknown_extensions[0]['extension'], '.unknown')
    
    def test_detect_file_type(self):
        """Test file type detection."""
        # Create test data
        category_id = self.manager.create_category("Test Category")
        extension_id = self.manager.create_extension(
            ".test", category_id, 
            is_rom=True, is_archive=False, is_save=False, is_patch=False
        )
        
        # Create platform
        with self.manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO platform (name) VALUES (?)", ("Test Platform",))
            platform_id = cursor.lastrowid
            conn.commit()
        
        # Add platform mapping
        self.manager.add_platform_mapping(platform_id, extension_id, is_primary=True)
        
        # Test file type detection
        file_type_info = self.manager.detect_file_type("testfile.test")
        self.assertIsNotNone(file_type_info)
        self.assertEqual(file_type_info['extension'], '.test')
        self.assertEqual(file_type_info['category'], 'Test Category')
        self.assertTrue(file_type_info['is_rom'])
        self.assertFalse(file_type_info['is_archive'])
        self.assertFalse(file_type_info['is_save'])
        self.assertFalse(file_type_info['is_patch'])
        self.assertEqual(len(file_type_info['platforms']), 1)
        self.assertEqual(file_type_info['platforms'][0]['platform_id'], platform_id)
    
    def test_get_supported_extensions(self):
        """Test getting supported extensions grouped by type."""
        # Create test data
        category_id = self.manager.create_category("Test Category")
        
        # Create different types of extensions
        self.manager.create_extension(".rom", category_id, is_rom=True)
        self.manager.create_extension(".zip", category_id, is_archive=True)
        self.manager.create_extension(".sav", category_id, is_save=True)
        self.manager.create_extension(".ips", category_id, is_patch=True)
        self.manager.create_extension(".inactive", category_id, is_rom=True, is_active=False)
        
        # Get supported extensions
        extensions = self.manager.get_supported_extensions()
        
        self.assertIn('.rom', extensions['rom'])
        self.assertIn('.zip', extensions['archive'])
        self.assertIn('.sav', extensions['save'])
        self.assertIn('.ips', extensions['patch'])
        self.assertNotIn('.inactive', extensions['rom'])  # Inactive extension should not be included
    
    def test_export_import_json(self):
        """Test JSON export and import functionality."""
        # Create test data
        category_id = self.manager.create_category("Test Category", "Test description")
        extension_id = self.manager.create_extension(".test", category_id, is_rom=True)
        
        # Create platform and mapping
        with self.manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO platform (name) VALUES (?)", ("Test Platform",))
            platform_id = cursor.lastrowid
            conn.commit()
        
        self.manager.add_platform_mapping(platform_id, extension_id, is_primary=True)
        
        # Record unknown extension
        unknown_id = self.manager.record_unknown_extension(".unknown", 1)
        
        # Export to JSON
        export_file = "/tmp/test_export.json"
        success = self.manager.export_extensions(export_file, 'json')
        self.assertTrue(success)
        self.assertTrue(os.path.exists(export_file))
        
        # Verify export file content
        with open(export_file, 'r') as f:
            export_data = json.load(f)
        
        self.assertIn('metadata', export_data)
        self.assertIn('categories', export_data)
        self.assertIn('extensions', export_data)
        self.assertIn('mappings', export_data)
        self.assertIn('unknown_extensions', export_data)
        
        self.assertEqual(len(export_data['categories']), 1)
        self.assertEqual(len(export_data['extensions']), 1)
        self.assertEqual(len(export_data['mappings']), 1)
        self.assertEqual(len(export_data['unknown_extensions']), 1)
        
        # Clean up
        os.unlink(export_file)
    
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
        
        try:
            # Import the data
            results = self.manager.import_extensions(self.export_file, 'json', overwrite=False)
            
            self.assertTrue(results['success'])
            self.assertEqual(results['categories_imported'], 1)
            self.assertEqual(results['extensions_imported'], 1)
            self.assertEqual(results['mappings_imported'], 0)
            self.assertEqual(results['unknown_imported'], 0)
            
            # Verify data was imported
            categories = self.manager.get_categories()
            self.assertEqual(len(categories), 1)
            self.assertEqual(categories[0]['name'], 'Imported Category')
            
            extensions = self.manager.get_extensions()
            self.assertEqual(len(extensions), 1)
            self.assertEqual(extensions[0]['extension'], '.imported')
            
        finally:
            if os.path.exists(self.export_file):
                os.unlink(self.export_file)
    
    def test_csv_import_not_implemented(self):
        """Test that importing a CSV file raises the correct error and does not import data."""
        # Prepare a dummy CSV file
        csv_content = "id,name,description\n1,Test Category,Test Description"
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w') as temp_csv:
            temp_csv.write(csv_content)
            csv_path = temp_csv.name
        
        try:
            # Attempt to import CSV and expect error
            results = self.manager.import_extensions(csv_path, 'csv')
            self.assertFalse(results['success'])
            self.assertIn("Unsupported import format", str(results['errors']))
            
            # Ensure no data was imported
            categories = self.manager.get_categories()
            self.assertEqual(len(categories), 0)
            
        finally:
            os.remove(csv_path)
    
    def test_import_json_malformed(self):
        """Test import error handling for malformed JSON."""
        malformed_json = '{"metadata": {"export_date": "2025-01-01", "version": "1.0", "format": "json"}, "categories": [}'  # Invalid JSON
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
            tmp.write(malformed_json)
            tmp_path = tmp.name
        
        try:
            results = self.manager.import_extensions(tmp_path, 'json')
            self.assertFalse(results['success'])
            self.assertTrue(any('expecting' in str(error).lower() or 'json' in str(error).lower() for error in results['errors']))
        finally:
            os.remove(tmp_path)
    
    def test_import_json_missing_fields(self):
        """Test import error handling for missing required fields."""
        missing_fields_json = '{"metadata": {"export_date": "2025-01-01", "version": "1.0", "format": "json"}}'  # Missing categories, extensions, etc.
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
            tmp.write(missing_fields_json)
            tmp_path = tmp.name
        
        try:
            results = self.manager.import_extensions(tmp_path, 'json')
            # Should succeed but with no data imported
            self.assertTrue(results['success'])
            self.assertEqual(results['categories_imported'], 0)
            self.assertEqual(results['extensions_imported'], 0)
        finally:
            os.remove(tmp_path)


class TestPlatformDetectionIntegration(unittest.TestCase):
    """Test platform detection integration scenarios."""
    
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
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create extension registry tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_type_category (
                    category_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    sort_order INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_extension (
                    extension_id INTEGER PRIMARY KEY,
                    extension TEXT NOT NULL UNIQUE,
                    category_id INTEGER NOT NULL REFERENCES file_type_category(category_id),
                    description TEXT,
                    mime_type TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_rom BOOLEAN DEFAULT FALSE,
                    is_archive BOOLEAN DEFAULT FALSE,
                    is_save BOOLEAN DEFAULT FALSE,
                    is_patch BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS platform (
                    platform_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS platform_extension (
                    platform_extension_id INTEGER PRIMARY KEY,
                    platform_id INTEGER NOT NULL REFERENCES platform(platform_id),
                    extension_id INTEGER NOT NULL REFERENCES file_extension(extension_id),
                    is_primary BOOLEAN DEFAULT FALSE,
                    confidence REAL DEFAULT 1.0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(platform_id, extension_id)
                )
            """)
            
            conn.commit()
    
    def test_platform_detection_primary_mapping(self):
        """Test platform detection with primary mapping."""
        # Create test data
        category_id = self.manager.create_category("Test Category")
        extension_id = self.manager.create_extension(".test", category_id)
        
        # Create platforms
        with self.manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO platform (name) VALUES (?)", ("Primary Platform",))
            primary_platform_id = cursor.lastrowid
            cursor.execute("INSERT INTO platform (name) VALUES (?)", ("Secondary Platform",))
            secondary_platform_id = cursor.lastrowid
            conn.commit()
        
        # Add mappings - primary and secondary
        self.manager.add_platform_mapping(primary_platform_id, extension_id, is_primary=True, confidence=1.0)
        self.manager.add_platform_mapping(secondary_platform_id, extension_id, is_primary=False, confidence=0.8)
        
        # Test detection - should return primary platform
        file_type_info = self.manager.detect_file_type("testfile.test")
        self.assertIsNotNone(file_type_info)
        self.assertEqual(len(file_type_info['platforms']), 2)
        
        # Primary mapping should be first
        primary_mapping = next((p for p in file_type_info['platforms'] if p['is_primary']), None)
        self.assertIsNotNone(primary_mapping)
        self.assertEqual(primary_mapping['platform_id'], primary_platform_id)
    
    def test_platform_detection_equal_confidence(self):
        """Test platform detection when multiple mappings have equal confidence and none are primary."""
        # Create test data
        category_id = self.manager.create_category("Test Category")
        extension_id = self.manager.create_extension(".test", category_id)
        
        # Create platforms
        with self.manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO platform (name) VALUES (?)", ("Platform A",))
            platform_a_id = cursor.lastrowid
            cursor.execute("INSERT INTO platform (name) VALUES (?)", ("Platform B",))
            platform_b_id = cursor.lastrowid
            conn.commit()
        
        # Add mappings with equal confidence, no primary
        self.manager.add_platform_mapping(platform_a_id, extension_id, is_primary=False, confidence=0.9)
        self.manager.add_platform_mapping(platform_b_id, extension_id, is_primary=False, confidence=0.9)
        
        # Test detection - should return one of the platforms consistently
        file_type_info = self.manager.detect_file_type("testfile.test")
        self.assertIsNotNone(file_type_info)
        self.assertEqual(len(file_type_info['platforms']), 2)
        
        # Both platforms should be present
        platform_ids = [p['platform_id'] for p in file_type_info['platforms']]
        self.assertIn(platform_a_id, platform_ids)
        self.assertIn(platform_b_id, platform_ids)
        
        # Neither should be primary
        primary_mappings = [p for p in file_type_info['platforms'] if p['is_primary']]
        self.assertEqual(len(primary_mappings), 0)
    
    def test_platform_detection_consistency(self):
        """Test that platform detection is consistent when multiple mappings have equal confidence."""
        # Create test data
        category_id = self.manager.create_category("Test Category")
        extension_id = self.manager.create_extension(".test", category_id)
        
        # Create platforms
        with self.manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO platform (name) VALUES (?)", ("Platform A",))
            platform_a_id = cursor.lastrowid
            cursor.execute("INSERT INTO platform (name) VALUES (?)", ("Platform B",))
            platform_b_id = cursor.lastrowid
            conn.commit()
        
        # Add mappings with equal confidence, no primary
        self.manager.add_platform_mapping(platform_a_id, extension_id, is_primary=False, confidence=0.9)
        self.manager.add_platform_mapping(platform_b_id, extension_id, is_primary=False, confidence=0.9)
        
        # Test detection multiple times to ensure consistency
        results = []
        for _ in range(10):
            file_type_info = self.manager.detect_file_type("testfile.test")
            if file_type_info and file_type_info['platforms']:
                # Get the first platform (should be consistent)
                first_platform = file_type_info['platforms'][0]
                results.append(first_platform['platform_id'])
        
        # All results should be the same (consistent)
        self.assertTrue(all(r == results[0] for r in results), "Platform detection should be consistent")
        
        # The result should be one of the two platforms
        self.assertIn(results[0], [platform_a_id, platform_b_id])


if __name__ == '__main__':
    unittest.main()