#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch extract user-provided papers into Markdown full-text (v1.6).

Strategy:
  - PDF: try `mineru-open-api extract` (table/formula aware). On failure, fall
    back to PyMuPDF plain-text extraction so the pipeline never blocks on a
    single tool's availability.
  - .docx: use `python-docx` paragraph iteration.
  - .md / .markdown / .txt: copy through.
  - Everything else: recorded as unsupported, not silently dropped.

The script never overwrites existing extraction results. A manifest of
extracted files is written to `user_materials/extracted/extraction_manifest.json`
so downstream gates (Phase 1.7 papers gate) can verify completeness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SUPPORTED_PDF = {".pdf"}
SUPPORTED_DOCX = {".docx"}
SUPPORTED_MD = {".md", ".markdown", ".txt"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._\-\u4e00-\u9fff]+", "_", name).strip("._")
    return cleaned[:100] or "paper"


def locate_mineru() -> str | None:
    """Find mineru-open-api on PATH or in npm global root."""
    found = shutil.which("mineru-open-api")
    if found:
        return found
    # Common Windows npm global location
    candidates = [
        Path.home() / "AppData" / "Roaming" / "npm" / "mineru-open-api.cmd",
        Path.home() / "AppData" / "Roaming" / "npm" / "mineru-open-api",
    ]
    for cand in candidates:
        if cand.exists():
            return str(cand)
    return None


def extract_pdf_mineru(source: Path, output_dir: Path, timeout: int) -> tuple[bool, str]:
    binary = locate_mineru()
    if not binary:
        return False, "mineru-open-api not found on PATH"
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [binary, "extract", str(source), "-o", str(output_dir)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "mineru-open-api timeout"
    if result.returncode != 0:
        return False, (result.stderr or result.stdout or "mineru exit non-zero").strip()[:300]
    # MinerU creates a Markdown file with the source's stem
    produced = list(output_dir.glob(f"{source.stem}.md"))
    if not produced:
        return False, "mineru returned no Markdown"
    return True, str(produced[0])


def extract_pdf_pymupdf(source: Path, output_dir: Path) -> tuple[bool, str]:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return False, "PyMuPDF not installed"
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{safe_name(source.stem)}.md"
    try:
        with fitz.open(source) as doc:
            pages = []
            for index, page in enumerate(doc, start=1):
                text = page.get_text("text") or ""
                if text.strip():
                    pages.append(f"## 第 {index} 页\n\n{text.strip()}\n")
            body = "\n".join(pages)
    except Exception as exc:  # noqa: BLE001
        return False, f"PyMuPDF error: {exc}"
    if not body.strip():
        return False, "PyMuPDF produced empty text (scanned PDF?)"
    target.write_text(body, encoding="utf-8")
    return True, str(target)


def extract_docx(source: Path, output_dir: Path) -> tuple[bool, str]:
    try:
        from docx import Document
    except ImportError:
        return False, "python-docx not installed"
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{safe_name(source.stem)}.md"
    try:
        doc = Document(str(source))
        paragraphs = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
    except Exception as exc:  # noqa: BLE001
        return False, f"python-docx error: {exc}"
    if not paragraphs:
        return False, "Document contains no paragraphs"
    target.write_text("\n\n".join(paragraphs), encoding="utf-8")
    return True, str(target)


def extract_markdown(source: Path, output_dir: Path) -> tuple[bool, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{safe_name(source.stem)}.md"
    shutil.copy2(source, target)
    return True, str(target)


def extract_one(source: Path, output_dir: Path, timeout: int) -> dict:
    suffix = source.suffix.lower()
    record: dict = {
        "source": source.name,
        "source_sha256": sha256_file(source),
        "size_bytes": source.stat().st_size,
        "extractor": None,
        "output": None,
        "status": "pending",
        "message": "",
    }
    if suffix in SUPPORTED_PDF:
        ok, payload = extract_pdf_mineru(source, output_dir, timeout)
        if ok:
            record["extractor"] = "mineru-open-api"
            record["output"] = payload
            record["status"] = "success"
            return record
        record["message"] = f"mineru failed: {payload}; trying PyMuPDF"
        ok2, payload2 = extract_pdf_pymupdf(source, output_dir)
        if ok2:
            record["extractor"] = "pymupdf-fallback"
            record["output"] = payload2
            record["status"] = "success"
            record["message"] = f"mineru failed: {payload}; used PyMuPDF fallback"
            return record
        record["status"] = "failed"
        record["message"] = f"mineru: {payload}; pymupdf: {payload2}"
        return record
    if suffix in SUPPORTED_DOCX:
        ok, payload = extract_docx(source, output_dir)
        record["extractor"] = "python-docx"
        record["status"] = "success" if ok else "failed"
        record["output"] = payload if ok else None
        record["message"] = payload if not ok else ""
        return record
    if suffix in SUPPORTED_MD:
        ok, payload = extract_markdown(source, output_dir)
        record["extractor"] = "copy"
        record["status"] = "success" if ok else "failed"
        record["output"] = payload if ok else None
        record["message"] = payload if not ok else ""
        return record
    record["status"] = "unsupported"
    record["message"] = f"unsupported extension: {suffix}"
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description="提取用户提供的文献全文（Phase 1.7）")
    parser.add_argument("--workdir", required=True, help="项目工作目录")
    parser.add_argument("--input-dir", default=None,
                        help="PDF/Word/MD 源目录；默认扫描 user_materials/ 顶层（不含 extracted/）")
    parser.add_argument("--timeout", type=int, default=300, help="单篇 MinerU 超时秒数")
    args = parser.parse_args()

    workdir = Path(args.workdir).expanduser().resolve()
    if not workdir.is_dir():
        print(f"FAIL: 工作目录不存在: {workdir}")
        return 2

    extracted_dir = workdir / "user_materials" / "extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)

    input_dir = Path(args.input_dir).expanduser().resolve() if args.input_dir else (workdir / "user_materials")
    if not input_dir.is_dir():
        print(f"FAIL: 输入目录不存在: {input_dir}")
        return 2

    candidates: list[Path] = []
    for entry in sorted(input_dir.iterdir()):
        if entry.is_dir():
            continue
        if entry.parent.name == "extracted":
            continue
        suffix = entry.suffix.lower()
        if suffix in (SUPPORTED_PDF | SUPPORTED_DOCX | SUPPORTED_MD):
            candidates.append(entry)

    if not candidates:
        print(json.dumps({
            "ok": True,
            "extracted": 0,
            "message": "未找到可提取的 PDF/Word/Markdown 文件",
        }, ensure_ascii=False))
        return 0

    manifest_path = extracted_dir / "extraction_manifest.json"
    existing: dict[str, dict] = {}
    if manifest_path.is_file():
        try:
            existing = {item["source_sha256"]: item for item in json.loads(manifest_path.read_text(encoding="utf-8")).get("items", [])}
        except (OSError, json.JSONDecodeError):
            existing = {}

    items: list[dict] = list(existing.values())
    new_records: list[dict] = []
    for source in candidates:
        digest = sha256_file(source)
        if digest in existing and existing[digest].get("status") == "success":
            continue
        record = extract_one(source, extracted_dir, args.timeout)
        record["source_sha256"] = digest
        record["extracted_at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        items.append(record)
        new_records.append(record)

    items.sort(key=lambda x: x.get("source", ""))
    manifest = {
        "schema_version": "1.6",
        "workdir": str(workdir),
        "items": items,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    }
    tmp = manifest_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, manifest_path)

    successful = sum(1 for r in new_records if r.get("status") == "success")
    failed = sum(1 for r in new_records if r.get("status") == "failed")
    print(json.dumps({
        "ok": True,
        "scanned": len(candidates),
        "new_successful": successful,
        "new_failed": failed,
        "manifest": str(manifest_path),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
