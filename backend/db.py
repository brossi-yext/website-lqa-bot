# backend/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite database file path
DATABASE_URL = "sqlite:///./qa.db"

# Create the engine (connection to SQLite)
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# Create a session class for database operations
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()
