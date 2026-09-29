# DuelArena Ignis runtime feed format

The current Control Center consumes schema version `1`.

Example platform manifest:

```json
{
  "schema_version": 1,
  "version": "2026.09.29.2015-a1b2c3d-e4f5a6b-1122334",
  "platforms": ["windows-x64"],
  "components": {
    "core_commit": "...",
    "cardscripts_commit": "...",
    "babelcdb_commit": "..."
  },
  "bundle": {
    "url": "https://github.com/OWNER/REPO/releases/download/TAG/duelarena-ignis-windows-x64-VERSION.zip",
    "sha256": "...",
    "size": 123456
  }
}
```

The ZIP root contains `metadata.json`:

```json
{
  "schema_version": 1,
  "version": "...",
  "platform": "windows-x64",
  "core_library": "core/ocgcore.dll",
  "scripts_root": "scripts",
  "database_files": ["database/cards.cdb"],
  "components": {
    "core_commit": "...",
    "cardscripts_commit": "...",
    "babelcdb_commit": "..."
  }
}
```

A provider migration does not change these schemas; only the manifest/bundle URLs change.
