> ⚠️ **This document is machine-translated from the Chinese original (`README.md`) and has not been reviewed by a human.**
> **本文档为机器翻译**，未经人工校对。若与 `README.md` 有出入，**以中文版为准**。
> Translation source: `README.md` @ commit `a7b23b4`, generated 2026-10-20.

---

# Kaoju — Evidence-Ledger Deep Research skill

> Turning "I think" into "here's the ledger."

A Claude Code skill that digs a question into a Chinese-language report that is **ledgered, auditable, and willing to commit to a judgement**.

**中文版**: [README.md](README.md)

---

## The problem it solves

Most "AI deep research" produces **information arrangement**, not **judgement**:

| | Arranging information (default) | Judging (this skill) |
|---|---|---|
| Method | Search many sources → group by topic → produce a checklist | Read a few primary sources closely → surface the tension → argue to a judgement |
| Output | "A did X, B did Y" | "A and B started from opposite premises and converged — why?" |
| Reads like | A tidy wiki entry | A memo written by someone who actually thought |

Arranging information is easier to write, looks more complete, and fools you more easily. This skill is a guardrail that pulls the output the other way.

---

## Core: two tables + four conditions

A research run produces two kinds of things — **sources** and **claims**. This skill records them in two separate tables:

- `sources.csv`: one row per source (URL, type, credibility, original root, discovery path…)
- `claims.csv`: one row per conclusion (which sources it cites, confidence, any dissent…)

Every claim must then pass **four-condition triangulation**:

> **≥3 independent sources, ≥2 source types, ≥2 original roots, ≥2 independent discovery paths**

All four must hold. **Crucially, `status` is not filled in by the model — it is computed from the source table by a script.** If what you wrote disagrees with the source table, validation fails outright.

Two hard rules:

1. **With no primary source, confidence may not exceed `medium`.** Three secondary retellings of the same original fact look like independent confirmation; they are one voice repeated three times.
2. **Contradictions are not settled by majority vote.** When a weighty objection exists, you may not call the claim established just because the supporting side has more sources.

---

## Install

```bash
git clone https://github.com/f25h-233/kaoju-skill ~/.claude/skills/kaoju
cp ~/.claude/skills/kaoju/agents/research-fetcher.md ~/.claude/agents/
```

The second step is not optional — Claude Code only loads agents from `~/.claude/agents/`.

---

## Usage

Just ask in plain language:

```
帮我深挖一下 LNG 接收站的投资逻辑
考据一下 Postgres 逻辑复制和 CDC 工具的取舍
写一份调研报告：这个技术选型值不值得
```

Trigger words: 考据, 深挖, 深度调研, 调研报告, 挖到底, 刨根问底, 值不值得.

**Not for**: fact lookups answerable in one search; summarising a single document the user already provided; pure brainstorming; short answers of a paragraph or less.

### Machine-translated `description`

The skill's frontmatter `description` is Chinese (it drives triggering). For English readers, a translation:

> Evidence-ledger deep research — dig a question into a Chinese-language report that has a ledger, is auditable, and dares to commit to a judgement. Core is two tables (a `sources.csv` source table and a `claims.csv` claim ledger) plus four-condition triangulation: every conclusion must state how many independent sources, how many source types, how many original roots, and how many independent discovery paths back it; with no primary source, confidence may not exceed medium; minority dissent may not be overruled by majority vote. Use when the user asks to dig deep, find out clearly, make a judgement, or write a report, and the answer requires synthesising across sources, involves trade-offs, and should be reusable as a document. Trigger words: 考据, 深挖, 深度调研, 帮我查清楚, 调研报告, 技术选型, 竞品分析, 政策分析, 可行性分析, 值不值得. Not for: fact lookups answerable in one search, summarising a single document the user supplied, brainstorming that needs no evidence, or short answers of a paragraph or less.

---

## Validation scripts

```bash
python scripts/check_all.py --workspace <workspace> --depth medium
```

One command runs ledger validation, citation validation, source quality, and summary generation. Exit code `0` = pass, `1` = some step failed.

**All scripts are pure Python standard library, zero third-party dependencies, and run directly on Windows.**

**The scripts are optional**: delete `scripts/` and the workflow still runs, with validation degraded to a manual checklist — but the report must then carry the line "降级模式：未做机器校验" (degraded mode: no machine validation).

### What the scripts can and cannot do

| Can | Cannot |
|---|---|
| Catch a self-contradicting ledger (declared `triangulated` but the source table says otherwise) | Judge whether a conclusion is correct |
| Catch confidence above the ceiling, or suppressed dissent | Verify that a quoted passage is real |
| Catch dangling citations and dropped outline sections | Prove that you actually read the source |

**Scripts passing ≠ conclusions reliable.** Reliability comes from cross-source triangulation and the red team, not from the scripts.

---

## Layout

```
kaoju/
├── SKILL.md                     # Entry: three principles, 9 phases, depth gates, quick reference
├── references/
│   ├── ledger.md            ★   # Column definitions, four conditions, 8 statuses (single source of truth)
│   ├── workflow.md              # Phase-by-phase detail
│   ├── source-scoring.md        # Credibility rubric + domain authority tiers
│   ├── adversarial.md           # Five red-team roles
│   ├── report-shape.md          # Argument-chain structure + self-check list
│   ├── subagent-prompts.md      # Dispatch templates + search axes + anti-recursion rule
│   ├── handoff.md               # Cross-session handoff + state window
│   └── fetch.md                 # Local fetch channel
├── scripts/
│   ├── ledger_check.py      ★   # 11 machine assertions
│   ├── check_all.py             # Single validation entry point
│   ├── verify_citations.py      # Citation integrity
│   ├── source_evaluator.py      # Source authority scoring
│   └── emit_run_summary.py      # Run summary
├── agents/research-fetcher.md   # Constrained fetcher agent (install to ~/.claude/agents/)
├── fixtures/                    # Test fixtures (passing + failing)
└── evals/evals.json             # Routing regression tests
```

---

## Three design trade-offs

**1. The 13-column ledger is split into two 10-column tables.**
Source type, original root, and discovery path are not properties of a *claim* — they are properties of a *source*. Left in the claim table, a claim citing 5 sources needs 15 cells kept positionally aligned — exactly the kind of work a model gets silently wrong while the script stays quiet. After splitting, each fact is written once.

**2. Everything is persisted; no "deliver only the final draft".**
Intermediate results all go to disk. This is not fussiness: auto-compaction is disabled on this machine, so long research does not degrade gracefully — it hits a wall. Anything not on disk is already lost.

**3. The red team is positioned as gap-finding, not falsification.**
Every subagent here runs the same model, so the five roles are not five independent minds and their shared blind spots are not eliminated. Reliability of key conclusions therefore comes from cross-source triangulation, not the red team; and **do not spawn more agents "for independence"** — more agents add cost, not independence.

---

## Credits

| Source | License | Contribution |
|---|---|---|
| [Socialpranker/deepdive](https://github.com/Socialpranker/deepdive) | MIT | Four-condition triangulation, 8 statuses, confidence ceiling, dissent protection, state window, red-team gating, circuit breakers |
| [staruhub/ClaudeSkills](https://github.com/staruhub/ClaudeSkills) | MIT | Three validation scripts, degraded mode, output tiers, handoff protocol |
| [SeanEllyJames/deep-research-skill](https://github.com/SeanEllyJames/deep-research-skill) | MIT (**ideas only**) | Meta-reflection questions, "good answer" standard, section-title detector, counter-evidence search terms |
| [grapeot/context-infrastructure](https://github.com/grapeot/context-infrastructure) | No license | Ideational origin of the Deep-vs-Wide framing (acknowledgement) |

Why the third entry is ideas-only and not text, see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) §3.

---

## Maintenance

- After editing `README.md`, re-run the translation of this file and update the source commit and date above.
  **The goal is not synchronisation — it is that non-synchronisation stays visible.**
- Column definitions live in exactly one place: `references/ledger.md`. Do not copy them elsewhere.
- This directory is both the skill install location and a git working tree. **Do not run `git clean -fdx` here.**

---

## License

MIT © 2026 f25h-233
