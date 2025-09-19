#!/usr/bin/env python3
"""Comprehensive tests for the extension registry manager."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from typing import Optional

from extension_registry_manager import ExtensionRegistryManager


class ExtensionRegistryTestCase(unittest.TestCase):
    """Base test case providing a fresh registry database."""

    def setUp(self) -> None:
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self._initialise_schema(self.db_path)
        self.manager = ExtensionRegistryManager(self.db_path)
        self._export_path: Optional[str] = None

    def tearDown(self) -> None:
        if self._export_path and os.path.exists(self._export_path):
            os.unlink(self._export_path)
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    @staticmethod
    def _initialise_schema(db_path: str) -> None:
        """Create the minimum schema required by the registry manager."""
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS file_type_category (
                category_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                sort_order INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS file_extension (
                extension TEXT PRIMARY KEY,
                category_id INTEGER NOT NULL REFERENCES file_type_category(category_id),
                description TEXT,
                is_active INTEGER DEFAULT 1,
                treat_as_archive INTEGER DEFAULT 0,
                treat_as_disc INTEGER DEFAULT 0,
                treat_as_auxiliary INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS platform (
                platform_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS platform_extension (
                platform_id INTEGER NOT NULL REFERENCES platform(platform_id),
                extension TEXT NOT NULL REFERENCES file_extension(extension),
                is_primary INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (platform_id, extension)
            )
            """
        )

        cursor.execute(
            """
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
            """
        )

        conn.commit()
        conn.close()

    def _create_platform(self, name: str) -> int:
        """Helper that inserts a platform directly into the database."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO platform (name) VALUES (?)", (name,))
        platform_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return platform_id


class TestExtensionRegistryCRUD(ExtensionRegistryTestCase):
    """CRUD style tests for categories, extensions, and mappings."""

    def test_category_and_extension_crud(self) -> None:
        """Verify category and extension lifecycle including derived flags."""
        category_id = self.manager.create_category("ROM", "Game ROM files", 1, True)
        self.assertGreater(category_id, 0)

        extension = self.manager.create_extension(
            ".nes",
            category_id,
            description="Nintendo Entertainment System ROM",
            is_active=True,
            treat_as_archive=False,
            treat_as_disc=False,
            treat_as_auxiliary=False,
        )
        self.assertEqual(extension, ".nes")

        record = self.manager.get_extension(".nes")
        self.assertIsNotNone(record)
        assert record is not None
        self.assertTrue(record["is_rom"])  # derived via compatibility shim
        self.assertFalse(record["treat_as_archive"])
        self.assertFalse(record["treat_as_disc"])
        self.assertFalse(record["treat_as_auxiliary"])

        updated = self.manager.update_extension(".nes", treat_as_disc=1)
        self.assertTrue(updated)
        record = self.manager.get_extension(".nes")
        assert record is not None
        self.assertTrue(record["treat_as_disc"])
        self.assertFalse(record["is_rom"])

        deleted = self.manager.delete_extension(".nes")
        self.assertTrue(deleted)
        record = self.manager.get_extension(".nes")
        assert record is not None
        self.assertFalse(record["is_active"])

    def test_platform_mapping_crud(self) -> None:
        """Ensure platform mappings honour the new composite key."""
        category_id = self.manager.create_category("ROM", "Game ROM files", 1, True)
        self.manager.create_extension(
            ".nes",
            category_id,
            description="Nintendo ROM",
            is_active=True,
        )
        platform_id = self._create_platform("NES")

        created = self.manager.create_platform_extension(platform_id, ".nes", is_primary=True)
        self.assertTrue(created)

        mappings = self.manager.get_platform_extensions(platform_id=platform_id)
        self.assertEqual(len(mappings), 1)
        mapping = mappings[0]
        self.assertEqual(mapping["extension"], ".nes")
        self.assertTrue(mapping["is_primary"])

        updated = self.manager.update_platform_extension(platform_id, ".nes", is_primary=False)
        self.assertTrue(updated)
        mapping = self.manager.get_platform_extensions(platform_id=platform_id)[0]
        self.assertFalse(mapping["is_primary"])

        deleted = self.manager.delete_platform_extension(platform_id, ".nes")
        self.assertTrue(deleted)
        self.assertFalse(self.manager.get_platform_extensions(platform_id=platform_id))

    def test_summary_counts_reflect_flags(self) -> None:
        """Summary output should align with treat_as_* semantics."""
        rom_id = self.manager.create_category("ROM", "Game ROM files", 1, True)
        archive_id = self.manager.create_category("Archive", "Compressed", 2, True)

        self.manager.create_extension(".nes", rom_id, "ROM", is_active=True)
        self.manager.create_extension(
            ".zip",
            archive_id,
            "Archive",
            treat_as_archive=True,
        )
        self.manager.create_extension(
            ".cue",
            rom_id,
            "Disc",
            treat_as_disc=True,
        )
        summary = self.manager.get_extension_registry_summary()

        self.assertEqual(summary["extensions"]["total_extensions"], 3)
        self.assertEqual(summary["extensions"]["rom_extensions"], 1)
        self.assertEqual(summary["extensions"]["archive_extensions"], 1)
        self.assertEqual(summary["extensions"]["disc_extensions"], 1)


class TestUnknownExtensionWorkflow(ExtensionRegistryTestCase):
    """Tests covering detection and unknown extension approval."""

    def test_detect_file_type_and_record_unknown(self) -> None:
        """Known extensions should be returned, unknown ones recorded."""
        category_id = self.manager.create_category("ROM", "Game ROM files", 1, True)
        self.manager.create_extension(".nes", category_id, "ROM")

        known = self.manager.detect_file_type("MegaGame.NES")
        self.assertIsNotNone(known)
        assert known is not None
        self.assertEqual(known["extension"], ".nes")

        unknown = self.manager.detect_file_type("demo.weird")
        self.assertIsNone(unknown)
        recorded = self.manager.get_unknown_extensions()
        self.assertEqual(len(recorded), 1)
        self.assertEqual(recorded[0]["extension"], ".weird")
        self.assertEqual(recorded[0]["file_count"], 1)

    def test_unknown_extension_approval(self) -> None:
        """Approving an unknown extension should create registry records."""
        category_id = self.manager.create_category("ROM", "Game ROM files", 1, True)
        platform_id = self._create_platform("NES")
        unknown_id = self.manager.record_unknown_extension(".mystery", 2)

        approved = self.manager.approve_unknown_extension(
            unknown_id,
            category_id=category_id,
            platform_id=platform_id,
            notes="Created during approval",
        )
        self.assertTrue(approved)

        extension = self.manager.get_extension(".mystery")
        self.assertIsNotNone(extension)
        assert extension is not None
        self.assertTrue(extension["is_active"])
        mappings = self.manager.get_platform_extensions(platform_id=platform_id)
        self.assertEqual(len(mappings), 1)
        self.assertEqual(mappings[0]["extension"], ".mystery")

        unknown_entries = self.manager.get_unknown_extensions(status="approved")
        self.assertEqual(len(unknown_entries), 1)
        self.assertEqual(unknown_entries[0]["notes"], "Created during approval")


class TestImportExportRoundTrip(ExtensionRegistryTestCase):
    """Validate import/export flows against the new schema."""

    def test_json_round_trip(self) -> None:
        """Export registry data to JSON and import into a fresh database."""
        rom_id = self.manager.create_category("ROM", "Game ROM files", 1, True)
        self.manager.create_extension(".nes", rom_id, "NES ROM")
        platform_id = self._create_platform("NES")
        self.manager.create_platform_extension(platform_id, ".nes", is_primary=True)
        self.manager.record_unknown_extension(".mystery", 1)

        export_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        export_file.close()
        self._export_path = export_file.name
        success = self.manager.export_extensions(self._export_path, "json")
        self.assertTrue(success)

        with open(self._export_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self.assertIn("extensions", payload)
        self.assertEqual(len(payload["extensions"]), 1)
        self.assertEqual(payload["extensions"][0]["extension"], ".nes")
        self.assertIn("mappings", payload)
        self.assertEqual(len(payload["mappings"]), 1)

        # Import into a new empty database
        other_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        other_db.close()
        self.addCleanup(lambda: os.path.exists(other_db.name) and os.unlink(other_db.name))
        self._initialise_schema(other_db.name)
        new_manager = ExtensionRegistryManager(other_db.name)

        results = new_manager.import_extensions(self._export_path, "json", overwrite=True)
        self.assertTrue(results["success"])
        self.assertEqual(len(new_manager.get_extensions()), 1)
        self.assertEqual(len(new_manager.get_platform_extensions()), 1)
        self.assertEqual(len(new_manager.get_unknown_extensions()), 1)

    def test_csv_export_structure(self) -> None:
        """Ensure CSV export writes headers expected by tooling."""
        rom_id = self.manager.create_category("ROM", "Game ROM files", 1, True)
        self.manager.create_extension(".nes", rom_id, "NES ROM")
        platform_id = self._create_platform("NES")
        self.manager.create_platform_extension(platform_id, ".nes", is_primary=True)

        export_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        export_file.close()
        self._export_path = export_file.name

        success = self.manager.export_extensions(self._export_path, "csv")
        self.assertTrue(success)

        with open(self._export_path, "r", encoding="utf-8") as handle:
            lines = [line.strip() for line in handle.readlines() if line.strip()]

        self.assertTrue(any(line.startswith('CATEGORIES') for line in lines))
        self.assertTrue(any(line.startswith('EXTENSIONS') for line in lines))
        self.assertTrue(any(line.startswith('PLATFORM MAPPINGS') for line in lines))
        self.assertTrue(any(line.startswith('UNKNOWN EXTENSIONS') for line in lines))


if __name__ == "__main__":  # pragma: no cover - allows standalone execution
    unittest.main()
