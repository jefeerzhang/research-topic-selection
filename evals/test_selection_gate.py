from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "selection_gate.py"
BUILD_MANIFEST = Path(__file__).resolve().parents[1] / "scripts" / "build_manifest.py"
INIT_PROJECT = Path(__file__).resolve().parents[1] / "scripts" / "init_project.py"
REGISTER_MATERIAL = Path(__file__).resolve().parents[1] / "scripts" / "register_material.py"
SPEC = importlib.util.spec_from_file_location("selection_gate", SCRIPT)
assert SPEC and SPEC.loader
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def write(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(root: Path, name: str, data: dict) -> None:
    write(root, name, json.dumps(data, ensure_ascii=False, indent=2))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protocol() -> dict:
    return {
        "schema_version": "1.5",
        "topic": "数字化转型如何影响企业韧性",
        "deliverable_type": "基金申报",
        "stakes": "high",
        "discipline_branch": "实证量化",
        "time_window": "2021-2026",
        "languages": ["zh-CN", "en-US"],
        "constraints": ["仅使用可获得数据"],
        "scan_dimensions": gate.SCAN_DIMS,
        "frozen_at": "2026-07-12T12:00:00+08:00",
    }


def scope_text() -> str:
    return "\n".join(
        [
            "# 三问与澄清",
            "## 关心的问题",
            "数字化转型如何通过不同机制影响企业韧性，并在何种制度条件下出现方向变化。",
            "## 为什么是现在",
            "近期政策、数据覆盖范围与企业实践均发生变化，使旧有结论值得重新检验。",
            "## 材料或基础",
            "已有企业面板数据、政策时间点、理论训练和可执行的计量分析工具。",
            "## 学科取向",
            "实证量化",
            "## 利害关系档",
            "基金申报（high）",
            "补充约束：只采用能够核验来源的数据，并在三个月内形成初步研究设计。",
        ]
    )


def evidence_rows(missing_counter_dimension: str | None = None) -> list[dict]:
    rows: list[dict] = []
    for index, dimension in enumerate(gate.SCAN_DIMS, start=1):
        rows.append(
            {
                "evidence_id": f"E{index}A",
                "dimension": dimension,
                "status": "verified",
                "claim": f"{dimension}存在支持该研究方向的直接证据。",
                "material_links": ["M-test12345678"],
                "relation": "confirm",
                "source_title": f"{dimension}支持来源",
                "source_url": f"https://example.org/{index}/support",
                "publication_date": "2025-01-01",
                "accessed_at": "2026-07-12",
                "stance": "support",
            }
        )
        if dimension != missing_counter_dimension:
            rows.append(
                {
                    "evidence_id": f"E{index}B",
                    "dimension": dimension,
                    "status": "verified",
                    "claim": f"{dimension}也存在限制条件或竞争性证据。",
                    "material_links": ["M-test12345678"],
                    "relation": "challenge",
                    "source_title": f"{dimension}反面来源",
                    "source_url": f"https://example.org/{index}/counter",
                    "publication_date": "2025-02-01",
                    "accessed_at": "2026-07-12",
                    "stance": "counter",
                }
            )
    return rows


def write_evidence(root: Path, missing_counter_dimension: str | None = None) -> None:
    text = "\n".join(json.dumps(row, ensure_ascii=False) for row in evidence_rows(missing_counter_dimension))
    write(root, "review/evidence_registry.jsonl", text + "\n")


def write_user_materials(root: Path) -> None:
    stored_rel = "user_materials/M-test12345678-user-note.md"
    material = (
        "# 用户研究笔记\n\n"
        "暂定题目：数字化转型如何通过信息处理与能力积累影响企业韧性。\n"
        "已有判断：不同制度环境下两种机制可能给出不同预测，需要寻找判别性证据。\n"
    )
    write(root, stored_rel, material)
    material_path = root / stored_rel
    material_id = "M-test12345678"
    write_json(
        root,
        "review/user_material_manifest.json",
        {
            "schema_version": "1.5",
            "workdir": gate.normpath(str(root)),
            "items": [
                {
                    "material_id": material_id,
                    "category": "literature-note",
                    "origin": "user-upload",
                    "label": "用户已有研究构想笔记",
                    "original_name": "user-note.md",
                    "stored_path": stored_rel,
                    "sha256": sha256(material_path),
                    "size_bytes": material_path.stat().st_size,
                    "registered_at": "2026-07-12T12:30:00+08:00",
                }
            ],
        },
    )
    analysis = "\n".join(
        [
            "# 用户材料研判",
            "## 材料概览",
            f"{material_id} 是用户研究笔记，包含暂定题目、两类竞争性机制和希望寻找判别证据的明确要求。",
            "## 用户已有研究问题",
            "用户关注数字化转型通过信息处理与能力积累影响企业韧性的差异，并希望识别制度边界。",
            "## 用户已有证据与观点",
            "材料直接表达了两类机制可能产生不同预测；目前尚未提供支持任一机制的系统经验文献。",
            "## 材料之间的冲突",
            "当前只有一份材料，不存在跨材料结论冲突，但题目范围与可操作变量之间仍有张力。",
            "## 对后续检索的约束",
            "后续必须围绕企业韧性、信息机制、能力机制和制度环境检索，不擅自改成一般数字化绩效研究。",
            "## 尚待核验",
            "需要核验两类机制的文献基础、可用代理变量、制度边界、反面结果以及公开数据可得性。",
            "证据边界说明：以上仅基于用户材料内容进行归纳，尚未把 Agent 的外部知识写成既有事实。" * 4,
        ]
    )
    write(root, "02_用户材料研判.md", analysis)


def scan_text() -> str:
    sections = ["# 五维扫描"]
    for dimension in gate.SCAN_DIMS:
        sections.extend(
            [
                f"## {dimension}",
                "支持证据表明该方向具有研究价值，但反面证据提示其效果依赖制度边界、样本范围和数据质量。",
            ]
        )
    sections.extend(
        [
            "## 反确认偏差记录",
            "主动检索了相反结论、实施限制与无效结果，并据此下调部分候选方向；同时记录未找到可靠来源的维度和实际检索式，避免把缺证据误写成支持结论。",
        ]
    )
    return "\n".join(sections)


def map_text() -> str:
    return "\n".join(
        [
            "# 问题域地图",
            "## 核心现实问题\n企业面对冲击时的韧性差异仍无法由单一数字化指标解释。",
            "## 主要学术分支\n资源基础、动态能力、组织信息处理和制度环境形成相互竞争的解释。",
            "## 政策/实践变化\n政策工具和平台技术改变了企业采用数字技术的成本与组织方式。",
            "## 可用数据\n企业面板、政策试点、专利和公开文本可形成多源证据，但代理变量需要核验。",
            "## 潜在研究切口\n比较信息机制与能力机制在不同制度环境下给出的方向相反预测。",
            "## 初步风险判断\n识别风险来自同期冲击、选择偏差和测量误差，需要预先设计安慰剂与替代指标。",
            "补充说明：地图中的每个切口均能回连证据台账，并明确哪些是来源支持、综合推断和尚待验证。" * 5,
        ]
    )


def literature_text() -> str:
    return "\n".join(
        [
            "# 文献脉络",
            "## 前沿方向\n研究从平均效应转向机制、边界条件和异质性，并开始使用多源数据识别组织过程。",
            "## 核心争论\n一类研究强调信息效率，另一类研究强调能力积累，也有证据认为复杂性会抵消收益。",
            "## 方法谱系\n现有方法包括面板模型、准实验、文本测量和案例比较，各自对应不同识别边界。",
            "证据边界与未决问题需要继续通过判别性设计核验。" * 6,
        ]
    )


def trend_text() -> str:
    return "\n".join(
        [
            "# 趋势判断",
            "## 政策趋势\n支持性政策增加，但适用对象与执行强度差异扩大。",
            "## 实践趋势\n企业从工具部署转向组织流程重构，失败案例也开始增加。",
            "## 学术趋势\n研究关注点由相关关系转向机制识别与边界条件。",
            "## 数据与方法趋势\n多源数据和准实验增加，但代理变量有效性仍是争议重点。",
            "## 阶段判断\n该领域处于由快速上升转向机制深化的阶段，简单平均效应题目吸引力下降。",
            "综合判断需要同时保留支持与限制条件，不能把政策热度直接等同于学术价值。" * 5,
        ]
    )


def gap_text() -> str:
    return "\n".join(
        [
            "# 核心缺口",
            "## 核心缺口 1",
            "### 既有研究已解释\n已有研究确认了数字化与韧性的统计关联，并提出信息和能力两类机制。",
            "### 仍不足\n现有证据尚不能区分竞争性机制，也未说明制度条件何时使效应反转。",
            "### 为何重要\n区分机制会改变理论判断、政策工具和企业投资策略，而不是简单补充变量。",
            "风险说明：关键变量代理质量和同期政策冲击可能削弱判别力度，需要 pilot 提前测试。" * 4,
        ]
    )


def question_scores(total_override: int | None = None) -> dict:
    candidates = []
    for index in range(1, 6):
        scores = {key: 4 for key in gate.QUESTION_SCORE_KEYS}
        decision = "selected" if index == 1 else ("dropped" if index == 5 else "parked")
        candidates.append(
            {
                "candidate_id": f"Q{index}",
                "question": f"候选研究问题 {index}",
                "gap_id": "G1",
                "scores": scores,
                "total": total_override if index == 1 and total_override is not None else 24,
                "decision": decision,
                "rationale": "依据重要性、可行性和证伪能力作出选择。",
                "kill_rule": "无法形成判别证据" if decision == "dropped" else "",
            }
        )
    return {"schema_version": "1.5", "candidates": candidates, "selected_card_ids": ["Q1"]}


def questions_text(include_falsifier: bool = True) -> str:
    candidates = []
    for index in range(1, 6):
        candidates.append(
            f"### 候选问题 {index}\n**候选 ID：** Q{index}\n核心问句：条件变化如何区分机制 A 与机制 B？\n"
            "对应缺口：G1。\n挑战的假设或张力：主流研究默认两种机制等价。"
        )
    falsifier = "**什么结果会推翻它：** 关键结果稳定为零且替代解释得到支持。\n" if include_falsifier else ""
    card = (
        "## 好问题卡 1\n"
        "**卡片 ID：** Q1\n"
        "**暂定题目：** 条件变化与竞争性机制识别\n"
        "**核心研究问题：** 哪种机制更能解释观察到的变化？\n"
        "**为什么值得做：** 答案会改变理论判断和政策工具选择。\n"
        "**挑战了什么默认假设：** 两种机制在经验上不可区分。\n"
        "**竞争性解释：** H1 为机制 A；H2 为机制 B。\n"
        "**关键判别证据或实验：** 比较两种机制给出的方向相反预测。\n"
        f"{falsifier}"
        "**两周内可做的 pilot：** 完成数据可得性、描述统计和方向性检验。\n"
        "**需要的数据/资源：** 公开数据、政策时间点与基础统计软件。\n"
        "**最强评审质疑：** 两种机制可能共同存在，判别证据不够排他。\n"
        "**下一步动作：** 预注册判别标准并根据 pilot 决定继续、修改或停止。\n"
        + "证据说明：事实来自前序台账；新增判断标记为综合推断或尚待验证。" * 10
    )
    score = "## 候选问题评分\n重要性｜可行性｜可证伪性｜证据杠杆｜原创性｜负向结果价值\n"
    return score + "\n".join(candidates) + "\n" + card


def topics_text(source_id: str = "Q1") -> str:
    sections = []
    for index in range(1, 4):
        sections.append(
            f"### 主推选题 {index}\n"
            f"**来源好问题卡：** {source_id}\n"
            "**研究问题：** 哪种竞争性机制更能解释观察结果？\n"
            "**数据/方法路径：** 使用可得数据进行判别性比较。\n"
            "**预期贡献：** 区分现有理论无法区分的机制。\n"
            "**可行性：** 数据与方法均在现有约束内。"
        )
    backups = "\n### 备选选题 1\n降级场景：关键数据不可得。\n### 备选选题 2\n降级场景：pilot 不支持主路径。"
    recommendation = "\n## 推荐判断\n**最推荐推进：** 主推选题 1\n**主要风险：** 判别力度不足。\n**下一步：** 执行 pilot。"
    return "# 3+2 选题推荐\n" + "\n".join(sections) + backups + recommendation + ("\n补充可行性说明。" * 30)


def create_review(root: Path, node: str) -> None:
    hashes = {artifact: sha256(root / artifact) for artifact in gate.REVIEW_BINDINGS[node]}
    verdict = {
        "node": node,
        "workdir": gate.normpath(str(root)),
        "reviewer_kind": "independent",
        "reviewer_model": "test-reviewer",
        "reviewer_agent_id": f"reviewer-{node}",
        "producer_agent_id": "producer-main",
        "verdict": "PASS",
        "p0_open": 0,
        "p0": [],
        "p1": [],
        "round": 1,
        "re_reviewed_dispositions": True,
        "artifact_hashes": hashes,
        "history": [{"round": 1, "p0_found": 0, "p0_open": 0, "p0_ids": []}],
    }
    transcript_rel = f"review/transcripts/{node}_r1.md"
    transcript = "独立审查测试记录\n```json\n" + json.dumps(verdict, ensure_ascii=False, indent=2) + "\n```\n"
    write(root, transcript_rel, transcript)
    stored = dict(verdict)
    stored["transcript_path"] = transcript_rel
    stored["agent_output_sha256"] = sha256(root / transcript_rel)
    write_json(root, f"review/review_{node}.json", stored)


def create_full_fixture(root: Path) -> None:
    write_json(root, "protocol.json", protocol())
    write(root, "01_三问与澄清.md", scope_text())
    write_user_materials(root)
    write(root, "03_五维扫描.md", scan_text())
    write_evidence(root)
    write(root, "04_问题域地图.md", map_text())
    create_review(root, "scan")
    write(root, "05_文献脉络.md", literature_text())
    write(root, "06_趋势判断.md", trend_text())
    write(root, "07_核心缺口.md", gap_text())
    write_json(root, "review/question_scores.json", question_scores())
    write(root, "07A_好问题卡.md", questions_text())
    write(root, "08_选题推荐.md", topics_text())
    create_review(root, "topics")
    manifest = {
        "schema_version": "1.5",
        "workdir": gate.normpath(str(root)),
        "topic": protocol()["topic"],
        "generated_at": "2026-07-12T13:00:00+08:00",
        "artifact_hashes": {artifact: sha256(root / artifact) for artifact in gate.DELIVERY_ARTIFACTS},
    }
    write_json(root, "review/delivery_manifest.json", manifest)


class SelectionGateV152Tests(unittest.TestCase):
    def test_skill_onboarding_declares_creator_process_and_interaction(self) -> None:
        skill_text = (Path(__file__).resolve().parents[1] / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("四川农业大学经济学院张剑", skill_text)
        self.assertIn("微信号：jefeerzhang", skill_text)
        self.assertIn("使用流程", skill_text)
        for marker in ["需求澄清", "材料提交", "五维", "3 个主推选题", "独立审查"]:
            self.assertIn(marker, skill_text)
        self.assertIn("多次交互", skill_text)
        for material_format in ["PDF", "Word", "Markdown", "对话框"]:
            self.assertIn(material_format, skill_text)

    def test_init_project_cli_freezes_scope_and_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            command = [
                sys.executable,
                "-B",
                str(INIT_PROJECT),
                "--workdir",
                tmp,
                "--topic",
                "数字化转型与企业韧性",
                "--why-now",
                "近期政策、数据覆盖范围和企业实践都发生变化，因此旧有结论需要重新接受检验",
                "--research-base",
                "已经具备企业面板数据、政策时间点、理论训练和可以执行的计量分析基础",
                "--deliverable-type",
                "基金申报",
                "--discipline-branch",
                "实证量化",
                "--time-window",
                "2021-2026",
            ]
            child_env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
            first = subprocess.run(
                command, capture_output=True, text=True, encoding="utf-8", env=child_env, check=False
            )
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            gate.check_enter(tmp, "scope")
            status = gate.status_report(tmp)
            self.assertEqual(status["next"], "materials")
            second = subprocess.run(
                command, capture_output=True, text=True, encoding="utf-8", env=child_env, check=False
            )
            self.assertEqual(second.returncode, 1)

    def test_register_material_cli_and_tamper_detection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "uploaded-note.md"
            source.write_text(
                "# 用户笔记\n暂定题目与摘要已经形成，重点比较信息机制和能力机制，并关注制度边界。",
                encoding="utf-8",
            )
            child_env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
            init_command = [
                sys.executable,
                "-B",
                str(INIT_PROJECT),
                "--workdir",
                tmp,
                "--topic",
                "数字化转型如何通过不同机制影响企业韧性",
                "--why-now",
                "近期政策、数据覆盖范围和企业实践均发生变化，旧有结论需要重新接受检验",
                "--research-base",
                "用户已经准备研究笔记，其中包含暂定题目、摘要、机制判断和后续希望核验的问题",
                "--deliverable-type",
                "基金申报",
                "--discipline-branch",
                "实证量化",
                "--time-window",
                "2021-2026",
            ]
            initialized = subprocess.run(
                init_command, capture_output=True, text=True, encoding="utf-8", env=child_env, check=False
            )
            self.assertEqual(initialized.returncode, 0, initialized.stdout + initialized.stderr)
            registered = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(REGISTER_MATERIAL),
                    "--workdir",
                    tmp,
                    "--input",
                    str(source),
                    "--category",
                    "literature-note",
                    "--origin",
                    "user-upload",
                    "--label",
                    "用户研究笔记",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=child_env,
                check=False,
            )
            self.assertEqual(registered.returncode, 0, registered.stdout + registered.stderr)
            manifest = json.loads((root / "review/user_material_manifest.json").read_text(encoding="utf-8"))
            item = manifest["items"][0]
            material_id = item["material_id"]
            analysis = "\n".join(
                [
                    "# 用户材料研判",
                    f"## 材料概览\n{material_id} 是用户提供的研究笔记，包含暂定题目和机制判断。",
                    "## 用户已有研究问题\n用户希望比较信息机制与能力机制对企业韧性的不同影响。",
                    "## 用户已有证据与观点\n材料表达了研究者的初步观点，但尚未提供系统外部证据。",
                    "## 材料之间的冲突\n当前仅一项材料，无跨材料冲突，但概念与变量之间仍需核验。",
                    "## 对后续检索的约束\n外部检索必须围绕用户指定的两类机制、企业韧性和制度边界。",
                    "## 尚待核验\n核验文献基础、竞争性解释、变量可得性和可能的反面结论。",
                    "材料研判严格区分用户原文、摘要归纳和 Agent 推断，不使用外部检索替代用户输入。" * 5,
                ]
            )
            write(root, "02_用户材料研判.md", analysis)
            gate.check_enter(tmp, "materials")

            stored = root / item["stored_path"]
            stored.write_text(stored.read_text(encoding="utf-8") + "\n登记后篡改", encoding="utf-8")
            with self.assertRaises(gate.GateFail):
                gate.check_enter(tmp, "materials")

    def test_register_material_accepts_pdf_word_markdown_and_other_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_json(root, "protocol.json", protocol())
            write(root, "01_三问与澄清.md", scope_text())
            write_json(
                root,
                "review/user_material_manifest.json",
                {"schema_version": "1.5", "workdir": gate.normpath(str(root)), "items": []},
            )
            child_env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
            files = [
                ("paper.pdf", b"%PDF-1.4 test material"),
                ("notes.docx", b"PK test word material"),
                ("idea.md", "# 题目与摘要\n研究构想内容".encode("utf-8")),
                ("archive.custom", b"other readable or extractable material"),
            ]
            for index, (name, content) in enumerate(files):
                source = root / name
                source.write_bytes(content)
                result = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(REGISTER_MATERIAL),
                        "--workdir",
                        tmp,
                        "--input",
                        str(source),
                        "--category",
                        "topic-abstract" if index >= 2 else "literature",
                        "--origin",
                        "user-inline" if name == "idea.md" else "user-upload",
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    env=child_env,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            manifest = json.loads((root / "review/user_material_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["items"]), 4)

    def test_scan_cannot_substitute_agent_search_for_user_materials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_json(root, "protocol.json", protocol())
            write(root, "01_三问与澄清.md", scope_text())
            write_json(
                root,
                "review/user_material_manifest.json",
                {"schema_version": "1.5", "workdir": gate.normpath(str(root)), "items": []},
            )
            write(root, "03_五维扫描.md", scan_text())
            write_evidence(root)
            with self.assertRaises(gate.GateFail):
                gate.check_enter(tmp, "scan")

    def test_full_final_chain_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_full_fixture(root)
            gate.check_enter(str(root), "final")

    def test_scope_rejects_stakes_downgrade(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad = protocol()
            bad["stakes"] = "standard"
            write_json(root, "protocol.json", bad)
            write(root, "01_三问与澄清.md", scope_text())
            with self.assertRaises(gate.GateFail):
                gate.check_enter(str(root), "scope")

    def test_evidence_registry_requires_counter_evidence_per_dimension(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_user_materials(root)
            write_evidence(root, missing_counter_dimension="政策扫描")
            with self.assertRaises(gate.GateFail):
                gate.check_evidence_registry(str(root))

    def test_evidence_registry_rejects_findings_unlinked_to_user_materials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_user_materials(root)
            rows = evidence_rows()
            rows[0]["material_links"] = ["M-agent-invented"]
            write(
                root,
                "review/evidence_registry.jsonl",
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
            )
            with self.assertRaises(gate.GateFail):
                gate.check_evidence_registry(str(root))

    def test_evidence_registry_accepts_independent_agent_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_user_materials(root)
            rows = evidence_rows()
            rows[0]["material_links"] = []
            rows[0]["relation"] = "independent"
            write(
                root,
                "review/evidence_registry.jsonl",
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
            )
            gate.check_evidence_registry(str(root))

    def test_question_scores_reject_false_total(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_json(root, "review/question_scores.json", question_scores(total_override=99))
            with self.assertRaises(gate.GateFail):
                gate.check_question_scores(str(root))

    def test_questions_reject_missing_falsifier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_json(root, "review/question_scores.json", question_scores())
            write(root, "07A_好问题卡.md", questions_text(include_falsifier=False))
            with self.assertRaises(gate.GateFail):
                gate.check_questions(str(root))

    def test_topics_reject_unselected_card_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_json(root, "review/question_scores.json", question_scores())
            write(root, "08_选题推荐.md", topics_text(source_id="Q2"))
            with self.assertRaises(gate.GateFail):
                gate.check_topics(str(root))

    def test_resume_chain_cannot_skip_scan_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_full_fixture(root)
            (root / "review/review_scan.json").unlink()
            with self.assertRaises(gate.GateFail):
                gate.check_enter(str(root), "questions")

    def test_delivery_manifest_rejects_upstream_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_full_fixture(root)
            write(root, "05_文献脉络.md", literature_text() + "\n审后篡改")
            with self.assertRaises(gate.GateFail):
                gate.check_delivery_manifest(str(root))

    def test_build_manifest_cli_creates_valid_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_full_fixture(root)
            (root / "review/delivery_manifest.json").unlink()
            result = subprocess.run(
                [sys.executable, "-B", str(BUILD_MANIFEST), "--workdir", str(root)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            gate.check_delivery_manifest(str(root))

    def test_status_reports_first_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = gate.status_report(tmp)
            self.assertFalse(result["complete"])
            self.assertEqual(result["next"], "scope")


if __name__ == "__main__":
    unittest.main()
