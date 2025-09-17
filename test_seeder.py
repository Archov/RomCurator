#!/usr/bin/env python3
"""
Test Seeder Script

Reads a seed configuration file and runs specified importers on specific files.
This makes testing individual importers and new features much easier.
"""

import json
import os
import sys
import sqlite3
import importlib.util
from pathlib import Path
from typing import Dict, List, Any
import logging

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from scripts.seeders.base_importer import BaseImporter
from scripts.seeders.mobygames import MobyGamesImporter
from scripts.seeders.tosec import TosecImporter
from scripts.seeders.no_intro import NoIntroImporter

class TestSeeder:
    """Test seeder that runs importers based on configuration."""
    
    def __init__(self, config_path: str, recreate_db: bool = False):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.logger = self._setup_logging()
        self.recreate_db = recreate_db
        
    def _load_config(self) -> Dict[str, Any]:
        """Load the seed configuration file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
            
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the test seeder."""
        logger = logging.getLogger('test_seeder')
        logger.setLevel(logging.DEBUG if self.config.get('options', {}).get('verbose_logging', False) else logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logger.level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def _get_importer(self, importer_type: str, db_path: str) -> BaseImporter:
        """Get the appropriate importer instance."""
        importer_map = {
            'mobygames': MobyGamesImporter,
            'nointro': NoIntroImporter,
            'tosec': TosecImporter
        }
        
        if importer_type not in importer_map:
            raise ValueError(f"Unknown importer type: {importer_type}")
            
        return importer_map[importer_type](db_path)
    
    def _recreate_database(self):
        """Recreate the database from scratch."""
        if not self.recreate_db:
            return
            
        db_path = self.config['database_path']
        self.logger.info(f"Recreating database: {db_path}")
        
        # Remove existing database
        if Path(db_path).exists():
            Path(db_path).unlink()
            self.logger.info("Removed existing database")
        
        # Create fresh database with current schema
        schema_file = "Rom Curator Database.sql"
        if not Path(schema_file).exists():
            self.logger.error(f"Schema file not found: {schema_file}")
            return False
            
        self.logger.info(f"Creating fresh database with schema: {schema_file}")
        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            with sqlite3.connect(db_path) as conn:
                conn.executescript(schema_sql)
                conn.commit()
            
            self.logger.info("✓ Database recreated successfully")
            
            # Seed with basic data (metadata_source, platforms, etc.)
            self.logger.info("Seeding database with basic data...")
            self._seed_basic_data(db_path)
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to recreate database: {e}")
            return False
    
    def _seed_basic_data(self, db_path: str):
        """Seed the database with basic required data."""
        try:
            # Run the fast reseed script to populate basic data
            import subprocess
            result = subprocess.run([
                "powershell", "-ExecutionPolicy", "Bypass", "-File", 
                "fast_reseed_database.ps1", "-DatabasePath", db_path
            ], capture_output=True, text=True, cwd=".")
            
            if result.returncode == 0:
                self.logger.info("✓ Basic data seeded successfully")
            else:
                self.logger.warning(f"Basic seeding had issues: {result.stderr}")
                # Fallback: manually insert essential data
                self._insert_essential_data(db_path)
        except Exception as e:
            self.logger.warning(f"Failed to run fast reseed script: {e}")
            # Fallback: manually insert essential data
            self._insert_essential_data(db_path)
    
    def _insert_essential_data(self, db_path: str):
        """Insert essential data manually as fallback."""
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Insert metadata sources
                cursor.execute("""
                    INSERT OR IGNORE INTO metadata_source (source_id, name, importer_script, schema_file_path) 
                    VALUES 
                    (1, 'No-Intro', 'scripts/seeders/no_intro.py', NULL),
                    (2, 'MobyGames', 'scripts/seeders/mobygames.py', 'seed-data/Moby/MobyGames.Schema.json'),
                    (3, 'TOSEC', 'scripts/seeders/tosec.py', 'seed-data/TOSEC/schema/TOSEC.dtd')
                """)
                
                # Insert some basic platforms
                cursor.execute("""
                    INSERT OR IGNORE INTO platform (platform_id, name) 
                    VALUES 
                    (33, 'Nintendo Entertainment System'),
                    (34, 'Super Nintendo Entertainment System')
                """)
                
                conn.commit()
                self.logger.info("✓ Essential data inserted manually")
        except Exception as e:
            self.logger.error(f"Failed to insert essential data: {e}")
    
    def _get_source_id(self, importer_type: str) -> int:
        """Get the source_id for the given importer type."""
        source_mapping = {
            'mobygames': 'MobyGames',
            'nointro': 'No-Intro',
            'tosec': 'TOSEC'
        }
        
        source_name = source_mapping.get(importer_type)
        if not source_name:
            return None
        
        db_path = self.config['database_path']
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT source_id FROM metadata_source WHERE name = ?", (source_name,))
            row = cursor.fetchone()
            return row[0] if row else None
    
    def _clear_existing_data(self):
        """Clear existing data if requested."""
        if not self.config.get('options', {}).get('clear_existing_data', False):
            return
            
        db_path = self.config['database_path']
        self.logger.info(f"Clearing existing data from {db_path}")
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Clear DAT-related tables
            tables_to_clear = [
                'dat_entry', 'dat_entry_regions', 'dat_platform',
                'import_log', 'import_session'
            ]
            
            for table in tables_to_clear:
                try:
                    cursor.execute(f"DELETE FROM {table}")
                    self.logger.info(f"Cleared table: {table}")
                except sqlite3.OperationalError as e:
                    if "no such table" not in str(e).lower():
                        self.logger.warning(f"Could not clear {table}: {e}")
            
            conn.commit()
    
    def _run_import(self, import_config: Dict[str, Any]) -> bool:
        """Run a single import operation."""
        name = import_config['name']
        importer_type = import_config['importer']
        file_path = Path(import_config['file_path'])
        platform_name = import_config.get('platform_name', 'Unknown Platform')
        
        self.logger.info(f"Starting import: {name}")
        self.logger.info(f"  Type: {importer_type}")
        self.logger.info(f"  File: {file_path}")
        self.logger.info(f"  Platform: {platform_name}")
        
        if not file_path.exists():
            self.logger.error(f"File not found: {file_path}")
            return False
        
        if self.config.get('options', {}).get('dry_run', False):
            self.logger.info("DRY RUN - Would import this file")
            return True
        
        try:
            importer = self._get_importer(importer_type, self.config['database_path'])
            
            # Create a mock args object for the importer
            class MockArgs:
                def __init__(self, source_id, files):
                    self.source_id = source_id
                    self.files = files
            
            # Get source_id for the importer type
            source_id = self._get_source_id(importer_type)
            if source_id is None:
                self.logger.error(f"Could not find source_id for {importer_type}")
                return False
            
            args = MockArgs(source_id, [str(file_path)])
            
            # Run the import
            importer.run(args)
            
            self.logger.info(f"✅ Import successful: {name}")
            return True
                
        except Exception as e:
            self.logger.error(f"❌ Import error for {name}: {e}")
            return False
    
    def run(self) -> bool:
        """Run all imports specified in the configuration."""
        self.logger.info(f"Starting test seeder: {self.config['name']}")
        self.logger.info(f"Description: {self.config.get('description', 'No description')}")
        
        # Recreate database if requested
        if self.recreate_db:
            if not self._recreate_database():
                self.logger.error("Failed to recreate database, aborting")
                return False
        else:
            # Clear existing data if requested
            self._clear_existing_data()
        
        # Run each import
        imports = self.config.get('imports', [])
        if not imports:
            self.logger.warning("No imports specified in configuration")
            return True
        
        success_count = 0
        total_count = len(imports)
        
        for i, import_config in enumerate(imports, 1):
            self.logger.info(f"\n--- Import {i}/{total_count} ---")
            if self._run_import(import_config):
                success_count += 1
        
        self.logger.info(f"\n=== Import Summary ===")
        self.logger.info(f"Successful: {success_count}/{total_count}")
        self.logger.info(f"Failed: {total_count - success_count}/{total_count}")
        
        return success_count == total_count

def main():
    """Main entry point."""
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python test_seeder.py <config_file> [--recreate-db]")
        print("Example: python test_seeder.py seed-config.json")
        print("Example: python test_seeder.py seed-config.json --recreate-db")
        sys.exit(1)
    
    config_file = sys.argv[1]
    recreate_db = len(sys.argv) == 3 and sys.argv[2] == '--recreate-db'
    
    try:
        seeder = TestSeeder(config_file, recreate_db)
        success = seeder.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
