#!/usr/bin/env python3
"""段2の検証: findings.json が証拠に裏付けられているかを決定論的に検査する。

使い方: python validate_findings.py <repo> [--out <dir>]
終了コード: 0 = 合格 / 1 = 不合格（指摘を標準出力へ）
"""
import argparse
import json
import sys
from pathlib import Path

from _common import load_criteria, read_lines

ALLOWED = {"met", "not_met", "hearing"}


def validate(repo, out):
    errs = []
    crit, sha = load_criteria()
    by_id = {c["id"]: c for c in crit["criteria"]}
    try:
        ev = json.loads((out / "evidence.json").read_text(encoding="utf-8"))
        fd = json.loads((out / "findings.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return [f"V00 入力を読めません: {e}"], None
    if ev["meta"]["criteria_sha256"] != sha:
        errs.append("V01 criteria.json が証拠収集時から変更されています。collect_evidence.py を再実行してください")
    seen = {}
    for f in fd.get("findings", []):
        if f.get("id") in seen:
            errs.append(f"V02 {f.get('id')}: 重複しています")
        seen[f.get("id")] = f
    for cid in by_id:
        if cid not in seen:
            errs.append(f"V02 {cid}: 判定がありません")
    for cid, f in seen.items():
        c = by_id.get(cid)
        if c is None:
            errs.append(f"V02 {cid}: カタログにない基準です（基準の追加は禁止）")
            continue
        st = f.get("status")
        if st not in ALLOWED:
            errs.append(f"V03 {cid}: status='{st}' は未解決です（met / not_met / hearing のいずれかにする）")
            continue
        locked = ev["items"].get(cid, {}).get("locked_status")
        if locked and st != locked:
            errs.append(f"V04 {cid}: スクリプト判定（{locked}）を変更できません")
            continue
        if st == "met":
            evs = f.get("evidence") or []
            if not evs:
                errs.append(f"V05 {cid}: met には証拠が1件以上必要です")
            for e in evs:
                if e.get("attested_by"):  # ヒアリング回答（申告）による証拠
                    if c["source"] == "repo":
                        errs.append(f"V11 {cid}: リポジトリで判定する基準に申告は使えません")
                    if not e.get("statement") or not e.get("where"):
                        errs.append(f"V11 {cid}: 申告には statement（回答内容）と where（証拠の所在）が必要です")
                    continue
                rel = e.get("path") or ""
                p = (repo / rel).resolve()
                if not rel or repo not in p.parents or not p.is_file():
                    errs.append(f"V06 {cid}: 証拠のファイルがリポジトリ内にありません: {rel}")
                    continue
                if e.get("line") is not None:
                    lines = read_lines(repo, rel)
                    no, ex = e["line"], (e.get("excerpt") or "").strip()
                    if not isinstance(no, int) or not (1 <= no <= len(lines)):
                        errs.append(f"V07 {cid}: 行番号が範囲外です: {rel}:{no}")
                    elif not ex or ex not in lines[no - 1]:
                        errs.append(f"V07 {cid}: 抜粋が該当行と一致しません: {rel}:{no}")
        elif st == "not_met":
            if c["source"] != "repo":
                errs.append(f"V08 {cid}: リポジトリ外に証拠がありうる基準です。not_met ではなく hearing にしてください")
            if not f.get("searched"):
                errs.append(f"V09 {cid}: not_met には探索した場所（searched）が必要です")
        elif st == "hearing":
            if c["source"] == "repo" and not locked:
                errs.append(f"V10 {cid}: リポジトリで判定する基準です。met か not_met にしてください")
    return errs, fd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    repo = Path(a.repo).resolve()
    out = Path(a.out).resolve() if a.out else repo / "maturity-out"
    errs, _ = validate(repo, out)
    if errs:
        print(f"[NG] {len(errs)} 件の指摘")
        for e in errs:
            print("  - " + e)
        return 1
    print("[OK] findings.json は検証に合格しました")
    return 0


if __name__ == "__main__":
    sys.exit(main())
