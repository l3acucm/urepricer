"""
Database configuration and session management.
Uses SQLAlchemy with synchronous connections for simplicity.
"""
from typing import Generator
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from loguru import logger

from src.core.config import get_settings

settings = get_settings()

# Create database engine
engine = create_engine(
    settings.sync_database_url,
    pool_pre_ping=True,
    pool_recycle=300,  # Recycle connections every 5 minutes
    echo=settings.debug,  # Log SQL queries in debug mode
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base with custom metadata for naming conventions
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    }
)

Base = declarative_base(metadata=metadata)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI endpoints to get database session.
    Automatically handles session cleanup.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def create_tables():
    """Create database tables if they don't exist."""
    try:
        logger.info("Ensuring database tables exist...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified/created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


def get_session() -> Session:
    """Get a new database session (for use outside FastAPI endpoints)."""
    return SessionLocal()