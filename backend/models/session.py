"""DB session helper: Postgres when DATABASE_URL points there, local SQLite file otherwise."""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models.db import Base


def get_engine():
    url = os.getenv("DATABASE_URL", "sqlite:///./orbitiq.db")
    # Render/Postgres style URL fix
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
