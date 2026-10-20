#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger_check.py —— 考据 skill 的账本机器校验

把「纪律」变成跑不过就交不了货的断言。纯标准库，零第三方依赖。

用法:
    python ledger_check.py --workspace <工作目录> [--depth shallow|medium|deep] [--json]

退出码:
    0 = 全部通过（可能有警告）
    1 = 有错误，账本不可交付

列定义见 ../references/ledger.md —— 那里是唯一事实来源，本文件不重复解释语义。
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------- 常量

SOURCE_COLS = [
    "sid", "url", "title", "date", "type", "credibility",
    "access", "root", "discovery_path", "caveat",
]

CLAIM_COLS = {
    "shallow": ["claim_id", "claim", "sources", "status", "confidence", "as_of"],
    "medium": [
        "claim_id", "claim", "hypothesis", "sources", "status", "confidence",
        "primary_source", "source_caveat", "dissent", "as_of",
    ],
}
CLAIM_COLS["deep"] = CLAIM_COLS["medium"]

STATUS_VALUES = {
    "triangulated", "contested", "contradicted", "single-type",
    "single-root", "single-path", "weak", "data-insufficient",
}
CONFIDENCE_VALUES = {"high", "medium", "low"}
TYPE_VALUES = {"一手", "学术", "行业媒体", "大众媒体", "专家博客", "论坛", "其他"}
ACCESS_VALUES = {"full", "partial", "abstract", "closed"}
THIN_ACCESS = {"partial", "abstract", "closed"}
CAVEAT_VALUES = {"-", "vendor", "self-reported"}
SID_RE = re.compile(r"^\d{2}$")
CAVEAT_DISPUTED_RE = re.compile(r"^disputed:(\d{2})$")
CLAIM_ID_RE = re.compile(r"CL\d+")
QUOTE_RE = re.compile(r"^>\s*\S")

MIN_SOURCES = 3
MIN_DIMENSIONS = 2
MIN_QUOTES = 2


# ---------------------------------------------------------------- 工具

def die(msg):
    print(f"错误: {msg}")
    sys.exit(1)


def read_csv(path):
    """用 csv 模块读，绝不 split(',')。返回 (表头, 行列表)。"""
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader]
        return list(reader.fieldnames or []), rows


def split_list(value):
    """把 '01;07;12' 拆成 ['01','07','12']；空值/'-' 返回 []。"""
    if not value:
        return []
    value = value.strip()
    if value in ("-", ""):
        return []
    return [p.strip() for p in value.split(";") if p.strip()]


def count_quotes(workspace, sid):
    """数 sources/NN_slug.md 里以 '> ' 开头的引用行。文件不存在返回 None。"""
    src_dir = workspace / "sources"
    if not src_dir.is_dir():
        return None
    matches = sorted(src_dir.glob(f"{sid}_*.md")) + sorted(src_dir.glob(f"{sid}.md"))
    if not matches:
        return None
    try:
        text = matches[0].read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    return sum(1 for line in text.splitlines() if QUOTE_RE.match(line))


def parse_claim_ids(path):
    """从 outline.md 里抠出所有 CLnn 形式的编号。用 tokenize 而不是硬编码单一正则，
    这样以后换编号规则时不会静默读到零条。"""
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    return set(CLAIM_ID_RE.findall(text))


# ---------------------------------------------------------------- 主校验

class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.notes = []

    def err(self, rule, msg):
        self.errors.append({"rule": rule, "message": msg})

    def warn(self, rule, msg):
        self.warnings.append({"rule": rule, "message": msg})

    def note(self, msg):
        self.notes.append(msg)

    @property
    def ok(self):
        return not self.errors


def load_tables(workspace, depth, rep):
    """读两张表并校验表头。返回 (sources_rows_by_sid, claims_rows) 或 None。"""
    src_path = workspace / "sources.csv"
    clm_path = workspace / "claims.csv"

    for p in (src_path, clm_path):
        if not p.is_file():
            rep.err("表存在", f"找不到 {p.name}（工作目录: {workspace}）")
    if not rep.ok:
        return None

    src_cols, src_rows = read_csv(src_path)
    clm_cols, clm_rows = read_csv(clm_path)

    # 断言 1：列名齐全（按档位）
    missing_src = [c for c in SOURCE_COLS if c not in src_cols]
    if missing_src:
        rep.err("断言1 列名齐全", f"sources.csv 缺列: {', '.join(missing_src)}（应有 {len(SOURCE_COLS)} 列，见 references/ledger.md）")
    extra_src = [c for c in src_cols if c not in SOURCE_COLS]
    if extra_src:
        rep.warn("断言1 列名齐全", f"sources.csv 有未知列: {', '.join(extra_src)}（列定义只写在 references/ledger.md）")

    want_claim_cols = CLAIM_COLS[depth]
    missing_clm = [c for c in want_claim_cols if c not in clm_cols]
    if missing_clm:
        msg = f"claims.csv 缺列: {', '.join(missing_clm)}（{depth} 档应有 {len(want_claim_cols)} 列）"
        if depth == "shallow":
            rep.warn("断言1 列名齐全", msg + " —— 浅档仅警告")
        else:
            rep.err("断言1 列名齐全", msg)

    if not rep.ok:
        return None

    # 断言 3：无重复 sid、无重复 URL
    seen_sid, seen_url = {}, {}
    for i, row in enumerate(src_rows, start=2):
        sid = (row.get("sid") or "").strip()
        url = (row.get("url") or "").strip()
        if not SID_RE.match(sid):
            rep.err("断言3 无重复", f"sources.csv 第 {i} 行 sid='{sid}' 不是两位数字（应为 01–99）")
            continue
        if sid in seen_sid:
            rep.err("断言3 无重复", f"sid {sid} 重复出现（第 {seen_sid[sid]} 行与第 {i} 行）")
        else:
            seen_sid[sid] = i
        if url:
            if url in seen_url:
                rep.err("断言3 无重复", f"同一 URL 被登记成两个 sid（{seen_url[url]} 与 {sid}）: {url[:80]}")
            else:
                seen_url[url] = sid

    # 逐行校验源表的取值域
    for i, row in enumerate(src_rows, start=2):
        sid = (row.get("sid") or "").strip()
        typ = (row.get("type") or "").strip()
        acc = (row.get("access") or "").strip()
        cav = (row.get("caveat") or "").strip()
        cred = (row.get("credibility") or "").strip()
        if typ and typ not in TYPE_VALUES:
            rep.err("取值域", f"sources.csv 第 {i} 行（sid {sid}）type='{typ}' 不在枚举内: {'/'.join(sorted(TYPE_VALUES))}")
        if acc and acc not in ACCESS_VALUES:
            rep.err("取值域", f"sources.csv 第 {i} 行（sid {sid}）access='{acc}' 不在枚举内: full/partial/abstract/closed")
        if cav and cav not in CAVEAT_VALUES and not CAVEAT_DISPUTED_RE.match(cav):
            rep.err("取值域", f"sources.csv 第 {i} 行（sid {sid}）caveat='{cav}' 不在枚举内: - / vendor / self-reported / disputed:NN")
        if cred and not cred.isdigit():
            rep.err("取值域", f"sources.csv 第 {i} 行（sid {sid}）credibility='{cred}' 不是整数")

    by_sid = {r["sid"].strip(): r for r in src_rows if SID_RE.match((r.get("sid") or "").strip())}

    # 断言 4：sources/NN_slug.md 与 sid 一一对应
    src_dir = workspace / "sources"
    if src_dir.is_dir():
        file_ids = set()
        for p in src_dir.glob("*.md"):
            m = re.match(r"^(\d{2})", p.name)
            if m:
                file_ids.add(m.group(1))
            else:
                rep.warn("断言4 编号", f"sources/{p.name} 文件名不是 NN_ 开头，无法对应 sid")
        for fid in sorted(file_ids - set(by_sid)):
            rep.err("断言4 编号", f"sources/ 下有 {fid}_*.md，但 sources.csv 里没有 sid={fid}（编号越界或漏登记）")
        for sid in sorted(set(by_sid) - file_ids):
            rep.warn("断言4 编号", f"sid={sid} 已登记但 sources/ 下没有对应的 NN_*.md（缺原文摘录文件）")
    else:
        rep.warn("断言4 编号", "没有 sources/ 目录 —— 无法校验编号，也无法数原文摘录（所有源都会被当作薄源）")

    return by_sid, clm_rows


def root_key(row, sid):
    """把 root 列折算成「出处身份」，用于判独立来源数。

    - `own`：这条源本身就是原始出处 → 它的身份是**它自己**（sid）。
      三个互相独立的一手源 root 都写 `own`，那是 3 个独立出处，不是 1 个。
    - `unclear`（或空）：查不出来源 → 保守地算作**同一个**未知出处，
      因为无法证明的独立性不能算独立性。
    - 其它：就是那个短 id，同一个 id 表示同一篇的转载。
    """
    r = (row.get("root") or "").strip()
    if r == "own":
        return f"own:{sid}"
    if not r or r == "unclear":
        return "unclear"
    return r


def source_is_thin(workspace, row):
    """薄源：付费墙摘要，或原文摘录不足 2 条。返回 (是否薄, 原因)。"""
    acc = (row.get("access") or "").strip()
    if acc in THIN_ACCESS:
        return True, f"access={acc}"
    n = count_quotes(workspace, (row.get("sid") or "").strip())
    if n is not None and n < MIN_QUOTES:
        return True, f"原文摘录只有 {n} 条（需 ≥{MIN_QUOTES}）"
    return False, ""


def evaluate_claim(workspace, row, by_sid, rep, line_no):
    """重算四条件，返回 (allowed_statuses, detail)。detail 用于报错时说明。"""
    sid_list = split_list(row.get("sources"))

    # 断言 11：sources 列的 token 必须合法且无重复
    bad = [s for s in sid_list if not SID_RE.match(s)]
    if bad:
        rep.err("断言11 sources 列", f"claims.csv 第 {line_no} 行 sources 含非法编号: {', '.join(bad)}")
    dup = {s for s in sid_list if sid_list.count(s) > 1}
    if dup:
        rep.err("断言11 sources 列", f"claims.csv 第 {line_no} 行 sources 重复引用: {', '.join(sorted(dup))}")

    # 断言 2：每个 sid 都要在源表里
    missing = [s for s in sid_list if s not in by_sid]
    if missing:
        rep.err("断言2 sid 存在", f"claims.csv 第 {line_no} 行引用了不存在的源: {', '.join(missing)}")

    effective, thin_notes = [], []
    for s in sid_list:
        if s not in by_sid:
            continue
        thin, why = source_is_thin(workspace, by_sid[s])
        if thin:
            thin_notes.append(f"{s}({why})")
        else:
            effective.append(s)

    # 断言 9：薄源不计入四条件
    types = {(by_sid[s].get("type") or "").strip() for s in effective}
    roots = {root_key(by_sid[s], s) for s in effective}
    paths = {(by_sid[s].get("discovery_path") or "").strip() for s in effective}
    n = len(set(effective))

    if thin_notes:
        rep.note(f"第 {line_no} 行（{row.get('claim_id')}）未计入三角验证的薄源: {', '.join(thin_notes)}")

    ok_n = n >= MIN_SOURCES
    ok_type = len(types) >= MIN_DIMENSIONS
    ok_root = len(roots) >= MIN_DIMENSIONS
    ok_path = len(paths) >= MIN_DIMENSIONS

    detail = (f"有效源 {n} 个（需 ≥{MIN_SOURCES}）、类型 {len(types)} 种、"
              f"原始出处 {len(roots)} 个、发现路径 {len(paths)} 条（后三项各需 ≥{MIN_DIMENSIONS}）")

    if n < MIN_SOURCES:
        base = {"weak", "data-insufficient"}
    elif not ok_type:
        base = {"single-type"}
    elif not ok_root:
        base = {"single-root"}
    elif not ok_path:
        base = {"single-path"}
    else:
        base = {"triangulated"}

    # 断言 8：有分量的异议 → 必须 contested/contradicted，不许按多数决压掉
    dissent_ids = split_list(row.get("dissent"))
    strong = []
    for d in dissent_ids:
        drow = by_sid.get(d)
        if not drow:
            rep.err("断言2 sid 存在", f"claims.csv 第 {line_no} 行 dissent 引用了不存在的源: {d}")
            continue
        try:
            cred = int((drow.get("credibility") or "0").strip() or 0)
        except ValueError:
            cred = 0
        if cred >= 4 or (drow.get("type") or "").strip() == "一手":
            strong.append(d)

    if strong:
        allowed = {"contested", "contradicted"}
        detail += f"；异议源 {'/'.join(strong)} 有分量，只能判 contested 或 contradicted"
    else:
        allowed = base

    return allowed, detail, n, len(types), len(roots), len(paths)


def check_claims(workspace, rows, by_sid, depth, rep):
    for i, row in enumerate(rows, start=2):
        cid = (row.get("claim_id") or "").strip() or f"第{i}行"
        status = (row.get("status") or "").strip()
        conf = (row.get("confidence") or "").strip()
        primary = (row.get("primary_source") or "").strip().upper()
        cav = (row.get("source_caveat") or "").strip()
        as_of = (row.get("as_of") or "").strip()

        if status and status not in STATUS_VALUES:
            rep.err("取值域", f"claims.csv 第 {i} 行（{cid}）status='{status}' 不在 8 值枚举内")
            continue
        if conf and conf not in CONFIDENCE_VALUES:
            rep.err("取值域", f"claims.csv 第 {i} 行（{cid}）confidence='{conf}' 不在枚举内: high/medium/low")
        if cav and cav not in CAVEAT_VALUES and not CAVEAT_DISPUTED_RE.match(cav):
            rep.err("取值域", f"claims.csv 第 {i} 行（{cid}）source_caveat='{cav}' 不在枚举内")
        if depth != "shallow":
            if primary and primary not in ("Y", "N"):
                rep.err("取值域", f"claims.csv 第 {i} 行（{cid}）primary_source='{primary}' 应为 Y 或 N")
            if not as_of:
                rep.warn("取值域", f"claims.csv 第 {i} 行（{cid}）as_of 为空 —— 非数值论点也请填 '-'")

        # 断言 5：重算四条件，与声明的 status 必须一致
        allowed, detail, n, ntype, nroot, npath = evaluate_claim(workspace, row, by_sid, rep, i)
        if status and status not in allowed:
            rep.err("断言5 四条件一致",
                    f"claims.csv 第 {i} 行（{cid}）声明 status='{status}'，但按源表重算只能是 "
                    f"{' 或 '.join(sorted(allowed))}。{detail}")

        # 断言 6：high 必须有 Y 的一手源
        if conf == "high" and primary != "Y" and depth != "shallow":
            rep.err("断言6 置信度天花板",
                    f"claims.csv 第 {i} 行（{cid}）confidence=high 但 primary_source={primary or '空'} —— "
                    f"没有一手源时置信度不许超过 medium")

        # 断言 7：caveat 压置信度
        if cav and cav != "-" and depth != "shallow":
            if conf == "high":
                rep.err("断言7 caveat 压置信度",
                        f"claims.csv 第 {i} 行（{cid}）source_caveat='{cav}' 但 confidence=high —— 应 ≤ medium")
            m = CAVEAT_DISPUTED_RE.match(cav)
            if m and conf not in ("low",) and not (row.get("dissent") or "").strip().strip("-"):
                rep.err("断言7 caveat 压置信度",
                        f"claims.csv 第 {i} 行（{cid}）source_caveat='{cav}' 且无仲裁/异议，confidence 应为 low")


def parse_sections(path):
    """抠出 markdown 的二级章节标题。"""
    text = path.read_text(encoding="utf-8", errors="replace")
    return [s.strip() for s in re.findall(r"^##\s+(.+?)\s*$", text, flags=re.MULTILINE)]


def check_outline(workspace, claim_rows, rep):
    """断言 10：账本 → 大纲 → 报告，三层不许掉东西。

    outline.md 是「论点编号」到「章节标题」的翻译层：
    每条已成立的论点必须在大纲里出现，而大纲的每个章节必须落到报告里。
    报告正文只写源编号 [01]，不写论点编号 —— 所以不拿 CLxx 去比对正文。
    """
    outline = workspace / "outline.md"
    report = workspace / "report.md"

    if not outline.is_file():
        rep.warn("断言10 outline 覆盖", "没有 outline.md —— 跳过覆盖检查（成文前应先写大纲）")
        return
    if not report.is_file():
        rep.warn("断言10 outline 覆盖", "没有 report.md —— 跳过覆盖检查")
        return

    outline_ids = parse_claim_ids(outline) or set()
    known_ids = {(r.get("claim_id") or "").strip() for r in claim_rows}

    # a) 每条已成立的论点都要进大纲
    required = [(r.get("claim_id") or "").strip() for r in claim_rows
                if (r.get("status") or "").strip() in ("triangulated", "contested")]
    missing = [c for c in required if c and c not in outline_ids]
    if missing:
        rep.err("断言10 outline 覆盖",
                f"这些 {len(missing)} 条已成立的论点没进大纲: {', '.join(missing)}"
                f"（triangulated/contested 的每条都必须落到某一章）")

    # b) 大纲不许引用账本里没有的编号
    dangling = sorted(i for i in outline_ids if i not in known_ids)
    if dangling:
        rep.err("断言10 outline 覆盖", f"outline.md 引用了账本里不存在的论点编号: {', '.join(dangling)}")

    # c) 大纲的每个章节都要在报告里出现（防「大纲写了、成文漏了」）
    report_text = report.read_text(encoding="utf-8", errors="replace")
    dropped = [s for s in parse_sections(outline) if s not in report_text]
    if dropped:
        rep.err("断言10 outline 覆盖",
                f"这些章节在大纲里有、报告里没有: {' / '.join(dropped[:6])}"
                f"{' 等' if len(dropped) > 6 else ''}（大纲到成文之间掉了内容）")


# ---------------------------------------------------------------- 入口

def infer_depth(workspace):
    plan = workspace / "research-plan.md"
    if plan.is_file():
        text = plan.read_text(encoding="utf-8", errors="replace")
        if re.search(r"深度[:：]\s*浅", text):
            return "shallow"
        if re.search(r"深度[:：]\s*深", text):
            return "deep"
        if re.search(r"深度[:：]\s*中", text):
            return "medium"
    return "medium"


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    ap = argparse.ArgumentParser(
        description="考据 skill 账本机器校验：把纪律变成跑不过就交不了货的断言。")
    ap.add_argument("--workspace", "-w", required=True, help="调研工作目录（含 sources.csv / claims.csv）")
    ap.add_argument("--depth", "-d", choices=["shallow", "medium", "deep"],
                    help="深度档位。不给则从 research-plan.md 读，读不到按 medium")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出，供 check_all.py 消费")
    args = ap.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.is_dir():
        die(f"工作目录不存在: {workspace}")

    depth = args.depth or infer_depth(workspace)
    rep = Report()

    loaded = load_tables(workspace, depth, rep)
    if loaded:
        by_sid, claim_rows = loaded
        check_claims(workspace, claim_rows, by_sid, depth, rep)
        check_outline(workspace, claim_rows, rep)

    if args.json:
        print(json.dumps({
            "check": "ledger",
            "depth": depth,
            "verdict": "PASS" if rep.ok else "FAIL",
            "errors": rep.errors,
            "warnings": rep.warnings,
            "notes": rep.notes,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"账本校验（{depth} 档） · {workspace}")
        print("-" * 60)
        for n in rep.notes:
            print(f"  提示  {n}")
        for w in rep.warnings:
            print(f"  警告  [{w['rule']}] {w['message']}")
        for e in rep.errors:
            print(f"  错误  [{e['rule']}] {e['message']}")
        print("-" * 60)
        if rep.ok:
            print(f"账本判定: PASS（{len(rep.warnings)} 条警告）")
        else:
            print(f"账本判定: FAIL（{len(rep.errors)} 条错误，{len(rep.warnings)} 条警告）")
            print("注意: 脚本只保证「账本自洽」，不保证「结论正确」。结论对不对靠三角验证和红队。")

    sys.exit(0 if rep.ok else 1)


if __name__ == "__main__":
    main()
