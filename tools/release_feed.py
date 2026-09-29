from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path


def load_descriptor(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise RuntimeError(f"Invalid descriptor: {path}")
    return value


def make_manifest(descriptor: dict, *, repo: str, tag: str) -> dict:
    filename = descriptor["filename"]
    return {
        "schema_version": 1,
        "version": descriptor["version"],
        "platforms": [descriptor["platform"]],
        "components": descriptor["components"],
        "bundle": {
            "url": f"https://github.com/{repo}/releases/download/{tag}/{filename}",
            "sha256": descriptor["sha256"],
            "size": int(descriptor["size"]),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", default="dist")
    parser.add_argument("--feed", default="feed")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--core-sha", required=True)
    parser.add_argument("--cardscripts-sha", required=True)
    parser.add_argument("--babelcdb-sha", required=True)
    args = parser.parse_args()

    dist = Path(args.dist)
    feed = Path(args.feed)
    feed.mkdir(parents=True, exist_ok=True)

    for descriptor_path in sorted(dist.glob("descriptor-*.json")):
        descriptor = load_descriptor(descriptor_path)
        if descriptor.get("version") != args.version:
            raise RuntimeError(f"Descriptor version mismatch: {descriptor_path}")
        platform = descriptor["platform"]
        manifest = make_manifest(descriptor, repo=args.repo, tag=args.tag)
        (feed / f"manifest-{platform}.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    source = {
        "version": args.version,
        "release_tag": args.tag,
        "published_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "core": args.core_sha,
        "cardscripts": args.cardscripts_sha,
        "babelcdb": args.babelcdb_sha,
    }
    (feed / "source.json").write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
