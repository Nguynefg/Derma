"""Resolve historical local archive paths after the storage reorganization."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def storage_path(value, root=PROJECT_ROOT):
    root = Path(root).resolve()
    path = Path(value)
    absolute = (root / path).resolve() if not path.is_absolute() else path.resolve()
    try:
        relative = absolute.relative_to(root)
    except ValueError:
        return path
    parts = relative.parts
    if parts[:2] == ("work", "backups"):
        return root / "storage" / "backups" / Path(*parts[2:])
    if parts[:2] == ("work", "icd-import"):
        return root / "storage" / "imports" / "icd-import" / Path(*parts[2:])
    if parts[:1] == ("work",):
        return root / "storage" / "temporary" / Path(*parts[1:])
    if parts[:1] == ("outputs",):
        return root / "storage" / "exports" / Path(*parts[1:])
    return path
