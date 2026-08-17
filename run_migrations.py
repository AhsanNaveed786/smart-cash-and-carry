import hashlib
from pathlib import Path

import psycopg

from database import Base, engine
import models


MIGRATIONS_DIRECTORY = (
    Path(__file__).resolve().parent / "migrations"
)


def get_psycopg_database_url() -> str:
    database_url = engine.url.render_as_string(
        hide_password=False
    )
    return database_url.replace(
        "postgresql+psycopg://",
        "postgresql://",
        1,
    )


def migration_checksum(content: str) -> str:
    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()


def main() -> None:
    Base.metadata.create_all(bind=engine)

    migration_files = sorted(
        MIGRATIONS_DIRECTORY.glob("*.sql")
    )
    if not migration_files:
        raise RuntimeError("No migration files were found.")

    with psycopg.connect(
        get_psycopg_database_url(),
        autocommit=True,
    ) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS app_schema_migrations (
                version VARCHAR(255) PRIMARY KEY,
                checksum VARCHAR(64) NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )

        applied_count = 0
        skipped_count = 0

        for migration_file in migration_files:
            version = migration_file.name
            content = migration_file.read_text(
                encoding="utf-8"
            )
            checksum = migration_checksum(content)

            existing_checksum = connection.execute(
                """
                SELECT checksum
                FROM app_schema_migrations
                WHERE version = %s
                """,
                (version,),
            ).fetchone()

            if existing_checksum is not None:
                if existing_checksum[0] != checksum:
                    raise RuntimeError(
                        f"Migration checksum changed: {version}"
                    )
                print(f"SKIPPED  {version}")
                skipped_count += 1
                continue

            try:
                connection.execute(
                    content,
                    prepare=False,
                )
                connection.execute(
                    """
                    INSERT INTO app_schema_migrations (
                        version,
                        checksum
                    )
                    VALUES (%s, %s)
                    """,
                    (version, checksum),
                )
            except Exception:
                connection.execute("ROLLBACK")
                raise

            print(f"APPLIED  {version}")
            applied_count += 1

    print(
        "Migration complete: "
        f"{applied_count} applied, "
        f"{skipped_count} already applied."
    )


if __name__ == "__main__":
    main()
