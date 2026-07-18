# 选题审查节点规则（v1.5.2）

> **加载时机**：执行 scan / topics 任一审查节点前。
> **审查分离原则**：选题技能只有两道 critical 闸（scan、topics），均强制 independent 审查；
> 其余阶段（三问/澄清/趋势/缺口）由主线程自检，不强制独立审查。

## 一、审查者与档位

| node   | 最低档位     | 说明 |
|--------|--------------|------|
| scan   | independent  | critical：五维扫描是否覆盖、是否确认偏差、问题域地图是否成立 |
| topics | independent  | critical：缺口是否真实、好问题卡是否成立、3+2 推荐是否可执、判断是否自洽 |

- **审查者永远 ≠ 产出者**：independent 档指在本地 GenericAgent 下用**独立上下文 / 独立模型调用**执行审查，
  其上下文不含产出过程（不读主线程中间草稿，只读落盘产物）。
- `reviewer_agent_id` / `producer_agent_id` 必须如实填写且不相等（selection_gate 字段级校验）。
- `node`、`workdir`、`reviewer_kind`、`p0_open`、`round`、`artifact_hashes`、
  `agent_output_sha256` 均为硬性字段；缺失即闸门 FAIL。
- 不依赖 codex-verify 等外部受控 runner；本地可用 subagent 机制或另起会话承担 independent 审查。

## 二、审查者输出（verdict JSON 模板）

审查者在报告末尾必须附一个 fenced JSON 块，主线程**原样**保存两份：
- 完整原始输出 → `review/transcripts/<node>_r<round>.md`
- fenced JSON 块 → `review/review_<node>.json`，仅允许主线程落盘时追加一个字段
  `agent_output_sha256`（= transcript 文件的 sha256）。

若保存 transcript 的位置不是默认路径，`review/review_<node>.json` 可额外追加
`transcript_path` 字段。除此之外，不得改写审查者 fenced JSON 的原始字段。

```json
{
  "node": "scan",
  "workdir": "/abs/path/to/workdir",
  "reviewer_kind": "independent",
  "reviewer_model": "模型标识",
  "reviewer_agent_id": "reviewer-session-xxx",
  "producer_agent_id": "main-thread-yyy",
  "verdict": "PASS",
  "p0_open": 0,
  "p0": [],
  "p1": [{"id": "P1-1", "issue": "..."}],
  "round": 1,
  "re_reviewed_dispositions": true,
  "artifact_hashes": {
    "03_五维扫描.md": "<sha256>",
    "04_问题域地图.md": "<sha256>"
  },
  "history": [
    {"round": 1, "p0_found": 0, "p0_open": 0, "p0_ids": []}
  ]
}
```

要点：
- `node` 必须等于当前节点名；`workdir` 必须等于当前工作目录绝对路径；跨目录复制旧 verdict 会被拒绝。
- `reviewer_kind` 对 scan/topics 必须为 `independent`；`reviewer_agent_id` 必须不同于 `producer_agent_id`。
- `verdict` 必须为 `PASS`，`p0_open` 必须为 0，且当前 `p0` 列表必须为空。
- `artifact_hashes` 由**审查者本人**对它实际读到的产物计算（shell `sha256sum` 或等价），
  逐文件填写——声明"我审的就是这一版"。selection_gate 会与当前文件实算值比对，
  防旧 verdict 重放、防审后再改产物。
- **若平台 read-only subagent 无法执行 shell 命令，应采用模式 A**：主线程先用 `--hash-template` 生成 hash 模板并传给 subagent，subagent 确认读到的产物与模板 hash 一致后直接引用。不一致时须拒绝引用并报告。
- 各节点绑定文件以 `scripts/selection_gate.py` 的 `REVIEW_BINDINGS` 为准。scan 同时绑定冻结协议、三问、
  用户材料 manifest、材料研判、五维扫描、问题域地图和结构化证据台账；topics 同时绑定协议、文献脉络、趋势、缺口、好问题卡、
  3+2 推荐、证据台账和候选评分。任何被绑定文件改变后旧 verdict 失效。
- `history` 每轮如实记录；`p0_found > 0` 的轮必须列 `p0_ids`。
- `agent_output_sha256` 必须等于完整 transcript 文件的 sha256。selection_gate 还会读取 transcript
  末尾 fenced JSON，与 `review/review_<node>.json` 的原始字段逐项比对。

## 三、执行模式与 hash 计算（v1.5.2 修订）

### 3.1 审查分离的本质

`independent` 审查的核心是**上下文隔离**：审查者不能读取主线程的中间思考、草稿或迭代过程，只能基于落盘产物做判断。它**不必然要求**审查 subagent 处于 read-only 或不能写文件。

### 3.2 hash 计算的两种可行模式

在当前 Hana/OpenHanako 等平台中，read-only subagent 通常**无法执行 shell 命令**计算文件 SHA-256，导致 verdict 中的 `artifact_hashes` 无法被 `selection_gate.py` 接受。推荐以下两种模式：

**模式 A：主线程预计算 hash 模板（推荐，改动最小）**
1. 主线程在送审前运行：
   ```bash
   python scripts/selection_gate.py --workdir <wd> --hash-template scan
   python scripts/selection_gate.py --workdir <wd> --hash-template topics
   ```
2. 将生成的 hash 模板作为提示词的一部分传给独立审查 subagent；
3. subagent 读取落盘产物后，确认模板中的 hash 与自己读到的内容一致，并**直接引用**这些 hash 填写 `artifact_hashes`；
4. 若 subagent 发现主线程在生成模板后、送审前修改了产物，应在审查报告中声明并拒绝引用旧 hash。

**模式 B：subagent 在 write 模式下执行 hash 计算**
1. 独立审查 subagent 仍然只读落盘产物，但允许其执行 shell/Python 命令计算 SHA-256；
2. subagent 自行计算 `artifact_hashes` 并写入 `review/review_<node>.json` 和 `review/transcripts/<node>_r<round>.md`；
3. 只要 subagent 的上下文不包含主线程产出过程，此模式不破坏审查分离原则。

### 3.3 对 read-only subagent 的限制说明

如果当前平台仅支持 read-only subagent 且禁止其执行任何命令，则**必须采用模式 A**。主线程不得以“审查者自己算”为由跳过 hash 模板传递，否则 `selection_gate.py` 会因 `artifact_hashes` 缺失或 PLACEHOLDER 而 FAIL。

## 四、处置闭环（禁自审的核心）

审查报 P0 后：
1. 执行者逐条处置，写 `review/dispositions_<node>.json`：
   ```json
   {"findings": [{"id": "P0-1", "status": "已修正", "evidence": "修正说明/diff/新值",
                  "reviewer_decision": null}]}
   ```
   status ∈ 已修正（附修正内容）/ 反驳成立（附证据，如检索记录、原文截图）/ 不适用（附理由）。
2. **回送原审查者复核**：审查者逐条裁决 `reviewer_decision: accepted | rejected`，
   写回 `review/dispositions_<node>.json`。rejected 的 P0 必须重新修正并再审。
3. 回环有界：单节点 round ≤ 3（selection_gate 超界 exit 3，升级人类裁决，不许自动重试）。
4. 只要 `history` 中任一轮 `p0_found > 0`，最终 verdict 必须设置
   `re_reviewed_dispositions: true`，且 `review/dispositions_<node>.json` 中每条历史 P0
   都必须有合法 `status`、非空 `evidence`、`reviewer_decision: accepted`。原审查者重签 verdict 时还必须把
   `review/dispositions_<node>.json` 的终版 SHA-256 加入 `artifact_hashes`，防止复核后无痕改写台账。

## 五、审查关注点清单（选题专用）

**scan 节点：**
- 协议是否真实冻结：交付类型、stakes、学科分支、时间窗口和约束是否与用户输入一致。
- 用户材料是否真正参与：抽查 manifest 中的原始材料与 `02_用户材料研判.md`，确认研究问题、已有观点、
  材料冲突和检索约束来自实际内容，而不是 Agent 只列文件名后自行发挥。
- 外部检索是否透明：允许使用用户材料之外的新证据与新方向；回应用户材料的发现应标记关系，独立发现应标记
  `independent`。不得悄悄替换用户研究对象，但有充分证据时可以明确建议修正或重构原题。
- 五维是否齐全（政策/文献/实践/数据/窗口），无维度仅写"暂无"。
- 是否确认偏差：扫描是否只找支持预设方向的证据，忽略反面/竞争性解释。
- 文献是否虚构/过期：引用政策/文献须标出来源与时效，禁止编造近期性。
- 台账是否忠实：抽查 `evidence_registry.jsonl` 的 claim、URL、日期、stance 与 03 正文是否对应；
  `unavailable` 是否确实记录了检索尝试，而不是逃避反面证据。
- 问题域地图是否成立：核心问题↔学术分支↔数据↔切口是否自洽、是否过度发散。

**topics 节点：**
- 缺口是否真实：1–3 个核心缺口须有"既有研究已解释 / 仍不足 / 为何重要"三段支撑。
- 问题是否成立：好问题卡须明确研究意义、默认假设、至少两个竞争性解释、关键判别证据和推翻条件。
- 评分是否诚实：`question_scores.json` 的整数评分、total、decision、kill_rule 是否与卡片和淘汰理由一致。
- pilot 是否有决策价值：两周 pilot 应能支持继续、修改或停止，而不只是“再查文献”。
- 映射是否真实：三个主推选题必须注明来源好问题卡；不得把同一卡片的文字改写伪装成三个独立问题。
- 3+2 是否可执：每个选题的数据/方法路径是否具体、是否与用户基础匹配。
- 判断是否自洽：优先/可以/谨慎/暂缓的分级理由是否一致，最推荐项是否有压倒性依据。
- 去 AI 味：中文表述是否落入模板腔（参考本地 writing_principles_sop）。

## 六、hash 模板辅助（与模式 A 配套）

主线程必须在送审前生成当前 artifact hash 模板，并**作为提示词内容传递给审查 subagent**：

```bash
python scripts/selection_gate.py --workdir <wd> --hash-template scan
python scripts/selection_gate.py --workdir <wd> --hash-template topics
```

在 subagent 提示词中应明确说明：
- 这是主线程预计算的 hash 模板；
- 审查者需确认自己读到的产物与模板 hash 一致；
- 若不一致，应在审查报告中声明并拒绝引用旧 hash；
- 若一致，可直接将模板中的 hash 填入 verdict JSON 的 `artifact_hashes` 字段。

审查者仍应以自己实际读取到的文件为准判断内容质量；hash 模板仅用于解决 read-only 子代理无法执行 shell 命令计算 hash 的问题，不降低审查独立性。

## 七、信任边界（如实声明）

本机制校验字段、hash 绑定、transcript hash 与 P0 处置闭环，**不提供密码学身份保证**。
蓄意伪造一整套自洽 transcript + verdict + 匹配 hash 仍是可能的（v1.5.2 级残留）。
彻底闭合需受控 runner 外部登记审查行为，超出本技能范围。
