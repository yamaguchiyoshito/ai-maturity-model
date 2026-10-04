#!/usr/bin/env python3
"""段1: リポジトリを走査し、基準ごとの証拠候補を決定論的に収集する。

使い方: python collect_evidence.py <repo> [--out <dir>]
出力:   <out>/evidence.json        収集した証拠候補とロック済み判定
        <out>/findings.draft.json  LLMが解決する下書き（candidate / unresolved を含む）
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

from _common import (MAX_CANDIDATES, git, is_git_repo, list_files, load_criteria,
                     match_files, read_lines)


def run_probe(repo, files, probe, isgit):
    """戻り値: (candidates, locked_status or None)"""
    t = probe["type"]
    if t == "glob":
        hits = match_files(files, probe["patterns"])[:MAX_CANDIDATES]
        return [{"path": h, "line": None, "excerpt": None} for h in hits], None
    if t == "grep":
        rx = re.compile(probe["pattern"], re.IGNORECASE)
        cands = []
        for f in match_files(files, probe["globs"]):
            for no, line in enumerate(read_lines(repo, f), 1):
                if rx.search(line):
                    cands.append({"path": f, "line": no, "excerpt": line.strip()[:200]})
                    break  # 1ファイル1件
            if len(cands) >= MAX_CANDIDATES:
                break
        return cands, None
    if t == "git_tracked":
        if not isgit:
            return [], "hearing"
        tracked = (git(repo, "ls-files") or "").splitlines()
        hits = match_files(tracked, probe["patterns"])[:MAX_CANDIDATES]
        return [{"path": h, "line": None, "excerpt": None} for h in hits], ("met" if hits else "not_met")
    if t == "git_authors":
        if not isgit:
            return [], "hearing"
        tracked = (git(repo, "ls-files") or "").splitlines()
        hits = match_files(tracked, probe["patterns"])
        if not hits:
            return [], "not_met"
        out = git(repo, "log", "--format=%ae", "--", *hits) or ""
        n = len({a.strip().lower() for a in out.splitlines() if a.strip()})
        cands = [{"path": hits[0], "line": None, "excerpt": None, "fact": f"コミット作成者 {n} 名"}]
        return cands, ("met" if n >= probe.get("min", 2) else "not_met")
    raise ValueError(f"未知のprobe種別: {t}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    repo = Path(a.repo).resolve()
    if not repo.is_dir():
        print(f"[NG] リポジトリが見つかりません: {repo}", file=sys.stderr)
        return 1
    out = Path(a.out).resolve() if a.out else repo / "maturity-out"
    out.mkdir(parents=True, exist_ok=True)

    crit, sha = load_criteria()
    files = list_files(repo)
    isgit = is_git_repo(repo)
    items, draft = {}, []
    for c in crit["criteria"]:
        cands, locked = [], None
        for p in c.get("probes", []):
            cs, lk = run_probe(repo, files, p, isgit)
            cands += cs
            locked = lk or locked
        cands = cands[:MAX_CANDIDATES]
        items[c["id"]] = {"candidates": cands, "locked_status": locked if c.get("locked") else None}
        f = {"id": c["id"], "text": c["text"], "source": c["source"], "evidence": [], "searched": [], "note": ""}
        if c.get("locked"):
            f["status"] = locked or "not_met"
            f["evidence"] = cands if f["status"] == "met" else []
            f["searched"] = ["git ls-files / git log（スクリプトが判定）"] if f["status"] == "not_met" else []
        elif cands:
            f["status"] = "candidate"
            f["evidence"] = cands
        elif c["source"] == "hearing":
            f["status"] = "hearing"
        else:
            f["status"] = "unresolved"
        draft.append(f)

    meta = {"repo": str(repo), "generated": datetime.date.today().isoformat(), "is_git": isgit,
            "head": (git(repo, "rev-parse", "HEAD") or "").strip() or None,
            "criteria_version": crit["version"], "criteria_sha256": sha, "file_count": len(files)}
    (out / "evidence.json").write_text(json.dumps({"meta": meta, "items": items}, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "findings.draft.json").write_text(json.dumps({"meta": meta, "findings": draft}, ensure_ascii=False, indent=2), encoding="utf-8")

    from collections import Counter
    cnt = Counter(f["status"] for f in draft)
    print(f"[OK] 走査ファイル数 {len(files)} / 基準 {len(draft)} 件 / Git管理 {'あり' if isgit else 'なし'}")
    print("     " + " / ".join(f"{k}: {v}" for k, v in sorted(cnt.items())))
    print(f"     出力: {out}/evidence.json, {out}/findings.draft.json")
    print("     次: findings.draft.json を findings.json に複写し、candidate と unresolved を解決する")
    return 0


if __name__ == "__main__":
    sys.exit(main())
