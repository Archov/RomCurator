#!/usr/bin/env python3
"""
Extension Registry Manager - CRUD operations for file extensions and platform mappings

This module provides comprehensive CRUD operations for the extension registry system,
including file type categories, file extensions, platform mappings, and unknown extension handling.
"""

import sqlite3
import logging
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path


class ExtensionRegistryManager:
    """Manages file extensions, categories, and platform mappings."""
    
    def __init__(self, db_path: str):
        """Initialize the extension registry manager."""
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with proper settings."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    # =============================================================================
    # FILE TYPE CATEGORY OPERATIONS
    # =============================================================================
    
    def create_category(self, name: str, description: str = None, sort_order: int = 0, is_active: bool = True) -> int:
        """Create a new file type category."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO file_type_category (name, description, sort_order, is_active)
                VALUES (?, ?, ?, ?)
            """, (name, description, sort_order, is_active))
            category_id = cursor.lastrowid
            conn.commit()
            
            self.logger.info(f"Created file type category: {name} (ID: {category_id})")
            return category_id
    
    def get_categories(self, active_only: bool = True) -> List[Dict]:
        """Get all file type categories."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM file_type_category"
            params = []
            
            if active_only:
                query += " WHERE is_active = 1"
            
            query += " ORDER BY sort_order, name"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_category(self, category_id: int) -> Optional[Dict]:
        """Get a specific file type category."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM file_type_category WHERE category_id = ?", (category_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_category(self, category_id: int, **kwargs) -> bool:
        """Update a file type category."""
        if not kwargs:
            return False
            
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Build dynamic update query
            set_clauses = []
            params = []
            
            for key, value in kwargs.items():
                if key in ['name', 'description', 'sort_order', 'is_active']:
                    set_clauses.append(f"{key} = ?")
                    params.append(value)
            
            if not set_clauses:
                return False
            
            params.append(category_id)
            query = f"UPDATE file_type_category SET {', '.join(set_clauses)} WHERE category_id = ?"
            
            cursor.execute(query, params)
            conn.commit()
            
            self.logger.info(f"Updated file type category ID {category_id}")
            return cursor.rowcount > 0
    
    def delete_category(self, category_id: int) -> bool:
        """Delete a file type category (soft delete by setting is_active = 0)."""
        return self.update_category(category_id, is_active=False)
    
    # =============================================================================
    # FILE EXTENSION OPERATIONS
    # =============================================================================
    
    def create_extension(self, extension: str, category_id: int, description: str = None, 
                        mime_type: str = None, is_active: bool = True, is_archive: bool = False,
                        is_rom: bool = False, is_save: bool = False, is_patch: bool = False) -> int:
        """Create a new file extension."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO file_extension 
                (extension, category_id, description, mime_type, is_active, is_archive, is_rom, is_save, is_patch)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (extension, category_id, description, mime_type, is_active, 
                  is_archive, is_rom, is_save, is_patch))
            extension_id = cursor.lastrowid
            conn.commit()
            
            self.logger.info(f"Created file extension: {extension} (ID: {extension_id})")
            return extension_id
    
    def get_extensions(self, category_id: int = None, active_only: bool = True, 
                      extension_type: str = None) -> List[Dict]:
        """Get file extensions with optional filtering."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT fe.*, ftc.name as category_name, ftc.description as category_description
                FROM file_extension fe
                JOIN file_type_category ftc ON fe.category_id = ftc.category_id
                WHERE 1=1
            """
            params = []
            
            if active_only:
                query += " AND fe.is_active = 1"
            
            if category_id:
                query += " AND fe.category_id = ?"
                params.append(category_id)
            
            if extension_type:
                if extension_type == 'rom':
                    query += " AND fe.is_rom = 1"
                elif extension_type == 'archive':
                    query += " AND fe.is_archive = 1"
                elif extension_type == 'save':
                    query += " AND fe.is_save = 1"
                elif extension_type == 'patch':
                    query += " AND fe.is_patch = 1"
            
            query += " ORDER BY ftc.sort_order, ftc.name, fe.extension"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_extension(self, extension_id: int) -> Optional[Dict]:
        """Get a specific file extension."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT fe.*, ftc.name as category_name, ftc.description as category_description
                FROM file_extension fe
                JOIN file_type_category ftc ON fe.category_id = ftc.category_id
                WHERE fe.extension_id = ?
            """, (extension_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_extension_by_name(self, extension: str) -> Optional[Dict]:
        """Get a file extension by its name (e.g., '.rom')."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT fe.*, ftc.name as category_name, ftc.description as category_description
                FROM file_extension fe
                JOIN file_type_category ftc ON fe.category_id = ftc.category_id
                WHERE fe.extension = ?
            """, (extension,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_extension(self, extension_id: int, **kwargs) -> bool:
        """Update a file extension."""
        if not kwargs:
            return False
            
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Build dynamic update query
            set_clauses = []
            params = []
            
            for key, value in kwargs.items():
                if key in ['extension', 'category_id', 'description', 'mime_type', 
                          'is_active', 'is_archive', 'is_rom', 'is_save', 'is_patch']:
                    set_clauses.append(f"{key} = ?")
                    params.append(value)
            
            if not set_clauses:
                return False
            
            # Add updated_at timestamp
            set_clauses.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            
            params.append(extension_id)
            query = f"UPDATE file_extension SET {', '.join(set_clauses)} WHERE extension_id = ?"
            
            cursor.execute(query, params)
            conn.commit()
            
            self.logger.info(f"Updated file extension ID {extension_id}")
            return cursor.rowcount > 0
    
    def delete_extension(self, extension_id: int) -> bool:
        """Delete a file extension (soft delete by setting is_active = 0)."""
        return self.update_extension(extension_id, is_active=False)
    
    # =============================================================================
    # PLATFORM EXTENSION MAPPING OPERATIONS
    # =============================================================================
    
    def create_platform_extension(self, platform_id: int, extension_id: int, 
                                 is_primary: bool = False, confidence: float = 1.0) -> int:
        """Create a platform-extension mapping."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO platform_extension 
                (platform_id, extension_id, is_primary, confidence)
                VALUES (?, ?, ?, ?)
            """, (platform_id, extension_id, is_primary, confidence))
            mapping_id = cursor.lastrowid
            conn.commit()
            
            self.logger.info(f"Created platform-extension mapping: Platform {platform_id} -> Extension {extension_id}")
            return mapping_id
    
    def get_platform_extensions(self, platform_id: int = None, extension_id: int = None) -> List[Dict]:
        """Get platform-extension mappings."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT pe.*, p.name as platform_name, fe.extension, fe.description as extension_description,
                       ftc.name as category_name
                FROM platform_extension pe
                JOIN platform p ON pe.platform_id = p.platform_id
                JOIN file_extension fe ON pe.extension_id = fe.extension_id
                JOIN file_type_category ftc ON fe.category_id = ftc.category_id
                WHERE 1=1
            """
            params = []
            
            if platform_id:
                query += " AND pe.platform_id = ?"
                params.append(platform_id)
            
            if extension_id:
                query += " AND pe.extension_id = ?"
                params.append(extension_id)
            
            query += " ORDER BY p.name, pe.is_primary DESC, fe.extension"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def update_platform_extension(self, platform_extension_id: int, **kwargs) -> bool:
        """Update a platform-extension mapping."""
        if not kwargs:
            return False
            
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Build dynamic update query
            set_clauses = []
            params = []
            
            for key, value in kwargs.items():
                if key in ['is_primary', 'confidence']:
                    set_clauses.append(f"{key} = ?")
                    params.append(value)
            
            if not set_clauses:
                return False
            
            params.append(platform_extension_id)
            query = f"UPDATE platform_extension SET {', '.join(set_clauses)} WHERE platform_extension_id = ?"
            
            cursor.execute(query, params)
            conn.commit()
            
            self.logger.info(f"Updated platform-extension mapping ID {platform_extension_id}")
            return cursor.rowcount > 0
    
    def delete_platform_extension(self, platform_extension_id: int) -> bool:
        """Delete a platform-extension mapping."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM platform_extension WHERE platform_extension_id = ?", 
                         (platform_extension_id,))
            conn.commit()
            
            self.logger.info(f"Deleted platform-extension mapping ID {platform_extension_id}")
            return cursor.rowcount > 0
    
    # =============================================================================
    # UNKNOWN EXTENSION OPERATIONS
    # =============================================================================
    
    def record_unknown_extension(self, extension: str, file_count: int = 1) -> int:
        """Record or update an unknown extension discovery."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if extension already exists
            cursor.execute("SELECT unknown_extension_id, file_count FROM unknown_extension WHERE extension = ?", 
                         (extension,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record
                new_count = existing['file_count'] + file_count
                cursor.execute("""
                    UPDATE unknown_extension 
                    SET file_count = ?, last_seen = ?
                    WHERE extension = ?
                """, (new_count, datetime.now().isoformat(), extension))
                conn.commit()
                
                self.logger.info(f"Updated unknown extension: {extension} (count: {new_count})")
                return existing['unknown_extension_id']
            else:
                # Create new record
                cursor.execute("""
                    INSERT INTO unknown_extension (extension, file_count)
                    VALUES (?, ?)
                """, (extension, file_count))
                unknown_id = cursor.lastrowid
                conn.commit()
                
                self.logger.info(f"Recorded new unknown extension: {extension} (count: {file_count})")
                return unknown_id
    
    def get_unknown_extensions(self, status: str = None) -> List[Dict]:
        """Get unknown extensions with optional status filtering."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT ue.*, ftc.name as suggested_category, p.name as suggested_platform
                FROM unknown_extension ue
                LEFT JOIN file_type_category ftc ON ue.suggested_category_id = ftc.category_id
                LEFT JOIN platform p ON ue.suggested_platform_id = p.platform_id
                WHERE 1=1
            """
            params = []
            
            if status:
                query += " AND ue.status = ?"
                params.append(status)
            
            query += " ORDER BY ue.file_count DESC, ue.first_seen DESC"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def update_unknown_extension(self, unknown_extension_id: int, **kwargs) -> bool:
        """Update an unknown extension record."""
        if not kwargs:
            return False
            
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Build dynamic update query
            set_clauses = []
            params = []
            
            for key, value in kwargs.items():
                if key in ['suggested_category_id', 'suggested_platform_id', 'status', 'notes']:
                    set_clauses.append(f"{key} = ?")
                    params.append(value)
            
            if not set_clauses:
                return False
            
            params.append(unknown_extension_id)
            query = f"UPDATE unknown_extension SET {', '.join(set_clauses)} WHERE unknown_extension_id = ?"
            
            cursor.execute(query, params)
            conn.commit()
            
            self.logger.info(f"Updated unknown extension ID {unknown_extension_id}")
            return cursor.rowcount > 0
    
    def approve_unknown_extension(self, unknown_extension_id: int, category_id: int, 
                                 platform_id: int = None, notes: str = None) -> bool:
        """Approve an unknown extension and create the corresponding extension record."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("BEGIN TRANSACTION")
                
                # Get the unknown extension details
                cursor.execute("SELECT * FROM unknown_extension WHERE unknown_extension_id = ?", 
                             (unknown_extension_id,))
                unknown_ext = cursor.fetchone()
                
                if not unknown_ext:
                    return False
                
                # Create the file extension
                cursor.execute("""
                    INSERT INTO file_extension 
                    (extension, category_id, description, is_active, is_rom, is_archive, is_save, is_patch)
                    VALUES (?, ?, ?, 1, 1, 0, 0, 0)
                """, (unknown_ext['extension'], category_id, notes or f"Auto-created from unknown extension"))
                
                extension_id = cursor.lastrowid
                
                # Create platform mapping if platform specified
                if platform_id:
                    cursor.execute("""
                        INSERT INTO platform_extension (platform_id, extension_id, is_primary, confidence)
                        VALUES (?, ?, 1, 1.0)
                    """, (platform_id, extension_id))
                
                # Update unknown extension status
                cursor.execute("""
                    UPDATE unknown_extension 
                    SET status = 'approved', suggested_category_id = ?, suggested_platform_id = ?, notes = ?
                    WHERE unknown_extension_id = ?
                """, (category_id, platform_id, notes, unknown_extension_id))
                
                cursor.execute("COMMIT")
                
                self.logger.info(f"Approved unknown extension: {unknown_ext['extension']} -> Extension ID {extension_id}")
                return True
                
            except Exception as e:
                cursor.execute("ROLLBACK")
                self.logger.error(f"Failed to approve unknown extension: {e}")
                return False
    
    def reject_unknown_extension(self, unknown_extension_id: int, notes: str = None) -> bool:
        """Reject an unknown extension."""
        return self.update_unknown_extension(unknown_extension_id, status='rejected', notes=notes)
    
    def ignore_unknown_extension(self, unknown_extension_id: int, notes: str = None) -> bool:
        """Ignore an unknown extension."""
        return self.update_unknown_extension(unknown_extension_id, status='ignored', notes=notes)
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def get_extension_registry_summary(self) -> Dict[str, Any]:
        """Get a summary of the extension registry."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get category counts
            cursor.execute("""
                SELECT COUNT(*) as total_categories,
                       COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_categories
                FROM file_type_category
            """)
            category_stats = dict(cursor.fetchone())
            
            # Get extension counts
            cursor.execute("""
                SELECT COUNT(*) as total_extensions,
                       COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_extensions,
                       COUNT(CASE WHEN is_rom = 1 THEN 1 END) as rom_extensions,
                       COUNT(CASE WHEN is_archive = 1 THEN 1 END) as archive_extensions,
                       COUNT(CASE WHEN is_save = 1 THEN 1 END) as save_extensions,
                       COUNT(CASE WHEN is_patch = 1 THEN 1 END) as patch_extensions
                FROM file_extension
            """)
            extension_stats = dict(cursor.fetchone())
            
            # Get platform mapping counts
            cursor.execute("""
                SELECT COUNT(*) as total_mappings,
                       COUNT(CASE WHEN is_primary = 1 THEN 1 END) as primary_mappings,
                       COUNT(DISTINCT platform_id) as platforms_with_mappings
                FROM platform_extension
            """)
            mapping_stats = dict(cursor.fetchone())
            
            # Get unknown extension counts
            cursor.execute("""
                SELECT COUNT(*) as total_unknown,
                       COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_unknown,
                       COUNT(CASE WHEN status = 'approved' THEN 1 END) as approved_unknown,
                       COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected_unknown,
                       COUNT(CASE WHEN status = 'ignored' THEN 1 END) as ignored_unknown
                FROM unknown_extension
            """)
            unknown_stats = dict(cursor.fetchone())
            
            return {
                'categories': category_stats,
                'extensions': extension_stats,
                'mappings': mapping_stats,
                'unknown': unknown_stats
            }
    
    def detect_file_type(self, filename: str) -> Optional[Dict]:
        """Detect file type based on extension."""
        path = Path(filename)
        extension = path.suffix.lower()
        
        if not extension:
            return None
        
        extension_info = self.get_extension_by_name(extension)
        if extension_info:
            return extension_info
        
        # If not found, record as unknown
        self.record_unknown_extension(extension)
        return None
    
    def get_extensions_for_platform(self, platform_id: int) -> List[Dict]:
        """Get all extensions associated with a platform."""
        return self.get_platform_extensions(platform_id=platform_id)
    
    def get_platforms_for_extension(self, extension_id: int) -> List[Dict]:
        """Get all platforms associated with an extension."""
        return self.get_platform_extensions(extension_id=extension_id)
    
    # =============================================================================
    # IMPORT/EXPORT FUNCTIONALITY
    # =============================================================================
    
    def export_extensions(self, file_path: str, format: str = 'json') -> bool:
        """Export extension registry data to file."""
        try:
            # Get all data
            categories = self.get_categories(active_only=False)
            extensions = self.get_extensions(active_only=False)
            mappings = self.get_platform_extensions()
            unknown = self.get_unknown_extensions()
            
            # Prepare export data
            export_data = {
                'metadata': {
                    'export_date': datetime.now().isoformat(),
                    'version': '1.0',
                    'format': format
                },
                'categories': categories,
                'extensions': extensions,
                'mappings': mappings,
                'unknown_extensions': unknown
            }
            
            if format.lower() == 'json':
                import json
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            elif format.lower() == 'csv':
                import csv
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    
                    # Write categories
                    writer.writerow(['CATEGORIES'])
                    writer.writerow(['category_id', 'name', 'description', 'sort_order', 'is_active'])
                    for cat in categories:
                        writer.writerow([
                            cat['category_id'], cat['name'], cat['description'] or '',
                            cat['sort_order'], cat['is_active']
                        ])
                    
                    writer.writerow([])  # Empty row
                    
                    # Write extensions
                    writer.writerow(['EXTENSIONS'])
                    writer.writerow(['extension_id', 'extension', 'category_id', 'description', 
                                   'mime_type', 'is_active', 'is_rom', 'is_archive', 'is_save', 'is_patch'])
                    for ext in extensions:
                        writer.writerow([
                            ext['extension_id'], ext['extension'], ext['category_id'],
                            ext['description'] or '', ext['mime_type'] or '', ext['is_active'],
                            ext['is_rom'], ext['is_archive'], ext['is_save'], ext['is_patch']
                        ])
                    
                    writer.writerow([])  # Empty row
                    
                    # Write mappings
                    writer.writerow(['PLATFORM MAPPINGS'])
                    writer.writerow(['platform_extension_id', 'platform_id', 'platform_name', 
                                   'extension_id', 'extension', 'is_primary', 'confidence'])
                    for mapping in mappings:
                        writer.writerow([
                            mapping['platform_extension_id'], mapping['platform_id'], mapping['platform_name'],
                            mapping['extension_id'], mapping['extension'], mapping['is_primary'], mapping['confidence']
                        ])
            
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            self.logger.info(f"Exported extension registry to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export extension registry: {e}")
            return False
    
    def import_extensions(self, file_path: str, format: str = 'json', overwrite: bool = False) -> Dict[str, Any]:
        """Import extension registry data from file."""
        import_results = {
            'success': False,
            'categories_imported': 0,
            'extensions_imported': 0,
            'mappings_imported': 0,
            'unknown_imported': 0,
            'errors': []
        }
        
        try:
            import_data = self._load_import_data(file_path, format)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("BEGIN TRANSACTION")

                try:
                    self._import_categories(cursor, import_data, overwrite, import_results)
                    self._import_extensions(cursor, import_data, overwrite, import_results)
                    self._import_mappings(cursor, import_data, overwrite, import_results)
                    self._import_unknown_extensions(cursor, import_data, overwrite, import_results)
                    
                    # Only commit if no errors occurred
                    if not import_results['errors']:
                        cursor.execute("COMMIT")
                        import_results['success'] = True
                        self.logger.info(f"Imported extension registry from {file_path}")
                    else:
                        cursor.execute("ROLLBACK")
                        self.logger.warning(f"Import failed due to errors: {import_results['errors']}")
                    
                except Exception as e:
                    cursor.execute("ROLLBACK")
                    import_results['errors'].append(f"Transaction failed: {e}")
                    raise

        except Exception as e:
            import_results['errors'].append(f"Import failed: {e}")
            self.logger.error(f"Failed to import extension registry: {e}")

        return import_results
    
    def _load_import_data(self, file_path: str, format: str) -> Dict[str, Any]:
        """Load import data from file."""
        if format.lower() != 'json':
            raise ValueError(f"Unsupported import format: {format}. Only 'json' is currently supported.")
        
        import json
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _import_categories(self, cursor, import_data: Dict[str, Any], overwrite: bool, import_results: Dict[str, Any]):
        """Import categories from import data."""
        if 'categories' not in import_data:
            return
            
        for cat_data in import_data['categories']:
            try:
                self._import_single_category(cursor, cat_data, overwrite, import_results)
            except Exception as e:
                import_results['errors'].append(f"Error importing category {cat_data.get('name', 'unknown')}: {e}")
    
    def _import_single_category(self, cursor, cat_data: Dict[str, Any], overwrite: bool, import_results: Dict[str, Any]):
        """Import a single category."""
        cursor.execute("SELECT category_id FROM file_type_category WHERE name = ?", (cat_data['name'],))
        existing = cursor.fetchone()

        if existing and not overwrite:
            return  # Skip existing

        if existing:
            cursor.execute("""
                UPDATE file_type_category 
                SET description = ?, sort_order = ?, is_active = ?
                WHERE category_id = ?
            """, (cat_data.get('description'), cat_data.get('sort_order', 0),
                 cat_data.get('is_active', True), existing['category_id']))
        else:
            cursor.execute("""
                INSERT INTO file_type_category (name, description, sort_order, is_active)
                VALUES (?, ?, ?, ?)
            """, (cat_data['name'], cat_data.get('description'),
                 cat_data.get('sort_order', 0), cat_data.get('is_active', True)))

        import_results['categories_imported'] += 1
    
    def _import_extensions(self, cursor, import_data: Dict[str, Any], overwrite: bool, import_results: Dict[str, Any]):
        """Import extensions from import data."""
        if 'extensions' not in import_data:
            return
            
        for ext_data in import_data['extensions']:
            try:
                self._import_single_extension(cursor, ext_data, overwrite, import_results)
            except Exception as e:
                import_results['errors'].append(f"Error importing extension {ext_data.get('extension', 'unknown')}: {e}")
    
    def _import_single_extension(self, cursor, ext_data: Dict[str, Any], overwrite: bool, import_results: Dict[str, Any]):
        """Import a single extension."""
        cursor.execute("SELECT extension_id FROM file_extension WHERE extension = ?", (ext_data['extension'],))
        existing = cursor.fetchone()

        if existing and not overwrite:
            return  # Skip existing

        if existing:
            cursor.execute("""
                UPDATE file_extension 
                SET category_id = ?, description = ?, mime_type = ?, 
                    is_active = ?, is_rom = ?, is_archive = ?, is_save = ?, is_patch = ?
                WHERE extension_id = ?
            """, (ext_data.get('category_id'), ext_data.get('description'),
                 ext_data.get('mime_type'), ext_data.get('is_active', True),
                 ext_data.get('is_rom', False), ext_data.get('is_archive', False),
                 ext_data.get('is_save', False), ext_data.get('is_patch', False),
                 existing['extension_id']))
        else:
            cursor.execute("""
                INSERT INTO file_extension 
                (extension, category_id, description, mime_type, is_active, 
                 is_rom, is_archive, is_save, is_patch)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ext_data['extension'], ext_data.get('category_id'),
                 ext_data.get('description'), ext_data.get('mime_type'),
                 ext_data.get('is_active', True), ext_data.get('is_rom', False),
                 ext_data.get('is_archive', False), ext_data.get('is_save', False),
                 ext_data.get('is_patch', False)))

        import_results['extensions_imported'] += 1
    
    def _import_mappings(self, cursor, import_data: Dict[str, Any], overwrite: bool, import_results: Dict[str, Any]):
        """Import platform mappings from import data."""
        if 'mappings' not in import_data:
            return
            
        for mapping_data in import_data['mappings']:
            try:
                self._import_single_mapping(cursor, mapping_data, overwrite, import_results)
            except Exception as e:
                import_results['errors'].append(f"Error importing mapping: {e}")
    
    def _import_single_mapping(self, cursor, mapping_data: Dict[str, Any], overwrite: bool, import_results: Dict[str, Any]):
        """Import a single platform mapping."""
        cursor.execute("""
            SELECT platform_extension_id FROM platform_extension 
            WHERE platform_id = ? AND extension_id = ?
        """, (mapping_data.get('platform_id'), mapping_data.get('extension_id')))
        existing = cursor.fetchone()

        if existing and not overwrite:
            return  # Skip existing

        if existing:
            cursor.execute("""
                UPDATE platform_extension 
                SET is_primary = ?, confidence = ?
                WHERE platform_extension_id = ?
            """, (mapping_data.get('is_primary', False),
                 mapping_data.get('confidence', 1.0), existing['platform_extension_id']))
        else:
            cursor.execute("""
                INSERT INTO platform_extension (platform_id, extension_id, is_primary, confidence)
                VALUES (?, ?, ?, ?)
            """, (mapping_data.get('platform_id'), mapping_data.get('extension_id'),
                 mapping_data.get('is_primary', False), mapping_data.get('confidence', 1.0)))

        import_results['mappings_imported'] += 1
    
    def _import_unknown_extensions(self, cursor, import_data: Dict[str, Any], overwrite: bool, import_results: Dict[str, Any]):
        """Import unknown extensions from import data."""
        if 'unknown_extensions' not in import_data:
            return
            
        for unknown_data in import_data['unknown_extensions']:
            try:
                self._import_single_unknown_extension(cursor, unknown_data, overwrite, import_results)
            except Exception as e:
                import_results['errors'].append(f"Error importing unknown extension {unknown_data.get('extension', 'unknown')}: {e}")
    
    def _import_single_unknown_extension(self, cursor, unknown_data: Dict[str, Any], overwrite: bool, import_results: Dict[str, Any]):
        """Import a single unknown extension."""
        cursor.execute("SELECT unknown_extension_id FROM unknown_extension WHERE extension = ?", (unknown_data['extension'],))
        existing = cursor.fetchone()

        if existing and not overwrite:
            return  # Skip existing

        if existing:
            cursor.execute("""
                UPDATE unknown_extension 
                SET file_count = ?, status = ?, suggested_category_id = ?, 
                    suggested_platform_id = ?, notes = ?
                WHERE unknown_extension_id = ?
            """, (unknown_data.get('file_count', 1), unknown_data.get('status', 'pending'),
                 unknown_data.get('suggested_category_id'), unknown_data.get('suggested_platform_id'),
                 unknown_data.get('notes'), existing['unknown_extension_id']))
        else:
            cursor.execute("""
                INSERT INTO unknown_extension 
                (extension, file_count, status, suggested_category_id, suggested_platform_id, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (unknown_data['extension'], unknown_data.get('file_count', 1),
                 unknown_data.get('status', 'pending'), unknown_data.get('suggested_category_id'),
                 unknown_data.get('suggested_platform_id'), unknown_data.get('notes')))

        import_results['unknown_imported'] += 1