# 文献提取工具规范（Phase 1.7）

> **加载时机**：Phase 1.5 材料交互与研判之后、Phase 2 五维扫描之前。
> **目标**：把用户提供的 PDF/Word/Markdown 批量转为 Markdown 全文，供后续扫描和问题域地图直接引用。

## 一、为什么先提取全文

现有的 `user_material_manifest.json` 只记录文件元信息和 SHA-256，不保存全文。Agent 在做 Phase 1.5 研判和 Phase 2 学术文献扫描时，只能凭标题和摘要推断，容易失真。

MinerU 提取的 Markdown 全文包含：

- 完整段落和章节结构；
- 表格内容（识别为 Markdown 表格）；
- 公式（识别为 LaTeX）；
- 图表标题（图片本身无法 OCR）；
- 参考文献列表。

提取结果是后续五维扫描和问题域地图的"事实输入"，必须先于研判和扫描完成。

## 二、工具选择与优先级

`scripts/extract_papers.py` 按以下优先级自动选择：

| 文件类型 | 第一选择 | 第二选择 | 第三选择 |
|---|---|---|---|
| `.pdf` | `mineru-open-api extract`（表格/公式识别） | PyMuPDF 纯文本提取 | 标记 `failed` |
| `.docx` | `python-docx` 段落提取 | — | 标记 `failed` |
| `.md` / `.markdown` / `.txt` | 直接复制 | — | 标记 `failed` |
| 其他 | 标记 `unsupported` | — | — |

## 三、MinerU CLI 用法

```bash
mineru-open-api extract "path/to/paper.pdf" -o "path/to/output/"
```

常用参数（参考 MinerU 官方文档）：

- `-o`：输出目录，脚本会自动在该目录下生成 `<源文件名>.md`；
- `-l` 或 `--language`：指定语言（`ch` / `en`），脚本默认走 MinerU 默认值；
- `--enable-table`：是否识别表格（默认开）；
- `--enable-formula`：是否识别公式（默认开）。

确认 MinerU 已安装：

```bash
mineru-open-api version
```

应在 PATH 中可用，或位于 `%AppData%\Roaming\npm\mineru-open-api.cmd`。

## 四、PyMuPDF 回退

当 MinerU 失败或不可用时，脚本自动调用 PyMuPDF（`fitz`）。PyMuPDF 只提取纯文本，不识别表格和公式，但能保证流程不阻塞。

PyMuPDF 的提取格式：

```markdown
## 第 1 页

正文段落...

## 第 2 页

正文段落...
```

如果 PDF 是纯图片扫描版，PyMuPDF 也无能为力，脚本会标记该 PDF 为 `failed` 并跳过。此时该论文不能进入 Phase 1.7 的闸门，需要用户手动提供 OCR 后的文本或重新上传。

## 五、运行方式

```bash
python scripts/extract_papers.py --workdir <项目目录>
```

可选参数：

- `--input-dir <目录>`：默认扫描 `<项目目录>/user_materials/` 顶层；
- `--timeout <秒>`：单篇 MinerU 超时（默认 300 秒）。

脚本是幂等的：已经成功提取的源文件（按 SHA-256 判断）不会重复提取。

## 六、产物

提取结果存放于 `<项目目录>/user_materials/extracted/`：

```
user_materials/extracted/
├── paper1.md
├── paper2.md
├── paper3.md
└── extraction_manifest.json   # 提取清单与状态
```

`extraction_manifest.json` 字段：

```json
{
  "schema_version": "1.6",
  "workdir": "C:/abs/path/to/project",
  "items": [
    {
      "source": "paper1.pdf",
      "source_sha256": "...",
      "size_bytes": 123456,
      "extractor": "mineru-open-api",
      "output": "user_materials/extracted/paper1.md",
      "status": "success",
      "message": "",
      "extracted_at": "2026-07-18T14:30:00+08:00"
    }
  ],
  "generated_at": "..."
}
```

`status` 取值：

- `success`：提取成功；
- `failed`：所有提取器都失败（见 `message`）；
- `unsupported`：文件类型不在支持范围内。

## 七、Phase 1.7 闸门校验

`selection_gate.py --enter papers` 校验：

1. `user_materials/extracted/extraction_manifest.json` 存在；
2. 至少有一项 `status=success`（默认阈值：≥1 篇论文成功提取）；
3. `user_material_manifest.json` 中至少有 1 项 `category=literature` 的材料已被成功提取（在 manifest 中可找到对应的 `source_sha256`）；
4. 没有 `status=failed` 的 `category=literature` 材料被静默跳过（即失败的文献必须在研判中说明，不能假装已经提取）。

## 八、提取失败的处理建议

- **网络问题导致 MinerU 失败**：脚本自动回退 PyMuPDF，无需干预；
- **扫描版 PDF**：PyMuPDF 也会失败，需要用户：
  - 手动 OCR（如 Tesseract / 百度 OCR / 微信图片转文字）；
  - 或提供已 OCR 的 PDF；
  - 或改提供 Markdown / Word 文本版；
- **加密 PDF**：MinerU 和 PyMuPDF 都会失败，需要用户提供解密版；
- **MinerU 整体不可用**：脚本自动回退 PyMuPDF，只要 PyMuPDF 提取出非空文本即可。

任何 `failed` 项都需要在 Phase 1.5 研判文件中明确标注，不能默默丢弃。
