"""Legacy metadata used only to migrate away an existing tblsource_files table.

Do not create these tables in the current schema.
"""

from sqlalchemy import Integer, Identity, ForeignKey, LargeBinary, UniqueConstraint
from sqlalchemy.dialects.mssql import VARBINARY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from app.database.models import String, Text, LibraryUpdate


class SourceBase(DeclarativeBase):
    pass


class SourceFile(SourceBase):
    __tablename__ = "tblsource_files"
    __table_args__ = (UniqueConstraint("update_id", "filename", "sha256"),)
    id: Mapped[int] = mapped_column("source_file_id", Integer, Identity(), primary_key=True)
    update_id: Mapped[str] = mapped_column(ForeignKey(LibraryUpdate.__table__.c.update_id))
    filename: Mapped[str] = mapped_column(String(254))
    sha256: Mapped[str] = mapped_column(String(64))
    content: Mapped[bytes] = mapped_column(LargeBinary().with_variant(VARBINARY(None), "mssql"))
    metadata_json: Mapped[str] = mapped_column(Text)
