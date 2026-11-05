"""Delete only the fixed reviewed scratch paths; never alter Windows execution policy."""
from __future__ import annotations
import argparse
import json
import os
import shutil
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGETS = ('backend\\.pytest_cache', 'frontend\\tsconfig.tsbuildinfo', 'research\\__pycache__', 'scripts\\__pycache__', 'frontend\\.npm-cache', 'backend\\app\\__pycache__', 'backend\\tests\\__pycache__', 'scripts\\content\\__pycache__', 'scripts\\import_export\\__pycache__', 'scripts\\maintenance\\__pycache__', 'scripts\\translation\\__pycache__', 'storage\\temporary\\api-search-tests-b', 'storage\\temporary\\archive', 'storage\\temporary\\cover-check', 'storage\\temporary\\non-disease-word-qa-20261021', 'storage\\temporary\\split-word-qa', 'storage\\temporary\\test-chat-regression', 'storage\\temporary\\test-content-completion-20261021-b', 'storage\\temporary\\test-content-completion-20261021-c', 'storage\\temporary\\test-content-completion-20261021-final', 'storage\\temporary\\test-content-completion-continuation-20261021-a', 'storage\\temporary\\test-content-completion-continuation-20261021-b', 'storage\\temporary\\test-content-completion-continuation-20261021-c', 'storage\\temporary\\test-content-completion-continuation-20261021-final', 'storage\\temporary\\test-content-completion-continuation-20261021-ready', 'storage\\temporary\\tests-cleanup-remaining-20261021-final', 'storage\\temporary\\tests-fix-remaining-20261021-a', 'storage\\temporary\\tests-library-repair-20261019-a', 'storage\\temporary\\tests-prune-20261021-a', 'storage\\temporary\\tests-prune-20261021-b', 'storage\\temporary\\tests-prune-renames-20261021', 'storage\\temporary\\tests-search-20261021-final', 'storage\\temporary\\word-export-test', 'backend\\app\\core\\__pycache__', 'backend\\app\\data\\__pycache__', 'backend\\app\\database\\__pycache__', 'backend\\app\\integrations\\__pycache__', 'backend\\app\\modules\\__pycache__', 'storage\\temporary\\disease-covers\\discover.py', 'storage\\temporary\\disease-covers\\download.py', 'storage\\temporary\\disease-covers\\refine.py', 'storage\\temporary\\disease-covers\\update-ui.py', 'storage\\temporary\\disease-covers\\verify.py', 'storage\\temporary\\disease-covers\\read-library.py', 'storage\\temporary\\disease-covers\\read_web.py', 'storage\\temporary\\disease-covers\\review_cached.py', 'storage\\temporary\\disease-covers\\candidates.json', 'storage\\temporary\\disease-covers\\contact-sheet.jpg', 'storage\\temporary\\disease-covers\\extra-review.json', 'storage\\temporary\\disease-covers\\library-records-live.json', 'backend\\app\\database\\migrations\\__pycache__', 'backend\\app\\integrations\\gemini\\__pycache__', 'backend\\app\\modules\\admin\\__pycache__', 'backend\\app\\modules\\assistant\\__pycache__', 'backend\\app\\modules\\auth\\__pycache__', 'backend\\app\\modules\\history\\__pycache__', 'backend\\app\\modules\\images\\__pycache__', 'backend\\app\\modules\\library\\__pycache__', 'backend\\app\\modules\\profile\\__pycache__', 'backend\\app\\modules\\symptoms\\__pycache__', 'frontend\\src\\shared\\utils\\articleIllustration.ts', 'frontend\\public\\assets\\library\\general.webp', 'frontend\\public\\assets\\library\\dermatology.webp', 'frontend\\public\\assets\\library\\molecules.webp', 'frontend\\public\\assets\\library\\vaccines.webp')


def reject_link(path: Path) -> None:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise ValueError(f"Link or junction rejected: {path}")


def inspect_target(relative: str) -> tuple[Path, dict[Path, int]]:
    target = ROOT.joinpath(*relative.split("\\"))
    if target == ROOT or not target.resolve().is_relative_to(ROOT):
        raise ValueError("Target outside project")
    for part in (target, *target.parents):
        if part == ROOT:
            break
        reject_link(part)
    sizes = {}
    if target.is_dir():
        def scan_error(error):
            raise error
        for base, dirs, files in os.walk(target, followlinks=False, onerror=scan_error):
            for name in dirs + files:
                child = Path(base) / name
                reject_link(child)
                if child.is_file():
                    sizes[child] = child.stat().st_size
    else:
        sizes[target] = target.stat().st_size
    return target, sizes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", "-WhatIf", action="store_true", dest="dry_run")
    args = parser.parse_args()
    results = []
    for relative in TARGETS:
        raw = ROOT.joinpath(*relative.split("\\"))
        if not os.path.lexists(raw):
            continue
        sizes = {}
        try:
            target, sizes = inspect_target(relative)
            if args.dry_run:
                results.append(dict(path=str(target), status="would_delete", files=len(sizes), bytes=sum(sizes.values())))
                continue
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            results.append(dict(path=str(target), status="deleted", files=len(sizes), bytes=sum(sizes.values())))
        except (OSError, ValueError) as error:
            removed = {p: size for p, size in sizes.items() if not os.path.lexists(p)} if not args.dry_run else {}
            results.append(dict(path=str(raw), status="not_deleted", reason=str(error), files=len(removed), bytes=sum(removed.values())))
    summary = dict(
        status="dry_run" if args.dry_run else "completed_with_skips" if any(r["status"] == "not_deleted" for r in results) else "completed",
        deleted_files=0 if args.dry_run else sum(r["files"] for r in results),
        planned_files=sum(r["files"] for r in results) if args.dry_run else None,
        freed_mb=0 if args.dry_run else round(sum(r["bytes"] for r in results) / 1048576, 2),
        not_deleted=sum(r["status"] == "not_deleted" for r in results),
    )
    if not args.dry_run:
        report = ROOT / "storage/exports/maintenance/cleanup-local-result.json"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(dict(summary=summary, targets=results), ensure_ascii=False, indent=2), encoding="utf-8")
        summary["report"] = str(report)
    print(json.dumps(summary, ensure_ascii=True))
    for result in results:
        if result["status"] == "not_deleted":
            print(json.dumps(result, ensure_ascii=True))
    return 1 if summary["not_deleted"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
