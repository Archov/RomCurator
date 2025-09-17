"""
Shared utilities for XML-based DAT file importers (No-Intro, TOSEC).
Contains common XML parsing and schema validation functionality.
"""

import xml.etree.ElementTree as ET
import lxml.etree as etree
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import urlparse


def extract_schema_url_from_dat(xml_file_path):
    """Extracts the XSD schema URL from the DAT file's schemaLocation attribute."""
    try:
        # Parse just enough to get the root element and its attributes
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        
        # Look for xsi:schemaLocation attribute
        schema_location = root.get('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation')
        if schema_location:
            # schemaLocation format is "namespace_uri schema_url"
            parts = schema_location.strip().split()
            if len(parts) >= 2:
                return parts[1]  # Return the schema URL part
        
        return None
    except Exception as e:
        print(f"Warning: Could not extract schema URL from DAT file: {e}")
        return None


def download_and_cache_schema(schema_url, cache_dir=".schema_cache"):
    """Downloads an XSD schema from a URL and caches it locally."""
    try:
        # Create cache directory if it doesn't exist
        cache_path = Path(cache_dir)
        cache_path.mkdir(exist_ok=True)
        
        # Generate cache filename from URL
        parsed_url = urlparse(schema_url)
        cache_filename = f"{parsed_url.netloc}_{Path(parsed_url.path).name}"
        cache_file = cache_path / cache_filename
        
        # Check if already cached
        if cache_file.exists():
            print(f"Using cached schema: {cache_file}")
            return str(cache_file)
        
        # Download the schema
        print(f"Downloading schema from: {schema_url}")
        with urllib.request.urlopen(schema_url, timeout=30) as response:
            schema_content = response.read()
        
        # Save to cache
        with open(cache_file, 'wb') as f:
            f.write(schema_content)
        
        print(f"Schema cached to: {cache_file}")
        return str(cache_file)
        
    except urllib.error.URLError as e:
        print(f"Warning: Could not download schema from {schema_url}: {e}")
        return None
    except Exception as e:
        print(f"Warning: Error caching schema: {e}")
        return None


def load_xsd_schema(schema_path):
    """Loads and returns the XSD schema for validation."""
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_doc = etree.parse(f)
            return etree.XMLSchema(schema_doc)
    except Exception as e:
        print(f"Warning: Could not load XSD schema from {schema_path}: {e}")
        return None


def load_dtd_schema(schema_path):
    """Loads and returns the DTD schema for validation."""
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            dtd_doc = etree.DTD(f)
            return dtd_doc
    except Exception as e:
        print(f"Warning: Could not load DTD schema from {schema_path}: {e}")
        return None


def validate_xml_against_schema(xml_file_path, schema, schema_type="XSD"):
    """Validates XML file against the provided schema (XSD or DTD)."""
    if not schema:
        return True, f"No {schema_type} schema provided - skipping validation"
    
    try:
        xml_doc = etree.parse(str(xml_file_path))
        if schema.validate(xml_doc):
            return True, f"{schema_type} validation successful"
        else:
            # Schema validation failed - collect all errors
            error_messages = []
            for error in schema.error_log:
                error_messages.append(f"Line {error.line}: {error.message}")
            
            # If there are many errors, truncate the list
            if len(error_messages) > 10:
                shown_errors = error_messages[:10]
                shown_errors.append(f"... and {len(error_messages) - 10} more errors")
                error_summary = "\\n".join(shown_errors)
            else:
                error_summary = "\\n".join(error_messages)
            
            return False, f"{schema_type} validation failed with {len(error_messages)} errors:\\n{error_summary}"
    except Exception as e:
        return False, f"Unexpected {schema_type} validation error: {e}"


def handle_schema_validation_warning(file_path, is_valid, validation_message, schema_type="XSD"):
    """Handle schema validation results with appropriate messaging."""
    if not is_valid:
        print(f"Warning: {schema_type} schema validation failed for {file_path.name}, but proceeding with import anyway.")
        print(f"Validation details: {validation_message}")
        print("Note: Many valid DAT files don't strictly conform to their schemas but are still importable.")
    else:
        print(f"{schema_type} schema validation passed: {validation_message}")


def process_dat_rom_entry(cursor, log_id, platform_id, game_name, sha1, is_clone=0, clone_of="", dat_format="auto"):
    """Insert a single ROM entry into the dat_entry table with enhanced parsing."""
    if not sha1:
        return False
    
    # Import parser here to avoid circular imports
    try:
        from .dat_parser import DATNameParser
    except ImportError:
        from dat_parser import DATNameParser
    
    # Parse the game name to extract universal metadata
    parser = DATNameParser()
    parsed_data = parser.parse_title(game_name, dat_format)
    
    # Check if the enhanced dat_entry table structure exists
    cursor.execute("PRAGMA table_info(dat_entry)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'base_title' in columns:
        # Use enhanced structure (v1.7)
        cursor.execute("""
            INSERT OR IGNORE INTO dat_entry (
                log_id, platform_id, release_title, rom_sha1, is_clone, clone_of,
                base_title, region_normalized, version_info, development_status,
                dump_status, language_codes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            log_id, platform_id, game_name, sha1.lower(), is_clone, clone_of,
            parsed_data['base_title'], parsed_data['region_normalized'],
            parsed_data['version_info'], parsed_data['development_status'],
            parsed_data['dump_status'], parsed_data['language_codes']
        ))
        
        # Insert format-specific metadata if any extra_info exists
        if parsed_data['extra_info']:
            cursor.execute("""
                INSERT OR IGNORE INTO dat_entry_metadata (
                    dat_entry_id, metadata_key, metadata_value
                ) VALUES (
                    (SELECT dat_entry_id FROM dat_entry WHERE rom_sha1 = ? AND log_id = ?),
                    'extra_info', ?
                )
            """, (sha1.lower(), log_id, parsed_data['extra_info']))
    else:
        # Fallback to basic structure (v1.6)
        cursor.execute("""
            INSERT OR IGNORE INTO dat_entry (
                log_id, platform_id, release_title, rom_sha1, is_clone, clone_of
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (log_id, platform_id, game_name, sha1.lower(), is_clone, clone_of))
    
    return True
