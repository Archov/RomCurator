-- ALTER STATEMENT FOR EXISTING DATABASES
-- Run this to add the external_id column to existing dat_entry tables

-- Add the external_id column
ALTER TABLE dat_entry ADD COLUMN external_id TEXT;

-- Create index on the new column for performance
CREATE INDEX IF NOT EXISTS idx_dat_entry_external_id ON dat_entry(external_id);

-- Note: After running this ALTER, you should re-import your DAT files 
-- using the updated No-Intro.py script to populate the external_id values.
