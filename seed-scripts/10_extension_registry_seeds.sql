-- =============================================================================
-- EXTENSION REGISTRY SEED DATA
-- =============================================================================
-- This script populates the extension registry with sensible defaults for
-- common file types encountered in ROM collections.

-- Insert file type categories
INSERT OR IGNORE INTO file_type_category (category_id, name, description, sort_order, is_active) VALUES
(1, 'Nintendo ROMs', 'Nintendo console ROM files', 10, 1),
(2, 'Sega ROMs', 'Sega console ROM files', 20, 1),
(3, 'Sony ROMs', 'Sony console ROM files', 30, 1),
(4, 'Microsoft ROMs', 'Microsoft console ROM files', 40, 1),
(5, 'Arcade ROMs', 'Arcade machine ROM files', 50, 1),
(6, 'Computer ROMs', 'Computer system ROM files', 60, 1),
(7, 'Handheld ROMs', 'Handheld console ROM files', 70, 1),
(8, 'Archive Files', 'Compressed archive files', 80, 1),
(9, 'Save Files', 'Game save files', 90, 1),
(10, 'Patch Files', 'Game patch and modification files', 100, 1),
(11, 'Other Files', 'Other file types', 999, 1);

-- Insert file extensions
INSERT OR IGNORE INTO file_extension (extension, category_id, description, mime_type, is_active, is_rom, is_archive, is_save, is_patch) VALUES
-- Nintendo ROMs
('.nes', 1, 'Nintendo Entertainment System ROM', 'application/x-nes-rom', 1, 1, 0, 0, 0),
('.sfc', 1, 'Super Nintendo Entertainment System ROM', 'application/x-snes-rom', 1, 1, 0, 0, 0),
('.smc', 1, 'Super Nintendo Entertainment System ROM', 'application/x-snes-rom', 1, 1, 0, 0, 0),
('.n64', 1, 'Nintendo 64 ROM', 'application/x-n64-rom', 1, 1, 0, 0, 0),
('.z64', 1, 'Nintendo 64 ROM (Z64 format)', 'application/x-n64-rom', 1, 1, 0, 0, 0),
('.v64', 1, 'Nintendo 64 ROM (V64 format)', 'application/x-n64-rom', 1, 1, 0, 0, 0),
('.gc', 1, 'GameCube ROM', 'application/x-gamecube-rom', 1, 1, 0, 0, 0),
('.gcm', 1, 'GameCube ROM', 'application/x-gamecube-rom', 1, 1, 0, 0, 0),
('.wad', 1, 'Wii WAD file', 'application/x-wii-wad', 1, 1, 0, 0, 0),
('.wbfs', 1, 'Wii WBFS file', 'application/x-wii-wbfs', 1, 1, 0, 0, 0),
('.gb', 1, 'Game Boy ROM', 'application/x-gameboy-rom', 1, 1, 0, 0, 0),
('.gbc', 1, 'Game Boy Color ROM', 'application/x-gameboy-color-rom', 1, 1, 0, 0, 0),
('.gba', 1, 'Game Boy Advance ROM', 'application/x-gba-rom', 1, 1, 0, 0, 0),
('.nds', 1, 'Nintendo DS ROM', 'application/x-nintendo-ds-rom', 1, 1, 0, 0, 0),
('.3ds', 1, 'Nintendo 3DS ROM', 'application/x-nintendo-3ds-rom', 1, 1, 0, 0, 0),

-- Sega ROMs
('.sms', 2, 'Sega Master System ROM', 'application/x-sms-rom', 1, 1, 0, 0, 0),
('.gg', 2, 'Game Gear ROM', 'application/x-gamegear-rom', 1, 1, 0, 0, 0),
('.md', 2, 'Sega Mega Drive ROM', 'application/x-genesis-rom', 1, 1, 0, 0, 0),
('.smd', 2, 'Sega Mega Drive ROM', 'application/x-genesis-rom', 1, 1, 0, 0, 0),
('.gen', 2, 'Sega Genesis ROM', 'application/x-genesis-rom', 1, 1, 0, 0, 0),
('.32x', 2, 'Sega 32X ROM', 'application/x-32x-rom', 1, 1, 0, 0, 0),
('.ss', 2, 'Sega Saturn ROM', 'application/x-saturn-rom', 1, 1, 0, 0, 0),
('.cdi', 2, 'Sega Saturn CDI', 'application/x-saturn-rom', 1, 1, 0, 0, 0),
('.dc', 2, 'Sega Dreamcast ROM', 'application/x-dreamcast-rom', 1, 1, 0, 0, 0),
('.gdi', 2, 'Sega Dreamcast GDI', 'application/x-dreamcast-rom', 1, 1, 0, 0, 0),

-- Sony ROMs
('.psx', 3, 'PlayStation ROM', 'application/x-psx-rom', 1, 1, 0, 0, 0),
('.ps1', 3, 'PlayStation ROM', 'application/x-psx-rom', 1, 1, 0, 0, 0),
('.ps2', 3, 'PlayStation 2 ROM', 'application/x-ps2-rom', 1, 1, 0, 0, 0),
('.ps3', 3, 'PlayStation 3 ROM', 'application/x-ps3-rom', 1, 1, 0, 0, 0),
('.ps4', 3, 'PlayStation 4 ROM', 'application/x-ps4-rom', 1, 1, 0, 0, 0),
('.ps5', 3, 'PlayStation 5 ROM', 'application/x-ps5-rom', 1, 1, 0, 0, 0),
('.psp', 3, 'PlayStation Portable ROM', 'application/x-psp-rom', 1, 1, 0, 0, 0),
('.psv', 3, 'PlayStation Vita ROM', 'application/x-psv-rom', 1, 1, 0, 0, 0),

-- Microsoft ROMs
('.xbe', 4, 'Xbox XBE file', 'application/x-xbox-xbe', 1, 1, 0, 0, 0),
('.xex', 4, 'Xbox 360 XEX file', 'application/x-xbox360-xex', 1, 1, 0, 0, 0),
('.xbox', 4, 'Xbox ROM', 'application/x-xbox-rom', 1, 1, 0, 0, 0),
('.xbox360', 4, 'Xbox 360 ROM', 'application/x-xbox360-rom', 1, 1, 0, 0, 0),
('.xboxone', 4, 'Xbox One ROM', 'application/x-xboxone-rom', 1, 1, 0, 0, 0),
('.xboxseries', 4, 'Xbox Series ROM', 'application/x-xboxseries-rom', 1, 1, 0, 0, 0),

-- Arcade ROMs
('.mame', 5, 'MAME ROM', 'application/x-mame-rom', 1, 1, 0, 0, 0),
('.fba', 5, 'FinalBurn Alpha ROM', 'application/x-fba-rom', 1, 1, 0, 0, 0),
('.neogeo', 5, 'Neo Geo ROM', 'application/x-neogeo-rom', 1, 1, 0, 0, 0),

-- Computer ROMs
('.pc', 6, 'PC ROM', 'application/x-pc-rom', 1, 1, 0, 0, 0),
('.dos', 6, 'DOS ROM', 'application/x-dos-rom', 1, 1, 0, 0, 0),
('.win', 6, 'Windows ROM', 'application/x-windows-rom', 1, 1, 0, 0, 0),
('.mac', 6, 'Macintosh ROM', 'application/x-mac-rom', 1, 1, 0, 0, 0),
('.linux', 6, 'Linux ROM', 'application/x-linux-rom', 1, 1, 0, 0, 0),

-- Handheld ROMs
('.lynx', 7, 'Atari Lynx ROM', 'application/x-lynx-rom', 1, 1, 0, 0, 0),
('.ngp', 7, 'Neo Geo Pocket ROM', 'application/x-ngp-rom', 1, 1, 0, 0, 0),
('.ws', 7, 'WonderSwan ROM', 'application/x-wonderswan-rom', 1, 1, 0, 0, 0),
('.wsc', 7, 'WonderSwan Color ROM', 'application/x-wonderswan-color-rom', 1, 1, 0, 0, 0),

-- Archive Files
('.zip', 8, 'ZIP archive', 'application/zip', 1, 0, 1, 0, 0),
('.7z', 8, '7-Zip archive', 'application/x-7z-compressed', 1, 0, 1, 0, 0),
('.rar', 8, 'RAR archive', 'application/x-rar-compressed', 1, 0, 1, 0, 0),
('.tar', 8, 'TAR archive', 'application/x-tar', 1, 0, 1, 0, 0),
('.gz', 8, 'GZIP archive', 'application/gzip', 1, 0, 1, 0, 0),
('.bz2', 8, 'BZIP2 archive', 'application/x-bzip2', 1, 0, 1, 0, 0),
('.xz', 8, 'XZ archive', 'application/x-xz', 1, 0, 1, 0, 0),

-- Save Files
('.sav', 9, 'Game save file', 'application/x-game-save', 1, 0, 0, 1, 0),
('.save', 9, 'Game save file', 'application/x-game-save', 1, 0, 0, 1, 0),
('.srm', 9, 'Game save file', 'application/x-game-save', 1, 0, 0, 1, 0),
('.state', 9, 'Emulator state file', 'application/x-emulator-state', 1, 0, 0, 1, 0),
('.quicksave', 9, 'Quick save file', 'application/x-game-save', 1, 0, 0, 1, 0),

-- Patch Files
('.ips', 10, 'IPS patch file', 'application/x-ips-patch', 1, 0, 0, 0, 1),
('.bps', 10, 'BPS patch file', 'application/x-bps-patch', 1, 0, 0, 0, 1),
('.ups', 10, 'UPS patch file', 'application/x-ups-patch', 1, 0, 0, 0, 1),
('.xdelta', 10, 'XDelta patch file', 'application/x-xdelta-patch', 1, 0, 0, 0, 1),
('.ppf', 10, 'PPF patch file', 'application/x-ppf-patch', 1, 0, 0, 0, 1),

-- Other Files
('.iso', 11, 'ISO image file', 'application/x-iso9660-image', 1, 0, 0, 0, 0),
('.bin', 11, 'Binary file', 'application/octet-stream', 1, 0, 0, 0, 0),
('.cue', 11, 'CUE sheet file', 'application/x-cue', 1, 0, 0, 0, 0),
('.img', 11, 'Disk image file', 'application/x-disk-image', 1, 0, 0, 0, 0),
('.dmg', 11, 'Disk image file', 'application/x-apple-diskimage', 1, 0, 0, 0, 0);

-- Insert platform mappings
-- Note: This assumes platforms exist in the platform table
-- You may need to adjust platform IDs based on your actual platform data

-- Nintendo platform mappings
INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'Nintendo Entertainment System' AND fe.extension = '.nes';

INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'Super Nintendo Entertainment System' AND fe.extension = '.sfc';

INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'Nintendo 64' AND fe.extension = '.n64';

INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'GameCube' AND fe.extension = '.gc';

INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'Wii' AND fe.extension = '.wad';

INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'Game Boy' AND fe.extension = '.gb';

INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'Game Boy Color' AND fe.extension = '.gbc';

INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'Game Boy Advance' AND fe.extension = '.gba';

INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'Nintendo DS' AND fe.extension = '.nds';

INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'Nintendo 3DS' AND fe.extension = '.3ds';

-- Sega platform mappings
INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'Sega Master System' AND fe.extension = '.sms';

INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'Game Gear' AND fe.extension = '.gg';

INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'Sega Mega Drive' AND fe.extension = '.md';

INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'Sega Genesis' AND fe.extension = '.gen';

INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'Sega 32X' AND fe.extension = '.32x';

INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'Sega Saturn' AND fe.extension = '.ss';

INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'Sega Dreamcast' AND fe.extension = '.dc';

-- Sony platform mappings
INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'PlayStation' AND fe.extension = '.psx';

INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'PlayStation 2' AND fe.extension = '.ps2';

INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'PlayStation 3' AND fe.extension = '.ps3';

INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'PlayStation Portable' AND fe.extension = '.psp';

-- Microsoft platform mappings
INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'Xbox' AND fe.extension = '.xbe';

INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'Xbox 360' AND fe.extension = '.xex';

-- Arcade platform mappings
INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'Arcade' AND fe.extension = '.mame';

-- Computer platform mappings
INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'PC' AND fe.extension = '.pc';

-- Handheld platform mappings
INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'Atari Lynx' AND fe.extension = '.lynx';

INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'Neo Geo Pocket' AND fe.extension = '.ngp';

INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 1, 1.0
FROM platform p, file_extension fe
WHERE p.name = 'WonderSwan' AND fe.extension = '.ws';

-- Generic platform mappings for common extensions
INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 0, 0.5
FROM platform p, file_extension fe
WHERE p.name = 'Generic' AND fe.extension = '.iso';

INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 0, 0.5
FROM platform p, file_extension fe
WHERE p.name = 'Generic' AND fe.extension = '.bin';

INSERT OR IGNORE INTO platform_extension (platform_id, extension_id, is_primary, confidence) 
SELECT p.platform_id, fe.extension_id, 0, 0.5
FROM platform p, file_extension fe
WHERE p.name = 'Generic' AND fe.extension = '.img';