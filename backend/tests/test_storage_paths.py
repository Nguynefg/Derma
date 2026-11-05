from app.core.paths import storage_path


def test_historical_archive_paths_and_current_paths(tmp_path):
    root = tmp_path / "project"
    assert storage_path(root / "work/backups/original.zip", root) == root / "storage/backups/original.zip"
    assert storage_path(root / "work/icd-import/titles.json", root) == root / "storage/imports/icd-import/titles.json"
    assert storage_path(root / "outputs/export.docx", root) == root / "storage/exports/export.docx"
    assert storage_path(root / "work/job/state.json", root) == root / "storage/temporary/job/state.json"
    current = root / "storage/backups/original.zip"
    assert storage_path(current, root) == current


def test_unrelated_paths_and_traversal_are_not_remapped(tmp_path):
    root = tmp_path / "project"
    outside = tmp_path / "other/work/backups/source.zip"
    assert storage_path(outside, root) == outside
    escaped = root / "work/../../outside.zip"
    assert storage_path(escaped, root) == escaped
