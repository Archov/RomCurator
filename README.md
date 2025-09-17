# ROM Curator - Unified Application Guide
## **Project Prime Directives**

* **North Star:** Build a tool that transforms chaos into control: take a sprawling mess of ROMs, ISOs, and random zips and create a single, trusted library folder structure that validates against DATs and applies sensible 1G1R rules. This becomes your permanent source of truth—an organized directory tree of validated files, searchable and versioned—so you never have to wonder "which folder has the good dump?" again. From this clean foundation, generate smart playlists using queries, genres, top-games lists, or any criteria that matters to you, then export exactly what each device needs in exactly the format it expects.  
* **Design Principle:** Every feature must reduce the total time from "I downloaded/changed something" to "all my devices are updated and organized." This means deterministic operations (so you can trust the results), smart diffing (so you only update what changed), and format-aware exports that understand what MiSTer vs EverDrive vs RetroArch actually need—even if that means duplicating or restructuring files. The architecture should be boring and bulletproof because the user's attention should be on playing games, not managing them. When there's a tradeoff between theoretical purity and "just works every time," we choose what works.

## Quick Start

**Single Entry Point**: Run the unified application with:

```bash
python start_rom_curator.py
```

or directly:

```bash
python rom_curator_main.py
```

## What's New

### ✅ **Unified Interface**
- **Single main window** with menu-driven access to all features
- **No more command-line arguments** - everything uses `config.json`
- **Consistent configuration** across all components

### ✅ **Enhanced Import Experience**
- **Real-time progress bars** showing current file and overall progress
- **Console output viewing** to see what's happening during imports
- **Detailed logging** with session-specific log files
- **Error recovery** with the ability to continue after failures
- **Import session logs** saved automatically for debugging

### ✅ **Better User Feedback**
- **Progress indicators** for all long-running operations
- **Status messages** in the status bar
- **Error dialogs** with detailed information
- **Log viewer** for reviewing past operations

## Application Structure

### **Main Window**
```
File Menu
├── Import Data
│   └── Metadata & DAT Importer...    # Enhanced importer with progress
└── Exit

Tools Menu
├── Curation
│   └── DAT-Metadata Matching...      # Curation interface
└── Database
    ├── Setup Matching System...      # Database initialization
    └── Validate Matching...          # Validation tools

View Menu
└── View Logs...                      # Log viewer window

Help Menu
├── Matching Guide...                 # Built-in documentation
└── About...                          # Application information
```

### **Configuration Management**
All settings are managed through `config.json`:

```json
{
    "database_path": "./database/RomCurator.db",
    "importer_scripts_directory": "./scripts/seeders/",
    "log_directory": "./logs/",
    "log_level": "INFO",
    "auto_create_directories": true,
    "progress_update_interval": 100,
    "gui_settings": {
        "window_width": 1200,
        "window_height": 800,
        "theme": "dark"
    }
}
```

### **Logging System**
- **Application logs**: `logs/rom_curator.log` (general application events)
- **Import session logs**: `logs/import_SourceName_YYYYMMDD_HHMMSS.log` (detailed import operations)
- **Configurable log levels**: DEBUG, INFO, WARNING, ERROR
- **Automatic log rotation** and cleanup

## Enhanced Import Process

### **New Import Features**
1. **File-by-file progress**: See exactly which file is being processed
2. **Real-time console output**: Watch the import happen in real-time
3. **Error handling**: Continue processing other files if one fails
4. **Session logging**: Each import session creates a detailed log file
5. **Stop capability**: Cancel long-running imports safely

### **Import Workflow**
1. **Select Source**: Choose your data source (MobyGames, No-Intro, TOSEC, etc.)
2. **Select Files**: Choose one or more files to import
3. **Start Import**: Watch progress in real-time
4. **Review Results**: Check console output and detailed logs
5. **Handle Errors**: Review any errors in the log files

### **Progress Indicators**
- **Overall progress bar**: Shows files completed vs. total files
- **Current operation**: Displays which file is currently being processed
- **Console output**: Real-time status messages and results
- **Detailed log**: Complete session log with timestamps

## Troubleshooting

### **Common Issues**

**Import Fails Immediately**
- Check that the database exists (create with schema script if needed)
- Verify importer script paths in source configuration
- Check log files for detailed error messages

**No Progress Shown**
- Ensure files are valid for the selected source type
- Check console output for error messages
- Review session log for detailed diagnostics

**Import Hangs**
- Use the "Stop Import" button to cancel safely
- Check if files are corrupted or extremely large
- Review timeout settings in the configuration

### **Log Files**
- **Main application log**: `logs/rom_curator.log`
- **Import session logs**: `logs/import_*.log`
- **Log viewer**: Access via View → View Logs menu

### **Configuration Issues**
- Delete `config.json` to regenerate default configuration
- Check file paths are correct for your system
- Verify directory permissions for log and database directories

## Migration from Previous Versions

### **From Individual Scripts**
- **No more command-line tools**: Use the GUI interface instead
- **Configuration centralized**: All settings in `config.json`
- **Logs organized**: All logs in the `logs/` directory

### **Database Compatibility**
- **v1.6 databases**: Fully compatible, will be enhanced on first use
- **v1.7 features**: Enhanced DAT parsing available after setup
- **Schema updates**: Automatic via Tools → Database → Setup Matching System

## Development and Debugging

### **Debug Mode**
Set log level to "DEBUG" in `config.json` for verbose output:
```json
{
    "log_level": "DEBUG"
}
```

### **Custom Configuration**
- Modify `config.json` for custom paths and settings
- Restart application to apply configuration changes
- Use absolute paths for better reliability

### **Adding New Features**
- All new tools should integrate with the main menu system
- Use the configuration manager for settings
- Implement proper logging and progress reporting
- Follow the established UI patterns for consistency

## Next Steps

1. **Start the application**: `python start_rom_curator.py`
2. **Import your data**: File → Import Data → Metadata & DAT Importer
3. **Set up matching**: Tools → Database → Setup Matching System
4. **Curate matches**: Tools → Curation → DAT-Metadata Matching
5. **Review logs**: View → View Logs for detailed information

The unified application provides a much better user experience with progress feedback, comprehensive logging, and a single entry point for all functionality.
