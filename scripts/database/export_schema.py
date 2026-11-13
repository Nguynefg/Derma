"""Run from backend with its environment: python ../scripts/database/export_schema.py."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from sqlalchemy.schema import CreateTable, CreateIndex
from sqlalchemy.dialects import postgresql, mssql
from app.database.models import Base
from app.main import app

target = ROOT / "docs" / "database"
target.mkdir(parents=True, exist_ok=True)
for name, dialect in [("postgresql", postgresql.dialect()), ("sqlserver", mssql.dialect())]:
    ddl = ["-- Generated from SQLAlchemy models. Initial schema, not a migration."]
    for table in Base.metadata.sorted_tables:
        ddl.append(str(CreateTable(table).compile(dialect=dialect)) + ";")
        for index in table.indexes:
            ddl.append(str(CreateIndex(index).compile(dialect=dialect)) + ";")
    (target / ("schema-" + name + ".sql")).write_text("\n\n".join(ddl), encoding="utf-8")
(ROOT / "docs" / "openapi.json").write_text(
    json.dumps(app.openapi(), ensure_ascii=False, indent=2), encoding="utf-8"
)
print("Exported PostgreSQL / SQL Server DDL and OpenAPI.")
