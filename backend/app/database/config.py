"""SQL Server settings contain no password. Environment DATABASE_URL wins."""

import json
import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from sqlalchemy import URL

CONFIG_PATH = Path(__file__).resolve().parents[2] / "database.local.json"


@dataclass(frozen=True)
class SQLServerSettings:
    server: str
    database: str = "BenhLy"
    driver: str = "ODBC Driver 18 for SQL Server"
    authentication: str = "windows"
    username: str | None = None
    encrypt: bool = True
    trust_server_certificate: bool = False
    provider: str = "sqlserver"

    def __post_init__(self):
        if self.provider != "sqlserver":
            raise ValueError("Unsupported database provider")
        if not re.fullmatch(r"[A-Za-z0-9_.\\,():-]{1,200}", self.server):
            raise ValueError("Invalid SQL Server name")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", self.database):
            raise ValueError("Invalid database name")
        if self.driver not in {"ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server"}:
            raise ValueError("Use Microsoft ODBC Driver 17 or 18")
        if self.authentication not in {"windows", "sql"}:
            raise ValueError("Invalid authentication mode")
        if self.authentication == "sql" and not self.username:
            raise ValueError("SQL username required")
        if type(self.encrypt) is not bool or type(self.trust_server_certificate) is not bool:
            raise ValueError("Encryption options must be booleans")
        if not self.encrypt:
            raise ValueError("SQL Server connections require encryption")

    def url(self, database=None):
        password = None
        if self.authentication == "sql":
            password = os.getenv("DERMA_SQL_PASSWORD")
            if not password:
                raise ValueError(
                    "Set DERMA_SQL_PASSWORD locally; do not put passwords in config files"
                )
        options = {
            "driver": self.driver,
            "Encrypt": "yes",
            "TrustServerCertificate": "yes" if self.trust_server_certificate else "no",
            "Connection Timeout": "5",
        }
        if self.driver.startswith("ODBC Driver 18"):
            options["LongAsMax"] = "Yes"
        return URL.create(
            "mssql+pyodbc",
            host=self.server,
            database=database or self.database,
            username=self.username if self.authentication == "sql" else None,
            password=password,
            query=options,
        )

    def save(self, path=CONFIG_PATH):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise ValueError(
                "Local database configuration already exists; preserve and review it first"
            )
        # Exclusive creation: do not replace another process configuration.
        with path.open("x", encoding="utf-8") as stream:
            json.dump(asdict(self), stream, ensure_ascii=False, indent=2)


def read_settings(path=CONFIG_PATH):
    path = Path(path)
    if path.stat().st_size > 8192:
        raise ValueError("Database configuration too large")
    return SQLServerSettings(**json.loads(path.read_text(encoding="utf-8")))


def configured_url(data_dir):
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    path = Path(os.getenv("DERMA_DATABASE_CONFIG", str(CONFIG_PATH)))
    if path.exists():
        return read_settings(path).url()
    return URL.create("sqlite", database=str(Path(data_dir) / "derma.db"))
