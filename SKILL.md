---
name: research-topic-selection
description: |
  AI 辅助科研选题系统 v1.5.2：从用户已有材料出发，经过外部检索和“好问题”压力测试，
  形成 3+2 可申报课题。集成刚性推进闸门（scripts/selection_gate.py）、
  独立审查分离（references/review-nodes.md）、五维扫描清单（references/scan-checklist.md）、
  强制用户材料交互（references/user-material-intake.md）、冻结协议与结构化证据血缘（references/artifact-schemas.md）、
  好问题闸门（references/good-question-gate.md）和学科分支适配
  （references/discipline-branches.md）。
  适用经济/管理/社科为主的论文选题与课题申报；自然/工程类走"工程应用"分支。
  触发词：科研选题、论文选题、课题申报选题、AI辅助选题、研究缺口、文献脉络、
  学术趋势、课题申报、社科选题、经管选题、研究问题优化、选题可证伪性。
---

# Research Topic Selection（科研/课题申报选题系统 v1.5.2）

AI 辅助的科研选题流程，**以研究者自身输入为唯一出发点**——不随机生成题目，而是把模糊兴趣收敛成经过竞争性解释、证伪条件和小规模 pilot 检验的 3+2 选题。

本技能 v1.5.2 使用**用户材料参与**、**冻结协议**、**结构化证据台账**、**全链路刚性闸门**、**好问题压力测试**与**独立审查分离**：
关键产物完成后必须过 `scripts/selection_gate.py`；scan / topics 两道 critical 闸强制独立审查，
处置闭环经原审查者复核，断点续写重新核验全部上游产物。结构化产物规范见 `references/artifact-schemas.md`。

---

## 启动说明（新任务首次响应必须发送）

每次新选题任务首次调用本技能时，先向用户说明以下内容。可以调整排版，但不得省略创建者、流程或多轮交互提示：

```markdown
本科研选题技能由四川农业大学经济学院张剑创建，微信号：jefeerzhang。

使用流程：
1. 明确研究兴趣、当前节点、研究基础和交付目标；
2. 请您提交已有材料，并由 Agent 完整读取和研判；
3. 围绕用户材料及 Agent 独立发现开展政策、文献、实践、数据和申报窗口扫描；
4. 梳理问题域、文献脉络、趋势和核心缺口；
5. 生成候选研究问题并进行可行性、可证伪性和评审风险测试；
6. 形成 3 个主推选题和 2 个备选选题；
7. 经过独立审查后交付最终推荐。

本技能会进行多次交互，包括需求澄清、材料提交、材料研判确认和选题判断确认。请提前准备相关材料，
例如 PDF、Word、Markdown 文档，也可以直接在对话框输入或粘贴题目、摘要、笔记、摘录和研究构想。
```

发送启动说明后，可以在同一条回复中继续提出“三问启动”。仅在新任务首次响应时发送，不在同一任务的后续轮次重复。

## 一、三问启动与协议冻结（Phase 0-1，BLOCKING）

用三个问题把模糊需求逼出结构化，**不要直接生成题目**：

1. **你在关心什么问题？**（现象/矛盾/政策/现象皆可，不求学术化）
2. **为什么是现在？**（新政策、新数据、新现象、个人节点）
3. **你已有什么材料或基础？**（数据、田野、理论训练、合作方）

若用户拒绝回答或输入过薄，停在 Phase 0，不硬编。确认学科取向（实证量化/质性案例/理论建构/工程应用，见 `references/discipline-branches.md`）、
利害关系档（课程论文/学位论文/期刊/基金申报）、时间范围、中英文偏好。
然后运行 `scripts/init_project.py`，一次性生成 `00_任务元信息.md`、`01_三问与澄清.md`、
`protocol.json`、空用户材料 manifest、空证据台账和空候选评分表。初始化脚本拒绝覆盖已有协议。

```bash
python scripts/init_project.py --workdir <wd> --topic "..." --why-now "..." \
  --research-base "已有数据、理论训练或合作条件" --deliverable-type "基金申报" --discipline-branch "实证量化" \
  --time-window "2021-2026" --language zh-CN --language en-US
python scripts/selection_gate.py --workdir <wd> --enter scope
```

研究边界发生实质变化时创建新工作目录，不在已审链条上无痕改写 `protocol.json`。

## 二、用户材料交互与研判（Phase 1.5，BLOCKING）

scope 通过后必须暂停，加载 `references/user-material-intake.md` 并请用户通过任意一种形式提供至少一项材料：

1. 相关文献；
2. 文献笔记、摘录或研究备忘；
3. 已有研究题目与摘要。

接受形式包括但不限于：

- PDF 文件；
- Word 文档（`.doc` / `.docx`）；
- Markdown 文档（`.md`）；
- 用户直接在对话框手输或粘贴的题目、摘要、笔记、摘录和研究构想；
- 其他能够读取或提取内容的文档形式。

**没有用户材料时不得进入外部检索。** 如果用户没有文献或笔记，至少要求其提供一个暂定题目和摘要；
对话中的文字应原样保存成 Markdown 后登记。使用 `scripts/register_material.py` 把材料复制到
`user_materials/` 并写入 `review/user_material_manifest.json`：

```bash
python scripts/register_material.py --workdir <wd> --input <file> \
  --category literature --origin user-upload --label "用户说明"
```

完整读取材料后生成 `02_用户材料研判.md`，逐项引用材料 ID，区分材料原文、用户观点和 Agent 推断，
说明已有研究问题、证据基础、材料冲突、对后续检索的约束和尚待核验事项。向用户展示简短研判摘要并等待确认；
用户纠正后更新研判文件，再过材料闸门：

```bash
python scripts/selection_gate.py --workdir <wd> --enter materials
```

材料登记不等于完成研判；manifest 中至少一项材料、所有文件 hash 有效且 `02_用户材料研判.md` 结构完整，闸门才 PASS。

## 三、五维扫描（Phase 2，BLOCKING）

材料闸门通过后，优先围绕 `02_用户材料研判.md` 中的尚待核验事项和检索约束开展五维扫描，
加载 `references/scan-checklist.md` 严格按清单执行：

用户材料是研究起点和约束来源，但不是后续证据的唯一来源。Agent 可以独立检索、发现并使用用户材料之外的
文献、政策、案例、数据和新方向；这些独立发现应在证据台账中使用空 `material_links` 和
`relation=independent`，并说明它为何与当前选题相关。

- **政策扫描**：国家/地方政策方向、试点、窗口期。
- **学术文献扫描**：主要分支、经典问题、近 3 年趋势、核心争论。
- **现实实践扫描**：案例、新兴现象、组织模式。
- **数据/材料扫描**：公开数据集、可得性分级（可得/需申请/不可得）。
- **发表/申报窗口扫描**：目标期刊、基金指南、截止时间。

**硬性约束**：凡涉时效性必须实际调用检索（本地 anysearch / web_search / web_google 等联网检索工具），
禁止编造近期性；每维至少 1 条反面/竞争性证据（反确认偏差，清单 §六）。**每个存在 `verified` 证据的维度，必须至少有一条 `counter` 或 `mixed` 证据；`unavailable` 条目必须登记至少两个检索式；`verified` 条目的 `source_url` 必须是 `http(s)` URL。**
除 Markdown 外，把决定选题判断的证据逐条写入 `review/evidence_registry.jsonl`；字段规范见
`references/artifact-schemas.md`。找不到可靠来源时使用 `status=unavailable` 并登记至少两个检索式，禁止编造链接。
落盘：`03_五维扫描.md`（含末尾"反确认偏差记录"段）和证据台账。

> 生成 03 后过 `python scripts/selection_gate.py --workdir <wd> --enter scan`
> （数字入口 `--enter 2`；校验冻结协议、用户材料及研判、03 五维结构、反确认偏差与证据台账）。

## 四、问题域地图（Phase 3）

把扫描结果织成一张地图，落到 6 点：
1. 核心现实问题
2. 主要学术分支
3. 政策/实践变化
4. 可用数据和材料
5. 潜在研究切口
6. 初步风险判断

落盘：`04_问题域地图.md`。地图须自洽（核心问题↔分支↔数据↔切口），过度发散须收敛。

> **scan 独立审查（critical，independent）**：过闸后调用独立审查者审 03+04，
> 输出 verdict JSON（模板与执行方式见 `references/review-nodes.md`），`p0_open=0` 才放行进入 Phase 5。
> 主线程应先用 `scripts/selection_gate.py --hash-template scan` 生成 artifact hash 模板并提供给审查者，
> 以解决 read-only 子代理无法执行 shell 计算 hash 的问题。
> 前过 `python scripts/selection_gate.py --workdir <wd> --enter scan-review`
> （数字入口 `--enter 4`；校验 scope+03+04、scan review、hash、transcript 与 P0 闭环）。

## 五、中等深度文献脉络（Phase 4）

围绕地图中的切口，做中等深度而非穷尽的文献脉络：前沿方向、核心争论、方法谱系。
落盘：`05_文献脉络.md`。

> 生成 05 后过 `python scripts/selection_gate.py --workdir <wd> --enter literature`
> （数字入口 `--enter 5`；重跑 scan-review 上游链，并校验 05 的前沿方向、核心争论和方法谱系）。

## 六、总体趋势判断（Phase 5）

四维度 + 阶段判断：
- 政策趋势 / 实践趋势 / 学术趋势 / 数据与方法趋势
- 阶段判断（起步/上升/成熟/转型/衰退）

落盘：`06_趋势判断.md`。

## 七、核心缺口（Phase 6，BLOCKING）

只取 1–3 个核心缺口，每个含三段：既有研究已解释 / 仍不足 / 为何重要。带风险标注。
落盘：`07_核心缺口.md`。

## 八、好问题闸门（Phase 6.5，BLOCKING）

加载 `references/good-question-gate.md`，把 1–3 个核心缺口转化为可检验的研究问题：

1. 使用假设挑战、竞争性解释、边界条件、条件变化等透镜生成 5–10 个候选问题。
2. 按重要性、可行性、可证伪性、证据杠杆、原创性、负向结果价值评分。
3. 淘汰只有“没人做过”、没有利益相关者、无法提出推翻条件或资源明显不可行的问题。
4. 为排名最高的 1–3 个问题生成完整“好问题卡”。

每张卡必须包含：核心研究问题、研究意义、默认假设、至少两个竞争性解释、关键判别证据、
推翻条件、两周 pilot、资源需求、最强评审质疑和下一步动作。

同步填写 `review/question_scores.json`：5-10 个候选的六维整数评分、总分、决策、理由和淘汰规则；
入选 ID 必须与好问题卡一致。**评分规范：六维均为 1-5 整数；`decision` 只能取 `selected` / `parked` / `dropped`，其中 `dropped` 必须填写 `kill_rule`；`selected_card_ids` 必须与 `decision=selected` 的候选完全一致。**格式见
`references/artifact-schemas.md`。

落盘：`07A_好问题卡.md` 和 `review/question_scores.json`。

> 生成 07A 后过 `python scripts/selection_gate.py --workdir <wd> --enter questions`
> （数字入口 `--enter 6`；校验 07 核心缺口、5–10 个候选问题、六维评分及 1–3 张完整好问题卡）。

## 九、3+2 课题选项（Phase 7，BLOCKING）

- **主推选题 3 个**：每个注明“来源好问题卡”，并含研究问题、数据/方法路径（按学科分支具体化）、预期贡献、可行性。
- **备选选题 2 个**：明确各自降级场景。
- **推荐判断**：最推荐推进 / 理由 / 主要风险 / 下一步需补充。

落盘：`08_选题推荐.md`。

> **topics 独立审查（critical，independent）**：调用独立审查者审 07+07A+08，verdict `p0_open=0` 才放行 final。
> 执行方式与 scan 独立审查相同：主线程先用 `scripts/selection_gate.py --hash-template topics` 生成 hash 模板并提供给审查者。
> 前过 `python scripts/selection_gate.py --workdir <wd> --enter topics`
> （数字入口 `--enter 7`；重跑 questions 上游链，校验 07+07A+08、结构化评分、topics review 与 hash 闭环）。

## 十、交付（final，BLOCKING）

topics 独立审查通过后运行：

```bash
python scripts/build_manifest.py --workdir <wd>
python scripts/selection_gate.py --workdir <wd> --enter final
```

final 会重新核验 scope→materials→scan→scan-review→literature→questions→topics 全链路，并检查
`review/delivery_manifest.json` 是否仍绑定当前协议、用户材料 manifest、材料研判、证据台账、03-08 产物和审查 verdict。

交付 `08_选题推荐.md` 给用户，并附：
- 研究主题与范围
- 关键缺口与最推荐选题
- 主要风险与下一步需补充
- 打包目录位置

---

## 十一、决策追问（Grill）机制

借鉴 `grill-me` 思路，在需要用户做判断的关键节点，采用**一次只追问一个决策、每个问题附带推荐答案**的方式，
沿决策树分支逐步推进，直到达成 shared understanding 后再进入下一阶段。

### 11.1 适用场景

- **Phase 0-1 scope 确认**：学科取向、利害关系档、时间窗口、语言偏好、硬约束等维度，逐项确认。
  主线程根据用户三问及已有材料给出推荐选项，用户确认或纠正后再进入下一项。
  "为什么是现在"由 Phase 2 五维扫描自然回答，不单独作为前置追问。
- **Phase 1.5 材料研判确认**：展示研判摘要后，逐条确认"用户已有研究问题""材料冲突""检索约束"等关键判断；
  用户有纠正时，先更新 `02_用户材料研判.md` 再过 materials 闸。
- **Phase 6.5 好问题压力测试**：对排名最高的 1-3 个候选问题，按 6 个关键字段逐项追问：
  核心研究问题、为什么值得做、默认假设与竞争性解释、关键判别证据与推翻条件、两周 pilot 与下一步动作、资源需求与最强评审质疑。
- **Phase 7 最终选题确认**：对最推荐选题，追问关键决策（样本范围、理论框架、方法路径、风险承受能力），
  确认后再落盘 `08_选题推荐.md`。
- **P0 处置闭环**：独立审查提出 P0 后，逐一追问每个 P0 的修正方案，回送原审查者复核。

### 11.2 追问原则

1. **一次只问一个决策**：不把学科取向、利害关系档、时间窗口等问题同时抛出。
2. **推荐答案与提示清单结合**：对学科取向、时间窗口等可推断项，给出"我建议选 X，理由是..."；对硬约束等必须用户主动声明的项，用提示清单引导用户逐项输入，不预设"暂无"。
3. **纠正即更新**：用户纠正后，立即重写对应落盘文件并重新过相关闸门，不在下游沿用旧判断。
4. **确认即留痕**：在 `01_三问与澄清.md`、研判文件、好问题卡或选题推荐中，体现用户已确认的关键决策。
5. **不无限追问**：每个节点的追问有明确边界（如 scope 的 5 个维度、好问题卡的 6 个关键字段），达成边界后停止。

---

## 十二、刚性闸门与审查机制（v1.5.2 核心）

### 12.1 闸门

`python scripts/selection_gate.py --workdir <wd> --enter {scope,materials,scan,scan-review,literature,questions,topics,final}`

数字入口：`1=scope`，`1.5=materials`，`2=scan`，`4=scan-review`，`5=literature`，`6=questions`，`7=topics`。

| enter | 校验内容 | 退出码 |
|-------|----------|--------|
| scope / 1 | 冻结协议字段、风险档位映射、三问与澄清 | 0 PASS / 1 FAIL |
| materials / 1.5 | 至少一项用户材料 + 文件大小/hash + 02 材料深度研判 + 材料 ID 全覆盖 | 同上 |
| scan / 2 | scope + materials + 03 五维 + 结构化证据台账 + 各维反面证据/显式 unavailable | 同上 |
| scan-review / 4 | 03+04 结构完整 + scan review verdict=PASS + artifact_hashes/transcript/P0 闭环均匹配 | 同上 |
| literature / 5 | 重跑全部 scan 链 + scan review + 05 文献脉络 | 同上 |
| questions / 6 | 重跑上游链 + 06 趋势 + 07 缺口 + 结构化评分 + 好问题卡 ID 闭环 | 同上 |
| topics / 7 | 07+07A+08 结构完整 + topics review verdict=PASS + artifact_hashes/transcript/P0 闭环均匹配 | 同上 |
| final | 重跑全部上游链 + delivery manifest 全产物 hash 血缘 | 同上 |
| —  | 单节点审查 round > 3 | 3（超界，升级人类） |

生成审查 hash 模板可用：

`python scripts/selection_gate.py --workdir <wd> --hash-template scan`

或：

`python scripts/selection_gate.py --workdir <wd> --hash-template topics`

使用 `python scripts/selection_gate.py --workdir <wd> --status` 诊断最早阻塞点；status 只报告，不绕过闸门。

### 12.2 审查分离（强制）

- scan / topics 两道 critical 闸强制 **independent** 审查：审查者上下文不含产出过程，只读落盘产物。
- `reviewer_agent_id ≠ producer_agent_id`（闸门字段级校验）。
- 不依赖特定外部 runner；本地用 subagent 机制或另起会话承担。
- 其余阶段（三问/澄清/趋势/缺口）主线程自检，不强制独立审查。

### 12.3 处置闭环（禁自审）

审查报 P0 → 执行者写 `review/dispositions_<node>.json` → **回送原审查者复核**
（`reviewer_decision: accepted|rejected`），rejected 须重修正再审。回环 ≤ 3 轮。

### 12.4 降级车道（降级有痕，不静默）

| id | 触发 | 处理方式 | 是否降 high |
|----|------|----------|--------------|
| user-material-missing | 用户尚未提供任何材料 | 停在 Phase 1.5 请求上传；不得自行检索替代 | 否 |
| scan-fallback | 某维无可靠来源 | 标"暂无可靠来源，风险标注"，不伪造 | 否 |
| data-unavailable | 数据不可得 | 选题可行性标红，转备选或改切口 | 否 |
| explicit-opt-out | 用户主动放弃独立审查 | 记 justification，下游知情 | 否 |
| resume-jump | 用户"从某步继续" | **必过前置闸**，上游 BLOCKING 不可静默绕过 | 否 |

### 12.5 断点续写

用户"从第 X 步继续/从推荐开始"等：先运行 `selection_gate --status`，再对目标阶段执行
`selection_gate --enter <对应>`。后段闸门会重新执行全部上游校验；上游产物缺失或 hash 过期则 FAIL。

### 12.6 信任边界（如实声明）

闸门校验字段、hash 绑定、transcript hash 与 P0 处置闭环，**不提供密码学身份保证**。
蓄意伪造一整套自洽 transcript+verdict+匹配 hash 仍可能（v1.5.2 级残留）。
彻底闭合需受控 runner 外部登记审查行为，超出本技能范围。

---

## 输出模板（供 08_选题推荐.md）

```markdown
# AI 辅助选题结果

## 1. 三问与澄清
- 关心的问题：
- 现在关心的原因：
- 材料或基础：

## 2. 初步问题域假设

## 2A. 用户材料研判
- 材料概览：
- 用户已有研究问题：
- 用户已有证据与观点：
- 材料之间的冲突：
- 对后续检索的约束：
- 尚待核验：

## 3. 五维扫描摘要
### 政策扫描
### 学术文献扫描
### 现实实践扫描
### 数据/材料扫描
### 发表/申报窗口扫描

## 4. 问题域地图
1. 核心现实问题：
2. 主要学术分支：
3. 政策/实践变化：
4. 可用数据和材料：
5. 潜在研究切口：
6. 初步风险判断：

## 5. 中等深度文献脉络

## 6. 总体趋势判断
- 政策趋势：
- 实践趋势：
- 学术趋势：
- 数据与方法趋势：
- 阶段判断：

## 7. 核心缺口

## 7A. 好问题压力测试
### 候选问题评分
| 候选 | 重要性 | 可行性 | 可证伪性 | 证据杠杆 | 原创性 | 负向结果价值 | 处理 |
|---|---:|---:|---:|---:|---:|---:|---|

### 候选问题 1
**候选 ID：** Q1
### 候选问题 2
### 候选问题 3
### 候选问题 4
### 候选问题 5

### 好问题卡 1
**卡片 ID：** Q1
### 好问题卡 2
### 好问题卡 3

## 8. 3+2 课题选项
### 主推选题 1
**来源好问题卡：** Q1
**研究问题：**
**数据/方法路径：**
**预期贡献：**
**可行性：**
### 主推选题 2
### 主推选题 3
### 备选选题 1
### 备选选题 2

## 9. 推荐判断
- 最推荐推进：
- 推荐理由：
- 主要风险：
- 下一步需要补充：
```

---

## Interaction Rules

- If the user is still designing the workflow itself, ask one decision question at a time.
- If the user wants actual topic selection, execute the workflow directly.
- If the input is too thin, ask the three-question start instead of generating topics immediately.
- After scope passes, stop and explicitly request user materials. Do not continue to web retrieval in the same turn unless the user has already supplied materials and confirmed the material brief.
- If no files are available, require at least a user-authored working title and abstract. There is no silent opt-out from the materials gate.
- If the user provides an article, policy, document, or URL as source material, read/analyze it first and preserve useful knowledge according to the knowledge-wiki rules.
- If current policy, literature, journal, or grant information is needed, use web/search tools; do not fabricate recency.
- **检索工具统一**：执行五维扫描时，优先调用本地 `anysearch` skill 或 `web_search` / `web_fetch` 工具；对每一维的关键结论，必须保留至少一个可追溯的来源 URL 或显式 `unavailable` 记录。
- Do not include “research draft grill me” as part of the default workflow. Only pressure-test drafts if the user explicitly asks.
- 若用户只要求优化一个已有题目，可从 Phase 6.5 开始，但必须先提供或补齐相当于 07 的缺口与证据基础。
- **v1.5.2 要求**：新任务首次响应先发送创建者、流程和多轮交互说明；再冻结 protocol；scope 后强制暂停获取用户材料并完成 02 研判；关键检索结论进入 evidence_registry；候选评分进入 question_scores；
  BLOCKING 产物完成后必须先过 `selection_gate.py`；questions 不得跳过；scan/topics 必须独立审查；final 必须有新鲜 delivery manifest；
  禁止主线程自审自盖合格章；降级必须留痕，断点续写不得静默绕过上游闸。
