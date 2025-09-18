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
INSERT OR IGNORE INTO file_extension (extension, category_id, description, mime_type, is_active, is_archive, is_rom, is_save, is_patch) VALUES
('.nes', 1, 'Nintendo Entertainment System ROM', 'application/x-nintendo-nes-rom', 1, 0, 1, 0, 0),
('.fds', 1, 'Famicom Disk System image', 'application/x-nintendo-fds-rom', 1, 1, 0, 0, 0),
('.sfc', 1, 'Super Nintendo ROM', 'application/x-snes-rom', 1, 1, 0, 0, 0),
('.smc', 1, 'Super Nintendo ROM (alternative)', 'application/x-snes-rom', 1, 1, 0, 0, 0),
('.gb', 1, 'Game Boy ROM', 'application/x-gameboy-rom', 1, 1, 0, 0, 0),
('.gbc', 1, 'Game Boy Color ROM', 'application/x-gameboy-color-rom', 1, 1, 0, 0, 0),
('.gba', 1, 'Game Boy Advance ROM', 'application/x-gba-rom', 1, 1, 0, 0, 0),
('.nds', 1, 'Nintendo DS ROM', 'application/x-nintendo-ds-rom', 1, 1, 0, 0, 0),
('.3ds', 1, 'Nintendo 3DS ROM', 'application/x-nintendo-3ds-rom', 1, 1, 0, 0, 0),
('.n64', 1, 'Nintendo 64 ROM', 'application/x-n64-rom', 1, 1, 0, 0, 0),
('.v64', 1, 'Nintendo 64 ROM (V64 format)', 'application/x-n64-rom', 1, 1, 0, 0, 0),
('.z64', 1, 'Nintendo 64 ROM (Z64 format)', 'application/x-n64-rom', 1, 1, 0, 0, 0),
('.wad', 1, 'Wii Virtual Console WAD', 'application/x-wii-wad', 1, 1, 0, 0, 0),
('.wbfs', 1, 'Wii WBFS image', 'application/x-wii-wbfs', 1, 1, 0, 0, 0),
('.iso', 1, 'Wii ISO image', 'application/x-wii-iso', 1, 1, 0, 0, 0),

-- Sega ROMs
('.sms', 1, 'Sega Master System ROM', 'application/x-sms-rom', 1, 1, 0, 0, 0),
('.gg', 1, 'Game Gear ROM', 'application/x-gamegear-rom', 1, 1, 0, 0, 0),
('.sg', 1, 'SG-1000 ROM', 'application/x-sg-1000-rom', 1, 1, 0, 0, 0),
('.sc', 1, 'SC-3000 ROM', 'application/x-sc-3000-rom', 1, 1, 0, 0, 0),
('.md', 1, 'Sega Genesis/Mega Drive ROM', 'application/x-genesis-rom', 1, 1, 0, 0, 0),
('.gen', 1, 'Sega Genesis ROM (alternative)', 'application/x-genesis-rom', 1, 1, 0, 0, 0),
('.smd', 1, 'Sega Genesis ROM (SMD format)', 'application/x-genesis-rom', 1, 1, 0, 0, 0),
('.bin', 1, 'Sega Genesis ROM (BIN format)', 'application/x-genesis-rom', 1, 1, 0, 0, 0),
('.32x', 1, 'Sega 32X ROM', 'application/x-32x-rom', 1, 1, 0, 0, 0),
('.cd', 1, 'Sega CD image', 'application/x-sega-cd-rom', 1, 1, 0, 0, 0),
('.cue', 1, 'Sega CD cue sheet', 'application/x-cue', 1, 1, 0, 0, 0),
('.chd', 1, 'Compressed Hunks of Data (Sega CD)', 'application/x-chd', 1, 1, 0, 0, 0),
('.sat', 1, 'Sega Saturn ROM', 'application/x-saturn-rom', 1, 1, 0, 0, 0),
('.mdf', 1, 'Sega Saturn MDF image', 'application/x-saturn-mdf', 1, 1, 0, 0, 0),
('.mds', 1, 'Sega Saturn MDS image', 'application/x-saturn-mds', 1, 1, 0, 0, 0),
('.gdi', 1, 'Sega Dreamcast GDI', 'application/x-dreamcast-gdi', 1, 1, 0, 0, 0),

-- Sony ROMs
('.psx', 1, 'PlayStation ROM', 'application/x-psx-rom', 1, 1, 0, 0, 0),
('.ps1', 1, 'PlayStation ROM (alternative)', 'application/x-psx-rom', 1, 1, 0, 0, 0),
('.ps2', 1, 'PlayStation 2 ROM', 'application/x-ps2-rom', 1, 1, 0, 0, 0),
('.psp', 1, 'PlayStation Portable ROM', 'application/x-psp-rom', 1, 1, 0, 0, 0),
('.pkg', 1, 'PlayStation Package', 'application/x-psp-pkg', 1, 1, 0, 0, 0),

-- Atari ROMs
('.a26', 1, 'Atari 2600 ROM', 'application/x-atari-2600-rom', 1, 1, 0, 0, 0),
('.a52', 1, 'Atari 5200 ROM', 'application/x-atari-5200-rom', 1, 1, 0, 0, 0),
('.a78', 1, 'Atari 7800 ROM', 'application/x-atari-7800-rom', 1, 1, 0, 0, 0),
('.lynx', 1, 'Atari Lynx ROM', 'application/x-atari-lynx-rom', 1, 1, 0, 0, 0),
('.jag', 1, 'Atari Jaguar ROM', 'application/x-atari-jaguar-rom', 1, 1, 0, 0, 0),

-- Other Console ROMs
('.pce', 1, 'PC Engine/TurboGrafx-16 ROM', 'application/x-pc-engine-rom', 1, 1, 0, 0, 0),
('.ngp', 1, 'Neo Geo Pocket ROM', 'application/x-neo-geo-pocket-rom', 1, 1, 0, 0, 0),
('.ngc', 1, 'Neo Geo Color ROM', 'application/x-neo-geo-color-rom', 1, 1, 0, 0, 0),
('.ws', 1, 'WonderSwan ROM', 'application/x-wonderswan-rom', 1, 1, 0, 0, 0),
('.wsc', 1, 'WonderSwan Color ROM', 'application/x-wonderswan-color-rom', 1, 1, 0, 0, 0),
('.int', 1, 'Intellivision ROM', 'application/x-intellivision-rom', 1, 1, 0, 0, 0),
('.col', 1, 'ColecoVision ROM', 'application/x-colecovision-rom', 1, 1, 0, 0, 0),
('.vec', 1, 'Vectrex ROM', 'application/x-vectrex-rom', 1, 1, 0, 0, 0),
('.chf', 1, 'Fairchild Channel F ROM', 'application/x-channel-f-rom', 1, 1, 0, 0, 0),

-- Computer ROMs
('.d64', 1, 'Commodore 64 disk image', 'application/x-c64-disk', 1, 1, 0, 0, 0),
('.d71', 1, 'Commodore 64 disk image (1571)', 'application/x-c64-disk', 1, 1, 0, 0, 0),
('.d81', 1, 'Commodore 64 disk image (1581)', 'application/x-c64-disk', 1, 1, 0, 0, 0),
('.g64', 1, 'Commodore 64 G64 disk image', 'application/x-c64-g64', 1, 1, 0, 0, 0),
('.t64', 1, 'Commodore 64 tape image', 'application/x-c64-tape', 1, 1, 0, 0, 0),
('.tap', 1, 'Commodore 64 tape image (TAP)', 'application/x-c64-tap', 1, 1, 0, 0, 0),
('.prg', 1, 'Commodore 64 program', 'application/x-c64-prg', 1, 1, 0, 0, 0),
('.crt', 1, 'Commodore 64 cartridge', 'application/x-c64-crt', 1, 1, 0, 0, 0),
('.p00', 1, 'Commodore 64 P00 file', 'application/x-c64-p00', 1, 1, 0, 0, 0),
('.s00', 1, 'Commodore 64 S00 file', 'application/x-c64-s00', 1, 1, 0, 0, 0),
('.dsk', 1, 'Apple II disk image', 'application/x-apple2-disk', 1, 1, 0, 0, 0),
('.do', 1, 'Apple II disk image (DO)', 'application/x-apple2-disk', 1, 1, 0, 0, 0),
('.po', 1, 'Apple II disk image (PO)', 'application/x-apple2-disk', 1, 1, 0, 0, 0),
('.nib', 1, 'Apple II NIB disk image', 'application/x-apple2-nib', 1, 1, 0, 0, 0),
('.2mg', 1, 'Apple II 2MG disk image', 'application/x-apple2-2mg', 1, 1, 0, 0, 0),
('.rom', 1, 'Generic ROM file', 'application/x-rom', 1, 1, 0, 0, 0),
('.bin', 1, 'Generic binary ROM', 'application/x-rom', 1, 1, 0, 0, 0),
('.hex', 1, 'Intel HEX ROM', 'application/x-intel-hex', 1, 1, 0, 0, 0),
('.s19', 1, 'Motorola S-record ROM', 'application/x-motorola-s19', 1, 1, 0, 0, 0);

-- =============================================================================
-- ARCHIVE FILE EXTENSIONS
-- =============================================================================

INSERT OR IGNORE INTO file_extension (extension, category_id, description, mime_type, is_active, is_rom, is_archive, is_save, is_patch) VALUES
('.zip', 2, 'ZIP archive', 'application/zip', 1, 0, 1, 0, 0),
('.7z', 2, '7-Zip archive', 'application/x-7z-compressed', 1, 0, 1, 0, 0),
('.rar', 2, 'RAR archive', 'application/x-rar-compressed', 1, 0, 1, 0, 0),
('.tar', 2, 'TAR archive', 'application/x-tar', 1, 0, 1, 0, 0),
('.gz', 2, 'GZIP compressed file', 'application/gzip', 1, 0, 1, 0, 0),
('.bz2', 2, 'BZIP2 compressed file', 'application/x-bzip2', 1, 0, 1, 0, 0),
('.xz', 2, 'XZ compressed file', 'application/x-xz', 1, 0, 1, 0, 0),
('.lha', 2, 'LHA archive', 'application/x-lha', 1, 0, 1, 0, 0),
('.lzh', 2, 'LZH archive', 'application/x-lzh', 1, 0, 1, 0, 0),
('.ace', 2, 'ACE archive', 'application/x-ace', 1, 0, 1, 0, 0),
('.cab', 2, 'CAB archive', 'application/vnd.ms-cab-compressed', 1, 0, 1, 0, 0),
('.arj', 2, 'ARJ archive', 'application/x-arj', 1, 0, 1, 0, 0),
('.z', 2, 'Compress compressed file', 'application/x-compress', 1, 0, 1, 0, 0),
('.Z', 2, 'Compress compressed file (uppercase)', 'application/x-compress', 1, 0, 1, 0, 0);

-- =============================================================================
-- SAVE FILE EXTENSIONS
-- =============================================================================

INSERT OR IGNORE INTO file_extension (extension, category_id, description, mime_type, is_active, is_rom, is_archive, is_save, is_patch) VALUES
('.sav', 3, 'Generic save file', 'application/x-save', 1, 0, 0, 1, 0),
('.srm', 3, 'SNES save file', 'application/x-snes-save', 1, 0, 0, 1, 0),
('.sra', 3, 'SNES save file (alternative)', 'application/x-snes-save', 1, 0, 0, 1, 0),
('.eep', 3, 'EEPROM save file', 'application/x-eeprom-save', 1, 0, 0, 1, 0),
('.sav', 3, 'Game Boy save file', 'application/x-gameboy-save', 1, 0, 0, 1, 0),
('.srm', 3, 'Game Boy save file (alternative)', 'application/x-gameboy-save', 1, 0, 0, 1, 0),
('.rtc', 3, 'Real-time clock save', 'application/x-rtc-save', 1, 0, 0, 1, 0),
('.mcr', 3, 'Memory card save', 'application/x-memory-card', 1, 0, 0, 1, 0),
('.ps1', 3, 'PlayStation memory card', 'application/x-psx-memory-card', 1, 0, 0, 1, 0),
('.ps2', 3, 'PlayStation 2 memory card', 'application/x-ps2-memory-card', 1, 0, 0, 1, 0),
('.vms', 3, 'Dreamcast VMU save', 'application/x-dreamcast-vmu', 1, 0, 0, 1, 0),
('.vmi', 3, 'Dreamcast VMU info', 'application/x-dreamcast-vmi', 1, 0, 0, 1, 0),
('.gci', 3, 'GameCube save file', 'application/x-gamecube-save', 1, 0, 0, 1, 0),
('.gcs', 3, 'GameCube save file (compressed)', 'application/x-gamecube-save', 1, 0, 0, 1, 0),
('.gca', 3, 'GameCube save file (alternative)', 'application/x-gamecube-save', 1, 0, 0, 1, 0),
('.wii', 3, 'Wii save file', 'application/x-wii-save', 1, 0, 0, 1, 0),
('.wad', 3, 'Wii save file (WAD)', 'application/x-wii-save', 1, 0, 0, 1, 0),
('.dat', 3, 'Generic save data', 'application/x-save-data', 1, 0, 0, 1, 0),
('.state', 3, 'Emulator save state', 'application/x-save-state', 1, 0, 0, 1, 0),
('.st0', 3, 'Emulator save state (slot 0)', 'application/x-save-state', 1, 0, 0, 1, 0),
('.st1', 3, 'Emulator save state (slot 1)', 'application/x-save-state', 1, 0, 0, 1, 0),
('.st2', 3, 'Emulator save state (slot 2)', 'application/x-save-state', 1, 0, 0, 1, 0),
('.st3', 3, 'Emulator save state (slot 3)', 'application/x-save-state', 1, 0, 0, 1, 0),
('.st4', 3, 'Emulator save state (slot 4)', 'application/x-save-state', 1, 0, 0, 1, 0),
('.st5', 3, 'Emulator save state (slot 5)', 'application/x-save-state', 1, 0, 0, 1, 0),
('.st6', 3, 'Emulator save state (slot 6)', 'application/x-save-state', 1, 0, 0, 1, 0),
('.st7', 3, 'Emulator save state (slot 7)', 'application/x-save-state', 1, 0, 0, 1, 0),
('.st8', 3, 'Emulator save state (slot 8)', 'application/x-save-state', 1, 0, 0, 1, 0),
('.st9', 3, 'Emulator save state (slot 9)', 'application/x-save-state', 1, 0, 0, 1, 0);

-- =============================================================================
-- PATCH FILE EXTENSIONS
-- =============================================================================

INSERT OR IGNORE INTO file_extension (extension, category_id, description, mime_type, is_active, is_rom, is_archive, is_patch) VALUES
('.ips', 4, 'IPS patch file', 'application/x-ips-patch', 1, 0, 0, 0, 1),
('.bps', 4, 'BPS patch file', 'application/x-bps-patch', 1, 0, 0, 0, 1),
('.ups', 4, 'UPS patch file', 'application/x-ups-patch', 1, 0, 0, 0, 1),
('.xdelta', 4, 'XDelta patch file', 'application/x-xdelta-patch', 1, 0, 0, 0, 1),
('.xdelta3', 4, 'XDelta3 patch file', 'application/x-xdelta3-patch', 1, 0, 0, 0, 1),
('.ppf', 4, 'PPF patch file', 'application/x-ppf-patch', 1, 0, 0, 0, 1),
('.aps', 4, 'APS patch file', 'application/x-aps-patch', 1, 0, 0, 0, 1),
('.vcdiff', 4, 'VCDiff patch file', 'application/x-vcdiff', 1, 0, 0, 0, 1),
('.diff', 4, 'Generic diff file', 'text/x-diff', 1, 0, 0, 0, 1),
('.patch', 4, 'Generic patch file', 'text/x-patch', 1, 0, 0, 0, 1);

-- =============================================================================
-- DOCUMENTATION FILE EXTENSIONS
-- =============================================================================

INSERT OR IGNORE INTO file_extension (extension, category_id, description, mime_type, is_active, is_rom, is_archive, is_save, is_patch) VALUES
('.txt', 5, 'Text file', 'text/plain', 1, 0, 0, 0, 0),
('.pdf', 5, 'PDF document', 'application/pdf', 1, 0, 0, 0, 0),
('.doc', 5, 'Microsoft Word document', 'application/msword', 1, 0, 0, 0, 0),
('.docx', 5, 'Microsoft Word document (2007+)', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 1, 0, 0, 0, 0),
('.rtf', 5, 'Rich Text Format', 'application/rtf', 1, 0, 0, 0, 0),
('.html', 5, 'HTML document', 'text/html', 1, 0, 0, 0, 0),
('.htm', 5, 'HTML document (short)', 'text/html', 1, 0, 0, 0, 0),
('.md', 5, 'Markdown document', 'text/markdown', 1, 0, 0, 0, 0),
('.readme', 5, 'Readme file', 'text/plain', 1, 0, 0, 0, 0),
('.nfo', 5, 'NFO information file', 'text/plain', 1, 0, 0, 0, 0);

-- =============================================================================
-- MEDIA FILE EXTENSIONS
-- =============================================================================

INSERT OR IGNORE INTO file_extension (extension, category_id, description, mime_type, is_active, is_rom, is_archive, is_save, is_patch) VALUES
('.png', 6, 'PNG image', 'image/png', 1, 0, 0, 0, 0),
('.jpg', 6, 'JPEG image', 'image/jpeg', 1, 0, 0, 0, 0),
('.jpeg', 6, 'JPEG image (alternative)', 'image/jpeg', 1, 0, 0, 0, 0),
('.gif', 6, 'GIF image', 'image/gif', 1, 0, 0, 0, 0),
('.bmp', 6, 'Bitmap image', 'image/bmp', 1, 0, 0, 0, 0),
('.tiff', 6, 'TIFF image', 'image/tiff', 1, 0, 0, 0, 0),
('.tif', 6, 'TIFF image (short)', 'image/tiff', 1, 0, 0, 0, 0),
('.ico', 6, 'Icon file', 'image/x-icon', 1, 0, 0, 0, 0),
('.svg', 6, 'SVG vector image', 'image/svg+xml', 1, 0, 0, 0, 0),
('.mp3', 6, 'MP3 audio', 'audio/mpeg', 1, 0, 0, 0, 0),
('.wav', 6, 'WAV audio', 'audio/wav', 1, 0, 0, 0, 0),
('.ogg', 6, 'OGG audio', 'audio/ogg', 1, 0, 0, 0, 0),
('.flac', 6, 'FLAC audio', 'audio/flac', 1, 0, 0, 0, 0),
('.mp4', 6, 'MP4 video', 'video/mp4', 1, 0, 0, 0, 0),
('.avi', 6, 'AVI video', 'video/x-msvideo', 1, 0, 0, 0, 0),
('.mkv', 6, 'Matroska video', 'video/x-matroska', 1, 0, 0, 0, 0),
('.webm', 6, 'WebM video', 'video/webm', 1, 0, 0, 0, 0);

-- =============================================================================
-- SYSTEM FILE EXTENSIONS
-- =============================================================================

INSERT OR IGNORE INTO file_extension (extension, category_id, description, mime_type, is_active, is_rom, is_archive, is_save, is_patch) VALUES
('.cfg', 7, 'Configuration file', 'text/plain', 1, 0, 0, 0, 0),
('.ini', 7, 'INI configuration file', 'text/plain', 1, 0, 0, 0, 0),
('.conf', 7, 'Configuration file', 'text/plain', 1, 0, 0, 0, 0),
('.config', 7, 'Configuration file', 'text/plain', 1, 0, 0, 0, 0),
('.xml', 7, 'XML file', 'application/xml', 1, 0, 0, 0, 0),
('.json', 7, 'JSON file', 'application/json', 1, 0, 0, 0, 0),
('.yaml', 7, 'YAML file', 'application/x-yaml', 1, 0, 0, 0, 0),
('.yml', 7, 'YAML file (short)', 'application/x-yaml', 1, 0, 0, 0, 0),
('.log', 7, 'Log file', 'text/plain', 1, 0, 0, 0, 0),
('.tmp', 7, 'Temporary file', 'text/plain', 1, 0, 0, 0, 0),
('.temp', 7, 'Temporary file', 'text/plain', 1, 0, 0, 0, 0),
('.bak', 7, 'Backup file', 'text/plain', 1, 0, 0, 0, 0),
('.backup', 7, 'Backup file', 'text/plain', 1, 0, 0, 0, 0);

-- =============================================================================
-- PLATFORM EXTENSION MAPPINGS
-- =============================================================================

-- Note: These mappings will be created after platforms are seeded
-- This is a template for common platform-extension relationships

-- Example mappings (these will be created by the application when platforms exist):
-- INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) VALUES
-- (1, 1, 1, 1.0),  -- NES platform -> .nes extension
-- (2, 2, 1, 1.0),  -- SNES platform -> .sfc extension
-- etc.

-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================

-- Verify the seed data was inserted correctly
SELECT 'Categories' as table_name, COUNT(*) as count FROM file_type_category
UNION ALL
SELECT 'Extensions' as table_name, COUNT(*) as count FROM file_extension
UNION ALL
SELECT 'Platform Mappings' as table_name, COUNT(*) as count FROM platform_extension;

-- Show extension counts by category
SELECT 
    ftc.name as category_name,
    COUNT(fe.extension_id) as extension_count,
    COUNT(CASE WHEN fe.is_active = 1 THEN 1 END) as active_count
FROM file_type_category ftc
LEFT JOIN file_extension fe ON ftc.category_id = fe.category_id
GROUP BY ftc.category_id, ftc.name
ORDER BY ftc.sort_order;