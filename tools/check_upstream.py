from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

UPSTREAMS = {
    "core": ("https://github.com/edo9300/ygopro-core.git", "refs/heads/master"),
    "cardscripts": ("https://github.com/ProjectIgnis/CardScripts.git", "refs/heads/master"),
    "babelcdb": ("https://github.com/ProjectIgnis/BabelCDB.git", "refs/heads/master"),
}


def remote_sha(url: str, ref: str) -> str:
    output = subprocess.check_output(["git", "ls-remote", url, ref], text=True).strip()
    if not output:
        raise RuntimeError(f"No SHA returned for {url} {ref}")
    sha = output.split()[0].strip().lower()
    if len(sha) != 40 or any(ch not in "0123456789abcdef" for ch in sha):
        raise RuntimeError(f"Invalid SHA returned for {url}: {sha}")
    return sha


def read_source(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def compute_changed(previous: dict, current: dict) -> bool:
    return any(str(previous.get(key) or "") != str(current.get(key) or "") for key in UPSTREAMS)


def make_version(current: dict, now: datetime | None = None) -> str:
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y.%m.%d.%H%M")
    return f"{stamp}-{current['core'][:7]}-{current['cardscripts'][:7]}-{current['babelcdb'][:7]}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-file", default="feed/source.json")
    parser.add_argument("--github-output")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    current = {key: remote_sha(url, ref) for key, (url, ref) in UPSTREAMS.items()}
    previous = read_source(Path(args.source_file))
    changed = bool(args.force or compute_changed(previous, current))
    version = make_version(current)

    result = {**current, "changed": changed, "version": version}
    print(json.dumps(result, indent=2))

    if args.github_output:
        output = Path(args.github_output)
        with output.open("a", encoding="utf-8") as handle:
            for key, value in result.items():
                handle.write(f"{key}={str(value).lower() if isinstance(value, bool) else value}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
