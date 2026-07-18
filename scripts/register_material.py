#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Register a user-provided research material in a v1.5.2 project.

The source file is copied into user_materials/ with a content-addressed name.
The manifest is atomically updated and duplicate content is not registered
twice. Existing project files are never overwritten.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from selection_gate import MATERIAL_CATEGORIES, MATERIAL_ORIGINS, check_scope, normpath


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")
        temp_name = file.name
    os.replace(temp_name, path)


def safe_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._\-\u4e00-\u9fff]+", "_", name).strip("._")
    return cleaned[:100] or "material"


def main() -> int:
    parser = argparse.ArgumentParser(description="登记用户上传的文献、笔记或题目摘要")
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--category", required=True, choices=sorted(MATERIAL_CATEGORIES))
    parser.add_argument("--origin", required=True, choices=sorted(MATERIAL_ORIGINS))
    parser.add_argument("--label", default="")
    args = parser.parse_args()

    workdir = Path(args.workdir).expanduser().resolve()
    source = Path(args.input).expanduser().resolve()
    if not workdir.is_dir():
        print(f"FAIL: workdir 不存在: {workdir}")
        return 2
    try:
        check_scope(str(workdir))
    except Exception as exc:
        print(f"FAIL: scope 尚未通过: {exc}")
        return 1
    if not source.is_file():
        print(f"FAIL: 输入文件不存在: {source}")
        return 2
    size = source.stat().st_size
    if size <= 0:
        print("FAIL: 用户材料不得为空文件")
        return 1

    manifest_path = workdir / "review" / "user_material_manifest.json"
    if not manifest_path.is_file():
        print(f"FAIL: 缺失材料 manifest: {manifest_path}")
        return 1
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: 材料 manifest 无法读取: {exc}")
        return 1
    if manifest.get("schema_version") != "1.5" or normpath(str(manifest.get("workdir") or "")) != normpath(str(workdir)):
        print("FAIL: 材料 manifest 版本或 workdir 不匹配")
        return 1
    items = manifest.get("items")
    if not isinstance(items, list):
        print("FAIL: 材料 manifest.items 必须是数组")
        return 1

    digest = sha256_file(source)
    existing = next((item for item in items if item.get("sha256") == digest), None)
    if existing is not None:
        print(json.dumps({"ok": True, "duplicate": True, "item": existing}, ensure_ascii=False))
        return 0

    material_id = f"M-{digest[:12]}"
    destination_name = f"{material_id}-{safe_name(source.name)}"
    destination_rel = Path("user_materials") / destination_name
    destination = workdir / destination_rel
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        print(f"FAIL: 目标材料文件已存在但未登记: {destination}")
        return 1
    with tempfile.NamedTemporaryFile("wb", dir=destination.parent, delete=False) as file:
        temp_path = Path(file.name)
    try:
        shutil.copy2(source, temp_path)
        if sha256_file(temp_path) != digest:
            print("FAIL: 材料复制后 hash 不一致")
            return 1
        os.replace(temp_path, destination)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    item = {
        "material_id": material_id,
        "category": args.category,
        "origin": args.origin,
        "label": args.label.strip(),
        "original_name": source.name,
        "stored_path": destination_rel.as_posix(),
        "sha256": digest,
        "size_bytes": size,
        "registered_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    }
    items.append(item)
    atomic_write_json(manifest_path, manifest)
    print(json.dumps({"ok": True, "duplicate": False, "item": item}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
