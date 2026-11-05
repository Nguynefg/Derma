"""Database-neutral model metadata; importing this module never opens a database."""

from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import (
    String as SQLString,
    Text as SQLText,
    Unicode,
    ForeignKey,
    Boolean,
    DateTime,
    JSON,
    Integer,
    Identity,
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
    __tablename__ = "tblusers"
    id: Mapped[int] = mapped_column("user_id", Integer, Identity(), primary_key=True)
    legacy_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LoginSession(Base):
    __tablename__ = "tblsessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("tblusers.user_id", ondelete="CASCADE"))
    csrf: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Bookmark(Base):
    __tablename__ = "tblbookmarks"
    user_id: Mapped[int] = mapped_column(
        ForeignKey("tblusers.user_id", ondelete="CASCADE"), primary_key=True
    )
    disease_id: Mapped[int] = mapped_column(
        ForeignKey("tbldiseases.disease_id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Disease(Base):
    __tablename__ = "tbldiseases"
    id: Mapped[int] = mapped_column("disease_id", Integer, Identity(), primary_key=True)
    slug: Mapped[str] = mapped_column(String(60), unique=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(120), index=True)
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
    __tablename__ = "tblsymptoms"
    id: Mapped[int] = mapped_column("symptom_id", Integer, Identity(), primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(80))


class DiseaseSymptom(Base):
    __tablename__ = "tbldisease_symptoms"
    disease_id: Mapped[int] = mapped_column(
        ForeignKey("tbldiseases.disease_id", ondelete="CASCADE"), primary_key=True
    )
    symptom_id: Mapped[int] = mapped_column(ForeignKey("tblsymptoms.symptom_id"), primary_key=True)


class Reference(Base):
    __tablename__ = "tblmedical_references"
    id: Mapped[int] = mapped_column("reference_id", Integer, Identity(), primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, default=lambda: str(uuid4()))
    disease_id: Mapped[int] = mapped_column(
        ForeignKey("tbldiseases.disease_id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String(200))
    publisher: Mapped[str] = mapped_column(String(150))
    url: Mapped[str] = mapped_column(Text)
    accessed_at: Mapped[str] = mapped_column(String(10))
    usage_note: Mapped[str] = mapped_column(Text)


class History(Base):
    __tablename__ = "tblsearch_history"
    id: Mapped[int] = mapped_column("history_id", Integer, Identity(), primary_key=True)
    legacy_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("tblusers.user_id", ondelete="CASCADE"))
    mode: Mapped[str] = mapped_column(String(20))
    query: Mapped[str] = mapped_column(String(300))
    results: Mapped[list] = mapped_column(JSON)
    consent_version: Mapped[str] = mapped_column(String(30), default="history-v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuditLog(Base):
    __tablename__ = "tbladmin_audit_logs"
    id: Mapped[int] = mapped_column("audit_id", Integer, Identity(), primary_key=True)
    legacy_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid4()))
    actor_id: Mapped[int] = mapped_column(ForeignKey("tblusers.user_id"))
    action: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(80))
    snapshot: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MedicalDocument(Base):
    __tablename__ = "tblmedical_documents"
    id: Mapped[int] = mapped_column("document_id", Integer, Identity(), primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, default=lambda: str(uuid4()))
    disease_id: Mapped[int] = mapped_column(
        ForeignKey("tbldiseases.disease_id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String(200))
    publisher: Mapped[str] = mapped_column(String(150))
    source_url: Mapped[str] = mapped_column(Text)
    usage_note: Mapped[str] = mapped_column(Text)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DocumentVersion(Base):
    __tablename__ = "tbldocument_versions"
    id: Mapped[int] = mapped_column("document_version_id", Integer, Identity(), primary_key=True)
    legacy_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid4()))
    document_id: Mapped[int] = mapped_column(
        ForeignKey("tblmedical_documents.document_id", ondelete="CASCADE")
    )
    version: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    publisher: Mapped[str] = mapped_column(String(150))
    source_url: Mapped[str] = mapped_column(Text)
    usage_note: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    checksum: Mapped[str] = mapped_column(String(64))
    editor_id: Mapped[int | None] = mapped_column(ForeignKey("tblusers.user_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LibraryUpdate(Base):
    __tablename__ = "tbllibrary_updates"
    id: Mapped[str] = mapped_column("update_id", String(100), primary_key=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ImageRecord(Base):
    """Private uploads; only administrator-labelled records become reference images."""

    __tablename__ = "tblimage_records"
    id: Mapped[int] = mapped_column("image_id", Integer, Identity(), primary_key=True)
    file_uuid: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("tblusers.user_id"))
    disease_id: Mapped[int | None] = mapped_column(
        ForeignKey("tbldiseases.disease_id"), nullable=True
    )
    pixel_sha256: Mapped[str] = mapped_column(String(64), index=True)
    image_type: Mapped[str] = mapped_column(String(20))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    is_reference: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_version: Mapped[str] = mapped_column(String(30), default="image-storage-v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
