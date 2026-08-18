BEGIN;

ALTER TABLE price_import_batches
    ADD COLUMN IF NOT EXISTS product_import_batch_id INTEGER;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_price_import_product_batch'
    ) THEN
        ALTER TABLE price_import_batches
            ADD CONSTRAINT fk_price_import_product_batch
            FOREIGN KEY (product_import_batch_id)
            REFERENCES product_import_batches(id)
            ON DELETE SET NULL;
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS ix_price_import_product_batch_id
    ON price_import_batches (product_import_batch_id);

ALTER TABLE product_import_rows
    ADD COLUMN IF NOT EXISTS suggested_category_name VARCHAR(120),
    ADD COLUMN IF NOT EXISTS confirmed_category_name VARCHAR(120);

INSERT INTO permissions (
    code,
    description,
    is_assignable_to_mini_admin
)
VALUES (
    'imports.manage',
    'Upload and review product and price imports',
    TRUE
)
ON CONFLICT (code) DO UPDATE
SET
    description = EXCLUDED.description,
    is_assignable_to_mini_admin = TRUE;

COMMIT;
