-- =============================================================================
-- EXTENSION REGISTRY SEED DATA
-- =============================================================================
-- This script seeds the extension registry with sensible defaults for common
-- file types encountered in ROM collections and game libraries.

-- Enable foreign key constraints
PRAGMA foreign_keys = ON;

-- =============================================================================
-- FILE TYPE CATEGORIES
-- =============================================================================

INSERT OR IGNORE INTO file_type_category (category_id, name, description, sort_order, is_active) VALUES
(1, 'ROM Files', 'Game ROM files and executables', 1, 1),
(2, 'Archive Files', 'Compressed archives containing ROMs', 2, 1),
(3, 'Save Files', 'Game save states and memory cards', 3, 1),
(4, 'Patch Files', 'ROM patches and modifications', 4, 1),
(5, 'Documentation', 'Game manuals, guides, and documentation', 5, 1),
(6, 'Media Files', 'Images, videos, and audio files', 6, 1),
(7, 'System Files', 'Emulator and system configuration files', 7, 1),
(8, 'Unknown', 'Unrecognized or unknown file types', 99, 1);

-- =============================================================================
-- ROM FILE EXTENSIONS
-- =============================================================================

-- Nintendo ROMs
INSERT OR IGNORE INTO file_extension (extension, category_id, description, is_active, treat_as_archive, treat_as_disc, treat_as_auxiliary) VALUES
('.nes', 1, 'Nintendo Entertainment System ROM', 1, 0, 0, 0),
('.fds', 1, 'Famicom Disk System image', 1, 0, 1, 0),
('.sfc', 1, 'Super Nintendo ROM', 1, 0, 0, 0),
('.smc', 1, 'Super Nintendo ROM (alternative)', 1, 0, 0, 0),
('.gb', 1, 'Game Boy ROM', 1, 0, 0, 0),
('.gbc', 1, 'Game Boy Color ROM', 1, 0, 0, 0),
('.gba', 1, 'Game Boy Advance ROM', 1, 0, 0, 0),
('.nds', 1, 'Nintendo DS ROM', 1, 0, 0, 0),
('.3ds', 1, 'Nintendo 3DS ROM', 1, 0, 0, 0),
('.n64', 1, 'Nintendo 64 ROM', 1, 0, 0, 0),
('.v64', 1, 'Nintendo 64 ROM (V64 format)', 1, 0, 0, 0),
('.z64', 1, 'Nintendo 64 ROM (Z64 format)', 1, 0, 0, 0),
('.wad', 1, 'Wii Virtual Console WAD', 1, 0, 0, 0),
('.wbfs', 1, 'Wii WBFS image', 1, 0, 1, 0),
('.iso', 1, 'Wii ISO image', 1, 0, 1, 0);

-- Sega ROMs
INSERT OR IGNORE INTO file_extension (extension, category_id, description, is_active, treat_as_archive, treat_as_disc, treat_as_auxiliary) VALUES
('.sms', 1, 'Sega Master System ROM', 1, 0, 0, 0),
('.gg', 1, 'Game Gear ROM', 1, 0, 0, 0),
('.sg', 1, 'SG-1000 ROM', 1, 0, 0, 0),
('.md', 1, 'Sega Genesis/Mega Drive ROM', 1, 0, 0, 0),
('.gen', 1, 'Sega Genesis ROM (alternative)', 1, 0, 0, 0),
('.smd', 1, 'Sega Mega Drive ROM', 1, 0, 0, 0),
('.32x', 1, 'Sega 32X ROM', 1, 0, 0, 0),
('.cdi', 1, 'Sega CD ISO', 1, 0, 1, 0),
('.cue', 1, 'Sega CD CUE sheet', 1, 0, 1, 0),
('.bin', 1, 'Sega CD BIN image', 1, 0, 1, 0),
('.sat', 1, 'Sega Saturn ROM', 1, 0, 0, 0),
('.chd', 1, 'Sega Saturn CHD image', 1, 0, 1, 0),
('.dc', 1, 'Dreamcast ROM', 1, 0, 0, 0),
('.gdi', 1, 'Dreamcast GDI image', 1, 0, 1, 0);

-- Sony ROMs
INSERT OR IGNORE INTO file_extension (extension, category_id, description, is_active, treat_as_archive, treat_as_disc, treat_as_auxiliary) VALUES
('.ps1', 1, 'PlayStation ROM', 1, 0, 0, 0),
('.psx', 1, 'PlayStation ROM (alternative)', 1, 0, 0, 0),
('.mdf', 1, 'PlayStation MDF image', 1, 0, 1, 0),
('.mds', 1, 'PlayStation MDS image', 1, 0, 1, 0),
('.img', 1, 'PlayStation IMG image', 1, 0, 1, 0),
('.pbp', 1, 'PlayStation Portable EBOOT', 1, 0, 0, 0),
('.cso', 1, 'PlayStation Portable CSO', 1, 0, 1, 0),
('.dax', 1, 'PlayStation Portable DAX', 1, 0, 1, 0);

-- Atari ROMs
INSERT OR IGNORE INTO file_extension (extension, category_id, description, is_active, treat_as_archive, treat_as_disc, treat_as_auxiliary) VALUES
('.a26', 1, 'Atari 2600 ROM', 1, 0, 0, 0),
('.a78', 1, 'Atari 7800 ROM', 1, 0, 0, 0),
('.lynx', 1, 'Atari Lynx ROM', 1, 0, 0, 0),
('.jag', 1, 'Atari Jaguar ROM', 1, 0, 0, 0),
('.j64', 1, 'Atari Jaguar ROM (alternative)', 1, 0, 0, 0);

-- Other ROMs
INSERT OR IGNORE INTO file_extension (extension, category_id, description, is_active, treat_as_archive, treat_as_disc, treat_as_auxiliary) VALUES
('.int', 1, 'Intellivision ROM', 1, 0, 0, 0),
('.col', 1, 'ColecoVision ROM', 1, 0, 0, 0),
('.vec', 1, 'Vectrex ROM', 1, 0, 0, 0),
('.pce', 1, 'PC Engine ROM', 1, 0, 0, 0),
('.tg16', 1, 'TurboGrafx-16 ROM', 1, 0, 0, 0),
('.ws', 1, 'WonderSwan ROM', 1, 0, 0, 0),
('.wsc', 1, 'WonderSwan Color ROM', 1, 0, 0, 0),
('.ngp', 1, 'Neo Geo Pocket ROM', 1, 0, 0, 0),
('.ngc', 1, 'Neo Geo Pocket Color ROM', 1, 0, 0, 0);

-- =============================================================================
-- ARCHIVE FILE EXTENSIONS
-- =============================================================================

INSERT OR IGNORE INTO file_extension (extension, category_id, description, is_active, treat_as_archive, treat_as_disc, treat_as_auxiliary) VALUES
('.zip', 2, 'ZIP archive', 1, 1, 0, 0),
('.7z', 2, '7-Zip archive', 1, 1, 0, 0),
('.rar', 2, 'RAR archive', 1, 1, 0, 0),
('.tar', 2, 'TAR archive', 1, 1, 0, 0),
('.gz', 2, 'GZIP archive', 1, 1, 0, 0),
('.bz2', 2, 'BZIP2 archive', 1, 1, 0, 0),
('.xz', 2, 'XZ archive', 1, 1, 0, 0),
('.lha', 2, 'LHA archive', 1, 1, 0, 0),
('.lzh', 2, 'LZH archive', 1, 1, 0, 0);

-- =============================================================================
-- SAVE FILE EXTENSIONS
-- =============================================================================

INSERT OR IGNORE INTO file_extension (extension, category_id, description, is_active, treat_as_archive, treat_as_disc, treat_as_auxiliary) VALUES
('.sav', 3, 'Generic save file', 1, 0, 0, 0),
('.srm', 3, 'SNES save file', 1, 0, 0, 0),
('.eep', 3, 'N64 EEPROM save', 1, 0, 0, 0),
('.fla', 3, 'N64 Flash save', 1, 0, 0, 0),
('.sra', 3, 'N64 SRAM save', 1, 0, 0, 0),
('.mcr', 3, 'Genesis save file', 1, 0, 0, 0),
('.psr', 3, 'PlayStation save file', 1, 0, 0, 0),
('.mcr', 3, 'Game Boy save file', 1, 0, 0, 0),
('.rtc', 3, 'Game Boy RTC save', 1, 0, 0, 0),
('.dsv', 3, 'DeSmuME save file', 1, 0, 0, 0),
('.duc', 3, 'DeSmuME save file', 1, 0, 0, 0),
('.sav', 3, 'VisualBoyAdvance save', 1, 0, 0, 0),
('.sgm', 3, 'VisualBoyAdvance save state', 1, 0, 0, 0);

-- =============================================================================
-- PATCH FILE EXTENSIONS
-- =============================================================================

INSERT OR IGNORE INTO file_extension (extension, category_id, description, is_active, treat_as_archive, treat_as_disc, treat_as_auxiliary) VALUES
('.ips', 4, 'IPS patch file', 1, 0, 0, 0),
('.bps', 4, 'BPS patch file', 1, 0, 0, 0),
('.ups', 4, 'UPS patch file', 1, 0, 0, 0),
('.xdelta', 4, 'XDelta patch file', 1, 0, 0, 0),
('.ppf', 4, 'PPF patch file', 1, 0, 0, 0);

-- =============================================================================
-- DOCUMENTATION FILE EXTENSIONS
-- =============================================================================

INSERT OR IGNORE INTO file_extension (extension, category_id, description, is_active, treat_as_archive, treat_as_disc, treat_as_auxiliary) VALUES
('.txt', 5, 'Text file', 1, 0, 0, 0),
('.pdf', 5, 'PDF document', 1, 0, 0, 0),
('.doc', 5, 'Word document', 1, 0, 0, 0),
('.docx', 5, 'Word document (new format)', 1, 0, 0, 0),
('.rtf', 5, 'Rich text format', 1, 0, 0, 0),
('.html', 5, 'HTML document', 1, 0, 0, 0),
('.htm', 5, 'HTML document', 1, 0, 0, 0),
('.xml', 5, 'XML document', 1, 0, 0, 0),
('.md', 5, 'Markdown document', 1, 0, 0, 0);

-- =============================================================================
-- MEDIA FILE EXTENSIONS
-- =============================================================================

INSERT OR IGNORE INTO file_extension (extension, category_id, description, is_active, treat_as_archive, treat_as_disc, treat_as_auxiliary) VALUES
('.png', 6, 'PNG image', 1, 0, 0, 0),
('.jpg', 6, 'JPEG image', 1, 0, 0, 0),
('.jpeg', 6, 'JPEG image', 1, 0, 0, 0),
('.gif', 6, 'GIF image', 1, 0, 0, 0),
('.bmp', 6, 'Bitmap image', 1, 0, 0, 0),
('.tiff', 6, 'TIFF image', 1, 0, 0, 0),
('.mp3', 6, 'MP3 audio', 1, 0, 0, 0),
('.wav', 6, 'WAV audio', 1, 0, 0, 0),
('.ogg', 6, 'OGG audio', 1, 0, 0, 0),
('.mp4', 6, 'MP4 video', 1, 0, 0, 0),
('.avi', 6, 'AVI video', 1, 0, 0, 0),
('.mkv', 6, 'MKV video', 1, 0, 0, 0);

-- =============================================================================
-- SYSTEM FILE EXTENSIONS
-- =============================================================================

INSERT OR IGNORE INTO file_extension (extension, category_id, description, is_active, treat_as_archive, treat_as_disc, treat_as_auxiliary) VALUES
('.cfg', 7, 'Configuration file', 1, 0, 0, 0),
('.ini', 7, 'INI configuration file', 1, 0, 0, 0),
('.conf', 7, 'Configuration file', 1, 0, 0, 0),
('.log', 7, 'Log file', 1, 0, 0, 0),
('.dat', 7, 'Data file', 1, 0, 0, 0),
('.dll', 7, 'Dynamic link library', 1, 0, 0, 0),
('.so', 7, 'Shared object', 1, 0, 0, 0),
('.exe', 7, 'Executable file', 1, 0, 0, 0);

-- =============================================================================
-- PLATFORM EXTENSION MAPPINGS
-- =============================================================================

-- Nintendo Platform Mappings
INSERT OR IGNORE INTO platform_extension (platform_id, extension, is_primary) VALUES
(1, '.nes', 1),   -- NES
(2, '.fds', 1),   -- Famicom Disk System
(3, '.sfc', 1),   -- SNES
(3, '.smc', 0),   -- SNES (alternative)
(4, '.gb', 1),    -- Game Boy
(5, '.gbc', 1),   -- Game Boy Color
(6, '.gba', 1),   -- Game Boy Advance
(7, '.nds', 1),   -- Nintendo DS
(8, '.3ds', 1),   -- Nintendo 3DS
(9, '.n64', 1),   -- Nintendo 64
(9, '.v64', 0),   -- Nintendo 64 (V64)
(9, '.z64', 0),   -- Nintendo 64 (Z64)
(10, '.wad', 1),  -- Wii
(10, '.wbfs', 0), -- Wii (WBFS)
(10, '.iso', 0);  -- Wii (ISO)

-- Sega Platform Mappings
INSERT OR IGNORE INTO platform_extension (platform_id, extension, is_primary) VALUES
(11, '.sms', 1),  -- Sega Master System
(12, '.gg', 1),   -- Game Gear
(13, '.sg', 1),   -- SG-1000
(14, '.md', 1),   -- Genesis/Mega Drive
(14, '.gen', 0),  -- Genesis (alternative)
(14, '.smd', 0),  -- Mega Drive (alternative)
(15, '.32x', 1),  -- Sega 32X
(16, '.cdi', 1),  -- Sega CD
(16, '.cue', 0),  -- Sega CD (CUE)
(16, '.bin', 0),  -- Sega CD (BIN)
(17, '.sat', 1),  -- Sega Saturn
(17, '.chd', 0),  -- Sega Saturn (CHD)
(18, '.dc', 1),   -- Dreamcast
(18, '.gdi', 0);  -- Dreamcast (GDI)

-- Sony Platform Mappings
INSERT OR IGNORE INTO platform_extension (platform_id, extension, is_primary) VALUES
(19, '.ps1', 1),  -- PlayStation
(19, '.psx', 0),  -- PlayStation (alternative)
(19, '.mdf', 0),  -- PlayStation (MDF)
(19, '.mds', 0),  -- PlayStation (MDS)
(19, '.img', 0),  -- PlayStation (IMG)
(20, '.pbp', 1),  -- PlayStation Portable
(20, '.cso', 0),  -- PlayStation Portable (CSO)
(20, '.dax', 0);  -- PlayStation Portable (DAX)

-- Atari Platform Mappings
INSERT OR IGNORE INTO platform_extension (platform_id, extension, is_primary) VALUES
(21, '.a26', 1),  -- Atari 2600
(22, '.a78', 1),  -- Atari 7800
(23, '.lynx', 1), -- Atari Lynx
(24, '.jag', 1),  -- Atari Jaguar
(24, '.j64', 0);  -- Atari Jaguar (alternative)

-- Other Platform Mappings
INSERT OR IGNORE INTO platform_extension (platform_id, extension, is_primary) VALUES
(25, '.int', 1),  -- Intellivision
(26, '.col', 1),  -- ColecoVision
(27, '.vec', 1),  -- Vectrex
(28, '.pce', 1),  -- PC Engine
(28, '.tg16', 0), -- TurboGrafx-16
(29, '.ws', 1),   -- WonderSwan
(29, '.wsc', 0),  -- WonderSwan Color
(30, '.ngp', 1),  -- Neo Geo Pocket
(30, '.ngc', 0);  -- Neo Geo Pocket Color