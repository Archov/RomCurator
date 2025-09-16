-- Add external_id column to dat_entry table for better clone relationship tracking
-- This allows us to store the original ID from DAT files which is used for clone relationships

ALTER TABLE dat_entry ADD COLUMN external_id TEXT;

-- Create an index on external_id for performance when looking up clone relationships
CREATE INDEX IF NOT EXISTS idx_dat_entry_external_id ON dat_entry(external_id);
