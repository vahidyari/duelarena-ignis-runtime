from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import tempfile

from tools.check_upstream import compute_changed, make_version
from tools.package_runtime import selected_database_files
from tools.release_feed import make_manifest


def _create_cdb(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE datas (id INTEGER PRIMARY KEY, ot INTEGER, alias INTEGER, setcode INTEGER, type INTEGER, atk INTEGER, def INTEGER, level INTEGER, race INTEGER, attribute INTEGER, category INTEGER)")
        connection.commit()


def test_database_selection_is_standard_only() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        names = [
            "cards.cdb",
            "release-abcd.cdb",
            "prerelease-abcd.cdb",
            "prerelease-cards-rush.cdb",
            "cards-rush.cdb",
            "cards-skills.cdb",
            "cards-unofficial.cdb",
            "goat-entries.cdb",
        ]
        for name in names:
            _create_cdb(root / name)
        selected = [path.name for path in selected_database_files(root)]
        assert selected == ["cards.cdb", "prerelease-abcd.cdb", "release-abcd.cdb"]


def test_upstream_change_detection() -> None:
    old = {"core": "a", "cardscripts": "b", "babelcdb": "c"}
    assert compute_changed(old, old) is False
    assert compute_changed(old, {**old, "cardscripts": "new"}) is True


def test_version_is_safe_and_deterministic_for_timestamp() -> None:
    current = {"core": "a" * 40, "cardscripts": "b" * 40, "babelcdb": "c" * 40}
    now = datetime(2026, 9, 29, 20, 15, tzinfo=timezone.utc)
    assert make_version(current, now) == "2026.09.29.2015-aaaaaaa-bbbbbbb-ccccccc"


def test_manifest_matches_control_center_schema() -> None:
    descriptor = {
        "schema_version": 1,
        "version": "2026.09.29.1",
        "platform": "windows-x64",
        "filename": "bundle.zip",
        "sha256": "a" * 64,
        "size": 123,
        "components": {
            "core_commit": "1" * 40,
            "cardscripts_commit": "2" * 40,
            "babelcdb_commit": "3" * 40,
        },
    }
    manifest = make_manifest(descriptor, repo="owner/repo", tag="ignis-test")
    assert manifest["schema_version"] == 1
    assert manifest["platforms"] == ["windows-x64"]
    assert manifest["bundle"]["url"].endswith("/ignis-test/bundle.zip")
    assert manifest["bundle"]["sha256"] == "a" * 64



def test_validator_contains_windows_dll_release_guard() -> None:
    source = Path("tools/validate_bundle.py").read_text(encoding="utf-8")
    assert "FreeLibrary" in source
    assert "_release_dynamic_library(library)" in source


def test_collect_steps_pin_release_build_config() -> None:
    source = Path(".github/workflows/build-runtime.yml").read_text(encoding="utf-8")
    assert source.count("BUILD_CONFIG: release") >= 4



def test_sqlite_handles_are_explicitly_closed_for_windows_cleanup() -> None:
    validator = Path("tools/validate_bundle.py").read_text(encoding="utf-8")
    packager = Path("tools/package_runtime.py").read_text(encoding="utf-8")
    assert "from contextlib import closing" in validator
    assert "with closing(sqlite3.connect" in validator
    assert "from contextlib import closing" in packager
    assert "with closing(sqlite3.connect" in packager
