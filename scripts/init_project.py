#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Initialize a research-topic-selection v1.5.2 work directory.

The script freezes scope decisions in protocol.json and creates the structured
ledgers used by later gates. It never overwrites an initialized project.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile


DELIVERABLE_STAKES = {
    "课程论文": "standard",
    "研究构想": "standard",
    "学位论文": "high",
    "期刊论文": "high",
    "基金申报": "high",
}
DISCIPLINE_BRANCHES = ["实证量化", "质性案例", "理论建构", "工程应用"]
SCAN_DIMS = ["政策扫描", "学术文献扫描", "现实实践扫描", "数据/材料扫描", "发表/申报窗口扫描"]


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as file:
        file.write(text)
        temp_name = file.name
    os.replace(temp_name, path)


def atomic_write_json(path: Path, data: dict) -> None:
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="初始化 research-topic-selection v1.5.2 工作目录")
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--why-now", required=True)
    parser.add_argument("--research-base", "--materials", dest="research_base", required=True)
    parser.add_argument("--deliverable-type", required=True, choices=sorted(DELIVERABLE_STAKES))
    parser.add_argument("--discipline-branch", required=True, choices=DISCIPLINE_BRANCHES)
    parser.add_argument("--time-window", required=True)
    parser.add_argument("--language", action="append", dest="languages")
    parser.add_argument("--constraint", action="append", dest="constraints")
    args = parser.parse_args()

    minimums = {
        "topic": (args.topic.strip(), 8),
        "why-now": (args.why_now.strip(), 20),
        "research-base": (args.research_base.strip(), 20),
        "time-window": (args.time_window.strip(), 4),
    }
    too_short = [f"{name}<{minimum}" for name, (value, minimum) in minimums.items() if len(value) < minimum]
    if too_short:
        print("FAIL: 初始化输入过薄，无法形成可审计 scope: " + ", ".join(too_short))
        return 1

    root = Path(args.workdir).expanduser().resolve()
    managed = [root / "protocol.json", root / "00_任务元信息.md", root / "01_三问与澄清.md"]
    existing = [str(path) for path in managed if path.exists()]
    if existing:
        print("FAIL: 工作目录已经初始化，拒绝覆盖: " + ", ".join(existing))
        return 1

    root.mkdir(parents=True, exist_ok=True)
    (root / "review" / "transcripts").mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    languages = args.languages or ["zh-CN"]
    constraints = args.constraints or []
    protocol = {
        "schema_version": "1.5",
        "topic": minimums["topic"][0],
        "deliverable_type": args.deliverable_type,
        "stakes": DELIVERABLE_STAKES[args.deliverable_type],
        "discipline_branch": args.discipline_branch,
        "time_window": minimums["time-window"][0],
        "languages": languages,
        "constraints": constraints,
        "scan_dimensions": SCAN_DIMS,
        "frozen_at": now,
    }
    metadata = (
        "# 任务元信息\n\n"
        f"- 研究主题：{args.topic.strip()}\n"
        f"- 交付类型：{args.deliverable_type}\n"
        f"- 风险档位：{protocol['stakes']}\n"
        f"- 初始化时间：{now}\n"
        "- 流程版本：research-topic-selection v1.5.2\n"
    )
    scope = (
        "# 三问与澄清\n\n"
        f"## 关心的问题\n{args.topic.strip()}\n\n"
        f"## 为什么是现在\n{args.why_now.strip()}\n\n"
        f"## 材料或基础\n{args.research_base.strip()}\n\n"
        f"## 学科取向\n{args.discipline_branch}\n\n"
        f"## 利害关系档\n{args.deliverable_type}（{protocol['stakes']}）\n\n"
        f"## 时间范围\n{args.time_window.strip()}\n\n"
        f"## 语言\n{', '.join(languages)}\n\n"
        f"## 硬约束\n{'; '.join(constraints) if constraints else '暂无额外约束'}\n"
    )
    atomic_write_json(root / "protocol.json", protocol)
    atomic_write_text(root / "00_任务元信息.md", metadata)
    atomic_write_text(root / "01_三问与澄清.md", scope)
    (root / "user_materials").mkdir(parents=True, exist_ok=True)
    atomic_write_json(
        root / "review" / "user_material_manifest.json",
        {"schema_version": "1.5", "workdir": str(root), "items": []},
    )
    atomic_write_text(root / "review" / "evidence_registry.jsonl", "")
    atomic_write_json(
        root / "review" / "question_scores.json",
        {"schema_version": "1.5", "candidates": [], "selected_card_ids": []},
    )
    print(json.dumps({"ok": True, "workdir": str(root), "protocol": protocol}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
