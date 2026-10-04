#!/usr/bin/env python3
"""段3: 検証済みの findings.json からレベルを算定し、評価下書き（Markdown）を出力する。

使い方: python score_and_render.py <repo> [--out <dir>] [--project <PJ名>]
出力:   <out>/score.json, <out>/maturity-report.md
レベル算定はこのスクリプトだけが行う。LLMはレベルを計算・変更しない。
"""
import argparse
import json
import sys
from pathlib import Path

from _common import load_criteria
from validate_findings import validate

MARK = {"met": "○", "not_met": "×", "hearing": "？"}
LABEL = {"met": "充足", "not_met": "未充足", "hearing": "要ヒアリング"}


def level_of(crits, status, judged, optimistic):
    ok = lambda s: s == "met" or (optimistic and s == "hearing")
    lv = 0
    for L in judged:
        if all(ok(status[c["id"]]) for c in crits if c["level"] == L):
            lv = L
        else:
            break
    return lv


def stage_of(stages, status, optimistic):
    ok = lambda s: s == "met" or (optimistic and s == "hearing")
    st = 0
    for i, key in enumerate(sorted(stages), 1):
        if all(ok(status[r]) for r in stages[key]["requires"]):
            st = i
        else:
            break
    return st


def ev_text(f):
    parts = []
    for e in f.get("evidence") or []:
        if e.get("attested_by"):
            parts.append(f"申告（{e['attested_by']}）: {e['statement']}／所在: {e['where']}")
            continue
        s = f"`{e['path']}" + (f":{e['line']}`" if e.get("line") else "`")
        if e.get("fact"):
            s += f"（{e['fact']}）"
        parts.append(s)
    if f["status"] == "not_met" and f.get("searched"):
        parts.append("探索: " + "、".join(str(x) for x in f["searched"]))
    if f.get("note"):
        parts.append(f["note"])
    return "<br>".join(parts) or "—"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--out", default=None)
    ap.add_argument("--project", default=None)
    a = ap.parse_args()
    repo = Path(a.repo).resolve()
    out = Path(a.out).resolve() if a.out else repo / "maturity-out"

    errs, fd = validate(repo, out)
    if errs:
        print(f"[NG] findings.json が未検証です（{len(errs)} 件）。validate_findings.py を合格させてください")
        return 1

    crit, _ = load_criteria()
    names, axes, judged = crit["levels"], crit["axes"], crit["judged_levels"]
    by_id = {c["id"]: c for c in crit["criteria"]}
    fmap = {f["id"]: f for f in fd["findings"]}
    status = {i: f["status"] for i, f in fmap.items()}

    rows = {}
    for ax in axes:
        cs = [c for c in crit["criteria"] if c["axis"] == ax]
        conf = level_of(cs, status, judged, False)
        pot = level_of(cs, status, judged, True)
        nxt = conf + 1
        gaps = [c["id"] for c in cs if c["level"] == nxt and status[c["id"]] != "met"] if nxt in judged else []
        rows[ax] = {"confirmed": conf, "potential": pot, "next_gaps": gaps}
    pj_conf = min(r["confirmed"] for r in rows.values())
    pj_pot = min(r["potential"] for r in rows.values())
    st_conf = stage_of(crit["stages"], status, False)
    st_pot = stage_of(crit["stages"], status, True)
    lack = "確定" if st_conf > pj_pot else ("疑い" if st_conf > pj_conf else "なし")
    repo_axes = crit.get("repo_axes", [])
    repo_conf = min(rows[x]["confirmed"] for x in repo_axes) if repo_axes else None
    constraint = [ax for ax, r in rows.items() if r["confirmed"] == pj_conf]
    hearings = [i for i, s in status.items() if s == "hearing"]

    score = {"meta": fd["meta"], "project": a.project, "axes": rows,
             "pj_level": {"confirmed": pj_conf, "potential": pj_pot},
             "automation_stage": {"confirmed": f"A{st_conf}" if st_conf else None, "potential": f"A{st_pot}" if st_pot else None},
             "control_deficit": lack, "repo_axes_level": repo_conf, "constraint_axes": constraint, "hearing_count": len(hearings)}
    (out / "score.json").write_text(json.dumps(score, ensure_ascii=False, indent=2), encoding="utf-8")

    lv = lambda n: f"レベル{n} {names[str(n)]}" if n else names["0"]
    sg = lambda n: f"A{n}" if n else "未到達"
    m = fd["meta"]
    L = []
    L.append(f"# AI利用成熟度 評価下書き：{a.project or repo.name}")
    L.append("")
    L.append("> **この文書は下書きです。** リポジトリから確認できた証拠だけで判定しています。"
             f"要ヒアリング {len(hearings)} 件を解消するまで、レベルは確定しません。")
    L.append("")
    L.append("| 項目 | 内容 |")
    L.append("|---|---|")
    L.append(f"| 対象 | `{m['repo']}` |")
    L.append(f"| コミット | `{m.get('head') or 'Git管理外'}` |")
    L.append(f"| 評価日 | {m['generated']} |")
    L.append(f"| 基準カタログ | v{m['criteria_version']} |")
    L.append("")
    L.append("## 1. 判定概要")
    L.append("")
    L.append(f"- **PJのレベル（確定）**：{lv(pj_conf)}")
    L.append(f"- **PJのレベル（暫定上限）**：{lv(pj_pot)}　※要ヒアリングがすべて充足だった場合")
    if repo_axes:
        L.append(f"- **リポジトリで確認できる{len(repo_axes)}軸の確定レベル**：{lv(repo_conf)}　※{'、'.join(axes[x] for x in repo_axes)}")
    L.append(f"- **自動化段階**：{sg(st_conf)}（暫定上限 {sg(st_pot)}）")
    L.append(f"- **制約になっている軸**：{'、'.join(axes[x] for x in constraint)}")
    L.append("")
    L.append("| 評価軸 | 確定 | 暫定上限 | 次レベルの未充足 |")
    L.append("|---|---|---|---:|")
    for ax, r in rows.items():
        L.append(f"| {axes[ax]} | {lv(r['confirmed'])} | {lv(r['potential'])} | {len(r['next_gaps'])} 件 |")
    L.append("")
    L.append("## 2. 統制状態")
    L.append("")
    if lack == "確定":
        L.append(f"**統制不足です。** 自動化段階 {sg(st_conf)} は レベル{st_conf} 以上を前提としますが、PJのレベルは暫定上限でも {lv(pj_pot)} です。"
                 "自動化を先に進めず、制約になっている軸を引き上げてください。")
    elif lack == "疑い":
        L.append(f"**統制不足の疑いがあります。** 自動化段階 {sg(st_conf)} は レベル{st_conf} 以上を前提としますが、PJの確定レベルは {lv(pj_conf)} です。"
                 "ヒアリング事項の解消後に再判定してください。")
    else:
        L.append(f"自動化段階 {sg(st_conf)} は、PJの確定レベル（{lv(pj_conf)}）の範囲内です。")
    L.append("")
    L.append("## 3. 次のレベルへの差分")
    L.append("")
    order = constraint + [x for x in axes if x not in constraint]
    for ax in order:
        r = rows[ax]
        if not r["next_gaps"]:
            continue
        tag = "（制約軸）" if ax in constraint else ""
        L.append(f"### {axes[ax]}{tag}：{lv(r['confirmed'])} → レベル{r['confirmed'] + 1}")
        L.append("")
        for cid in r["next_gaps"]:
            L.append(f"- {MARK[status[cid]]} `{cid}` {by_id[cid]['text']}（{LABEL[status[cid]]}）")
        L.append("")
    L.append("## 4. ヒアリング事項")
    L.append("")
    if hearings:
        L.append("リポジトリからは確認できない項目です。回答と証拠の所在を記入してください。")
        L.append("")
        L.append("| ID | 軸 | レベル | 質問 | 回答・証拠 |")
        L.append("|---|---|---:|---|---|")
        for cid in hearings:
            c = by_id[cid]
            axn = axes.get(c["axis"], "自動化段階")
            L.append(f"| `{cid}` | {axn} | {c['level']} | {c.get('question', c['text'])} | |")
    else:
        L.append("ヒアリング事項はありません。")
    L.append("")
    L.append("## 5. 基準別の判定と証拠")
    L.append("")
    L.append("記号：○ 充足 ／ × 未充足 ／ ？ 要ヒアリング")
    L.append("")
    for ax, axn in list(axes.items()) + [("AUTO", "自動化段階（A3の判定用）")]:
        L.append(f"### {axn}")
        L.append("")
        L.append("| 判定 | ID | レベル | 基準 | 証拠 |")
        L.append("|:-:|---|---:|---|---|")
        for c in crit["criteria"]:
            if c["axis"] == ax:
                f = fmap[c["id"]]
                L.append(f"| {MARK[f['status']]} | `{c['id']}` | {c['level']} | {c['text']} | {ev_text(f)} |")
        L.append("")
    L.append("## 6. この下書きの対象外")
    L.append("")
    L.append("- **レベル4・5**：複数PJの実績によるベースラインが必要なため、PJ単独では判定しません。")
    L.append("- **工程別の判定**：本下書きはPJ全体を軸別に判定します。工程別の判定は工程別チェックリストで行います。")
    L.append("- **継続利用の確認**：直近四半期の実行記録による維持判定は、ヒアリングで確認します。")
    L.append("")
    (out / "maturity-report.md").write_text("\n".join(L), encoding="utf-8")
    print(f"[OK] PJレベル 確定: {lv(pj_conf)} / 暫定上限: {lv(pj_pot)} / 自動化段階: {sg(st_conf)} / 統制不足: {lack}")
    print(f"     出力: {out}/maturity-report.md, {out}/score.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
