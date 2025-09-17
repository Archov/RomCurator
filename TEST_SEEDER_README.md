# Test Seeder System

A simple system for testing individual importers and new features without having to reseed the entire database.

## Quick Start

```bash
# Run a quick test with one file
python test_seeder.py seed-config-quick-test.json

# Test region standardization
python test_seeder.py seed-config-region-test.json

# Dry run (see what would be imported without actually doing it)
python test_seeder.py seed-config-dry-run.json
```

## Configuration File Format

The test seeder reads JSON configuration files that specify which files to import and how:

```json
{
  "name": "Test Name",
  "description": "What this test does",
  "database_path": "database/RomCurator.db",
  "imports": [
    {
      "name": "Import Name",
      "importer": "nointro|tosec|mobygames",
      "file_path": "path/to/file.dat",
      "platform_name": "Platform Name"
    }
  ],
  "options": {
    "clear_existing_data": false,
    "verbose_logging": true,
    "dry_run": false
  }
}
```

### Configuration Options

- **`name`**: Display name for the test
- **`description`**: Description of what the test does
- **`database_path`**: Path to the SQLite database
- **`imports`**: Array of import operations to run
  - **`name`**: Display name for this import
  - **`importer`**: Type of importer (`nointro`, `tosec`, `mobygames`)
  - **`file_path`**: Path to the file to import
  - **`platform_name`**: Platform name for the import
- **`options`**:
  - **`clear_existing_data`**: Clear existing DAT data before importing
  - **`verbose_logging`**: Enable detailed logging
  - **`dry_run`**: Show what would be imported without actually doing it

## Sample Configurations

### `seed-config.json`
Full test with all three importers using sample files.

### `seed-config-quick-test.json`
Quick test with just one file for rapid iteration.

### `seed-config-region-test.json`
Test the new region standardization system.

### `seed-config-dry-run.json`
Dry run mode to see what would be imported without actually doing it.

## Usage Examples

### Test Region Standardization
```bash
python test_seeder.py seed-config-region-test.json
```

### Quick Iteration Testing
```bash
python test_seeder.py seed-config-quick-test.json
```

### See What Would Be Imported
```bash
python test_seeder.py seed-config-dry-run.json
```

## Benefits

- **No Database Reseeding**: Test individual files without rebuilding the entire database
- **Rapid Iteration**: Quick tests for development and debugging
- **Flexible Configuration**: Easy to create new test scenarios
- **Dry Run Mode**: See what would happen without actually importing
- **Verbose Logging**: Detailed output for debugging
- **Error Handling**: Clear success/failure reporting

## Creating Custom Configurations

1. Copy an existing config file
2. Modify the `imports` array with your desired files
3. Adjust the `options` as needed
4. Run with `python test_seeder.py your-config.json`

This makes testing much faster and more focused than the full database reseeding process!
