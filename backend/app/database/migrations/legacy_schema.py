"""Database-neutral model metadata; importing this module never opens a database."""

from datetime import datetime, timezone
from sqlalchemy import (
    String as SQLString,
    Text as SQLText,
    Unicode,
    ForeignKey,
    Boolean,
    DateTime,
    JSON,
    Integer,
)
from sqlalchemy.dialects.mssql import NVARCHAR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def String(length):
    return SQLString(length).with_variant(Unicode(length), "mssql")


Text = SQLText().with_variant(NVARCHAR(None), "mssql")


def now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LoginSession(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    csrf: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Disease(Base):
    __tablename__ = "diseases"
    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    english_name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(60))
    summary: Mapped[str] = mapped_column(Text)
    details: Mapped[str] = mapped_column(Text)
    risk_factors: Mapped[str] = mapped_column(Text)
    prevention: Mapped[str] = mapped_column(Text)
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    review_status: Mapped[str] = mapped_column(String(40), default="source_summary")
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Symptom(Base):
    __tablename__ = "symptoms"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))


class DiseaseSymptom(Base):
    __tablename__ = "disease_symptoms"
    disease_id: Mapped[str] = mapped_column(
        ForeignKey("diseases.id", ondelete="CASCADE"), primary_key=True
    )
    symptom_id: Mapped[str] = mapped_column(ForeignKey("symptoms.id"), primary_key=True)


class Reference(Base):
    __tablename__ = "medical_references"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    disease_id: Mapped[str] = mapped_column(ForeignKey("diseases.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    publisher: Mapped[str] = mapped_column(String(150))
    url: Mapped[str] = mapped_column(Text)
    accessed_at: Mapped[str] = mapped_column(String(10))
    usage_note: Mapped[str] = mapped_column(Text)


class History(Base):
    __tablename__ = "search_history"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    mode: Mapped[str] = mapped_column(String(20))
    query: Mapped[str] = mapped_column(String(300))
    results: Mapped[list] = mapped_column(JSON)
    consent_version: Mapped[str] = mapped_column(String(30), default="history-v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuditLog(Base):
    __tablename__ = "admin_audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(80))
    snapshot: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MedicalDocument(Base):
    __tablename__ = "medical_documents"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    disease_id: Mapped[str] = mapped_column(ForeignKey("diseases.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    publisher: Mapped[str] = mapped_column(String(150))
    source_url: Mapped[str] = mapped_column(Text)
    usage_note: Mapped[str] = mapped_column(Text)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("medical_documents.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    publisher: Mapped[str] = mapped_column(String(150))
    source_url: Mapped[str] = mapped_column(Text)
    usage_note: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    checksum: Mapped[str] = mapped_column(String(64))
    editor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LibraryUpdate(Base):
    __tablename__ = "library_updates"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ImageRecord(Base):
    """Private uploads; only administrator-labelled records become reference images."""

    __tablename__ = "image_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    disease_id: Mapped[str | None] = mapped_column(ForeignKey("diseases.id"), nullable=True)
    pixel_sha256: Mapped[str] = mapped_column(String(64), index=True)
    image_type: Mapped[str] = mapped_column(String(20))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    is_reference: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_version: Mapped[str] = mapped_column(String(30), default="image-storage-v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
