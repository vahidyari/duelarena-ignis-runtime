from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import zipfile

SCRIPT_DIRS = ("official", "pre-release", "pre-errata")
EXCLUDED_DB_TOKENS = ("rush", "skill", "unofficial", "goat")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def selected_database_files(root: Path) -> list[Path]:
    result: list[Path] = []
    for path in sorted(root.glob("*.cdb")):
        name = path.name.lower()
        if any(token in name for token in EXCLUDED_DB_TOKENS):
            continue
        if name == "cards.cdb" or name.startswith("release-") or name.startswith("prerelease-"):
            result.append(path)
    if not any(path.name.lower() == "cards.cdb" for path in result):
        raise RuntimeError("BabelCDB cards.cdb is missing")
    return result


def validate_database(path: Path) -> None:
    # Explicitly close the native SQLite handle.  A connection context manager
    # only controls the transaction and can leave the file locked on Windows.
    with closing(sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        if not integrity or str(integrity[0]).lower() != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {path.name}")
        tables = {str(row[0]) for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "datas" not in tables:
            raise RuntimeError(f"Missing datas table: {path.name}")


def copy_scripts(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root_scripts = sorted(source.glob("*.lua"))
    if not any(path.name == "constant.lua" for path in root_scripts):
        raise RuntimeError("CardScripts constant.lua is missing")
    if not any(path.name == "utility.lua" for path in root_scripts):
        raise RuntimeError("CardScripts utility.lua is missing")
    for path in root_scripts:
        shutil.copy2(path, destination / path.name)
    for folder in SCRIPT_DIRS:
        src = source / folder
        if not src.is_dir():
            raise RuntimeError(f"CardScripts folder is missing: {folder}")
        shutil.copytree(src, destination / folder)


def build_runtime_tree(*, stage: Path, platform: str, core_library: Path, cardscripts: Path, babelcdb: Path,
                       version: str, core_sha: str, cardscripts_sha: str, babelcdb_sha: str) -> dict:
    if stage.exists():
        shutil.rmtree(stage)
    (stage / "core").mkdir(parents=True)
    (stage / "database").mkdir(parents=True)

    core_name = "ocgcore.dll" if platform == "windows-x64" else "libocgcore.so"
    target_core = stage / "core" / core_name
    shutil.copy2(core_library, target_core)

    copy_scripts(cardscripts, stage / "scripts")

    database_files: list[str] = []
    for source in selected_database_files(babelcdb):
        validate_database(source)
        target = stage / "database" / source.name
        shutil.copy2(source, target)
        database_files.append(target.relative_to(stage).as_posix())

    components = {
        "core_commit": core_sha,
        "cardscripts_commit": cardscripts_sha,
        "babelcdb_commit": babelcdb_sha,
    }
    metadata = {
        "schema_version": 1,
        "version": version,
        "platform": platform,
        "core_library": target_core.relative_to(stage).as_posix(),
        "scripts_root": "scripts",
        "database_files": database_files,
        "components": components,
    }
    (stage / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def zip_tree(stage: Path, archive: Path) -> None:
    archive.parent.mkdir(parents=True, exist_ok=True)
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(stage).as_posix())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=("windows-x64", "linux-x64"), required=True)
    parser.add_argument("--core-library", required=True)
    parser.add_argument("--cardscripts", required=True)
    parser.add_argument("--babelcdb", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--core-sha", required=True)
    parser.add_argument("--cardscripts-sha", required=True)
    parser.add_argument("--babelcdb-sha", required=True)
    parser.add_argument("--dist", default="dist")
    args = parser.parse_args()

    dist = Path(args.dist)
    dist.mkdir(parents=True, exist_ok=True)
    stage = dist / f"stage-{args.platform}"
    metadata = build_runtime_tree(
        stage=stage,
        platform=args.platform,
        core_library=Path(args.core_library),
        cardscripts=Path(args.cardscripts),
        babelcdb=Path(args.babelcdb),
        version=args.version,
        core_sha=args.core_sha,
        cardscripts_sha=args.cardscripts_sha,
        babelcdb_sha=args.babelcdb_sha,
    )

    filename = f"duelarena-ignis-{args.platform}-{args.version}.zip"
    archive = dist / filename
    zip_tree(stage, archive)
    descriptor = {
        "schema_version": 1,
        "version": args.version,
        "platform": args.platform,
        "filename": filename,
        "sha256": sha256_file(archive),
        "size": archive.stat().st_size,
        "components": metadata["components"],
    }
    (dist / f"descriptor-{args.platform}.json").write_text(json.dumps(descriptor, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(descriptor, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
