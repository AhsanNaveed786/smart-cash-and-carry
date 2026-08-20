import os
from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is missing. Add it to the .env file."
    )


# PostgreSQL connection pool tuned for production workloads.
# pool_size       — persistent connections kept open
# max_overflow    — extra connections allowed under burst load
# pool_timeout    — seconds to wait for a connection before raising
# pool_recycle    — recycle connections older than 30 minutes
#                   (prevents stale connection errors after DB restarts)
# pool_pre_ping   — verify connections are alive before using them
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
    connect_args={
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    } if DATABASE_URL.startswith("postgresql") else {},
)


SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    database = SessionLocal()

    try:
        yield database
    finally:
        database.close()