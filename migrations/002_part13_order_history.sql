BEGIN;

CREATE TABLE IF NOT EXISTS order_status_history (
    id SERIAL PRIMARY KEY,
    order_id INTEGER
        REFERENCES orders(id) ON DELETE SET NULL,
    order_number VARCHAR(40) NOT NULL,
    branch_id INTEGER
        REFERENCES branches(id) ON DELETE SET NULL,
    previous_status VARCHAR(30),
    new_status VARCHAR(30) NOT NULL,
    change_note VARCHAR(500),
    changed_by_admin_id INTEGER
        REFERENCES admins(id) ON DELETE SET NULL,
    changed_by_name VARCHAR(100),
    changed_by_email VARCHAR(320),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT order_history_valid_previous_status
        CHECK (
            previous_status IS NULL
            OR previous_status IN (
                'pending',
                'confirmed',
                'processing',
                'ready_for_pickup',
                'out_for_delivery',
                'completed',
                'cancelled'
            )
        ),
    CONSTRAINT order_history_valid_new_status
        CHECK (
            new_status IN (
                'pending',
                'confirmed',
                'processing',
                'ready_for_pickup',
                'out_for_delivery',
                'completed',
                'cancelled'
            )
        )
);

CREATE INDEX IF NOT EXISTS ix_order_status_history_order_id
    ON order_status_history (order_id);

CREATE INDEX IF NOT EXISTS ix_order_status_history_order_number
    ON order_status_history (order_number);

CREATE INDEX IF NOT EXISTS ix_order_status_history_branch_id
    ON order_status_history (branch_id);

CREATE INDEX IF NOT EXISTS ix_order_status_history_new_status
    ON order_status_history (new_status);

CREATE INDEX IF NOT EXISTS ix_order_status_history_changed_by_admin_id
    ON order_status_history (changed_by_admin_id);

CREATE INDEX IF NOT EXISTS ix_order_status_history_created_at
    ON order_status_history (created_at);

CREATE INDEX IF NOT EXISTS ix_order_history_number_created_at
    ON order_status_history (order_number, created_at);

INSERT INTO order_status_history (
    order_id,
    order_number,
    branch_id,
    previous_status,
    new_status,
    change_note,
    changed_by_admin_id,
    changed_by_name,
    changed_by_email,
    created_at
)
SELECT
    orders.id,
    orders.order_number,
    orders.branch_id,
    NULL,
    orders.status,
    'Existing order history baseline created during Part 13 migration.',
    NULL,
    NULL,
    NULL,
    orders.created_at
FROM orders
WHERE NOT EXISTS (
    SELECT 1
    FROM order_status_history
    WHERE order_status_history.order_number = orders.order_number
);

COMMIT;
