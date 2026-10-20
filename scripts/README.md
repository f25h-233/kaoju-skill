# 脚本

**全部纯 Python 标准库，零第三方依赖，Windows 上直接能跑。**

所有脚本都可以删。删了流程照样走，只是校验降级成人工自检——**但报告里必须写一行「降级模式：未做机器校验」**。

---

## 一条命令跑完全部

```bash
python check_all.py --workspace <工作目录> --depth shallow|medium|deep
```

退出码 `0` = 总判定通过；`1` = 有步骤失败，产物不可交付。

顺序固定，**先账本**——结构不对，后面几步都是空转。

| 步骤 | 脚本 | 查什么 |
|---|---|---|
| 1 | `ledger_check.py` | 账本结构与自洽性（11 条断言） |
| 2 | （内建） | `sources.csv` → `_check/sources.json` 转换 |
| 3 | （内建） | 由 `sources.csv` 生成最小 `registry.md` |
| 4 | `verify_citations.py` | 报告引用完整性 |
| 5 | `source_evaluator.py` | 来源权威分与多样性 |
| 6 | `emit_run_summary.py` | 生成 `run-summary.json` |

---

## 单独跑（调试用）

```bash
python ledger_check.py --workspace <工作目录> --depth medium
python verify_citations.py <报告.md> _check/sources.json --output _check/citations.json
python source_evaluator.py _check/sources.json --output _check/evaluation.json
python emit_run_summary.py --draft <报告.md> --registry _check/registry.md \
  --output-type full --stakes medium --orchestration lead+subagents \
  --output _check/run-summary.json
```

---

## `ledger_check.py` 的 11 条断言

| # | 断言 | 违规 |
|---|---|---|
| 1 | 两张表列名齐全（按档位） | 中/深 exit 1；浅档仅警告 |
| 2 | `claims.sources` 的每个 sid 都在源表里 | exit 1 |
| 3 | 无重复 sid、无同一 URL 登记两次 | exit 1 |
| 4 | `sources/NN_*.md` 编号与 sid 一一对应 | 越界 exit 1；缺文件警告 |
| 5 | **重算四条件，须与声明的 `status` 一致** | exit 1 |
| 6 | **`confidence=high` 必须 `primary_source=Y`** | exit 1 |
| 7 | `source_caveat≠-` 时 `confidence` ≤ medium | exit 1 |
| 8 | **有分量的异议存在时，必须判 `contested`/`contradicted`** | exit 1 |
| 9 | 薄源不计入四条件 | 计入则不通过 |
| 10 | **账本 → 大纲 → 报告三层覆盖** | exit 1 |
| 11 | `sources` 列编号合法且无重复 | exit 1 |

**第 5、8、10 条是这个 skill 的全部价值所在。** 没有它们，账本就是一张没人看的表格。

---

## 三处必须知道的集成细节

1. **`verify_citations.py` 零引用时会真空 PASS。** 它的判据是「每条引用都有对应条目」——报告里一个 `[NN]` 都没有时全部真空成立。`check_all.py` 先断言行内引用数 > 0，否则直接判 FAIL。

2. **`emit_run_summary.py` 从 `registry.md` 数源。** 我们没有这个文件，不生成的话 `source_count` 会恒为 0、被误读成「没找到源」。`check_all.py` 会由 `sources.csv` 生成一个最小的。

3. **`source_evaluator.py` 的 `--as-of` 只吃 `YYYY-MM-DD`。** 账本里的 `as_of` 可能是 `2025-Q3`，直接传会让它 exit 1。`check_all.py` 只在能解析成严格日期时才传。

---

## 能力边界（别高估）

- `verify_citations.py` 的「检查引用」**不联网**。它比对的是「你引的 URL 在不在你自己登记的源池里」，**不能证明你真的读过它**，更不能证明它说了你声称的话。它能抓悬空引用和格式问题，抓不了内容造假。
- `ledger_check.py` 查的是**结构自洽**，不是**结论正确**。一条结论可能四条件全满足、账本完全自洽，但仍然是错的。
- 脚本通过 ≠ 结论可靠。**结论可靠性靠跨来源三角验证和红队，不靠脚本。**

---

## 移植说明

`verify_citations.py` / `source_evaluator.py` / `emit_run_summary.py` 来自
[staruhub/ClaudeSkills](https://github.com/staruhub/ClaudeSkills) 的 `Geek-skills-deep-research`（MIT）。

本仓库的改动：

| 脚本 | 改动 |
|---|---|
| `emit_run_summary.py` | 无 |
| `verify_citations.py` | 加 stdout UTF-8 兜底（Windows 重定向时不炸） |
| `source_evaluator.py` | ① 输出文件加 `encoding="utf-8"`；② **增补中文能源/油气行业域名分档**（原表对油气零覆盖，会把中石油、GIIGNL、EIA 当未知域名丢掉） |

`ledger_check.py` 与 `check_all.py` 为本仓库新写。
`ledger_check.py` 的断言思路借鉴了 [Socialpranker/deepdive](https://github.com/Socialpranker/deepdive)（MIT）的 `validate_phases.py`，用中文重写并适配两张表结构，未搬运其代码。

完整声明见仓库根 `THIRD_PARTY_NOTICES.md`。
