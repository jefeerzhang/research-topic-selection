#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the final delivery lineage manifest after all topic gates pass."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile

from selection_gate import DELIVERY_ARTIFACTS, check_enter, load_json_rel, normpath, sha256_of


def atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")
        temp_name = file.name
    os.replace(temp_name, path)


def main() -> int:
    parser = argparse.ArgumentParser(description="生成选题交付血缘 manifest")
    parser.add_argument("--workdir", required=True)
    args = parser.parse_args()
    workdir = normpath(args.workdir)
    if not os.path.isdir(workdir):
        print(f"FAIL: workdir 不存在: {workdir}")
        return 2

    try:
        check_enter(workdir, "topics")
        protocol = load_json_rel(workdir, "protocol.json")
        hashes = {artifact: sha256_of(os.path.join(workdir, artifact)) for artifact in DELIVERY_ARTIFACTS}
    except Exception as exc:  # selection_gate provides user-facing messages
        print(f"FAIL: {exc}")
        return 1

    manifest = {
        "schema_version": "1.5",
        "workdir": workdir,
        "topic": protocol["topic"],
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "artifact_hashes": hashes,
    }
    destination = Path(workdir) / "review" / "delivery_manifest.json"
    atomic_write_json(destination, manifest)
    print(json.dumps({"ok": True, "manifest": str(destination)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
