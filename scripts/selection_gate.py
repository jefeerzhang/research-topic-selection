#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""research-topic-selection rigid gate (v1.5.2; schema v1.5).

The gate validates phase deliverables, the embedded Good Question stage, and
the two independent review nodes (`scan` and `topics`). It is intentionally
stricter than a simple file-exists check: review verdicts must be tied to the
current workdir, current artifacts, the transcript hash, and closed P0
dispositions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


ENTER_ALIASES = {
    "1": "scope",
    "scope": "scope",
    "1.5": "materials",
    "materials": "materials",
    "2": "scan",
    "scan": "scan",
    "4": "scan-review",
    "scan-review": "scan-review",
    "5": "literature",
    "literature": "literature",
    "6": "questions",
    "questions": "questions",
    "7": "topics",
    "topics": "topics",
    "final": "final",
}

DELIVERABLE_STAKES = {
    "课程论文": "standard",
    "研究构想": "standard",
    "学位论文": "high",
    "期刊论文": "high",
    "基金申报": "high",
}

DISCIPLINE_BRANCHES = {"实证量化", "质性案例", "理论建构", "工程应用"}
MATERIAL_CATEGORIES = {"literature", "literature-note", "topic-abstract"}
MATERIAL_ORIGINS = {"user-upload", "user-inline"}
EVIDENCE_STANCES = {"support", "counter", "mixed"}
EVIDENCE_STATUSES = {"verified", "unavailable"}
MATERIAL_RELATIONS = {"confirm", "challenge", "extend", "independent"}
QUESTION_SCORE_KEYS = ["重要性", "可行性", "可证伪性", "证据杠杆", "原创性", "负向结果价值"]

DELIVERY_ARTIFACTS = [
    "protocol.json",
    "01_三问与澄清.md",
    "02_用户材料研判.md",
    "03_五维扫描.md",
    "04_问题域地图.md",
    "05_文献脉络.md",
    "06_趋势判断.md",
    "07_核心缺口.md",
    "07A_好问题卡.md",
    "08_选题推荐.md",
    "review/evidence_registry.jsonl",
    "review/user_material_manifest.json",
    "review/question_scores.json",
    "review/review_scan.json",
    "review/review_topics.json",
]

SCAN_DIMS = [
    "政策扫描",
    "学术文献扫描",
    "现实实践扫描",
    "数据/材料扫描",
    "发表/申报窗口扫描",
]

REVIEW_BINDINGS = {
    "scan": [
        "protocol.json",
        "01_三问与澄清.md",
        "02_用户材料研判.md",
        "03_五维扫描.md",
        "04_问题域地图.md",
        "review/evidence_registry.jsonl",
        "review/user_material_manifest.json",
    ],
    "topics": [
        "protocol.json",
        "05_文献脉络.md",
        "06_趋势判断.md",
        "07_核心缺口.md",
        "07A_好问题卡.md",
        "08_选题推荐.md",
        "review/evidence_registry.jsonl",
        "review/question_scores.json",
    ],
}

QUESTION_CARD_MARKERS = [
    "核心研究问题",
    "为什么值得做",
    "挑战了什么默认假设",
    "竞争性解释",
    "关键判别证据或实验",
    "什么结果会推翻它",
    "两周内可做的 pilot",
    "需要的数据/资源",
    "最强评审质疑",
    "下一步动作",
]

QUESTION_SCORE_MARKERS = QUESTION_SCORE_KEYS

ALWAYS_INDEPENDENT = {"scan", "topics"}
DISPOSITION_STATUSES = {"已修正", "反驳成立", "不适用"}
MAX_REVIEW_ROUNDS = 3


class GateFail(Exception):
    """Expected validation failure."""


class LoopExceeded(Exception):
    """Review loop exceeded the configured maximum."""


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def normpath(path: str) -> str:
    return os.path.normcase(os.path.abspath(os.path.normpath(path)))


def read_text(workdir: str, rel: str) -> str:
    path = os.path.join(workdir, rel)
    if not os.path.isfile(path):
        raise GateFail(f"缺失文件: {rel}")
    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
        return f.read()


def load_json(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise GateFail(f"JSON 根对象必须是 object: {path}")
    return data


def load_json_rel(workdir: str, rel: str) -> dict[str, Any]:
    path = os.path.join(workdir, rel)
    if not os.path.isfile(path):
        raise GateFail(f"缺失文件: {rel}")
    try:
        return load_json(path)
    except json.JSONDecodeError as exc:
        raise GateFail(f"JSON 解析失败: {rel}: {exc}") from exc


def load_jsonl(workdir: str, rel: str) -> list[dict[str, Any]]:
    path = os.path.join(workdir, rel)
    if not os.path.isfile(path):
        raise GateFail(f"缺失文件: {rel}")
    rows: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8-sig") as file:
        for line_no, raw in enumerate(file, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise GateFail(f"{rel}:{line_no} JSON 解析失败: {exc}") from exc
            if not isinstance(row, dict):
                raise GateFail(f"{rel}:{line_no} 必须是 JSON object")
            rows.append(row)
    if not rows:
        raise GateFail(f"{rel} 不得为空")
    return rows


def require_string(data: dict[str, Any], key: str, rel: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise GateFail(f"{rel}.{key} 必须是非空字符串")
    return value.strip()


def check_protocol(workdir: str) -> dict[str, Any]:
    rel = "protocol.json"
    protocol = load_json_rel(workdir, rel)
    if protocol.get("schema_version") != "1.5":
        raise GateFail(f"{rel}.schema_version 必须为 1.5")
    require_string(protocol, "topic", rel)
    deliverable = require_string(protocol, "deliverable_type", rel)
    if deliverable not in DELIVERABLE_STAKES:
        raise GateFail(f"{rel}.deliverable_type 非法: {deliverable}")
    if protocol.get("stakes") != DELIVERABLE_STAKES[deliverable]:
        raise GateFail(
            f"{rel}.stakes={protocol.get('stakes')}，期望 {DELIVERABLE_STAKES[deliverable]}"
        )
    branch = require_string(protocol, "discipline_branch", rel)
    if branch not in DISCIPLINE_BRANCHES:
        raise GateFail(f"{rel}.discipline_branch 非法: {branch}")
    require_string(protocol, "time_window", rel)
    languages = protocol.get("languages")
    if not isinstance(languages, list) or not languages or not all(
        isinstance(item, str) and item.strip() for item in languages
    ):
        raise GateFail(f"{rel}.languages 必须是非空字符串数组")
    constraints = protocol.get("constraints")
    if not isinstance(constraints, list):
        raise GateFail(f"{rel}.constraints 必须是数组")
    dimensions = protocol.get("scan_dimensions")
    if dimensions != SCAN_DIMS:
        raise GateFail(f"{rel}.scan_dimensions 必须与五维扫描标准顺序完全一致")
    frozen_at = require_string(protocol, "frozen_at", rel)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T.+", frozen_at):
        raise GateFail(f"{rel}.frozen_at 不是 ISO 时间")
    return protocol


def check_evidence_registry(workdir: str) -> list[dict[str, Any]]:
    rel = "review/evidence_registry.jsonl"
    rows = load_jsonl(workdir, rel)
    material_ids = {str(item["material_id"]) for item in check_user_materials(workdir)}
    seen_ids: set[str] = set()
    by_dimension: dict[str, list[dict[str, Any]]] = {dim: [] for dim in SCAN_DIMS}
    for index, row in enumerate(rows, start=1):
        evidence_id = require_string(row, "evidence_id", f"{rel}:{index}")
        if evidence_id in seen_ids:
            raise GateFail(f"{rel} evidence_id 重复: {evidence_id}")
        seen_ids.add(evidence_id)
        dimension = require_string(row, "dimension", f"{rel}:{index}")
        if dimension not in by_dimension:
            raise GateFail(f"{rel}:{index}.dimension 非法: {dimension}")
        status = require_string(row, "status", f"{rel}:{index}")
        if status not in EVIDENCE_STATUSES:
            raise GateFail(f"{rel}:{index}.status 非法: {status}")
        require_string(row, "claim", f"{rel}:{index}")
        links = row.get("material_links")
        if not isinstance(links, list) or not all(isinstance(item, str) and item.strip() for item in links):
            raise GateFail(f"{rel}:{index}.material_links 必须是字符串数组")
        unknown_links = {item.strip() for item in links} - material_ids
        if unknown_links:
            raise GateFail(f"{rel}:{index}.material_links 含未登记材料 ID: {', '.join(sorted(unknown_links))}")
        relation = require_string(row, "relation", f"{rel}:{index}")
        if relation not in MATERIAL_RELATIONS:
            raise GateFail(f"{rel}:{index}.relation 非法: {relation}")
        if links and relation == "independent":
            raise GateFail(f"{rel}:{index} 已关联用户材料，relation 不得为 independent")
        if not links and relation != "independent":
            raise GateFail(f"{rel}:{index} 未关联用户材料时，relation 必须为 independent")
        if status == "verified":
            require_string(row, "source_title", f"{rel}:{index}")
            url = require_string(row, "source_url", f"{rel}:{index}")
            if not re.match(r"https?://", url, flags=re.I):
                raise GateFail(f"{rel}:{index}.source_url 必须是 HTTP(S) URL")
            require_string(row, "publication_date", f"{rel}:{index}")
            require_string(row, "accessed_at", f"{rel}:{index}")
            stance = require_string(row, "stance", f"{rel}:{index}")
            if stance not in EVIDENCE_STANCES:
                raise GateFail(f"{rel}:{index}.stance 非法: {stance}")
        else:
            require_string(row, "reason", f"{rel}:{index}")
            attempts = row.get("attempted_queries")
            if not isinstance(attempts, list) or len(attempts) < 2 or not all(
                isinstance(item, str) and item.strip() for item in attempts
            ):
                raise GateFail(f"{rel}:{index}.attempted_queries 至少需要 2 个非空检索式")
        by_dimension[dimension].append(row)

    for dimension, items in by_dimension.items():
        if not items:
            raise GateFail(f"{rel} 缺少维度: {dimension}")
        verified = [item for item in items if item.get("status") == "verified"]
        unavailable = [item for item in items if item.get("status") == "unavailable"]
        if not verified and not unavailable:
            raise GateFail(f"{rel} 的 {dimension} 没有可用证据或显式 unavailable 留痕")
        if verified and not any(item.get("stance") in {"counter", "mixed"} for item in verified):
            raise GateFail(f"{rel} 的 {dimension} 缺少 counter/mixed 反面或竞争性证据")
    return rows


def check_question_scores(workdir: str) -> tuple[list[dict[str, Any]], set[str]]:
    rel = "review/question_scores.json"
    data = load_json_rel(workdir, rel)
    if data.get("schema_version") != "1.5":
        raise GateFail(f"{rel}.schema_version 必须为 1.5")
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not 5 <= len(candidates) <= 10:
        raise GateFail(f"{rel}.candidates 需要 5-10 项")
    selected_raw = data.get("selected_card_ids")
    if not isinstance(selected_raw, list) or not 1 <= len(selected_raw) <= 3:
        raise GateFail(f"{rel}.selected_card_ids 需要 1-3 项")
    selected = {str(item).strip() for item in selected_raw if str(item).strip()}
    if len(selected) != len(selected_raw):
        raise GateFail(f"{rel}.selected_card_ids 不得为空或重复")

    seen: set[str] = set()
    selected_by_decision: set[str] = set()
    for index, candidate in enumerate(candidates, start=1):
        if not isinstance(candidate, dict):
            raise GateFail(f"{rel}.candidates[{index}] 必须是 object")
        candidate_id = require_string(candidate, "candidate_id", f"{rel}.candidates[{index}]")
        if candidate_id in seen:
            raise GateFail(f"{rel} candidate_id 重复: {candidate_id}")
        seen.add(candidate_id)
        require_string(candidate, "question", f"{rel}.candidates[{index}]")
        require_string(candidate, "gap_id", f"{rel}.candidates[{index}]")
        require_string(candidate, "rationale", f"{rel}.candidates[{index}]")
        scores = candidate.get("scores")
        if not isinstance(scores, dict) or set(scores) != set(QUESTION_SCORE_KEYS):
            raise GateFail(f"{rel} 的 {candidate_id}.scores 必须恰好包含六个评分维度")
        values: list[int] = []
        for key in QUESTION_SCORE_KEYS:
            value = scores.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 5:
                raise GateFail(f"{rel} 的 {candidate_id}.{key} 必须是 1-5 整数")
            values.append(value)
        if candidate.get("total") != sum(values):
            raise GateFail(f"{rel} 的 {candidate_id}.total 与六维评分之和不一致")
        decision = candidate.get("decision")
        if decision not in {"selected", "parked", "dropped"}:
            raise GateFail(f"{rel} 的 {candidate_id}.decision 非法: {decision}")
        if decision == "selected":
            selected_by_decision.add(candidate_id)
        if decision == "dropped" and not str(candidate.get("kill_rule") or "").strip():
            raise GateFail(f"{rel} 的 {candidate_id} 已 dropped，但缺少 kill_rule")
    if selected != selected_by_decision:
        raise GateFail(f"{rel}.selected_card_ids 与 decision=selected 的候选不一致")
    return candidates, selected


def require_file(workdir: str, rel: str, min_chars: int = 1) -> str:
    txt = read_text(workdir, rel)
    if len(txt.strip()) < min_chars:
        raise GateFail(f"{rel} 内容过少，至少需要 {min_chars} 个字符")
    return txt


def require_markers(workdir: str, rel: str, markers: list[str]) -> str:
    txt = require_file(workdir, rel)
    missing = [marker for marker in markers if marker not in txt]
    if missing:
        raise GateFail(f"{rel} 缺少必需段落/关键词: {', '.join(missing)}")
    return txt


def require_section_after_marker(txt: str, rel: str, marker: str, min_chars: int = 20) -> None:
    idx = txt.find(marker)
    if idx < 0:
        raise GateFail(f"{rel} 缺少必需段落: {marker}")
    tail = txt[idx + len(marker) :].strip()
    if len(tail) < min_chars:
        raise GateFail(f"{rel} 的「{marker}」段内容过少")


def count_marked_headings(txt: str, marker: str) -> int:
    pattern = re.compile(rf"(?m)^#{{1,6}}\s*{re.escape(marker)}(?:\s*\d+)?(?:\s*[:：].*)?\s*$")
    return len(pattern.findall(txt))


def marked_sections(txt: str, marker: str) -> list[str]:
    pattern = re.compile(rf"(?m)^#{{1,6}}\s*{re.escape(marker)}(?:\s*\d+)?(?:\s*[:：].*)?\s*$")
    matches = list(pattern.finditer(txt))
    sections: list[str] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(txt)
        sections.append(txt[match.end() : end])
    return sections


def extract_last_fenced_json(txt: str) -> dict[str, Any] | None:
    blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", txt, flags=re.S | re.I)
    for block in reversed(blocks):
        try:
            parsed = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def review_had_p0(rv: dict[str, Any]) -> bool:
    if rv.get("p0"):
        return True
    history = rv.get("history", [])
    if not isinstance(history, list):
        raise GateFail("review.history 必须是数组")
    for item in history:
        if not isinstance(item, dict):
            raise GateFail("review.history 内部元素必须是 object")
        try:
            if int(item.get("p0_found", 0)) > 0 or int(item.get("p0_open", 0)) > 0:
                return True
        except (TypeError, ValueError):
            raise GateFail("review.history 的 p0_found/p0_open 必须是整数")
    return False


def expected_p0_ids(rv: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for item in rv.get("history", []):
        for p0_id in item.get("p0_ids", []) or []:
            ids.add(str(p0_id))
    for item in rv.get("p0", []) or []:
        if isinstance(item, dict) and item.get("id"):
            ids.add(str(item["id"]))
    return ids


def verify_dispositions(workdir: str, node: str, rv: dict[str, Any]) -> None:
    if not review_had_p0(rv):
        return
    disp_rel = os.path.join("review", f"dispositions_{node}.json")
    disp_path = os.path.join(workdir, disp_rel)
    if not os.path.isfile(disp_path):
        raise GateFail(f"审查节点 {node} 曾出现 P0，但缺失处置闭环: {disp_rel}")
    artifact_hashes = rv.get("artifact_hashes")
    canonical_rel = disp_rel.replace(os.sep, "/")
    declared_hash = artifact_hashes.get(canonical_rel) if isinstance(artifact_hashes, dict) else None
    if declared_hash != sha256_of(disp_path):
        raise GateFail(f"审查节点 {node} 的终版处置台账未被重签 verdict hash 绑定: {canonical_rel}")
    disp = load_json(disp_path)
    findings = disp.get("findings")
    if not isinstance(findings, list) or not findings:
        raise GateFail(f"{disp_rel} 必须包含非空 findings 数组")

    seen: set[str] = set()
    for item in findings:
        if not isinstance(item, dict):
            raise GateFail(f"{disp_rel}.findings 内部元素必须是 object")
        fid = str(item.get("id", "")).strip()
        status = item.get("status")
        decision = item.get("reviewer_decision")
        if not fid:
            raise GateFail(f"{disp_rel} 存在缺少 id 的处置项")
        seen.add(fid)
        if status not in DISPOSITION_STATUSES:
            raise GateFail(f"{disp_rel} 的 {fid} status 非法: {status}")
        if decision != "accepted":
            raise GateFail(f"{disp_rel} 的 {fid} 尚未被原审查者 accepted")
        if not str(item.get("evidence", "")).strip():
            raise GateFail(f"{disp_rel} 的 {fid} 缺少 evidence")

    missing = expected_p0_ids(rv) - seen
    if missing:
        raise GateFail(f"{disp_rel} 未覆盖历史 P0: {', '.join(sorted(missing))}")
    if rv.get("re_reviewed_dispositions") is not True:
        raise GateFail(f"审查节点 {node} 出现过 P0，review.re_reviewed_dispositions 必须为 true")


def verify_review(workdir: str, node: str) -> dict[str, Any]:
    rv_rel = os.path.join("review", f"review_{node}.json")
    rv_path = os.path.join(workdir, rv_rel)
    if not os.path.isfile(rv_path):
        raise GateFail(f"缺失审查 verdict: {rv_rel}")
    rv = load_json(rv_path)

    if rv.get("node") != node:
        raise GateFail(f"{rv_rel} node={rv.get('node')}，期望 {node}")
    if rv.get("workdir") is None:
        raise GateFail(f"{rv_rel} 缺少 workdir")
    if normpath(str(rv["workdir"])) != normpath(workdir):
        raise GateFail(f"{rv_rel} workdir 与当前目录不一致")
    if node in ALWAYS_INDEPENDENT and rv.get("reviewer_kind") != "independent":
        raise GateFail(f"审查节点 {node} 必须 reviewer_kind=independent")
    if rv.get("verdict") != "PASS":
        raise GateFail(f"审查节点 {node} verdict={rv.get('verdict')}，未 PASS")

    try:
        round_no = int(rv.get("round"))
    except (TypeError, ValueError):
        raise GateFail(f"{rv_rel} round 必须是整数")
    if round_no < 1:
        raise GateFail(f"{rv_rel} round 必须 >= 1")
    if round_no > MAX_REVIEW_ROUNDS:
        raise LoopExceeded(f"审查节点 {node} round={round_no} 超界 > {MAX_REVIEW_ROUNDS}")

    try:
        p0_open = int(rv.get("p0_open"))
    except (TypeError, ValueError):
        raise GateFail(f"{rv_rel} p0_open 必须是整数")
    if p0_open != 0:
        raise GateFail(f"审查节点 {node} p0_open={p0_open}，未闭合")
    if rv.get("p0"):
        raise GateFail(f"审查节点 {node} 当前 verdict 仍含 P0 列表，未闭合")

    reviewer = rv.get("reviewer_agent_id")
    producer = rv.get("producer_agent_id")
    if not reviewer or not producer or reviewer == producer:
        raise GateFail(f"审查节点 {node} reviewer/producer 缺失或相等（自审违规）")

    artifact_hashes = rv.get("artifact_hashes")
    if not isinstance(artifact_hashes, dict):
        raise GateFail(f"{rv_rel} artifact_hashes 必须是 object")
    for art in REVIEW_BINDINGS.get(node, []):
        ap = os.path.join(workdir, art)
        if not os.path.isfile(ap):
            raise GateFail(f"审查绑定产物缺失: {art}（node={node}）")
        if art not in artifact_hashes:
            raise GateFail(f"verdict 未绑定: {art}（node={node}）")
        actual = sha256_of(ap)
        if artifact_hashes[art] != actual:
            raise GateFail(f"hash 失配: {art}（node={node}，产物已变更，旧 verdict 失效）")

    transcript_rel = rv.get("transcript_path") or os.path.join("review", "transcripts", f"{node}_r{round_no}.md")
    transcript_path = (
        str(transcript_rel)
        if os.path.isabs(str(transcript_rel))
        else os.path.join(workdir, str(transcript_rel))
    )
    if not os.path.isfile(transcript_path):
        raise GateFail(f"缺失审查 transcript: {transcript_rel}")
    agent_output_sha256 = rv.get("agent_output_sha256")
    if not agent_output_sha256:
        raise GateFail(f"{rv_rel} 缺少 agent_output_sha256")
    if agent_output_sha256 != sha256_of(transcript_path):
        raise GateFail(f"审查 transcript hash 失配: {transcript_rel}")

    with open(transcript_path, "r", encoding="utf-8-sig", errors="ignore") as f:
        transcript_txt = f.read()
    transcript_json = extract_last_fenced_json(transcript_txt)
    if transcript_json is None:
        raise GateFail(f"{transcript_rel} 未找到 fenced JSON verdict")
    rv_without_append = {k: v for k, v in rv.items() if k not in {"agent_output_sha256", "transcript_path"}}
    for key, value in transcript_json.items():
        if rv_without_append.get(key) != value:
            raise GateFail(f"{rv_rel} 与 transcript fenced JSON 字段不一致: {key}")

    verify_dispositions(workdir, node, rv)
    return rv


def check_scope(workdir: str) -> None:
    check_protocol(workdir)
    require_markers(
        workdir,
        "01_三问与澄清.md",
        ["关心的问题", "为什么是现在", "材料或基础", "学科取向", "利害关系档"],
    )
    require_file(workdir, "01_三问与澄清.md", min_chars=180)


def check_user_materials(workdir: str) -> list[dict[str, Any]]:
    rel = "review/user_material_manifest.json"
    manifest = load_json_rel(workdir, rel)
    if manifest.get("schema_version") != "1.5":
        raise GateFail(f"{rel}.schema_version 必须为 1.5")
    if normpath(str(manifest.get("workdir") or "")) != normpath(workdir):
        raise GateFail(f"{rel}.workdir 与当前目录不一致")
    items = manifest.get("items")
    if not isinstance(items, list) or not items:
        raise GateFail("尚未登记用户材料：请让用户上传文献、文献笔记或研究题目与摘要")

    root = normpath(workdir)
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise GateFail(f"{rel}.items[{index}] 必须是 object")
        item_rel = f"{rel}.items[{index}]"
        material_id = require_string(item, "material_id", item_rel)
        if material_id in seen_ids:
            raise GateFail(f"{rel} material_id 重复: {material_id}")
        seen_ids.add(material_id)
        category = require_string(item, "category", item_rel)
        if category not in MATERIAL_CATEGORIES:
            raise GateFail(f"{item_rel}.category 非法: {category}")
        origin = require_string(item, "origin", item_rel)
        if origin not in MATERIAL_ORIGINS:
            raise GateFail(f"{item_rel}.origin 非法: {origin}")
        require_string(item, "original_name", item_rel)
        stored_rel = require_string(item, "stored_path", item_rel).replace("/", os.sep)
        if os.path.isabs(stored_rel) or os.path.normpath(stored_rel).startswith(".."):
            raise GateFail(f"{item_rel}.stored_path 必须是工作目录内相对路径")
        stored_path = normpath(os.path.join(workdir, stored_rel))
        if stored_path == root or not stored_path.startswith(root + os.sep):
            raise GateFail(f"{item_rel}.stored_path 越出工作目录")
        if stored_path in seen_paths:
            raise GateFail(f"{rel} stored_path 重复: {stored_rel}")
        seen_paths.add(stored_path)
        if not os.path.isfile(stored_path):
            raise GateFail(f"用户材料文件缺失: {stored_rel}")
        expected_size = item.get("size_bytes")
        if not isinstance(expected_size, int) or expected_size <= 0:
            raise GateFail(f"{item_rel}.size_bytes 必须是正整数")
        if os.path.getsize(stored_path) != expected_size:
            raise GateFail(f"用户材料大小失配: {stored_rel}")
        expected_hash = require_string(item, "sha256", item_rel)
        if not re.fullmatch(r"[0-9a-fA-F]{64}", expected_hash):
            raise GateFail(f"{item_rel}.sha256 格式非法")
        if sha256_of(stored_path).lower() != expected_hash.lower():
            raise GateFail(f"用户材料 hash 失配，文件登记后已改变: {stored_rel}")
        require_string(item, "registered_at", item_rel)

    analysis_rel = "02_用户材料研判.md"
    analysis = require_markers(
        workdir,
        analysis_rel,
        [
            "材料概览",
            "用户已有研究问题",
            "用户已有证据与观点",
            "材料之间的冲突",
            "对后续检索的约束",
            "尚待核验",
        ],
    )
    for material_id in seen_ids:
        if material_id not in analysis:
            raise GateFail(f"{analysis_rel} 未引用已登记材料 ID: {material_id}")
    require_file(workdir, analysis_rel, min_chars=400)
    return items


def check_materials(workdir: str) -> None:
    check_scope(workdir)
    check_user_materials(workdir)


def check_scan(workdir: str) -> None:
    check_materials(workdir)
    txt = require_markers(workdir, "03_五维扫描.md", SCAN_DIMS + ["反确认偏差记录"])
    for marker in SCAN_DIMS:
        require_section_after_marker(txt, "03_五维扫描.md", marker, min_chars=20)
    require_section_after_marker(txt, "03_五维扫描.md", "反确认偏差记录", min_chars=40)
    check_evidence_registry(workdir)


def check_map(workdir: str) -> None:
    require_markers(
        workdir,
        "04_问题域地图.md",
        ["核心现实问题", "主要学术分支", "政策/实践变化", "可用数据", "潜在研究切口", "初步风险判断"],
    )
    require_file(workdir, "04_问题域地图.md", min_chars=300)


def check_literature(workdir: str) -> None:
    require_markers(workdir, "05_文献脉络.md", ["前沿方向", "核心争论", "方法谱系"])
    require_file(workdir, "05_文献脉络.md", min_chars=200)


def check_trend(workdir: str) -> None:
    require_markers(
        workdir,
        "06_趋势判断.md",
        ["政策趋势", "实践趋势", "学术趋势", "数据与方法趋势", "阶段判断"],
    )
    require_file(workdir, "06_趋势判断.md", min_chars=220)


def check_gap(workdir: str) -> None:
    require_markers(workdir, "07_核心缺口.md", ["核心缺口", "既有研究已解释", "仍不足", "为何重要"])
    require_file(workdir, "07_核心缺口.md", min_chars=200)


def check_questions(workdir: str) -> None:
    txt = require_markers(
        workdir,
        "07A_好问题卡.md",
        ["候选问题评分"] + QUESTION_SCORE_MARKERS + QUESTION_CARD_MARKERS,
    )
    candidate_count = count_marked_headings(txt, "候选问题")
    if candidate_count < 5 or candidate_count > 10:
        raise GateFail("07A_好问题卡.md 需要 5-10 个「候选问题」标题")

    candidates, selected = check_question_scores(workdir)
    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        if candidate_id not in txt:
            raise GateFail(f"07A_好问题卡.md 未出现结构化候选 ID: {candidate_id}")

    cards = marked_sections(txt, "好问题卡")
    if len(cards) < 1 or len(cards) > 3:
        raise GateFail("07A_好问题卡.md 需要 1-3 个「好问题卡」标题")
    for index, card in enumerate(cards, start=1):
        missing = [marker for marker in QUESTION_CARD_MARKERS if marker not in card]
        if missing:
            raise GateFail(f"好问题卡 {index} 缺少字段: {', '.join(missing)}")
        if len(card.strip()) < 250:
            raise GateFail(f"好问题卡 {index} 内容过少")
        card_id_match = re.search(
            r"卡片\s*ID\s*[:：]\s*(?:\*\*)?\s*([A-Za-z0-9_-]+)", card, flags=re.I
        )
        if card_id_match is None:
            raise GateFail(f"好问题卡 {index} 缺少「卡片 ID」")
        if card_id_match.group(1) not in selected:
            raise GateFail(f"好问题卡 {index} 的卡片 ID 未列入 selected_card_ids")
    require_file(workdir, "07A_好问题卡.md", min_chars=900)


def check_topics(workdir: str) -> None:
    txt = require_markers(
        workdir,
        "08_选题推荐.md",
        [
            "主推选题",
            "备选选题",
            "推荐判断",
            "最推荐推进",
            "主要风险",
            "下一步",
            "来源好问题卡",
        ],
    )
    main_topics = marked_sections(txt, "主推选题")
    if len(main_topics) < 3:
        raise GateFail("08_选题推荐.md 至少需要 3 个「主推选题」标题")
    _, selected = check_question_scores(workdir)
    for index, topic in enumerate(main_topics[:3], start=1):
        missing = [
            marker
            for marker in ["来源好问题卡", "研究问题", "数据/方法路径", "预期贡献", "可行性"]
            if marker not in topic
        ]
        if missing:
            raise GateFail(f"主推选题 {index} 缺少字段: {', '.join(missing)}")
        source_match = re.search(
            r"来源好问题卡\s*[:：]\s*(?:\*\*)?\s*([A-Za-z0-9_-]+)", topic, flags=re.I
        )
        if source_match is None:
            raise GateFail(f"主推选题 {index} 的来源好问题卡必须填写结构化卡片 ID")
        if source_match.group(1) not in selected:
            raise GateFail(f"主推选题 {index} 引用了未入选的好问题卡: {source_match.group(1)}")
    if count_marked_headings(txt, "备选选题") < 2:
        raise GateFail("08_选题推荐.md 至少需要 2 个「备选选题」标题")
    require_file(workdir, "08_选题推荐.md", min_chars=350)


def check_delivery_manifest(workdir: str) -> None:
    rel = "review/delivery_manifest.json"
    manifest = load_json_rel(workdir, rel)
    if manifest.get("schema_version") != "1.5":
        raise GateFail(f"{rel}.schema_version 必须为 1.5")
    if normpath(str(manifest.get("workdir") or "")) != normpath(workdir):
        raise GateFail(f"{rel}.workdir 与当前目录不一致")
    hashes = manifest.get("artifact_hashes")
    if not isinstance(hashes, dict):
        raise GateFail(f"{rel}.artifact_hashes 必须是 object")
    for artifact in DELIVERY_ARTIFACTS:
        path = os.path.join(workdir, artifact)
        if not os.path.isfile(path):
            raise GateFail(f"交付血缘产物缺失: {artifact}")
        if hashes.get(artifact) != sha256_of(path):
            raise GateFail(f"交付 manifest hash 失配: {artifact}")


def check_enter(workdir: str, enter: str) -> None:
    target = ENTER_ALIASES.get(enter)
    if target is None:
        raise GateFail(f"未知 enter 目标: {enter}")

    if target == "scope":
        check_scope(workdir)
        return
    if target == "materials":
        check_materials(workdir)
        return
    if target == "scan":
        check_scan(workdir)
        return
    if target == "scan-review":
        check_scan(workdir)
        check_map(workdir)
        verify_review(workdir, "scan")
        return
    if target == "literature":
        check_scan(workdir)
        check_map(workdir)
        verify_review(workdir, "scan")
        check_literature(workdir)
        return
    if target == "questions":
        check_scan(workdir)
        check_map(workdir)
        verify_review(workdir, "scan")
        check_literature(workdir)
        check_trend(workdir)
        check_gap(workdir)
        check_questions(workdir)
        return
    if target == "topics":
        check_enter(workdir, "questions")
        check_topics(workdir)
        verify_review(workdir, "topics")
        return
    if target == "final":
        check_enter(workdir, "topics")
        check_delivery_manifest(workdir)
        return


def artifact_hash_template(workdir: str, node: str) -> dict[str, Any]:
    if node not in REVIEW_BINDINGS:
        raise GateFail(f"未知 review node: {node}")
    return {
        "node": node,
        "workdir": normpath(workdir),
        "artifact_hashes": {
            rel: sha256_of(os.path.join(workdir, rel))
            for rel in REVIEW_BINDINGS[node]
            if os.path.isfile(os.path.join(workdir, rel))
        },
    }


def status_report(workdir: str) -> dict[str, Any]:
    stages = ["scope", "materials", "scan", "scan-review", "literature", "questions", "topics", "final"]
    completed: list[str] = []
    for stage in stages:
        try:
            check_enter(workdir, stage)
        except (GateFail, LoopExceeded) as exc:
            return {
                "ok": True,
                "complete": False,
                "completed": completed,
                "next": stage,
                "blocker": str(exc),
            }
        completed.append(stage)
    return {"ok": True, "complete": True, "completed": completed, "next": None, "blocker": None}


def main() -> int:
    ap = argparse.ArgumentParser(description="research-topic-selection 刚性闸门")
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--enter", choices=sorted(ENTER_ALIASES.keys()))
    ap.add_argument("--hash-template", choices=sorted(REVIEW_BINDINGS.keys()))
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    workdir = os.path.abspath(args.workdir)
    if not os.path.isdir(workdir):
        message = f"workdir 不存在: {workdir}"
        print(json.dumps({"ok": False, "error": message}, ensure_ascii=False) if args.json else f"FAIL: {message}")
        return 2

    try:
        if args.hash_template:
            result = artifact_hash_template(workdir, args.hash_template)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.status:
            result = status_report(workdir)
            if args.json:
                print(json.dumps(result, ensure_ascii=False))
            elif result["complete"]:
                print("STATUS: COMPLETE")
            else:
                done = ", ".join(result["completed"]) or "none"
                print(f"STATUS: completed={done}; next={result['next']}; blocker={result['blocker']}")
            return 0
        if not args.enter:
            raise GateFail("必须提供 --enter、--status，或使用 --hash-template 生成审查 hash 模板")
        check_enter(workdir, args.enter)
    except LoopExceeded as e:
        print(
            json.dumps({"ok": False, "loop_exceeded": True, "error": str(e)}, ensure_ascii=False)
            if args.json
            else f"LOOP_EXCEEDED: {e}"
        )
        return 3
    except GateFail as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False) if args.json else f"FAIL: {e}")
        return 1
    except Exception as e:  # noqa: BLE001
        message = f"{type(e).__name__}: {e}"
        print(json.dumps({"ok": False, "error": message}, ensure_ascii=False) if args.json else f"ERROR: {message}")
        return 2

    normalized = ENTER_ALIASES[args.enter]
    print(
        json.dumps({"ok": True, "enter": args.enter, "target": normalized}, ensure_ascii=False)
        if args.json
        else f"PASS: 允许进入 {normalized}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
