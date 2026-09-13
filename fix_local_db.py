from sqlalchemy import text
from database import engine

def fix_db():
    queries = [
        "ALTER TABLE website_settings ADD COLUMN IF NOT EXISTS delivery_charges NUMERIC(12, 2) DEFAULT 0.00 NOT NULL;",
        "ALTER TABLE website_settings ADD COLUMN IF NOT EXISTS free_delivery_threshold NUMERIC(12, 2) DEFAULT 3000.00 NOT NULL;",
        "ALTER TABLE website_settings ADD COLUMN IF NOT EXISTS min_order_amount_for_delivery NUMERIC(12, 2) DEFAULT 0.00 NOT NULL;",
        "ALTER TABLE website_settings ADD COLUMN IF NOT EXISTS theme_color VARCHAR(20) DEFAULT '#005c4b' NOT NULL;"
    ]
    with engine.begin() as conn:
        for q in queries:
            try:
                conn.execute(text(q))
            except Exception as e:
                print(f"Error executing {q}: {e}")
    print("Local database fixed!")

fix_db()
