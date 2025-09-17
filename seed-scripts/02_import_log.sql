PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE import_log (
    log_id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES metadata_source(source_id),
    file_name TEXT NOT NULL,
    file_hash TEXT NOT NULL, -- SHA1 hash of the imported file for idempotency
    import_timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    records_processed INTEGER DEFAULT 0,
    notes TEXT,
    UNIQUE(file_hash) -- Prevent the exact same file from being processed twice
);
INSERT INTO import_log VALUES(8,2,'MobyGames-SNES-Catalog.json','eb196df4f5a96aa515c00b36bb3db802cef2ac93534a7029b9b753c41a8a38f2','2025-09-16T18:31:41.926237','completed',1270,'Successfully processed 1270 game entries.');
INSERT INTO import_log VALUES(18,3,'Nintendo Famicom & Entertainment System - Applications - [NES] (TOSEC-v2025-01-15_CM).dat','d21dadc073ceb316f58935c1c2c735e26d310a4e69ef836fb05dcca6ec8533d4','2025-09-16T18:40:34.529781','completed',235,'Successfully processed 235 game entries for platform ''Nintendo Famicom & Entertainment System''.');
INSERT INTO import_log VALUES(19,3,'Nintendo Famicom & Entertainment System - Applications - [UNF] (TOSEC-v2011-02-22_CM).dat','dd7b944b4bfb845f81a06118c0b2b725d48fe2500b28bd8b76b30b08704e879f','2025-09-16T18:40:34.741312','completed',2,'Successfully processed 2 game entries for platform ''Nintendo Famicom & Entertainment System''.');
INSERT INTO import_log VALUES(20,3,'Nintendo Famicom & Entertainment System - Demos - [NES] (TOSEC-v2025-01-15_CM).dat','b9e65098b40d1e0fa75b23adc39a495e8a3ddbedbe674ab18bc05032930852cb','2025-09-16T18:40:34.971185','completed',222,'Successfully processed 222 game entries for platform ''Nintendo Famicom & Entertainment System''.');
INSERT INTO import_log VALUES(21,3,'Nintendo Famicom & Entertainment System - Demos - [UNF] (TOSEC-v2011-02-22_CM).dat','9d07e669c44c777b0dcb44eb443d822a15686191f99f6fe9f457ab8684146f1f','2025-09-16T18:40:35.188042','completed',6,'Successfully processed 6 game entries for platform ''Nintendo Famicom & Entertainment System''.');
INSERT INTO import_log VALUES(22,3,'Nintendo Famicom & Entertainment System - Educational (TOSEC-v2011-02-22_CM).dat','5b101fbface106fb2d6f71cf9af0cad393a9c4032c865b94334674a76fd2359a','2025-09-16T18:40:35.407429','completed',113,'Successfully processed 113 game entries for platform ''Nintendo Famicom & Entertainment System''.');
INSERT INTO import_log VALUES(23,3,'Nintendo Famicom & Entertainment System - Firmware (TOSEC-v2011-02-22_CM).dat','7c08978da50f3db79f4ccebb05876e556d775e3747a4cb0093da6b007793d03c','2025-09-16T18:40:35.632387','completed',12,'Successfully processed 12 game entries for platform ''Nintendo Famicom & Entertainment System''.');
INSERT INTO import_log VALUES(24,3,'Nintendo Famicom & Entertainment System - Games - [NES] (TOSEC-v2025-01-15_CM).dat','17cc50f66765462f3ba1e55e23d1ee3d53cdc267b80a12a955c65b654d042f3d','2025-09-16T18:40:37.764675','completed',12266,'Successfully processed 12266 game entries for platform ''Nintendo Famicom & Entertainment System''.');
INSERT INTO import_log VALUES(25,3,'Nintendo Famicom & Entertainment System - Games - [UNF] (TOSEC-v2011-02-22_CM).dat','21dc471c1182b6aa2e1e99a4523d71ec94e48488aff321812fa6d76e5b45d99a','2025-09-16T18:40:38.048940','completed',95,'Successfully processed 95 game entries for platform ''Nintendo Famicom & Entertainment System''.');
INSERT INTO import_log VALUES(26,3,'Nintendo Famicom & Entertainment System - Homebrew - Games (TOSEC-v2025-01-15_CM).dat','56e0c3677f08866ce462234a327bfbd8f5fdb0f87a21694f784d072e9fa2cf2b','2025-09-16T18:40:38.291700','completed',28,'Successfully processed 28 game entries for platform ''Nintendo Famicom & Entertainment System''.');
INSERT INTO import_log VALUES(27,1,'Nintendo - Nintendo Entertainment System (Headered) (20250914-033119).dat','6714bd2640f71a5b968f4bebefd67591b8b038608fcad39c605bd0da143c3dfe','2025-09-16T18:41:24.471342','completed',4429,'Successfully processed 4429 game entries for platform ''Nintendo Entertainment System''.');
INSERT INTO import_log VALUES(28,1,'Nintendo - Nintendo Entertainment System (Headered) (Aftermarket) (20250914-033119).dat','0e82306ce9e1daeea83dbbaa20683ab9d1dbae4d7023c8476a35ae5291262b02','2025-09-16T18:41:25.676634','completed',2866,'Successfully processed 2866 game entries for platform ''Nintendo Entertainment System''.');
INSERT INTO import_log VALUES(29,1,'Nintendo - Nintendo Entertainment System (Headerless) (20250914-033119).dat','41a5bac264920d94dd468dd7e1f24a7458ee52cab2e9fae10609074a2dfc81f3','2025-09-16T18:41:27.125464','completed',4433,'Successfully processed 4433 game entries for platform ''Nintendo Entertainment System''.');
INSERT INTO import_log VALUES(30,1,'Nintendo - Nintendo Entertainment System (Headerless) (Aftermarket) (20250914-033119).dat','99f2537d6f4c5f88345ad9a427b4efa455dda74956f835139b316aeeb2acab7d','2025-09-16T18:41:28.421006','completed',2866,'Successfully processed 2866 game entries for platform ''Nintendo Entertainment System''.');
INSERT INTO import_log VALUES(31,1,'Nintendo - Super Nintendo Entertainment System (20250903-215730).dat','2d5965c41c8c27bbc6c93c225d3396f445ec0ea46bc674002ad6f15ae4d67907','2025-09-16T18:41:29.612097','completed',4067,'Successfully processed 4067 game entries for platform ''Super Nintendo Entertainment System''.');
INSERT INTO import_log VALUES(32,1,'Nintendo - Super Nintendo Entertainment System (Aftermarket) (20250903-215730).dat','10c20f0b2ac0e7601d580f428a7b3e5f0209dd50688504e1b19ee274d7863438','2025-09-16T18:41:30.150946','completed',164,'Successfully processed 164 game entries for platform ''Super Nintendo Entertainment System''.');
INSERT INTO import_log VALUES(33,2,'MobyGames-NES-Catalog.json','97ff16ff3b2e506daf349c1dbb73288698196a2219f83b4f7093f8c6f55c1200','2025-09-16T18:43:57.663822','completed',1544,'Successfully processed 1544 game entries.');
COMMIT;
