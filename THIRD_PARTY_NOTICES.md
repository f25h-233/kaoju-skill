# 第三方声明

本仓库的代码与思想来自三个开源项目。逐项说明如下。

---

## §1 Socialpranker/deepdive

- **来源**：https://github.com/Socialpranker/deepdive
- **许可证**：MIT License, Copyright (c) 2026 ivanterescheenko-ai
- **吸收方式**：**仅思想，未搬运代码**（`scripts/ledger_check.py` 借鉴了其思路，但由本仓库用中文重写）

### 吸收的思想

| 内容 | 落在本仓库哪里 |
|---|---|
| 四条件三角验证（源数 / 类型数 / 原始出处数 / 发现路径数） | `references/ledger.md`、`scripts/ledger_check.py` |
| 8 状态枚举、3 值置信度 | `references/ledger.md` |
| 没有一手源则置信度封顶 medium | `references/ledger.md`、断言 6 |
| 异议保护（少数派不许被多数决压掉） | `references/ledger.md`、断言 8 |
| `root` / `discovery_path` 元数据设计 | `references/ledger.md`、`references/source-scoring.md` |
| 薄源不计入三角验证 | `references/ledger.md`、断言 9 |
| 状态窗口每轮重写 + 体积上限 | `references/handoff.md` |
| 红队按深度设闸、明确不用 1–5 分打分 | `references/adversarial.md` |
| 熔断四条（补漏波次上限 / 饱和度 / 无进展 / 首轮不计） | `SKILL.md` |
| `outline.md` 作为检索与成文的接合点 | `references/workflow.md`、断言 10 |

### 代码层面

`scripts/ledger_check.py` 的断言设计**借鉴**了 `deepdive` 仓库 `scripts/validate_phases.py` 中
`check_ledger_columns`、`check_source_perimeter`、`parse_outline` 三个函数的思路。
本仓库的实现是**用中文重写并适配「两张表」结构的新代码**，未复制其源码。

### 未吸收

`phases.yaml`、`runner/`、wiki 子系统、`fetch_source.py`、俄文文档体系、其目录约定（`sources/`、`.verify/`、`memo.md` 等）。

---

## §2 staruhub/ClaudeSkills

- **来源**：https://github.com/staruhub/ClaudeSkills （具体为 `skills/Geek-skills-deep-research/`）
- **许可证**：MIT License, Copyright (c) 2025-2026 staruhub
- **吸收方式**：**复制了代码**（三个脚本），依 MIT 要求附全文

### 本仓库复制并修改的文件

| 本仓库文件 | 原文件 | 改动 |
|---|---|---|
| `scripts/emit_run_summary.py` | `scripts/emit_run_summary.py` | **无改动** |
| `scripts/verify_citations.py` | `scripts/verify_citations.py` | 在 `main()` 开头加 stdout UTF-8 兜底（Windows 重定向下防止中文 JSON 编码崩溃） |
| `scripts/source_evaluator.py` | `scripts/source_evaluator.py` | ① 输出文件写入加 `encoding="utf-8"`（原代码缺此参数，中文标题在 Windows 上会乱码或报错）；② **增补中文能源/油气行业域名分档表**（`TIER_1/2/3` 各追加若干域名） |

### 概念吸收

产物形态分档（brief / full）、Degraded mode（脚本可选、缺失时降级）、跨会话交接协议、按论点类型的证据阶梯。

### 明确未继承的两处缺陷

1. **`registry.md` 被四个文件反复要求，但它的格式在原仓库中从未被定义过。** 本仓库改为明确定义的 `sources.csv`（列定义见 `references/ledger.md`），并由 `check_all.py` 生成最小 `registry.md` 供下游脚本消费。
2. **原 `verify_citations.py` 全部 325 行不含任何网络请求**，其「检查引用」实际是「检查这个 URL 在不在你自己登记的源池里」，不能验证引文内容。本仓库在 `scripts/README.md` 的能力边界一节如实标注了这一点。

### MIT 许可证全文

```
MIT License

Copyright (c) 2025-2026 staruhub

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## §3 SeanEllyJames/deep-research-skill —— 仅思想，未取一字

- **来源**：https://github.com/SeanEllyJames/deep-research-skill
- **许可证**：MIT License, Copyright (c) 2026 SeanEllyJames
- **吸收方式**：**仅吸收思想，未复制任何原文**

### 为什么只取思想

该仓库的 `LICENSE` 文件包含以下自述：

> This work is derived from and builds upon grapeot/context-infrastructure
> (https://github.com/grapeot/context-infrastructure), which is licensed under
> the MIT License, Copyright (c) grapeot.

**经核实，该自述与上游的实际授权状态不符。** 核实方式与结论：

- 遍历 `grapeot/context-infrastructure` 仓库的完整文件树（HEAD），**未发现任何 LICENSE、COPYING 或 NOTICE 文件**
- GitHub API 对该仓库返回的 `license` 字段为 `null`
- 无许可证即默认「保留所有权利」（all rights reserved）
- 该仓库的 GitHub 许可证识别结果为 `NOASSERTION`（无法识别）而非 `MIT`——因为上述自述改动了标准 MIT 正文，破坏了模式匹配

**核实日期**：2026-10-20

此外，该仓库 README 中「Deep-vs-Wide framing … are additions by the copyright holder above」的说法亦不准确：
该框架的正源是 `grapeot` 仓库 README 所链接的公开文章（yage.ai《为什么AI只会说正确的废话，以及怎么把它逼出舒适区》）。

**基于以上，本仓库不复制其任何原文，仅吸收不受版权保护的思想并用自己的话重写。**

### 吸收的思想

| 思想 | 落在本仓库哪里 |
|---|---|
| 立案阶段先拷问问题本身（为什么要问 / 隐藏假设 / 有没有「显而易见但其实不对」的标准答案） | `references/workflow.md` P0、`SKILL.md` |
| 「好答案」的标准：核心论点应能在业内引发争论，而非集体点头 | `references/workflow.md`、`references/report-shape.md` |
| **章节标题检测器**：标题若可直接用作搜索关键词，则结构是信息分类而非论证链 | `references/report-shape.md` |
| 反例检索的具体词（`criticism` / `failure` / `problem` / `why not`） | `references/adversarial.md`、`SKILL.md` 速查表 |
| 「删掉所有表格和 bullet 后，剩余段落能否独立成文」 | `references/report-shape.md` |

### 本仓库的一处反向修正

该 skill **明文四处禁止保存中间结果**（「最终只交付一个汇总报告，中间结果不保存」等）。
本仓库**采取相反的做法**：要求全面落盘、每阶段先写盘再继续。
理由见 `SKILL.md` 第 0 节第三条——本机自动压缩关闭，不落盘的中间结果在长调研中会直接丢失。

### 致谢

思想致谢：SeanEllyJames，及其所声明的上游 grapeot/context-infrastructure。

---

## §4 本机工具链

`fetch.py` / `fetch_js.py` 为使用者自有工具，**不在本仓库分发**。本 skill 仅调用、不打包。

---

## §5 本仓库许可

MIT License, Copyright (c) 2026 f25h-233 —— 见 `LICENSE`。

MIT 与 MIT 完全兼容，故本仓库可在保留上述声明的前提下以 MIT 分发。
