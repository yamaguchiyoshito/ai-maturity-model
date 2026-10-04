#!/usr/bin/env python3
"""基準の正本（criteria/*.json）から、チェックリストのページとSkill同梱の基準を生成する。

使い方:
  python tools/build_pages.py          生成して書き込む
  python tools/build_pages.py --check  生成物が正本と一致するか検査する（不一致なら exit 1）

Python標準ライブラリのみを使用する。生成物を手で編集しないこと。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CRITERIA = ROOT / "criteria" / "criteria.json"
PROCESS = ROOT / "criteria" / "process.json"
SKILL_COPY = ROOT / "skills" / "ai-maturity-assessor" / "references" / "criteria.json"
GEN_NOTE = "<!-- このページは tools/build_pages.py が生成します。編集は criteria/ の正本で行ってください。 -->"
SOURCE = {"repo": "リポジトリ", "either": "リポジトリまたはヒアリング", "hearing": "ヒアリング"}
AXIS_SLUG = {"SK": "skill", "ENV": "environment", "STD": "standard-assets", "PRC": "process", "EST": "estimate"}
AXIS_PREFACE = (
    "**このページの読み方**：IDは「軸-レベル-連番」です。「確認元」が「リポジトリ」の基準はリポジトリを探して見つからなければ未充足、"
    "「ヒアリング」の基準は探さずに要ヒアリングにします。「リポジトリまたはヒアリング」は、リポジトリで見つからなければヒアリングで確認します。"
    "質問文は「ヒアリング時の質問」列にあります。分からない用語は[用語集](../appendix/glossary.md)を参照してください。\n\n"
)
STAGE_PREFACE = (
    "**このページの読み方**：各段階の基準IDは、軸別チェックリストの基準を参照しています。"
    "判定した自動化段階が、PJのレベルの上限を超えていれば統制不足です。\n\n"
)
PROCESS_PREFACE = (
    "**このページの読み方**：各項目の「判定」欄に、その工程でできていれば印を付けます。見出しのタグ（開発標準資産の前提、レベル1、レベル2、A2、A3、A4）は、"
    "項目がどのレベルまたは自動化段階に対応するかを示します。あるタグの項目をすべて満たした最上位のタグが、この工程の判定です。"
    "【ローカル事前検証】は、共有する前に個人の作業環境で行うビルド・静的解析・テストを指します。\n\n"
)


def fm(title, order):
    return f"---\ntitle: {title}\nnav_order: {order}\n---\n\n{GEN_NOTE}\n\n"


def esc(s):
    return s.replace("|", "\\|")


def axis_page(crit, ax, order):
    name = crit["axes"][ax]
    out = fm(name, order)
    out += f"# {name}\n\n"
    out += AXIS_PREFACE
    out += f"基準カタログ v{crit['version']}。下位レベルを含むすべての基準を満たした最上位のレベルが、この軸のレベルです。\n\n"
    for lv in crit["judged_levels"]:
        cs = [c for c in crit["criteria"] if c["axis"] == ax and c["level"] == lv]
        out += f"## レベル{lv}：{crit['levels'][str(lv)]}\n\n"
        out += "| ID | 基準 | 確認元 | ヒアリング時の質問 |\n|---|---|---|---|\n"
        for c in cs:
            out += f"| `{c['id']}` | {esc(c['text'])} | {SOURCE[c['source']]} | {esc(c.get('question', '—'))} |\n"
        out += "\n"
    out += "## レベル4・5\n\n複数PJの実績によるベースラインが必要なため、PJ単独では判定しません。状態定義は[レベル別ビュー](../model/levels.md)を参照してください。\n"
    return out


def stage_page(crit, order):
    by_id = {c["id"]: c for c in crit["criteria"]}
    out = fm("自動化段階", order)
    out += "# 自動化段階の判定基準\n\n"
    out += STAGE_PREFACE
    out += "下位の段階を含むすべての必須基準を満たした最上位の段階が、PJの自動化段階です。A4は本カタログでは判定しません。\n\n"
    for key in sorted(crit["stages"]):
        st = crit["stages"][key]
        out += f"## {key}：{st['name']}\n\n前提レベル：レベル{st['min_level']}以上\n\n"
        out += "| ID | 必須基準 | 確認元 |\n|---|---|---|\n"
        for cid in st["requires"]:
            c = by_id[cid]
            out += f"| `{cid}` | {esc(c['text'])} | {SOURCE[c['source']]} |\n"
        out += "\n"
    return out


def process_page(proc, p, order):
    out = fm(p["name"], order)
    out += f"# {p['name']}\n\n"
    out += PROCESS_PREFACE
    out += f"主な評価対象：{p['target']}\n\n"
    out += f"工程別カタログ v{proc['version']}。タグは初期割当です。\n\n"
    for tag, label in proc["tags"].items():
        items = [t for g, t in p["items"] if g == tag]
        if not items:
            continue
        out += f"## {label}\n\n| 判定 | 項目 |\n|:-:|---|\n"
        for t in items:
            out += f"| □ | {esc(t)} |\n"
        out += "\n"
    return out


def build():
    crit = json.loads(CRITERIA.read_text(encoding="utf-8"))
    proc = json.loads(PROCESS.read_text(encoding="utf-8"))
    ids = [c["id"] for c in crit["criteria"]]
    assert len(ids) == len(set(ids)), "基準IDが重複しています"
    for st in crit["stages"].values():
        for r in st["requires"]:
            assert r in ids, f"stages が未定義の基準を参照しています: {r}"
    for p in proc["processes"]:
        for g, _ in p["items"]:
            assert g in proc["tags"], f"未定義のタグ: {g}"
    outs = {SKILL_COPY: CRITERIA.read_text(encoding="utf-8")}
    for i, ax in enumerate(crit["axes"], 1):
        outs[ROOT / "docs" / "checklist" / f"{AXIS_SLUG[ax]}.md"] = axis_page(crit, ax, i)
    outs[ROOT / "docs" / "checklist" / "automation.md"] = stage_page(crit, len(crit["axes"]) + 1)
    for i, p in enumerate(proc["processes"], 1):
        outs[ROOT / "docs" / "process" / f"{p['slug']}.md"] = process_page(proc, p, i)
    return outs


def main():
    check = "--check" in sys.argv
    outs = build()
    drift = []
    for path, text in outs.items():
        cur = path.read_text(encoding="utf-8") if path.exists() else None
        if cur != text:
            drift.append(path.relative_to(ROOT).as_posix())
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
    if check and drift:
        print(f"[NG] 正本と一致しない生成物が {len(drift)} 件あります。python tools/build_pages.py を実行してください")
        for d in drift:
            print("  - " + d)
        return 1
    print(f"[OK] 生成物 {len(outs)} 件" + ("は正本と一致しています" if check else f"（更新 {len(drift)} 件）"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
