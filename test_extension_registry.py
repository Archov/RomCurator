#!/usr/bin/env python3
"""
Extension Registry Tests - Automated tests for CRUD operations and unknown extension handling

This module provides comprehensive tests for the extension registry system,
validating CRUD operations, persistence, and unknown extension handling.
"""

import unittest
import sqlite3
import tempfile
import os
from pathlib import Path
import sys

# Add the workspace to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from extension_registry_manager import ExtensionRegistryManager


class TestExtensionRegistryManager(unittest.TestCase):
    """Test cases for the ExtensionRegistryManager class."""
    
    def setUp(self):
        """Set up test database and manager."""
        # Create a temporary database file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # Create the database schema
        self.create_test_schema()
        
        # Initialize the manager
        self.manager = ExtensionRegistryManager(self.db_path)
    
    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def create_test_schema(self):
        """Create the database schema for testing."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Create the extension registry tables
            conn.execute("""
                CREATE TABLE file_type_category (
                    category_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    sort_order INTEGER DEFAULT 0,
                    is_active BOOLEAN NOT NULL DEFAULT 1
                )
            """)
            
            conn.execute("""
                CREATE TABLE file_extension (
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
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            
            conn.execute("""
                CREATE TABLE platform_extension (
                    platform_extension_id INTEGER PRIMARY KEY,
                    platform_id INTEGER NOT NULL,
                    extension_id INTEGER NOT NULL REFERENCES file_extension(extension_id),
                    is_primary BOOLEAN NOT NULL DEFAULT 0,
                    confidence REAL DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    UNIQUE(platform_id, extension_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE unknown_extension (
                    unknown_extension_id INTEGER PRIMARY KEY,
                    extension TEXT NOT NULL,
                    first_seen TEXT NOT NULL DEFAULT (datetime('now')),
                    last_seen TEXT NOT NULL DEFAULT (datetime('now')),
                    file_count INTEGER DEFAULT 1,
                    suggested_category_id INTEGER REFERENCES file_type_category(category_id),
                    suggested_platform_id INTEGER,
                    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'ignored')),
                    notes TEXT,
                    UNIQUE(extension)
                )
            """)
            
            # Create a test platform table
            conn.execute("""
                CREATE TABLE platform (
                    platform_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE
                )
            """)
            
            # Insert test platforms
            conn.execute("INSERT INTO platform (platform_id, name) VALUES (1, 'Nintendo Entertainment System')")
            conn.execute("INSERT INTO platform (platform_id, name) VALUES (2, 'Super Nintendo Entertainment System')")
            conn.execute("INSERT INTO platform (platform_id, name) VALUES (3, 'Sega Genesis')")
            
            conn.commit()
    
    def test_create_category(self):
        """Test creating a file type category."""
        category_id = self.manager.create_category(
            name="Test Category",
            description="A test category",
            sort_order=1,
            is_active=True
        )
        
        self.assertIsInstance(category_id, int)
        self.assertGreater(category_id, 0)
        
        # Verify the category was created
        category = self.manager.get_category(category_id)
        self.assertIsNotNone(category)
        self.assertEqual(category['name'], "Test Category")
        self.assertEqual(category['description'], "A test category")
        self.assertEqual(category['sort_order'], 1)
        self.assertTrue(category['is_active'])
    
    def test_get_categories(self):
        """Test retrieving categories."""
        # Create test categories
        cat1_id = self.manager.create_category("Category 1", "First category", 1, True)
        cat2_id = self.manager.create_category("Category 2", "Second category", 2, False)
        
        # Test getting all categories
        all_categories = self.manager.get_categories(active_only=False)
        self.assertEqual(len(all_categories), 2)
        
        # Test getting only active categories
        active_categories = self.manager.get_categories(active_only=True)
        self.assertEqual(len(active_categories), 1)
        self.assertEqual(active_categories[0]['name'], "Category 1")
    
    def test_update_category(self):
        """Test updating a category."""
        category_id = self.manager.create_category("Original Name", "Original description")
        
        # Update the category
        success = self.manager.update_category(
            category_id,
            name="Updated Name",
            description="Updated description",
            sort_order=5
        )
        
        self.assertTrue(success)
        
        # Verify the update
        category = self.manager.get_category(category_id)
        self.assertEqual(category['name'], "Updated Name")
        self.assertEqual(category['description'], "Updated description")
        self.assertEqual(category['sort_order'], 5)
    
    def test_create_extension(self):
        """Test creating a file extension."""
        # First create a category
        category_id = self.manager.create_category("ROM Files", "Game ROM files")
        
        # Create an extension
        extension_id = self.manager.create_extension(
            extension=".nes",
            category_id=category_id,
            description="Nintendo Entertainment System ROM",
            mime_type="application/x-nintendo-nes-rom",
            is_rom=True
        )
        
        self.assertIsInstance(extension_id, int)
        self.assertGreater(extension_id, 0)
        
        # Verify the extension was created
        extension = self.manager.get_extension(extension_id)
        self.assertIsNotNone(extension)
        self.assertEqual(extension['extension'], ".nes")
        self.assertEqual(extension['category_id'], category_id)
        self.assertTrue(extension['is_rom'])
    
    def test_get_extensions(self):
        """Test retrieving extensions with filtering."""
        # Create test data
        rom_cat_id = self.manager.create_category("ROM Files", "Game ROM files")
        archive_cat_id = self.manager.create_category("Archives", "Archive files")
        
        nes_id = self.manager.create_extension(".nes", rom_cat_id, is_rom=True)
        zip_id = self.manager.create_extension(".zip", archive_cat_id, is_archive=True)
        
        # Test getting all extensions
        all_extensions = self.manager.get_extensions()
        self.assertEqual(len(all_extensions), 2)
        
        # Test filtering by category
        rom_extensions = self.manager.get_extensions(category_id=rom_cat_id)
        self.assertEqual(len(rom_extensions), 1)
        self.assertEqual(rom_extensions[0]['extension'], ".nes")
        
        # Test filtering by type
        rom_type_extensions = self.manager.get_extensions(extension_type='rom')
        self.assertEqual(len(rom_type_extensions), 1)
        self.assertEqual(rom_type_extensions[0]['extension'], ".nes")
    
    def test_create_platform_extension(self):
        """Test creating platform-extension mappings."""
        # Create test data
        category_id = self.manager.create_category("ROM Files", "Game ROM files")
        extension_id = self.manager.create_extension(".nes", category_id, is_rom=True)
        
        # Create platform mapping
        mapping_id = self.manager.create_platform_extension(
            platform_id=1,  # NES platform
            extension_id=extension_id,
            is_primary=True,
            confidence=1.0
        )
        
        self.assertIsInstance(mapping_id, int)
        self.assertGreater(mapping_id, 0)
        
        # Verify the mapping was created
        mappings = self.manager.get_platform_extensions(platform_id=1)
        self.assertEqual(len(mappings), 1)
        self.assertEqual(mappings[0]['extension'], ".nes")
        self.assertTrue(mappings[0]['is_primary'])
    
    def test_record_unknown_extension(self):
        """Test recording unknown extensions."""
        # Record an unknown extension
        unknown_id = self.manager.record_unknown_extension(".unknown", 5)
        
        self.assertIsInstance(unknown_id, int)
        self.assertGreater(unknown_id, 0)
        
        # Verify it was recorded
        unknown_extensions = self.manager.get_unknown_extensions()
        self.assertEqual(len(unknown_extensions), 1)
        self.assertEqual(unknown_extensions[0]['extension'], ".unknown")
        self.assertEqual(unknown_extensions[0]['file_count'], 5)
        self.assertEqual(unknown_extensions[0]['status'], 'pending')
        
        # Record the same extension again (should update count)
        self.manager.record_unknown_extension(".unknown", 3)
        
        unknown_extensions = self.manager.get_unknown_extensions()
        self.assertEqual(len(unknown_extensions), 1)
        self.assertEqual(unknown_extensions[0]['file_count'], 8)  # 5 + 3
    
    def test_approve_unknown_extension(self):
        """Test approving an unknown extension."""
        # Create test data
        category_id = self.manager.create_category("ROM Files", "Game ROM files")
        unknown_id = self.manager.record_unknown_extension(".test", 10)
        
        # Approve the unknown extension
        success = self.manager.approve_unknown_extension(
            unknown_id, category_id, platform_id=1, notes="Test approval"
        )
        
        self.assertTrue(success)
        
        # Verify the extension was created
        extension = self.manager.get_extension_by_name(".test")
        self.assertIsNotNone(extension)
        self.assertEqual(extension['extension'], ".test")
        self.assertEqual(extension['category_id'], category_id)
        self.assertTrue(extension['is_rom'])
        
        # Verify the platform mapping was created
        mappings = self.manager.get_platform_extensions(platform_id=1)
        self.assertEqual(len(mappings), 1)
        self.assertEqual(mappings[0]['extension'], ".test")
        
        # Verify the unknown extension status was updated
        unknown_extensions = self.manager.get_unknown_extensions()
        self.assertEqual(unknown_extensions[0]['status'], 'approved')
    
    def test_reject_unknown_extension(self):
        """Test rejecting an unknown extension."""
        unknown_id = self.manager.record_unknown_extension(".reject", 1)
        
        # Reject the unknown extension
        success = self.manager.reject_unknown_extension(unknown_id, "Not a valid extension")
        
        self.assertTrue(success)
        
        # Verify the status was updated
        unknown_extensions = self.manager.get_unknown_extensions()
        self.assertEqual(unknown_extensions[0]['status'], 'rejected')
        self.assertEqual(unknown_extensions[0]['notes'], "Not a valid extension")
    
    def test_ignore_unknown_extension(self):
        """Test ignoring an unknown extension."""
        unknown_id = self.manager.record_unknown_extension(".ignore", 1)
        
        # Ignore the unknown extension
        success = self.manager.ignore_unknown_extension(unknown_id, "Not relevant")
        
        self.assertTrue(success)
        
        # Verify the status was updated
        unknown_extensions = self.manager.get_unknown_extensions()
        self.assertEqual(unknown_extensions[0]['status'], 'ignored')
        self.assertEqual(unknown_extensions[0]['notes'], "Not relevant")
    
    def test_detect_file_type(self):
        """Test file type detection."""
        # Create test extensions
        category_id = self.manager.create_category("ROM Files", "Game ROM files")
        self.manager.create_extension(".nes", category_id, is_rom=True)
        
        # Test known extension
        detected = self.manager.detect_file_type("game.nes")
        self.assertIsNotNone(detected)
        self.assertEqual(detected['extension'], ".nes")
        self.assertTrue(detected['is_rom'])
        
        # Test unknown extension
        detected = self.manager.detect_file_type("unknown.xyz")
        self.assertIsNone(detected)
        
        # Verify unknown extension was recorded
        unknown_extensions = self.manager.get_unknown_extensions()
        self.assertEqual(len(unknown_extensions), 1)
        self.assertEqual(unknown_extensions[0]['extension'], ".xyz")
    
    def test_get_extension_registry_summary(self):
        """Test getting extension registry summary."""
        # Create test data
        category_id = self.manager.create_category("ROM Files", "Game ROM files")
        extension_id = self.manager.create_extension(".nes", category_id, is_rom=True)
        self.manager.create_platform_extension(1, extension_id, is_primary=True)
        self.manager.record_unknown_extension(".unknown", 1)
        
        # Get summary
        summary = self.manager.get_extension_registry_summary()
        
        # Verify summary structure
        self.assertIn('categories', summary)
        self.assertIn('extensions', summary)
        self.assertIn('mappings', summary)
        self.assertIn('unknown', summary)
        
        # Verify counts
        self.assertEqual(summary['categories']['total_categories'], 1)
        self.assertEqual(summary['extensions']['total_extensions'], 1)
        self.assertEqual(summary['mappings']['total_mappings'], 1)
        self.assertEqual(summary['unknown']['total_unknown'], 1)
    
    def test_soft_delete(self):
        """Test soft delete functionality."""
        # Create test data
        category_id = self.manager.create_category("Test Category", "Test description")
        extension_id = self.manager.create_extension(".test", category_id)
        
        # Soft delete category
        success = self.manager.delete_category(category_id)
        self.assertTrue(success)
        
        # Verify category is marked as inactive
        category = self.manager.get_category(category_id)
        self.assertFalse(category['is_active'])
        
        # Soft delete extension
        success = self.manager.delete_extension(extension_id)
        self.assertTrue(success)
        
        # Verify extension is marked as inactive
        extension = self.manager.get_extension(extension_id)
        self.assertFalse(extension['is_active'])
    
    def test_foreign_key_constraints(self):
        """Test foreign key constraint enforcement."""
        # Try to create extension with non-existent category
        with self.assertRaises(sqlite3.IntegrityError):
            self.manager.create_extension(".test", 99999)  # Non-existent category_id
        
        # Try to create platform mapping with non-existent extension
        with self.assertRaises(sqlite3.IntegrityError):
            self.manager.create_platform_extension(1, 99999)  # Non-existent extension_id


class TestExtensionRegistryIntegration(unittest.TestCase):
    """Integration tests for the extension registry system."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # Create full schema
        self.create_full_schema()
        self.manager = ExtensionRegistryManager(self.db_path)
    
    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def create_full_schema(self):
        """Create the full database schema for integration testing."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Read and execute the full schema
            schema_file = Path(__file__).parent / "Rom Curator Database.sql"
            if schema_file.exists():
                with open(schema_file, 'r', encoding='utf-8') as f:
                    schema_sql = f.read()
                conn.executescript(schema_sql)
            else:
                # Fallback: create minimal schema
                conn.execute("""
                    CREATE TABLE platform (
                        platform_id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE
                    )
                """)
                conn.execute("""
                    CREATE TABLE file_type_category (
                        category_id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        description TEXT,
                        sort_order INTEGER DEFAULT 0,
                        is_active BOOLEAN NOT NULL DEFAULT 1
                    )
                """)
                conn.execute("""
                    CREATE TABLE file_extension (
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
                        created_at TEXT NOT NULL DEFAULT (datetime('now')),
                        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                    )
                """)
                conn.execute("""
                    CREATE TABLE platform_extension (
                        platform_extension_id INTEGER PRIMARY KEY,
                        platform_id INTEGER NOT NULL REFERENCES platform(platform_id),
                        extension_id INTEGER NOT NULL REFERENCES file_extension(extension_id),
                        is_primary BOOLEAN NOT NULL DEFAULT 0,
                        confidence REAL DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
                        created_at TEXT NOT NULL DEFAULT (datetime('now')),
                        UNIQUE(platform_id, extension_id)
                    )
                """)
                conn.execute("""
                    CREATE TABLE unknown_extension (
                        unknown_extension_id INTEGER PRIMARY KEY,
                        extension TEXT NOT NULL,
                        first_seen TEXT NOT NULL DEFAULT (datetime('now')),
                        last_seen TEXT NOT NULL DEFAULT (datetime('now')),
                        file_count INTEGER DEFAULT 1,
                        suggested_category_id INTEGER REFERENCES file_type_category(category_id),
                        suggested_platform_id INTEGER REFERENCES platform(platform_id),
                        status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'ignored')),
                        notes TEXT,
                        UNIQUE(extension)
                    )
                """)
            
            # Insert test platforms
            conn.execute("INSERT INTO platform (platform_id, name) VALUES (1, 'Nintendo Entertainment System')")
            conn.execute("INSERT INTO platform (platform_id, name) VALUES (2, 'Super Nintendo Entertainment System')")
            conn.execute("INSERT INTO platform (platform_id, name) VALUES (3, 'Sega Genesis')")
            
            conn.commit()
    
    def test_full_workflow(self):
        """Test a complete workflow from unknown extension to approved extension."""
        # Step 1: Record unknown extensions
        unknown1_id = self.manager.record_unknown_extension(".newrom", 15)
        unknown2_id = self.manager.record_unknown_extension(".badfile", 2)
        
        # Step 2: Create categories
        rom_cat_id = self.manager.create_category("ROM Files", "Game ROM files")
        archive_cat_id = self.manager.create_category("Archives", "Archive files")
        
        # Step 3: Approve the first unknown extension
        success = self.manager.approve_unknown_extension(
            unknown1_id, rom_cat_id, platform_id=1, notes="New ROM format"
        )
        self.assertTrue(success)
        
        # Step 4: Reject the second unknown extension
        success = self.manager.reject_unknown_extension(unknown2_id, "Not a valid ROM format")
        self.assertTrue(success)
        
        # Step 5: Verify the results
        unknown_extensions = self.manager.get_unknown_extensions()
        self.assertEqual(len(unknown_extensions), 2)
        
        approved = [ue for ue in unknown_extensions if ue['status'] == 'approved']
        rejected = [ue for ue in unknown_extensions if ue['status'] == 'rejected']
        
        self.assertEqual(len(approved), 1)
        self.assertEqual(len(rejected), 1)
        self.assertEqual(approved[0]['extension'], ".newrom")
        self.assertEqual(rejected[0]['extension'], ".badfile")
        
        # Step 6: Verify the approved extension was created
        extension = self.manager.get_extension_by_name(".newrom")
        self.assertIsNotNone(extension)
        self.assertTrue(extension['is_rom'])
        
        # Step 7: Verify platform mapping was created
        mappings = self.manager.get_platform_extensions(platform_id=1)
        self.assertEqual(len(mappings), 1)
        self.assertEqual(mappings[0]['extension'], ".newrom")
        self.assertTrue(mappings[0]['is_primary'])
        
        # Step 8: Test file type detection
        detected = self.manager.detect_file_type("game.newrom")
        self.assertIsNotNone(detected)
        self.assertEqual(detected['extension'], ".newrom")
    
    def test_bulk_operations(self):
        """Test bulk operations and performance."""
        # Create categories
        rom_cat_id = self.manager.create_category("ROM Files", "Game ROM files")
        archive_cat_id = self.manager.create_category("Archives", "Archive files")
        
        # Create many extensions
        extensions = [".nes", ".snes", ".gen", ".psx", ".n64", ".gba", ".nds", ".3ds"]
        extension_ids = []
        
        for ext in extensions:
            ext_id = self.manager.create_extension(ext, rom_cat_id, is_rom=True)
            extension_ids.append(ext_id)
        
        # Create platform mappings
        for i, ext_id in enumerate(extension_ids):
            platform_id = (i % 3) + 1  # Distribute across platforms 1, 2, 3
            self.manager.create_platform_extension(platform_id, ext_id, is_primary=(i < 3))
        
        # Verify all extensions were created
        all_extensions = self.manager.get_extensions()
        self.assertEqual(len(all_extensions), len(extensions))
        
        # Verify platform mappings were created
        all_mappings = self.manager.get_platform_extensions()
        self.assertEqual(len(all_mappings), len(extensions))
        
        # Test filtering
        rom_extensions = self.manager.get_extensions(extension_type='rom')
        self.assertEqual(len(rom_extensions), len(extensions))
        
        # Test platform-specific extensions
        platform1_extensions = self.manager.get_extensions_for_platform(1)
        self.assertGreater(len(platform1_extensions), 0)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)