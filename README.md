<sub>🌐 <b>中文</b></sub>

<div align="center">

# research-topic-selection

> *「不是让 AI 给你想一个题目，而是把你的模糊兴趣变成经得起审查的研究决策。」*

[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-research--topic--selection-blueviolet)](SKILL.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**一个面向经管与社科研究者的可审计选题流程：从材料到最终选题，每一步都留下证据、反证和可证伪条件。**

[效果示例](#效果示例) · [快速开始](#快速开始) · [触发方式](#触发方式) · [能交付什么](#能交付什么) · [它和同类有什么不同](#它和同类有什么不同) · [安全边界](#安全边界) · [文件结构](#文件结构)

</div>

---

## 它解决什么问题

你读了很多文献，笔记也做了不少，但一到要写“研究问题”就卡住。更常见的是：AI 确实能给你生成几十个题目，可你根本判断不了哪个靠谱，最后只能凭感觉选一个，写到一半才发现数据拿不到、问题已经被别人做过了，或者根本没法证伪。

这个 Skill 不是题目生成器。它换了一种思路：

- **材料优先**：不接受空泛提问，必须先把你的文献、数据、研究笔记、研究基础纳入流程；
- **证据强制**：每个判断都要留下支持你观点和反对你观点的证据；
- **阶段冻结**：研究范围一旦确定就不能偷偷漂移，防止越写越散；
- **独立审查**：关键节点（扫描、选题）必须由另一个“审查人格”重新过一遍；
- **可退出**：不是每个方向都值得做。它会告诉你该继续、修改、暂缓还是淘汰。

结果不是一个花哨的标题，而是一套可以写进开题报告、导师汇报或项目申请书里的研究决策材料。

---

## v1.6 新增能力

相比 v1.5.2，这一版做了三件事：

1. **Phase 0 基本情况摸底**：在三问之前，先了解研究者的学科背景、当前阶段、历史沿革、研究基础、交付目标、时间约束六个维度。追问有据可依。
2. **Phase 1.7 文献批量提取**：用户提供的 PDF 用 MinerU 批量转为 Markdown 全文（含表格和公式），Word 用 python-docx，Markdown 直接复制。MinerU 失败自动回退 PyMuPDF。提取清单写入 `user_materials/extracted/extraction_manifest.json`。
3. **Phase 3.5 文献矩阵**：基于提取的全文生成"研究问题 × 方法"二维矩阵，空白格标注"待验证"并喂给 Phase 6 核心缺口判断。归一化规则匹配待后续 LLM 增强。

完整流程：

```
摸底 → 三问 → 协议冻结 → 材料交互 → 文献提取 → 五维扫描 → 问题域地图 → 文献矩阵 → 文献脉络 → 趋势判断 → 核心缺口 → 好问题 → 3+2 选题 → 交付
```

新增闸门：

- `papers`（Phase 1.7）：至少 1 篇文献成功提取，`category=literature` 材料都有对应成功记录。
- `scan-review` 中新增矩阵校验：`03A_文献矩阵.md` 存在且 ≥300 字符、含 Markdown 表格、含空白格说明；`review/matrix.json` 结构完整；`empty_cells` 至少 1 项 `candidate_gap=true`。

## 效果示例

输入：你对“平台劳动者如何应对算法管理”感兴趣，手头有一些文献笔记、问卷设计经验和公开招聘数据。

启动后，它会自动创建如下工作目录结构：

```
workspace/
├── 00_protocol.md            # 冻结的研究协议：题目、时间窗、学科分支、交付物
├── 01_materials_manifest.md  # 已录入材料清单与血缘
├── 02_evidence_ledger.md     # 五维扫描的证据台账
├── 03_scan_report.md         # 政策/文献/实践/数据/发表窗口五维扫描报告
├── 04_domain_map.md          # 研究问题域地图
├── 05_question_cards.md      # 候选问题卡，每个都带反证和推翻条件
├── 06_3plus2_selection.md   # 3 个主推方向 + 2 个备选方向
├── 07A_good_question_gate.md # 好问题闸门的逐项 verdict
├── 08_recommendation.md      # 最终选题推荐与两周 pilot 计划
└── 09_delivery_manifest.md   # 交付物清单
```

其中每个候选问题都会强制回答：

| 检查项 | 示例 |
|---|---|
| 研究价值 | 为什么算法管理对职业稳定性值得现在研究 |
| 竞争性解释 | 收入下降、技能贬值、身份认同是否也能解释同一现象 |
| 关键证据 | 平台规则变化、劳动者访谈、公开招聘数据 |
| 推翻条件 | 如果算法评分与离职率无显著相关，则该方向应被淘汰 |
| 两周 pilot | 先用招聘数据做描述性统计，再决定是否需要深入访谈 |
| 当前决策 | 继续 / 修改 / 暂缓 / 淘汰 |

这不是模板填空，而是每个字段都必须基于你提供的材料或经过扫描后形成的证据。

---

## 快速开始

### 推荐安装

```bash
npx skills add jefeerzhang/research-topic-selection
```

### 备用安装

```bash
git clone https://github.com/jefeerzhang/research-topic-selection.git
# 复制到你的 Agent skills 目录，例如：
# cp -r research-topic-selection ~/.codex/skills/
```

装完对 Agent 说：

```text
我想用 research-topic-selection 来确定一个研究选题。我的主题是：
“平台劳动者的算法管理与职业稳定性”。

我手头的材料包括：
- 已有平台劳动文献笔记（Markdown，约 1.5 万字）
- 一份问卷设计经验（之前做过的非随机抽样）
- 公开招聘数据（某平台 2022-2024 年的岗位描述）

请用标准研究构想作为交付物，学科分支为实证量化，时间窗为 2022-2026，语言为中文。
```

Agent 会调用 `init_project.py` 创建研究目录，并引导你进入 `scope` 闸门和后续流程。

---

## 触发方式

你可以直接对 Agent 说：

- “帮我看看这个选题值不值得做。”
- “我想从兴趣收敛成一个可执行的研究问题。”
- “我有材料，想做一个研究选题审计。”
- “用这个 skill 评估一下我的研究问题。”
- “我想确定硕士/博士论文题目。”
- “帮我生成一个研究构想，用于项目申请。”
- “我想让 AI 严格审查一下我的选题。”

以下情况它不会替你直接生成题目，而是先要求材料：

- “给我几个新颖的选题”——没有材料，不启动；
- “帮我 brainstorm 一下”——仅提供灵感，不进入审计流程；
- 拒绝提供反证或推翻条件——审计无法完成，会暂停并说明原因。

---

## 能交付什么

| 能力 | 交付物 | 典型使用场景 |
|---|---|---|
| 研究协议冻结 | `00_protocol.md` | 防止研究范围在后续写作中漂移 |
| 材料与证据管理 | `01_materials_manifest.md` + `02_evidence_ledger.md` | 导师/评审追问时快速溯源 |
| 五维扫描 | `03_scan_report.md` | 政策、文献、实践、数据、发表窗口一次性盘点 |
| 问题域收敛 | `04_domain_map.md` | 把模糊兴趣拆成可比较的问题空间 |
| 候选问题审查 | `05_question_cards.md` | 每个候选都带反证和推翻条件 |
| 3+2 决策 | `06_3plus2_selection.md` | 主推 3 个方向 + 备选 2 个方向 |
| 好问题闸门 | `07A_good_question_gate.md` | 独立审查 verdict |
| 最终推荐 | `08_recommendation.md` | 可写进开题报告或项目书 |
| 交付清单 | `09_delivery_manifest.md` | 明确后续工作包 |

---

## 它和同类有什么不同

| 维度 | 普通 AI 选题助手 | 这个 Skill |
|---|---|---|
| 输入 | 你描述兴趣，AI 直接生成题目 | 必须提供材料，AI 基于材料审计 |
| 输出 | 多个标题 + 摘要 | 一套带证据、反证、推翻条件的决策材料 |
| 过程 | 单轮对话，越问越散 | 多阶段、有冻结协议、有阶段闸门 |
| 反确认偏差 | 很少要求 | 强制要求每个 verified 维度都有 mixed/counter 证据 |
| 可证伪性 | 通常不讨论 | 每个候选问题必须给出推翻条件 |
| 退出机制 | 不停推荐 | 明确建议继续、修改、暂缓或淘汰 |
| 适用范围 | 找灵感 | 从灵感到可执行选题 |

---

## 安全边界

- **不伪造来源**：没有材料或检索失败时，不会编造文献或数据，会标记为 `unavailable` 并暂停。
- **不替代学术判断**：最终选题仍需研究者本人确认，Skill 提供的是审计和决策支持。
- **不跳过关键阶段**：如果 `scope` 闸门未通过，不会进入扫描；如果 `scan` 审查未通过，不会生成问题卡。
- **不碰隐私数据**：所有材料由用户自行管理，Skill 只按用户提供的本地路径读取，不上传。
- **不保证发表**：仅提高选题过程的透明度，不承诺任何学术成果。

---

## 文件结构

```
research-topic-selection/
├── SKILL.md                          # 主流程：Phase 0 → final
├── README.md                         # 本文件
├── LICENSE                           # MIT 许可证
├── .skill_id                         # 本 skill 唯一标识
├── scripts/                          # 可执行脚本
│   ├── init_project.py              # 初始化研究项目与冻结协议
│   ├── register_material.py         # 注册并校验用户材料
│   ├── selection_gate.py            # 阶段闸门（scope / scan / topics / final）
│   └── build_manifest.py            # 构建交付物清单
├── references/                       # 流程规范与检查清单
│   ├── artifact-schemas.md          # 产物结构定义
│   ├── user-material-intake.md      # 材料录入规范
│   ├── scan-checklist.md            # 五维扫描检查清单
│   ├── good-question-gate.md        # 好问题闸门标准
│   ├── review-nodes.md              # 独立审查节点规则
│   └── discipline-branches.md       # 学科分支约定
├── evals/                            # 自动化测试
│   └── test_selection_gate.py       # 闸门测试（17 项全部通过）
└── examples/                         # 真实案例与测试 prompt
    ├── case-platform-labor.md
    ├── case-lightweight.md
    └── test-prompts.json
```

---

## 验证与测试

```bash
cd research-topic-selection
pytest evals -q
```

预期输出：

```
17 passed in ~2s
```

完整端到端测试：用 [examples/test-prompts.json](examples/test-prompts.json) 中的任一 prompt，从初始化到 `scope` 闸门通过，应能在本地工作目录生成 `00_protocol.md`。

---

## 致谢

方法论与流程设计受以下项目和框架启发：

- [Luban](https://github.com/jefeerzhang/luban) — 鲁班 Skill 打磨框架，提供了本 README 的 house-style 模板和 birth-checklist。
- [CARS](https://github.com/Eureka39/CARS) — 苏格拉底式研究选题审查流程。
- 科学社会学中的“反确认偏差”与“可证伪性”原则。

创建者：@jefeerzhang

---

## License

[MIT](LICENSE)

---

<div align="center">

*从模糊兴趣到可审计选题：先给材料，再给判断。*

</div>
