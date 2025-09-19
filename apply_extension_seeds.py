#!/usr/bin/env python3
"""
Apply Extension Registry Seeds - Python script to populate the database with default extensions
"""

import sqlite3
import sys
from pathlib import Path

def apply_seeds(db_path: str):
    """Apply the extension registry seed data to the database."""
    
    # Read the seed script
    seed_file = Path(__file__).parent / "seed-scripts" / "10_extension_registry_seeds.sql"
    
    if not seed_file.exists():
        print(f"Error: Seed file not found: {seed_file}")
        return False
    
    try:
        with open(seed_file, 'r', encoding='utf-8') as f:
            seed_sql = f.read()
        
        # Connect to database and apply seeds
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Split the SQL into individual statements and execute them
            statements = [stmt.strip() for stmt in seed_sql.split(';') if stmt.strip()]
            
            for statement in statements:
                if statement.upper().startswith('SELECT'):
                    # Execute SELECT statements and print results
                    cursor = conn.execute(statement)
                    results = cursor.fetchall()
                    if results:
                        print(f"Query: {statement[:50]}...")
                        for row in results:
                            print(f"  {row}")
                        print()
                else:
                    # Execute other statements
                    conn.execute(statement)
            
            conn.commit()
            print("Extension registry seeds applied successfully!")
            return True
            
    except Exception as e:
        print(f"Error applying seeds: {e}")
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
    
    success = apply_seeds(db_path)
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())