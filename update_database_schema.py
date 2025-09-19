#!/usr/bin/env python3
"""
Update Database Schema - Apply schema updates to existing database
"""

import sqlite3
import sys
from pathlib import Path

def update_schema(db_path: str):
    """Update the database schema to include extension registry tables."""
    
    # Read the updated schema
    schema_file = Path(__file__).parent / "Rom Curator Database.sql"
    
    if not schema_file.exists():
        print(f"Error: Schema file not found: {schema_file}")
        return False
    
    try:
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        # Connect to database and apply schema updates
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Extract only the extension registry section
            start_marker = "-- ============================================================================="
            end_marker = "-- INGESTION FOUNDATION VIEWS (New in v1.9)"
            
            start_idx = schema_sql.find("-- EXTENSION REGISTRY TABLES (New in v1.10)")
            if start_idx == -1:
                print("Error: Extension registry section not found in schema file")
                return False
            
            # Find the end of the extension registry section
            end_idx = schema_sql.find(end_marker, start_idx)
            if end_idx == -1:
                # If not found, take everything from start to end of file
                end_idx = len(schema_sql)
            
            extension_sql = schema_sql[start_idx:end_idx]
            
            # Split into statements and execute
            statements = [stmt.strip() for stmt in extension_sql.split(';') if stmt.strip() and not stmt.strip().startswith('--')]
            
            for statement in statements:
                try:
                    conn.execute(statement)
                    print(f"Executed: {statement[:50]}...")
                except sqlite3.OperationalError as e:
                    if "already exists" in str(e):
                        print(f"Skipped (already exists): {statement[:50]}...")
                    else:
                        print(f"Error executing: {statement[:50]}...")
                        print(f"  Error: {e}")
                        return False
            
            conn.commit()
            print("Database schema updated successfully!")
            return True
            
    except Exception as e:
        print(f"Error updating schema: {e}")
        return False

def main():
    """Main function."""
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = "database/RomCurator.db"
    
    if not Path(db_path).exists():
        print(f"Error: Database file not found: {db_path}")
        print("Please create the database first using the schema creation script.")
        return 1
    
    success = update_schema(db_path)
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())