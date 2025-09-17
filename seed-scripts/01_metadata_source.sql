PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE metadata_source (
    source_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    -- Path to the python script that can parse this source's files.
    -- e.g., 'scripts/seeders/1_import_dat_files.py'
    importer_script TEXT,
    schema_file_path TEXT
);
INSERT INTO metadata_source VALUES(1,'No-Intro','scripts/seeders/no-intro.py',NULL);
INSERT INTO metadata_source VALUES(2,'MobyGames','scripts/seeders/mobygames.py','seed-data/Moby/MobyGames.Schema.json');
INSERT INTO metadata_source VALUES(3,'TOSEC','scripts/seeders/tosec.py','seed-data/TOSEC/schema/TOSEC.dtd');
COMMIT;
