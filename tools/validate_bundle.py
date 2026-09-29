from __future__ import annotations

import argparse
import ctypes
import json
from pathlib import Path
import sqlite3
import tempfile
import zipfile


def validate_bundle(archive: Path, expected_platform: str | None = None) -> dict:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                relative = Path(info.filename)
                if relative.is_absolute() or ".." in relative.parts:
                    raise RuntimeError(f"Unsafe ZIP member: {info.filename}")
            zf.extractall(root)

        metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
        if metadata.get("schema_version") != 1:
            raise RuntimeError("Unsupported metadata schema")
        if expected_platform and metadata.get("platform") != expected_platform:
            raise RuntimeError(f"Platform mismatch: {metadata.get('platform')} != {expected_platform}")

        scripts = root / metadata["scripts_root"]
        for name in ("constant.lua", "utility.lua"):
            if not (scripts / name).is_file():
                raise RuntimeError(f"Missing required script: {name}")
        for folder in ("official", "pre-release"):
            if not (scripts / folder).is_dir():
                raise RuntimeError(f"Missing CardScripts folder: {folder}")

        for relative in metadata["database_files"]:
            db = root / relative
            if not db.is_file():
                raise RuntimeError(f"Missing DB: {relative}")
            with sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True) as connection:
                tables = {str(row[0]) for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if "datas" not in tables:
                    raise RuntimeError(f"Missing datas table: {relative}")

        core = root / metadata["core_library"]
        if not core.is_file():
            raise RuntimeError(f"Missing core library: {metadata['core_library']}")
        library = ctypes.CDLL(str(core))
        getter = library.OCG_GetVersion
        getter.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
        getter.restype = None
        major = ctypes.c_int()
        minor = ctypes.c_int()
        getter(ctypes.byref(major), ctypes.byref(minor))
        if major.value <= 0:
            raise RuntimeError("ocgcore returned invalid API version")
        return {"ok": True, "api_major": major.value, "api_minor": minor.value, "metadata": metadata}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive")
    parser.add_argument("--expected-platform")
    args = parser.parse_args()
    result = validate_bundle(Path(args.archive), args.expected_platform)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
