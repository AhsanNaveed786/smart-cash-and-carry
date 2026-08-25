-- Migration 006: Add variant detection columns to product_import_rows

BEGIN;

ALTER TABLE product_import_rows ADD COLUMN IF NOT EXISTS variant_group_key VARCHAR(255);
ALTER TABLE product_import_rows ADD COLUMN IF NOT EXISTS variant_size_label VARCHAR(100);
ALTER TABLE product_import_rows ADD COLUMN IF NOT EXISTS merge_as_variant BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE product_import_rows ADD COLUMN IF NOT EXISTS variant_master_row_id INTEGER REFERENCES product_import_rows(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_product_import_rows_variant_group_key ON product_import_rows (variant_group_key);

COMMIT;
