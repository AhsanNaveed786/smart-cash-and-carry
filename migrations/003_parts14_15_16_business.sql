BEGIN;

CREATE TABLE IF NOT EXISTS data_exports (
    id SERIAL PRIMARY KEY,
    export_type VARCHAR(30) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'completed',
    branch_id INTEGER
        REFERENCES branches(id) ON DELETE SET NULL,
    created_by_admin_id INTEGER
        REFERENCES admins(id) ON DELETE SET NULL,
    file_name VARCHAR(255) NOT NULL,
    file_sha256 VARCHAR(64) NOT NULL,
    filters_snapshot JSON NOT NULL DEFAULT '{}',
    record_count INTEGER NOT NULL DEFAULT 0,
    total_amount NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    allows_order_deletion BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_order_count INTEGER NOT NULL DEFAULT 0,
    orders_deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT data_export_valid_type
        CHECK (export_type IN ('orders', 'products')),
    CONSTRAINT data_export_valid_status
        CHECK (status IN ('completed', 'failed')),
    CONSTRAINT data_export_counts_non_negative
        CHECK (record_count >= 0 AND deleted_order_count >= 0),
    CONSTRAINT data_export_total_non_negative
        CHECK (total_amount >= 0)
);

CREATE INDEX IF NOT EXISTS ix_data_exports_export_type
    ON data_exports (export_type);

CREATE INDEX IF NOT EXISTS ix_data_exports_status
    ON data_exports (status);

CREATE INDEX IF NOT EXISTS ix_data_exports_branch_id
    ON data_exports (branch_id);

CREATE INDEX IF NOT EXISTS ix_data_exports_created_by_admin_id
    ON data_exports (created_by_admin_id);

CREATE INDEX IF NOT EXISTS ix_data_exports_created_at
    ON data_exports (created_at);

CREATE TABLE IF NOT EXISTS order_export_items (
    id SERIAL PRIMARY KEY,
    export_id INTEGER NOT NULL
        REFERENCES data_exports(id) ON DELETE CASCADE,
    order_id INTEGER
        REFERENCES orders(id) ON DELETE SET NULL,
    order_number VARCHAR(40) NOT NULL,
    branch_id INTEGER
        REFERENCES branches(id) ON DELETE SET NULL,
    status_at_export VARCHAR(30) NOT NULL,
    total_amount NUMERIC(12, 2) NOT NULL,
    order_created_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    deleted_by_admin_id INTEGER
        REFERENCES admins(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_order_export_item
        UNIQUE (export_id, order_number),
    CONSTRAINT order_export_item_total_non_negative
        CHECK (total_amount >= 0)
);

CREATE INDEX IF NOT EXISTS ix_order_export_items_export_id
    ON order_export_items (export_id);

CREATE INDEX IF NOT EXISTS ix_order_export_items_order_id
    ON order_export_items (order_id);

CREATE INDEX IF NOT EXISTS ix_order_export_items_order_number
    ON order_export_items (order_number);

CREATE INDEX IF NOT EXISTS ix_order_export_items_branch_id
    ON order_export_items (branch_id);

CREATE INDEX IF NOT EXISTS ix_order_export_items_deleted_at
    ON order_export_items (deleted_at);

CREATE TABLE IF NOT EXISTS revenue_order_ledger (
    id SERIAL PRIMARY KEY,
    order_id INTEGER
        REFERENCES orders(id) ON DELETE SET NULL,
    order_number VARCHAR(40) NOT NULL UNIQUE,
    branch_id INTEGER
        REFERENCES branches(id) ON DELETE SET NULL,
    branch_name VARCHAR(100) NOT NULL,
    completion_date DATE NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL,
    total_amount NUMERIC(12, 2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT revenue_ledger_total_non_negative
        CHECK (total_amount >= 0)
);

CREATE INDEX IF NOT EXISTS ix_revenue_order_ledger_order_id
    ON revenue_order_ledger (order_id);

CREATE INDEX IF NOT EXISTS ix_revenue_order_ledger_order_number
    ON revenue_order_ledger (order_number);

CREATE INDEX IF NOT EXISTS ix_revenue_order_ledger_branch_id
    ON revenue_order_ledger (branch_id);

CREATE INDEX IF NOT EXISTS ix_revenue_order_ledger_completion_date
    ON revenue_order_ledger (completion_date);

CREATE INDEX IF NOT EXISTS ix_revenue_order_ledger_completed_at
    ON revenue_order_ledger (completed_at);

CREATE INDEX IF NOT EXISTS ix_revenue_ledger_date_branch
    ON revenue_order_ledger (completion_date, branch_id);

WITH completed_orders AS (
    SELECT
        orders.id AS order_id,
        orders.order_number,
        orders.branch_id,
        branches.name AS branch_name,
        orders.total_amount,
        COALESCE(
            (
                SELECT MIN(order_status_history.created_at)
                FROM order_status_history
                WHERE
                    order_status_history.order_number
                        = orders.order_number
                    AND order_status_history.new_status = 'completed'
            ),
            orders.updated_at,
            orders.created_at
        ) AS completed_at
    FROM orders
    JOIN branches ON branches.id = orders.branch_id
    WHERE orders.status = 'completed'
)
INSERT INTO revenue_order_ledger (
    order_id,
    order_number,
    branch_id,
    branch_name,
    completion_date,
    completed_at,
    total_amount
)
SELECT
    completed_orders.order_id,
    completed_orders.order_number,
    completed_orders.branch_id,
    completed_orders.branch_name,
    (
        completed_orders.completed_at
        AT TIME ZONE 'Asia/Karachi'
    )::DATE,
    completed_orders.completed_at,
    completed_orders.total_amount
FROM completed_orders
ON CONFLICT (order_number) DO NOTHING;

COMMIT;
