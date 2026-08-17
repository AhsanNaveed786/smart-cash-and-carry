BEGIN;

ALTER TABLE admins
    ADD COLUMN IF NOT EXISTS role VARCHAR(30),
    ADD COLUMN IF NOT EXISTS login_allowed BOOLEAN,
    ADD COLUMN IF NOT EXISTS login_allowed_from TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS login_allowed_until TIMESTAMPTZ;

UPDATE admins
SET
    role = COALESCE(role, 'mini_admin'),
    login_allowed = COALESCE(login_allowed, TRUE);

UPDATE admins
SET role = 'super_admin'
WHERE id = (
    SELECT id
    FROM admins
    ORDER BY created_at, id
    LIMIT 1
)
AND NOT EXISTS (
    SELECT 1
    FROM admins
    WHERE role = 'super_admin'
);

ALTER TABLE admins
    ALTER COLUMN role SET DEFAULT 'mini_admin',
    ALTER COLUMN role SET NOT NULL,
    ALTER COLUMN login_allowed SET DEFAULT TRUE,
    ALTER COLUMN login_allowed SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'admin_valid_role'
    ) THEN
        ALTER TABLE admins
            ADD CONSTRAINT admin_valid_role
            CHECK (role IN ('super_admin', 'mini_admin'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_admins_role
    ON admins (role);

CREATE INDEX IF NOT EXISTS ix_admins_login_allowed
    ON admins (login_allowed);

CREATE UNIQUE INDEX IF NOT EXISTS uq_admins_one_super_admin
    ON admins (role)
    WHERE role = 'super_admin';

ALTER TABLE admin_sessions
    ADD COLUMN IF NOT EXISTS revoked_by_admin_id INTEGER,
    ADD COLUMN IF NOT EXISTS revoke_reason VARCHAR(255);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_admin_sessions_revoked_by_admin'
    ) THEN
        ALTER TABLE admin_sessions
            ADD CONSTRAINT fk_admin_sessions_revoked_by_admin
            FOREIGN KEY (revoked_by_admin_id)
            REFERENCES admins(id)
            ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_admin_sessions_revoked_by_admin_id
    ON admin_sessions (revoked_by_admin_id);

CREATE TABLE IF NOT EXISTS permissions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255) NOT NULL,
    is_assignable_to_mini_admin BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_permissions_code
    ON permissions (code);

CREATE TABLE IF NOT EXISTS admin_permissions (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER NOT NULL
        REFERENCES admins(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL
        REFERENCES permissions(id) ON DELETE CASCADE,
    granted_by_admin_id INTEGER
        REFERENCES admins(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_admin_permission
        UNIQUE (admin_id, permission_id)
);

CREATE INDEX IF NOT EXISTS ix_admin_permissions_admin_id
    ON admin_permissions (admin_id);

CREATE INDEX IF NOT EXISTS ix_admin_permissions_permission_id
    ON admin_permissions (permission_id);

CREATE TABLE IF NOT EXISTS admin_branch_access (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER NOT NULL
        REFERENCES admins(id) ON DELETE CASCADE,
    branch_id INTEGER NOT NULL
        REFERENCES branches(id) ON DELETE CASCADE,
    granted_by_admin_id INTEGER
        REFERENCES admins(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_admin_branch_access
        UNIQUE (admin_id, branch_id)
);

CREATE INDEX IF NOT EXISTS ix_admin_branch_access_admin_id
    ON admin_branch_access (admin_id);

CREATE INDEX IF NOT EXISTS ix_admin_branch_access_branch_id
    ON admin_branch_access (branch_id);

CREATE TABLE IF NOT EXISTS admin_audit_logs (
    id SERIAL PRIMARY KEY,
    actor_admin_id INTEGER
        REFERENCES admins(id) ON DELETE SET NULL,
    target_admin_id INTEGER
        REFERENCES admins(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    details JSON NOT NULL DEFAULT '{}',
    ip_address VARCHAR(45),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_admin_audit_logs_actor_admin_id
    ON admin_audit_logs (actor_admin_id);

CREATE INDEX IF NOT EXISTS ix_admin_audit_logs_target_admin_id
    ON admin_audit_logs (target_admin_id);

CREATE INDEX IF NOT EXISTS ix_admin_audit_logs_action
    ON admin_audit_logs (action);

CREATE INDEX IF NOT EXISTS ix_admin_audit_logs_created_at
    ON admin_audit_logs (created_at);

INSERT INTO permissions (
    code,
    description,
    is_assignable_to_mini_admin
)
VALUES
    ('products.read', 'View product listings', TRUE),
    ('prices.read', 'View branch product prices', TRUE),
    ('prices.update', 'Update assigned-branch prices', TRUE),
    ('orders.read', 'View assigned-branch orders', TRUE),
    ('orders.update_status', 'Change assigned-order status', TRUE),
    ('admins.manage', 'Create and control admins', FALSE),
    ('sessions.manage', 'View and revoke admin sessions', FALSE),
    ('exports.orders', 'Export order records', FALSE),
    ('exports.products', 'Export product and price records', FALSE),
    ('revenue.read', 'View revenue dashboards', FALSE),
    (
        'orders.delete_exported',
        'Delete successfully exported orders',
        FALSE
    )
ON CONFLICT (code) DO UPDATE
SET
    description = EXCLUDED.description,
    is_assignable_to_mini_admin =
        EXCLUDED.is_assignable_to_mini_admin;

COMMIT;
