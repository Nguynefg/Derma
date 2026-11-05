"""WHO classification metadata, separate from editorial articles and image labels."""

from sqlalchemy import Integer, Identity, ForeignKey, UniqueConstraint, LargeBinary, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.mssql import VARBINARY
from app.database.models import String, Text, now
from datetime import datetime


class ICDBase(DeclarativeBase):
    pass


class ICDRelease(ICDBase):
    __tablename__ = "tblicd_releases"
    id: Mapped[int] = mapped_column("release_id", Integer, Identity(), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    version: Mapped[str] = mapped_column(String(100))
    language: Mapped[str] = mapped_column(String(10), default="en")
    status: Mapped[str] = mapped_column(String(30), default="development_snapshot")
    entity_count: Mapped[int] = mapped_column(Integer)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ICDSource(ICDBase):
    __tablename__ = "tblicd_sources"
    id: Mapped[int] = mapped_column("source_id", Integer, Identity(), primary_key=True)
    release_id: Mapped[int] = mapped_column(ForeignKey("tblicd_releases.release_id"))
    filename: Mapped[str] = mapped_column(String(254))
    sha256: Mapped[str] = mapped_column(String(64))
    content: Mapped[bytes] = mapped_column(LargeBinary().with_variant(VARBINARY(None), "mssql"))


class ICDEntity(ICDBase):
    __tablename__ = "tblicd_entities"
    __table_args__ = (UniqueConstraint("release_id", "linearization_uri"),)
    id: Mapped[int] = mapped_column("entity_id", Integer, Identity(), primary_key=True)
    release_id: Mapped[int] = mapped_column(ForeignKey("tblicd_releases.release_id"), index=True)
    foundation_uri: Mapped[str | None] = mapped_column(String(300), nullable=True)
    linearization_uri: Mapped[str] = mapped_column(String(300))
    parent_uri: Mapped[str | None] = mapped_column(String(300), nullable=True)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    raw_code: Mapped[str] = mapped_column(String(50))
    block_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str] = mapped_column(Text)
    class_kind: Mapped[str] = mapped_column(String(20))
    chapter_no: Mapped[str] = mapped_column(String(10), index=True)
    depth: Mapped[int] = mapped_column(Integer)
    source_order: Mapped[int] = mapped_column(Integer)
    browser_url: Mapped[str] = mapped_column(Text)
    raw_row: Mapped[str] = mapped_column(Text)


class ICDChapterDocument(ICDBase):
    __tablename__ = "tblicd_chapter_documents"
    __table_args__ = (UniqueConstraint("release_id", "chapter_no"),)
    id: Mapped[int] = mapped_column("chapter_document_id", Integer, Identity(), primary_key=True)
    release_id: Mapped[int] = mapped_column(ForeignKey("tblicd_releases.release_id"))
    chapter_no: Mapped[str] = mapped_column(String(10))
    embedded_filename: Mapped[str] = mapped_column(String(100))
    paragraph_count: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    paragraphs_json: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
