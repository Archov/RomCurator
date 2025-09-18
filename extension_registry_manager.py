"""
Extension Registry Manager for ROM Curator

This module provides comprehensive management of file extensions, categories,
platform mappings, and unknown extension handling for the ROM Curator system.

Features:
- CRUD operations for file type categories
- CRUD operations for file extensions
- Platform-extension mapping management
- Unknown extension tracking and approval
- Import/export functionality (JSON/CSV)
- File type detection and platform inference
"""

import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import csv


class ExtensionRegistryManager:
    """Manages file extension registry, categories, and platform mappings."""
    
    def __init__(self, db_path: str):
        """Initialize the extension registry manager."""
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Ensure database has the required tables
        self._ensure_tables_exist()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with proper configuration."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def _ensure_tables_exist(self):
        """Ensure extension registry tables exist in the database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if extension registry tables exist
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='file_type_category'
                """)
                
                if not cursor.fetchone():
                    self.logger.warning("Extension registry tables not found. Please run database migration.")
                    return
                
        except Exception as e:
            self.logger.error(f"Error checking extension registry tables: {e}")
            raise
    
    # =============================================================================
    # CATEGORY MANAGEMENT
    # =============================================================================
    
    def create_category(self, name: str, description: str = None, 
                       sort_order: int = 0, is_active: bool = True) -> int:
        """Create a new file type category."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO file_type_category (name, description, sort_order, is_active)
                    VALUES (?, ?, ?, ?)
                """, (name, description, sort_order, is_active))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                raise ValueError(f"Category '{name}' already exists")
            raise
        except Exception as e:
            self.logger.error(f"Error creating category: {e}")
            raise
    
    def get_category(self, category_id: int) -> Optional[Dict[str, Any]]:
        """Get a category by ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM file_type_category WHERE category_id = ?
                """, (category_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"Error getting category: {e}")
            return None
    
    def get_categories(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """Get all categories, optionally filtered by active status."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT * FROM file_type_category"
                params = []
                
                if active_only:
                    query += " WHERE is_active = ?"
                    params.append(True)
                
                query += " ORDER BY sort_order, name"
                
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Error getting categories: {e}")
            return []
    
    def update_category(self, category_id: int, **kwargs) -> bool:
        """Update a category."""
        try:
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
                query = f"UPDATE file_type_category SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE category_id = ?"
                
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error updating category: {e}")
            return False
    
    def delete_category(self, category_id: int) -> bool:
        """Delete a category (only if no extensions are using it)."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if category is in use
                cursor.execute("SELECT COUNT(*) FROM file_extension WHERE category_id = ?", (category_id,))
                if cursor.fetchone()[0] > 0:
                    raise ValueError("Cannot delete category that is in use by extensions")
                
                cursor.execute("DELETE FROM file_type_category WHERE category_id = ?", (category_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error deleting category: {e}")
            return False
    
    # =============================================================================
    # EXTENSION MANAGEMENT
    # =============================================================================
    
    def create_extension(self, extension: str, category_id: int, 
                        description: str = None, mime_type: str = None,
                        is_active: bool = True, is_rom: bool = False,
                        is_archive: bool = False, is_save: bool = False,
                        is_patch: bool = False) -> int:
        """Create a new file extension."""
        try:
            # Ensure extension starts with a dot
            if not extension.startswith('.'):
                extension = '.' + extension
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO file_extension 
                    (extension, category_id, description, mime_type, is_active, 
                     is_rom, is_archive, is_save, is_patch)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (extension, category_id, description, mime_type, is_active,
                     is_rom, is_archive, is_save, is_patch))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                raise ValueError(f"Extension '{extension}' already exists")
            raise
        except Exception as e:
            self.logger.error(f"Error creating extension: {e}")
            raise
    
    def get_extension(self, extension_id: int) -> Optional[Dict[str, Any]]:
        """Get an extension by ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT fe.*, ftc.name as category_name
                    FROM file_extension fe
                    JOIN file_type_category ftc ON fe.category_id = ftc.category_id
                    WHERE fe.extension_id = ?
                """, (extension_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"Error getting extension: {e}")
            return None
    
    def get_extension_by_name(self, extension: str) -> Optional[Dict[str, Any]]:
        """Get an extension by name."""
        try:
            # Ensure extension starts with a dot
            if not extension.startswith('.'):
                extension = '.' + extension
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT fe.*, ftc.name as category_name
                    FROM file_extension fe
                    JOIN file_type_category ftc ON fe.category_id = ftc.category_id
                    WHERE fe.extension = ?
                """, (extension,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"Error getting extension by name: {e}")
            return None
    
    def get_extensions(self, category_id: int = None, active_only: bool = False) -> List[Dict[str, Any]]:
        """Get extensions, optionally filtered by category and active status."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT fe.*, ftc.name as category_name
                    FROM file_extension fe
                    JOIN file_type_category ftc ON fe.category_id = ftc.category_id
                """
                params = []
                conditions = []
                
                if category_id is not None:
                    conditions.append("fe.category_id = ?")
                    params.append(category_id)
                
                if active_only:
                    conditions.append("fe.is_active = ?")
                    params.append(True)
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                query += " ORDER BY ftc.sort_order, ftc.name, fe.extension"
                
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Error getting extensions: {e}")
            return []
    
    def update_extension(self, extension_id: int, **kwargs) -> bool:
        """Update an extension."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Build dynamic update query
                set_clauses = []
                params = []
                
                for key, value in kwargs.items():
                    if key in ['extension', 'category_id', 'description', 'mime_type', 
                              'is_active', 'is_rom', 'is_archive', 'is_save', 'is_patch']:
                        set_clauses.append(f"{key} = ?")
                        params.append(value)
                
                if not set_clauses:
                    return False
                
                params.append(extension_id)
                query = f"UPDATE file_extension SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE extension_id = ?"
                
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error updating extension: {e}")
            return False
    
    def delete_extension(self, extension_id: int) -> bool:
        """Delete an extension."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM file_extension WHERE extension_id = ?", (extension_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error deleting extension: {e}")
            return False
    
    # =============================================================================
    # PLATFORM MAPPING MANAGEMENT
    # =============================================================================
    
    def add_platform_mapping(self, platform_id: int, extension_id: int,
                            is_primary: bool = False, confidence: float = 1.0) -> int:
        """Add a platform-extension mapping."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO platform_extension (platform_id, extension_id, is_primary, confidence)
                    VALUES (?, ?, ?, ?)
                """, (platform_id, extension_id, is_primary, confidence))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                raise ValueError("Platform-extension mapping already exists")
            raise
        except Exception as e:
            self.logger.error(f"Error adding platform mapping: {e}")
            raise
    
    def get_platforms_for_extension(self, extension_id: int) -> List[Dict[str, Any]]:
        """Get platform mappings for an extension."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT pe.*, p.name as platform_name
                    FROM platform_extension pe
                    JOIN platform p ON pe.platform_id = p.platform_id
                    WHERE pe.extension_id = ?
                    ORDER BY pe.is_primary DESC, pe.confidence DESC
                """, (extension_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Error getting platforms for extension: {e}")
            return []
    
    def update_platform_mapping(self, mapping_id: int, **kwargs) -> bool:
        """Update a platform mapping."""
        try:
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
                
                params.append(mapping_id)
                query = f"UPDATE platform_extension SET {', '.join(set_clauses)} WHERE platform_extension_id = ?"
                
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error updating platform mapping: {e}")
            return False
    
    def delete_platform_mapping(self, mapping_id: int) -> bool:
        """Delete a platform mapping."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM platform_extension WHERE platform_extension_id = ?", (mapping_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error deleting platform mapping: {e}")
            return False
    
    # =============================================================================
    # UNKNOWN EXTENSION MANAGEMENT
    # =============================================================================
    
    def record_unknown_extension(self, extension: str, file_count: int = 1) -> int:
        """Record an unknown extension discovery."""
        try:
            # Ensure extension starts with a dot
            if not extension.startswith('.'):
                extension = '.' + extension
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if already exists
                cursor.execute("SELECT unknown_extension_id, file_count FROM unknown_extension WHERE extension = ?", (extension,))
                existing = cursor.fetchone()
                
                if existing:
                    # Update count and last_seen
                    new_count = existing['file_count'] + file_count
                    cursor.execute("""
                        UPDATE unknown_extension 
                        SET file_count = ?, last_seen = CURRENT_TIMESTAMP
                        WHERE unknown_extension_id = ?
                    """, (new_count, existing['unknown_extension_id']))
                    conn.commit()
                    return existing['unknown_extension_id']
                else:
                    # Create new record
                    cursor.execute("""
                        INSERT INTO unknown_extension (extension, file_count)
                        VALUES (?, ?)
                    """, (extension, file_count))
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"Error recording unknown extension: {e}")
            raise
    
    def get_unknown_extensions(self, status: str = None) -> List[Dict[str, Any]]:
        """Get unknown extensions, optionally filtered by status."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT ue.*, ftc.name as suggested_category, p.name as suggested_platform
                    FROM unknown_extension ue
                    LEFT JOIN file_type_category ftc ON ue.suggested_category_id = ftc.category_id
                    LEFT JOIN platform p ON ue.suggested_platform_id = p.platform_id
                """
                params = []
                
                if status:
                    query += " WHERE ue.status = ?"
                    params.append(status)
                
                query += " ORDER BY ue.file_count DESC, ue.first_seen ASC"
                
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Error getting unknown extensions: {e}")
            return []
    
    def update_unknown_extension(self, unknown_id: int, **kwargs) -> bool:
        """Update an unknown extension."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Build dynamic update query
                set_clauses = []
                params = []
                
                for key, value in kwargs.items():
                    if key in ['status', 'suggested_category_id', 'suggested_platform_id', 'notes']:
                        set_clauses.append(f"{key} = ?")
                        params.append(value)
                
                if not set_clauses:
                    return False
                
                params.append(unknown_id)
                query = f"UPDATE unknown_extension SET {', '.join(set_clauses)} WHERE unknown_extension_id = ?"
                
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error updating unknown extension: {e}")
            return False
    
    def approve_unknown_extension(self, unknown_id: int, category_id: int, 
                                 platform_id: int = None, notes: str = None) -> bool:
        """Approve an unknown extension and create it as a regular extension."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("BEGIN TRANSACTION")
                
                try:
                    # Get unknown extension details
                    cursor.execute("SELECT * FROM unknown_extension WHERE unknown_extension_id = ?", (unknown_id,))
                    unknown = cursor.fetchone()
                    if not unknown:
                        raise ValueError("Unknown extension not found")
                    
                    # Create the extension
                    extension_id = self.create_extension(
                        extension=unknown['extension'],
                        category_id=category_id,
                        description=f"Approved from unknown extension discovery",
                        is_active=True
                    )
                    
                    # Add platform mapping if provided
                    if platform_id:
                        self.add_platform_mapping(platform_id, extension_id, is_primary=True)
                    
                    # Update unknown extension status
                    cursor.execute("""
                        UPDATE unknown_extension 
                        SET status = 'approved', suggested_category_id = ?, 
                            suggested_platform_id = ?, notes = ?
                        WHERE unknown_extension_id = ?
                    """, (category_id, platform_id, notes, unknown_id))
                    
                    cursor.execute("COMMIT")
                    return True
                    
                except Exception as e:
                    cursor.execute("ROLLBACK")
                    raise
        except Exception as e:
            self.logger.error(f"Error approving unknown extension: {e}")
            return False
    
    # =============================================================================
    # FILE TYPE DETECTION
    # =============================================================================
    
    def detect_file_type(self, filename: str) -> Optional[Dict[str, Any]]:
        """Detect file type information for a given filename."""
        try:
            file_path = Path(filename)
            extension = file_path.suffix.lower()
            
            if not extension:
                return None
            
            # Get extension info from registry
            extension_info = self.get_extension_by_name(extension)
            if not extension_info:
                return None
            
            # Get platform mappings
            platform_mappings = self.get_platforms_for_extension(extension_info['extension_id'])
            
            return {
                'extension': extension_info['extension'],
                'category': extension_info['category_name'],
                'is_rom': extension_info['is_rom'],
                'is_archive': extension_info['is_archive'],
                'is_save': extension_info['is_save'],
                'is_patch': extension_info['is_patch'],
                'platforms': platform_mappings
            }
        except Exception as e:
            self.logger.error(f"Error detecting file type: {e}")
            return None
    
    def get_supported_extensions(self) -> Dict[str, List[str]]:
        """Get supported extensions grouped by type."""
        try:
            extensions = self.get_extensions(active_only=True)
            
            result = {
                'rom': [],
                'archive': [],
                'save': [],
                'patch': []
            }
            
            for ext in extensions:
                if ext['is_rom']:
                    result['rom'].append(ext['extension'])
                if ext['is_archive']:
                    result['archive'].append(ext['extension'])
                if ext['is_save']:
                    result['save'].append(ext['extension'])
                if ext['is_patch']:
                    result['patch'].append(ext['extension'])
            
            return result
        except Exception as e:
            self.logger.error(f"Error getting supported extensions: {e}")
            return {'rom': [], 'archive': [], 'save': [], 'patch': []}
    
    # =============================================================================
    # IMPORT/EXPORT FUNCTIONALITY
    # =============================================================================
    
    def export_extensions(self, file_path: str, format: str = 'json') -> bool:
        """Export extension registry data to file."""
        try:
            # Get all data
            categories = self.get_categories()
            extensions = self.get_extensions()
            unknown_extensions = self.get_unknown_extensions()
            
            # Get platform mappings
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT pe.*, p.name as platform_name, fe.extension
                    FROM platform_extension pe
                    JOIN platform p ON pe.platform_id = p.platform_id
                    JOIN file_extension fe ON pe.extension_id = fe.extension_id
                """)
                mappings = [dict(row) for row in cursor.fetchall()]
            
            export_data = {
                'metadata': {
                    'export_date': datetime.now().isoformat(),
                    'version': '1.0',
                    'format': format
                },
                'categories': categories,
                'extensions': extensions,
                'mappings': mappings,
                'unknown_extensions': unknown_extensions
            }
            
            if format.lower() == 'json':
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
            elif format.lower() == 'csv':
                # Export as multiple CSV files
                base_path = Path(file_path).with_suffix('')
                
                # Categories CSV
                with open(f"{base_path}_categories.csv", 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=['category_id', 'name', 'description', 'sort_order', 'is_active'])
                    writer.writeheader()
                    writer.writerows(categories)
                
                # Extensions CSV
                with open(f"{base_path}_extensions.csv", 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=['extension_id', 'extension', 'category_id', 'description', 'mime_type', 'is_active', 'is_rom', 'is_archive', 'is_save', 'is_patch'])
                    writer.writeheader()
                    writer.writerows(extensions)
                
                # Mappings CSV
                with open(f"{base_path}_mappings.csv", 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=['platform_extension_id', 'platform_id', 'platform_name', 'extension_id', 'extension', 'is_primary', 'confidence'])
                    writer.writeheader()
                    writer.writerows(mappings)
                
                # Unknown extensions CSV
                with open(f"{base_path}_unknown.csv", 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=['unknown_extension_id', 'extension', 'file_count', 'status', 'suggested_category', 'suggested_platform', 'notes'])
                    writer.writeheader()
                    writer.writerows(unknown_extensions)
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
            # Load data from file
            import_data = self._load_import_data(file_path, format)
            if not import_data:
                import_results['errors'].append(f"Failed to load data from {file_path}")
                return import_results
            
            # Import data in transaction
            self._import_data_in_transaction(import_data, overwrite, import_results)
            
        except Exception as e:
            import_results['errors'].append(f"Import failed: {e}")
            self.logger.error(f"Failed to import extension registry: {e}")
        
        return import_results
    
    def _load_import_data(self, file_path: str, format: str) -> Optional[Dict[str, Any]]:
        """Load import data from file."""
        if format.lower() == 'json':
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            raise ValueError(f"Unsupported import format: {format}. Only 'json' is currently supported.")
    
    def _import_data_in_transaction(self, import_data: Dict[str, Any], overwrite: bool, import_results: Dict[str, Any]):
        """Import data within a database transaction."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION")
            
            try:
                # Import each data type
                self._import_categories(cursor, import_data, overwrite, import_results)
                self._import_extensions(cursor, import_data, overwrite, import_results)
                self._import_mappings(cursor, import_data, overwrite, import_results)
                self._import_unknown_extensions(cursor, import_data, overwrite, import_results)
                
                # Only commit if no errors occurred
                if not import_results['errors']:
                    cursor.execute("COMMIT")
                    import_results['success'] = True
                    self.logger.info("Extension registry import completed successfully")
                else:
                    cursor.execute("ROLLBACK")
                    import_results['success'] = False
                    
            except Exception as e:
                cursor.execute("ROLLBACK")
                import_results['errors'].append(f"Transaction failed: {e}")
                raise
    
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
        
        if existing and overwrite:
            # Update existing
            cursor.execute("""
                UPDATE file_type_category 
                SET description = ?, sort_order = ?, is_active = ?
                WHERE category_id = ?
            """, (cat_data.get('description'), cat_data.get('sort_order', 0),
                 cat_data.get('is_active', True), existing['category_id']))
        else:
            # Create new
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
        
        if existing and overwrite:
            # Update existing
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
            # Create new
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
        
        if existing and overwrite:
            # Update existing
            cursor.execute("""
                UPDATE platform_extension 
                SET is_primary = ?, confidence = ?
                WHERE platform_extension_id = ?
            """, (mapping_data.get('is_primary', False),
                 mapping_data.get('confidence', 1.0), existing['platform_extension_id']))
        else:
            # Create new
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
        
        if existing and overwrite:
            # Update existing
            cursor.execute("""
                UPDATE unknown_extension 
                SET file_count = ?, status = ?, suggested_category_id = ?, 
                    suggested_platform_id = ?, notes = ?
                WHERE unknown_extension_id = ?
            """, (unknown_data.get('file_count', 1), unknown_data.get('status', 'pending'),
                 unknown_data.get('suggested_category_id'), unknown_data.get('suggested_platform_id'),
                 unknown_data.get('notes'), existing['unknown_extension_id']))
        else:
            # Create new
            cursor.execute("""
                INSERT INTO unknown_extension 
                (extension, file_count, status, suggested_category_id, suggested_platform_id, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (unknown_data['extension'], unknown_data.get('file_count', 1),
                 unknown_data.get('status', 'pending'), unknown_data.get('suggested_category_id'),
                 unknown_data.get('suggested_platform_id'), unknown_data.get('notes')))
        
        import_results['unknown_imported'] += 1