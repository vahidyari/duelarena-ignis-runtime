# DuelArena Ignis Runtime

Provider-agnostic build/update feed for DuelArena Automated Standard Duel.

This repository does **not** contain DuelArena card legality or banlists. DuelArena remains authoritative for deck legality, selected artwork, card identity, and banlists. This repository only builds a validated Project Ignis runtime bundle containing:

- `ygopro-core` shared library
- Project Ignis CardScripts needed by Standard duels
- Project Ignis BabelCDB Standard databases
- immutable runtime metadata + SHA-256 feed manifests

## What happens automatically

The GitHub Action runs every 6 hours, but it only builds when one of these upstream commits changed:

- `edo9300/ygopro-core`
- `ProjectIgnis/CardScripts`
- `ProjectIgnis/BabelCDB`

When something changed, it builds Windows x64 and Linux x64 bundles, validates them, publishes immutable GitHub Release assets, then updates the small feed manifests under `feed/`.

DuelArena Control Center only downloads a full bundle when the feed version changes. The active runtime is never overwritten in-place; Control Center stages, SHA-256 verifies, performs its native smoke duel, then atomically activates the new version.

## First setup

1. Create a **public** GitHub repository, recommended name: `duelarena-ignis-runtime`.
2. Upload the contents of this folder to the repository root.
3. Open **Actions → Build DuelArena Ignis Runtime → Run workflow**.
4. Set `force_build` to `true` for the first run.
5. Wait for both platform builds and the publish job to finish.
6. Your Windows manifest URL will be:

   `https://raw.githubusercontent.com/<OWNER>/<REPO>/main/feed/manifest-windows-x64.json`

7. Put that URL in DuelArena `.env`:

   `IGNIS_RUNTIME_MANIFEST_URL=https://raw.githubusercontent.com/<OWNER>/<REPO>/main/feed/manifest-windows-x64.json`

8. Restart DuelArena Control Center, then use **Automated Duel → CHECK UPDATE → UPDATE NOW → TEST ENGINE**.

For a future Linux server use:

`https://raw.githubusercontent.com/<OWNER>/<REPO>/main/feed/manifest-linux-x64.json`

## Why public?

The current DuelArena runtime updater intentionally uses a normal unauthenticated HTTP(S) manifest URL. A private GitHub repository would require credentials/token handling. Keeping this feed public is also natural for the upstream AGPL components it redistributes.

## Later migration away from GitHub

The feed format is provider-agnostic. You can later host the same `manifest-*.json` and ZIP bundles on your own server, Cloudflare R2, object storage, or a normal web server. Then only `IGNIS_RUNTIME_MANIFEST_URL` changes in DuelArena.

## Bundle layout

Each ZIP contains:

```text
core/
  ocgcore.dll          # Windows, or libocgcore.so on Linux
scripts/
  *.lua                # base scripts
  official/
  pre-release/
  pre-errata/
database/
  cards.cdb
  release-*.cdb
  prerelease-*.cdb     # Standard only; Rush excluded
metadata.json
```

## Safety model

- exact upstream commits are pinned per build
- no build when upstream commits are unchanged
- ZIP SHA-256 is published in the manifest
- SQLite databases are structurally validated
- CardScripts base files are validated
- the built shared library is loaded and `OCG_GetVersion` is called in CI
- DuelArena Control Center performs the stronger native opening-hand smoke duel before activation
- previous local runtime remains available for rollback

## Standard-only scope

This feed intentionally excludes Rush, Skills, and unofficial/anime databases/scripts from the Automated Standard runtime. Prerelease Standard scripts/databases are included.

## Licensing

`ygopro-core` and Project Ignis CardScripts are AGPL-3.0-or-later projects. BabelCDB is maintained by Project Ignis and redistributed here only as runtime data. Preserve upstream copyright/license files when you redistribute modified upstream code. This builder is intended to make upstream provenance explicit in every bundle via commit hashes.
