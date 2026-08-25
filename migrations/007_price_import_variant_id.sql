-- Migration 007: Add variant_id to price_import_rows

BEGIN;

ALTER TABLE price_import_rows ADD COLUMN IF NOT EXISTS variant_id INTEGER REFERENCES product_variants(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_price_import_rows_variant_id ON price_import_rows (variant_id);

COMMIT;
