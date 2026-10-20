#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_all.py —— 考据 skill 的总校验入口

一条命令跑完全部机器校验，中途不因单步失败而停（跑完再报全部）。

用法:
    python check_all.py --workspace <工作目录> [--depth shallow|medium|deep] [--json]

退出码:
    0 = 总判定 PASS
    1 = 有步骤 FAIL，产物不可交付

顺序固定：先账本（结构不对，后面都是空转）。
本包装器还负责堵三处会让校验「静默假通过」的裂缝，详见下方注释。
"""

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

DEPTH_TO_TYPE = {"shallow": "brief", "medium": "full", "deep": "full"}
DEPTH_TO_STAKES = {"shallow": "low", "medium": "medium", "deep": "high"}


def run(script, args, label):
    """跑一个子脚本，返回 (ok, stdout, stderr)。脚本缺失时返回 None 表示跳过。"""
    path = HERE / script
    if not path.is_file():
        return None, "", f"脚本不存在: {path}"
    env = dict(os.environ)
    # 一次保护所有子脚本：Windows 上 cp936 控制台会把中文 JSON 打炸
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, str(path)] + args,
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
    )
    return proc.returncode == 0, proc.stdout, proc.stderr


def csv_to_sources_json(workspace, out_path):
    """裂缝1：staruhub 两个脚本吃 sources.json，我们的账本是 sources.csv。

    字段映射：url/title/date 直传；relevance_score 与 depth_score 由 credibility 折算
    （1–5 → 2–10），因为本 skill 不单独给相关性和深度打分。
    """
    src = workspace / "sources.csv"
    if not src.is_file():
        return 0, "sources.csv 不存在"
    rows = []
    with open(src, "r", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            url = (r.get("url") or "").strip()
            if not url:
                continue
            try:
                cred = int((r.get("credibility") or "3").strip() or 3)
            except ValueError:
                cred = 3
            rows.append({
                "url": url,
                "title": (r.get("title") or "").strip(),
                "date": (r.get("date") or "").strip(),
                "relevance_score": max(1, min(5, cred)) * 2.0,
                "depth_score": max(1, min(5, cred)) * 2.0,
            })
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(rows), ""


def make_registry(workspace, out_path):
    """裂缝3：emit_run_summary.py 从 registry.md 数源（正则 ^\\[(\\d+)\\]）。
    我们没这个文件，不生成的话 source_count 会恒为 0、被误读成「没找到源」。
    """
    src = workspace / "sources.csv"
    if not src.is_file():
        return False
    lines = []
    with open(src, "r", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            sid = (r.get("sid") or "").strip()
            if sid:
                lines.append(f"[{sid}] {(r.get('title') or '').strip()} | {(r.get('url') or '').strip()}")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def valid_as_of(workspace):
    """source_evaluator 的 --as-of 只吃 YYYY-MM-DD，我们的 as_of 可能是 2025-Q3。
    不是严格日期就不传，让它用默认（今天）。"""
    clm = workspace / "claims.csv"
    if not clm.is_file():
        return None
    import re
    with open(clm, "r", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            v = (r.get("as_of") or "").strip()
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
                return v
    return None


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="考据 skill 总校验：账本 + 引用 + 源质量 + 摘要")
    ap.add_argument("--workspace", "-w", required=True, help="调研工作目录")
    ap.add_argument("--depth", "-d", choices=["shallow", "medium", "deep"], default="medium")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出总结果")
    args = ap.parse_args()

    ws = Path(args.workspace).expanduser().resolve()
    if not ws.is_dir():
        print(f"错误: 工作目录不存在: {ws}")
        sys.exit(1)

    depth = args.depth
    check_dir = ws / "_check"
    check_dir.mkdir(exist_ok=True)

    results = []      # (步骤, 判定, 说明)
    notes = []

    def add(step, ok, msg, skipped=False):
        results.append({"step": step, "verdict": "SKIP" if skipped else ("PASS" if ok else "FAIL"),
                        "message": msg})

    # ---- 1. 账本（必须最先，结构不对后面都是空转）
    ok, out, err = run("ledger_check.py", ["--workspace", str(ws), "--depth", depth, "--json"], "账本")
    if ok is None:
        add("账本校验", False, err, skipped=True)
    else:
        try:
            data = json.loads(out)
            n_err = len(data.get("errors", []))
            add("账本校验", data.get("verdict") == "PASS",
                f"{data.get('verdict')}（{n_err} 错 / {len(data.get('warnings', []))} 警）")
            notes.extend(f"账本: {e['message']}" for e in data.get("errors", []))
        except json.JSONDecodeError:
            add("账本校验", ok, "输出无法解析为 JSON")

    # ---- 2. 转 sources.json（裂缝1）
    n_src, why = csv_to_sources_json(ws, check_dir / "sources.json")
    if why:
        add("源表转换", False, why)
    else:
        add("源表转换", n_src > 0, f"{n_src} 条源")

    # ---- 3. registry.md（裂缝3）
    made = make_registry(ws, check_dir / "registry.md")
    add("registry 生成", made, "由 sources.csv 生成" if made else "sources.csv 不可读")

    report = ws / "report.md"

    # ---- 4. 引用校验 + 零引用假通过（裂缝2）
    if not report.is_file():
        add("引用校验", False, "report.md 不存在，跳过", skipped=True)
    else:
        ok, out, err = run("verify_citations.py",
                           [str(report), str(check_dir / "sources.json"),
                            "--output", str(check_dir / "citations.json")], "引用")
        if ok is None:
            add("引用校验", False, err, skipped=True)
        else:
            try:
                data = json.loads((check_dir / "citations.json").read_text(encoding="utf-8"))
                summary = data.get("summary", {})
                n_inline = summary.get("total_inline_citations", 0)
                if n_inline == 0:
                    # 裂缝2：零引用时 verify_citations 判据真空成立，会假 PASS
                    add("引用校验", False,
                        "报告里一个 [NN] 引用编号都没有 —— 校验器会真空通过，这里直接判 FAIL")
                else:
                    add("引用校验", summary.get("verdict") == "PASS",
                        f"{n_inline} 处行内引用 / {summary.get('reference_entries', 0)} 条条目 / "
                        f"{summary.get('issue_count', 0)} 个问题")
            except (json.JSONDecodeError, OSError) as exc:
                add("引用校验", False, f"结果不可读: {exc}")

    # ---- 5. 源质量
    as_of = valid_as_of(ws)
    ev_args = [str(check_dir / "sources.json"),
               "--output", str(check_dir / "evaluation.json"),
               "--mode", "lightweight" if depth == "shallow" else "standard"]
    if as_of:
        ev_args += ["--as-of", as_of]
    ok, out, err = run("source_evaluator.py", ev_args, "源质量")
    if ok is None:
        add("源质量", False, err, skipped=True)
    else:
        try:
            d = json.loads((check_dir / "evaluation.json").read_text(encoding="utf-8"))
            kept, dropped = len(d.get("kept", [])), len(d.get("dropped", []))
            # 源被丢光说明域名表不认这些源，是配置问题不是内容问题 —— 只警告
            add("源质量", True, f"保留 {kept} / 丢弃 {dropped}")
            if kept == 0 and n_src > 0:
                notes.append("源质量: 全部源都被丢弃 —— 域名权威表可能不认这些站点，"
                             "检查 source_evaluator.py 的 TIER 表，或调低 --min-score")
        except (json.JSONDecodeError, OSError) as exc:
            add("源质量", False, f"结果不可读: {exc}")

    # ---- 6. run-summary
    if not report.is_file():
        add("run-summary", False, "report.md 不存在，跳过", skipped=True)
    else:
        sum_args = [
            "--draft", str(report),
            "--registry", str(check_dir / "registry.md"),
            "--output-type", DEPTH_TO_TYPE[depth],
            "--stakes", DEPTH_TO_STAKES[depth],
            "--orchestration", "lead+subagents",
            "--skill-version", "1.0",
            "--output", str(check_dir / "run-summary.json"),
        ]
        ok, out, err = run("emit_run_summary.py", sum_args, "摘要")
        if ok is None:
            add("run-summary", False, err, skipped=True)
        else:
            add("run-summary", ok, "已生成 _check/run-summary.json" if ok else (err or out)[-200:])

    # ---- 汇总
    failed = [r for r in results if r["verdict"] == "FAIL"]
    skipped = [r for r in results if r["verdict"] == "SKIP"]
    passed = [r for r in results if r["verdict"] == "PASS"]
    overall = "FAIL" if failed else ("PASS" if passed else "SKIP")

    if args.json:
        print(json.dumps({"check": "all", "depth": depth, "verdict": overall,
                          "results": results, "notes": notes},
                         ensure_ascii=False, indent=2))
    else:
        print(f"总校验（{depth} 档） · {ws}")
        print("=" * 66)
        for r in results:
            mark = {"PASS": "通过", "FAIL": "失败", "SKIP": "跳过"}[r["verdict"]]
            print(f"  [{mark}] {r['step']:<10} {r['message']}")
        if notes:
            print("-" * 66)
            for n in notes:
                print(f"  提示  {n}")
        print("=" * 66)
        print(f"总判定: {overall}（{len(passed)} 通过 / {len(failed)} 失败 / {len(skipped)} 跳过）")
        if failed:
            print("先把上面标「失败」的产物修好再交。注意：不要为了通过去改账本。")
        print("提醒: 这些脚本只保证「账本自洽、引用闭合」，不保证「结论正确」。")
        print("      结论对不对，靠跨来源三角验证和红队，不靠脚本。")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
