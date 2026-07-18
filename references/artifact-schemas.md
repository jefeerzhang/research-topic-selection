# 结构化产物规范

> 加载时机：初始化项目、填写五维证据台账、完成候选评分或准备最终交付时。

## 一、冻结协议 `protocol.json`

使用 `scripts/init_project.py` 生成，不要手工改变 `frozen_at` 或风险档位。研究边界确需改变时，创建新工作目录；不要在旧审查链上无痕改题。

```json
{
  "schema_version": "1.5",
  "topic": "研究者关心的问题",
  "deliverable_type": "基金申报",
  "stakes": "high",
  "discipline_branch": "实证量化",
  "time_window": "2021-2026",
  "languages": ["zh-CN", "en-US"],
  "constraints": ["可使用公开数据", "三个月内完成"],
  "scan_dimensions": [
    "政策扫描",
    "学术文献扫描",
    "现实实践扫描",
    "数据/材料扫描",
    "发表/申报窗口扫描"
  ],
  "researcher_profile": {
    "discipline": "劳动经济学（应用经济学二级学科），长期关注平台劳动与数字经济",
    "stage": "博士二年级，距离毕业还有两年半，下学期需要开题",
    "history": "硕士做的是平台劳动的收入研究，现在想转向职业稳定性。半途放弃过"算法歧视"方向，因为数据不可得",
    "base": "已掌握 Stata 和 Python，有某外卖平台 2022-2024 年的招聘数据 8000 条，没有骑手访谈数据",
    "deliverable": "博士学位论文开题报告（high）",
    "time": "2027 年 6 月前完成开题，每周可投入 30 小时"
  },
  "frozen_at": "2026-07-12T12:00:00+08:00"
}
```

`deliverable_type -> stakes` 为固定映射：课程论文/研究构想为 `standard`；学位论文/期刊论文/基金申报为 `high`。

`researcher_profile` 六个字段（学科背景、当前阶段、历史沿革、研究基础、交付目标、时间约束）由 Phase 0 摸底获取（见 `references/intake-protocol.md`），影响 Phase 1 追问方式、Phase 1.5 材料引导、Phase 2 扫描目标、Phase 6.5 pilot 可行性判断。所有字段可缺省，但 `discipline`、`stage`、`deliverable` 至少填写一项。

## 二、用户材料 manifest `review/user_material_manifest.json`

使用 `scripts/register_material.py` 生成和更新，不手工复制材料后伪造登记项。

```json
{
  "schema_version": "1.5",
  "workdir": "C:/abs/path/to/project",
  "items": [
    {
      "material_id": "M-a1b2c3d4e5f6",
      "category": "literature",
      "origin": "user-upload",
      "label": "用户认为最重要的基础文献",
      "original_name": "paper.pdf",
      "stored_path": "user_materials/M-a1b2c3d4e5f6-paper.pdf",
      "sha256": "<64位sha256>",
      "size_bytes": 123456,
      "registered_at": "2026-07-12T12:30:00+08:00"
    }
  ]
}
```

`category` 只能是：`literature`（文献）、`literature-note`（文献笔记）、`topic-abstract`（题目与摘要）。
至少登记一项。材料文件必须位于工作目录的 `user_materials/`，后续闸门重新计算大小和 SHA-256。

## 三、证据台账 `review/evidence_registry.jsonl`

每行一个 JSON object。`evidence_id` 全局唯一，`dimension` 必须是五维之一。

可靠来源：

```json
{"evidence_id":"E-POLICY-001","dimension":"政策扫描","status":"verified","claim":"政策文件明确支持该试点方向","material_links":["M-a1b2c3d4e5f6"],"relation":"confirm","source_title":"政策文件标题","source_url":"https://example.org/policy","publication_date":"2025-06-01","accessed_at":"2026-07-12","stance":"support"}
```

反面或竞争性证据：

```json
{"evidence_id":"E-POLICY-002","dimension":"政策扫描","status":"verified","claim":"配套实施细则限制了适用范围","material_links":["M-a1b2c3d4e5f6"],"relation":"challenge","source_title":"实施细则","source_url":"https://example.org/rule","publication_date":"2025-09-01","accessed_at":"2026-07-12","stance":"counter"}
```

确实没有可靠来源时使用显式降级，不得写假链接：

```json
{"evidence_id":"E-VENUE-001","dimension":"发表/申报窗口扫描","status":"unavailable","claim":"尚未找到下一年度正式指南","material_links":["M-a1b2c3d4e5f6"],"relation":"extend","reason":"官方渠道尚未发布","attempted_queries":["官方站点+年度+指南","主管部门+申报通知"]}
```

每个存在 verified 证据的维度至少有一条 `counter` 或 `mixed`。台账不是参考文献列表；`claim` 必须说明该来源支持或反驳了什么判断。
若外部发现直接回应用户材料，`material_links` 关联相应材料 ID，`relation` 使用 `confirm`、`challenge` 或 `extend`。
若是 Agent 独立检索发现的新证据，允许 `material_links: []`，此时 `relation` 必须为 `independent`。

## 四、候选评分 `review/question_scores.json`

```json
{
  "schema_version": "1.5",
  "candidates": [
    {
      "candidate_id": "Q1",
      "question": "核心问句",
      "gap_id": "G1",
      "scores": {
        "重要性": 5,
        "可行性": 4,
        "可证伪性": 5,
        "证据杠杆": 4,
        "原创性": 4,
        "负向结果价值": 3
      },
      "total": 25,
      "decision": "selected",
      "rationale": "保留或淘汰理由",
      "kill_rule": ""
    }
  ],
  "selected_card_ids": ["Q1"]
}
```

要求：5-10 个候选；评分只能为 1-5 整数；`total` 必须等于六项之和；`selected_card_ids` 必须与 `decision=selected` 完全一致；`dropped` 项必须填写 `kill_rule`。

`07A_好问题卡.md` 中每个候选注明“候选 ID”，每张卡注明“卡片 ID”；`08_选题推荐.md` 的“来源好问题卡”填写同一 ID。

## 四点五、文献矩阵 `review/matrix.json`（v1.6 新增）

由 Phase 3.5 生成，二维矩阵的结构化视图。

```json
{
  "schema_version": "1.5",
  "y_axis": ["算法评分与离职率", "平台规则透明度", "收入波动机制", "职业安全感"],
  "x_axis": ["面板计量", "案例研究", "田野调查", "文本分析"],
  "cells": [
    {"y": "算法评分与离职率", "x": "面板计量", "papers": ["M-aa11b2c3d4e5", "M-bb22c3d4e5f6"]},
    {"y": "平台规则透明度", "x": "案例研究", "papers": ["M-cc33d4e5f6a7"]}
  ],
  "empty_cells": [
    {"y": "职业安全感", "x": "面板计量", "candidate_gap": true, "note": "无定量研究或归一化失败"}
  ]
}
```

要求：

- `y_axis`、`x_axis`、`cells`、`empty_cells` 必须均为数组；
- `cells[].papers` 是 `material_id` 列表，关联 `review/user_material_manifest.json` 中的材料；
- `empty_cells[].candidate_gap` 是布尔值，标识该空白格是否作为核心缺口候选进入 Phase 6；
- `empty_cells[].note` 说明空白格的解释（"无定量研究"/"检索不全"/"归一化失败"等）。

矩阵闸门校验（`scan-review` 闸门）：

- `03A_文献矩阵.md` 存在且 ≥300 字符，含 Markdown 表格（`| ... | ... |`）；
- 包含"空白格说明"段；
- `review/matrix.json` 是合法 JSON，结构完整；
- `empty_cells` 中至少标注 `candidate_gap: true` 的项，否则视为"无候选缺口"，需在 `04_问题域地图.md` 中说明。

## 五、交付 manifest

topics 独立审查通过后运行：

```bash
python scripts/build_manifest.py --workdir <wd>
python scripts/selection_gate.py --workdir <wd> --enter final
```

`build_manifest.py` 原子写入 `review/delivery_manifest.json`，绑定协议、用户材料 manifest、材料研判、
五维证据、03-08 产物及两份审查 verdict。任何被绑定文件改变后，旧 manifest 自动失效，必须重走受影响的闸门和审查。
