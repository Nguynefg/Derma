import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.database.models import (
    Base,
    User,
    LoginSession,
    Disease,
    Symptom,
    DiseaseSymptom,
    Reference,
    History,
    AuditLog,
    MedicalDocument,
    DocumentVersion,
    LibraryUpdate,
    now,
)
from app.database.config import configured_url

DATA_DIR = Path(os.getenv("DATA_DIR", str(Path(__file__).resolve().parents[2] / "data")))
DATABASE_URL = configured_url(DATA_DIR)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if str(DATABASE_URL).startswith("sqlite") else {},
    pool_pre_ping=True,
    hide_parameters=True,
)
if engine.dialect.name == "sqlite":
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    @event.listens_for(engine, "connect")
    def sqlite_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")


SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as db:
        yield db
