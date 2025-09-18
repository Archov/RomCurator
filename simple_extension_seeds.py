#!/usr/bin/env python3
"""
Simple Extension Seeds - Populate database with basic extension data
"""

import sqlite3
from pathlib import Path

def apply_simple_seeds(db_path: str):
    """Apply simple extension registry seed data."""
    
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Insert categories
            categories = [
                (1, 'ROM Files', 'Game ROM files and executables', 1, 1),
                (2, 'Archive Files', 'Compressed archives containing ROMs', 2, 1),
                (3, 'Save Files', 'Game save states and memory cards', 3, 1),
                (4, 'Patch Files', 'ROM patches and modifications', 4, 1),
                (5, 'Documentation', 'Game manuals, guides, and documentation', 5, 1),
                (6, 'Media Files', 'Images, videos, and audio files', 6, 1),
                (7, 'System Files', 'Emulator and system configuration files', 7, 1),
                (8, 'Unknown', 'Unrecognized or unknown file types', 99, 1)
            ]
            
            for cat in categories:
                conn.execute("""
                    INSERT OR IGNORE INTO file_type_category 
                    (category_id, name, description, sort_order, is_active)
                    VALUES (?, ?, ?, ?, ?)
                """, cat)
            
            # Insert some basic ROM extensions
            rom_extensions = [
                ('.nes', 1, 'Nintendo Entertainment System ROM', 'application/x-nintendo-nes-rom', 1, 0, 1, 0, 0),
                ('.sfc', 1, 'Super Nintendo ROM', 'application/x-snes-rom', 1, 0, 1, 0, 0),
                ('.smc', 1, 'Super Nintendo ROM (alternative)', 'application/x-snes-rom', 1, 0, 1, 0, 0),
                ('.gb', 1, 'Game Boy ROM', 'application/x-gameboy-rom', 1, 0, 1, 0, 0),
                ('.gbc', 1, 'Game Boy Color ROM', 'application/x-gameboy-color-rom', 1, 0, 1, 0, 0),
                ('.gba', 1, 'Game Boy Advance ROM', 'application/x-gba-rom', 1, 0, 1, 0, 0),
                ('.nds', 1, 'Nintendo DS ROM', 'application/x-nintendo-ds-rom', 1, 0, 1, 0, 0),
                ('.n64', 1, 'Nintendo 64 ROM', 'application/x-n64-rom', 1, 0, 1, 0, 0),
                ('.md', 1, 'Sega Genesis/Mega Drive ROM', 'application/x-genesis-rom', 1, 0, 1, 0, 0),
                ('.gen', 1, 'Sega Genesis ROM (alternative)', 'application/x-genesis-rom', 1, 0, 1, 0, 0),
                ('.smd', 1, 'Sega Genesis ROM (SMD format)', 'application/x-genesis-rom', 1, 0, 1, 0, 0),
                ('.psx', 1, 'PlayStation ROM', 'application/x-psx-rom', 1, 0, 1, 0, 0),
                ('.ps1', 1, 'PlayStation ROM (alternative)', 'application/x-psx-rom', 1, 0, 1, 0, 0),
                ('.iso', 1, 'ISO image', 'application/x-iso9660-image', 1, 0, 1, 0, 0),
                ('.bin', 1, 'Generic binary ROM', 'application/x-rom', 1, 0, 1, 0, 0),
                ('.rom', 1, 'Generic ROM file', 'application/x-rom', 1, 0, 1, 0, 0)
            ]
            
            for ext in rom_extensions:
                conn.execute("""
                    INSERT OR IGNORE INTO file_extension 
                    (extension, category_id, description, mime_type, is_active, is_archive, is_rom, is_save, is_patch)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, ext)
            
            # Insert some archive extensions
            archive_extensions = [
                ('.zip', 2, 'ZIP archive', 'application/zip', 1, 1, 0, 0, 0),
                ('.7z', 2, '7-Zip archive', 'application/x-7z-compressed', 1, 1, 0, 0, 0),
                ('.rar', 2, 'RAR archive', 'application/x-rar-compressed', 1, 1, 0, 0, 0),
                ('.tar', 2, 'TAR archive', 'application/x-tar', 1, 1, 0, 0, 0),
                ('.gz', 2, 'GZIP compressed file', 'application/gzip', 1, 1, 0, 0, 0)
            ]
            
            for ext in archive_extensions:
                conn.execute("""
                    INSERT OR IGNORE INTO file_extension 
                    (extension, category_id, description, mime_type, is_active, is_archive, is_rom, is_save, is_patch)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, ext)
            
            # Insert some save file extensions
            save_extensions = [
                ('.sav', 3, 'Generic save file', 'application/x-save', 1, 0, 0, 1, 0),
                ('.srm', 3, 'SNES save file', 'application/x-snes-save', 1, 0, 0, 1, 0),
                ('.eep', 3, 'EEPROM save file', 'application/x-eeprom-save', 1, 0, 0, 1, 0),
                ('.state', 3, 'Emulator save state', 'application/x-save-state', 1, 0, 0, 1, 0)
            ]
            
            for ext in save_extensions:
                conn.execute("""
                    INSERT OR IGNORE INTO file_extension 
                    (extension, category_id, description, mime_type, is_active, is_archive, is_rom, is_save, is_patch)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, ext)
            
            # Insert some patch file extensions
            patch_extensions = [
                ('.ips', 4, 'IPS patch file', 'application/x-ips-patch', 1, 0, 0, 0, 1),
                ('.bps', 4, 'BPS patch file', 'application/x-bps-patch', 1, 0, 0, 0, 1),
                ('.ups', 4, 'UPS patch file', 'application/x-ups-patch', 1, 0, 0, 0, 1),
                ('.xdelta', 4, 'XDelta patch file', 'application/x-xdelta-patch', 1, 0, 0, 0, 1)
            ]
            
            for ext in patch_extensions:
                conn.execute("""
                    INSERT OR IGNORE INTO file_extension 
                    (extension, category_id, description, mime_type, is_active, is_archive, is_rom, is_save, is_patch)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, ext)
            
            conn.commit()
            print("Extension registry seeds applied successfully!")
            
            # Show summary
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM file_type_category")
            cat_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM file_extension")
            ext_count = cursor.fetchone()[0]
            
            print(f"Created {cat_count} categories and {ext_count} extensions")
            
            return True
            
    except Exception as e:
        print(f"Error applying seeds: {e}")
        return False

def main():
    """Main function."""
    db_path = "database/RomCurator.db"
    
    if not Path(db_path).exists():
        print(f"Error: Database file not found: {db_path}")
        return 1
    
    success = apply_simple_seeds(db_path)
    return 0 if success else 1

if __name__ == '__main__':
    import sys
    sys.exit(main())