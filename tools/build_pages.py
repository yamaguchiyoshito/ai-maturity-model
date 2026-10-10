#!/usr/bin/env python3
"""基準の正本（criteria/*.json）から、チェックリストのページ、成熟度マトリクス、Skill同梱の基準を生成する。

使い方:
  python tools/build_pages.py          生成して書き込む
  python tools/build_pages.py --check  生成物が正本と一致するか検査する（不一致なら exit 1）

Python標準ライブラリのみを使用する。生成物を手で編集しないこと。
"""
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CRITERIA = ROOT / "criteria" / "criteria.json"
PROCESS = ROOT / "criteria" / "process.json"
MODEL = ROOT / "criteria" / "model.json"
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


def fm(title, order, **extra):
    lines = [f"title: {title}", f"nav_order: {order}"] + [f"{k}: {v}" for k, v in extra.items()]
    return "---\n" + "\n".join(lines) + f"\n---\n\n{GEN_NOTE}\n\n"


def html(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def anchor(s):
    """VitePressの見出しIDに合わせる。VitePressは見出しをNFKD正規化し小文字化するため、濁点・半濁点を含む語は分解された形になる。"""
    return unicodedata.normalize("NFKD", s).lower()


def attr_json(obj):
    """HTML属性（単引用符）に埋め込むJSON。"""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("&", "&amp;").replace("'", "&#39;")


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


MATRIX_INTRO = (
    "成熟度モデルの全体を一枚で見渡すための表です。[軸別ビュー](axes.md)、[レベル別ビュー](levels.md)、[自動化段階](automation.md)に分かれている定義を、"
    "行に評価軸、列にレベルを取って並べ直しています。表は横にスクロールでき、見出し行と評価軸の列は固定されます。\n\n"
    "表のセルを選ぶと、その軸の自己評価として記録され、下の集計に[判定規則](rules.md)（PJのレベルは5軸の最小値、自動化段階は前提レベルを超えると統制不足）を当てた結果が表示されます。"
    "記録はこのブラウザのローカルストレージにだけ保存され、サーバーには送られません。\n\n"
    "**この集計は申告に基づく自己評価です。** 判定規則は自己申告だけでは充足としないため、確定には[評価の進め方](../assess/howto.md)の手順で証拠を確認してください。"
    "集計のMarkdownは[報告書の例](../assess/sample-report.md)の「軸別レベル」表と同じ形式で、評価下書きの出発点として使えます。\n\n"
)


def matrix_page(crit, model, order):
    """成熟度マトリクス。軸×レベルの表（選択可能）、自動化段階の表（選択可能）、成熟度レベルの表（導出結果を強調）。"""
    lv_keys = ["0", "1", "2", "3", "4", "5"]
    levels = model["levels"]
    stages = model["stages"]
    org = set(model["org_levels"])
    by_id = {c["id"]: c for c in crit["criteria"]}
    counts = {(c["axis"], c["level"]): 0 for c in crit["criteria"]}
    for c in crit["criteria"]:
        counts[(c["axis"], c["level"])] += 1

    def lv_head(k):
        if k == "0":
            return "<th scope=\"col\" data-level=\"0\">未到達</th>"
        return f"<th scope=\"col\" data-level=\"{k}\">レベル{k}<br><span class=\"mm-lv-name\">{html(levels[k]['name'])}</span></th>"

    data = {
        "levels": {k: v["name"] for k, v in levels.items()},
        "next": {k: v["next"] for k, v in levels.items()},
        "maxStage": {k: v["max_stage"] for k, v in levels.items()},
        "orgLevels": sorted(org),
        "axes": [{"id": a["id"], "name": a["name"]} for a in model["axes"]],
        "estimateAxis": "EST",
        "stages": {k: {"name": v["name"], "posture": v["posture"], "minLevel": v["min_level"]} for k, v in stages.items()},
        "effects": {k: {"task": v["task"], "project": v["project"], "handling": v["handling"]} for k, v in model["effects"].items()},
        "effectRules": model["effect_rules"],
    }

    out = fm("成熟度マトリクス", order, aside="false")
    out += "# 成熟度マトリクス\n\n"
    out += MATRIX_INTRO
    out += "<ClientOnly><MatrixAssessment /></ClientOnly>\n\n"
    out += f"<div class=\"mm-data\" data-model='{attr_json(data)}' hidden></div>\n\n"

    # 1. 軸別レベル
    out += "## 軸別レベル\n\n"
    out += "行が評価軸、列がレベルです。各セルの文は[軸別ビュー](axes.md)の「状態」と同じで、「具体例（架空PJ）」はセル内で開きます。架空PJは[はじめに](../guide/index.md)で設定した販売管理システム更改PJです。"
    out += "「基準」のリンクは[軸別チェックリスト](../checklist/index.md)の該当レベルへ移動します。レベル4・5は、複数PJの実績によるベースラインが必要なため、PJ単独では判定しません。\n\n"
    out += "<div class=\"mm-matrix-wrap\"><table class=\"mm-matrix mm-matrix-axes\" aria-label=\"軸別レベル\">\n"
    out += "<thead><tr><th scope=\"col\">評価軸</th>" + "".join(lv_head(k) for k in lv_keys) + "</tr></thead>\n<tbody>\n"
    for a in model["axes"]:
        out += f"<tr data-axis=\"{a['id']}\" data-axis-name=\"{html(a['name'])}\">"
        out += f"<th scope=\"row\" class=\"mm-axis\"><a href=\"axes.html#{anchor(a['anchor'])}\">{html(a['name'])}</a><div class=\"mm-def\">{html(a['plain'])}</div></th>"
        for k in lv_keys:
            cls = "mm-cell" + (" mm-org" if int(k) in org else "")
            out += f"<td class=\"{cls}\" data-level=\"{k}\" role=\"button\" tabindex=\"0\" aria-pressed=\"false\" aria-label=\"{html(a['name'])} を {'未到達' if k == '0' else 'レベル' + k} として記録\">"
            out += f"<span class=\"mm-mark\" aria-hidden=\"true\">選択中</span><p class=\"mm-state\">{html(a['states'][k])}</p>"
            out += f"<details><summary>具体例（架空PJ）</summary><p>{html(a['examples'][k])}</p></details>"
            n = counts.get((a["id"], int(k)))
            if n:
                out += f"<a class=\"mm-more\" href=\"../checklist/{a['checklist']}.html#{anchor('レベル' + k + '-' + levels[k]['name'])}\">基準 {n} 件</a>"
            elif int(k) in org:
                out += "<span class=\"mm-more mm-org-note\">組織側の整備が到達条件</span>"
            out += "</td>"
        out += "</tr>\n"
    out += "</tbody></table></div>\n\n"

    # 2. 自動化段階
    out += "## 自動化段階\n\n"
    out += "列が段階です。「状態」の行のセルを選ぶと、実行記録で確認できた最上位の段階として記録されます。各段階の定義と前提レベルは[自動化段階](automation.md)、必須基準は[自動化段階の判定基準](../checklist/automation.md)にあります。\n\n"
    st_keys = ["0", "A1", "A2", "A3", "A4"]
    out += "<div class=\"mm-matrix-wrap\"><table class=\"mm-matrix mm-matrix-stages\" aria-label=\"自動化段階\">\n"
    out += "<thead><tr><th scope=\"col\">項目</th>"
    for k in st_keys:
        st = stages[k]
        label = html(st["posture"]) if k == "0" else f"{k}<br><span class=\"mm-lv-name\">{html(st['posture'])}</span>"
        out += f"<th scope=\"col\" data-stage=\"{k}\">{label}</th>"
    out += "</tr></thead>\n<tbody>\n"
    out += "<tr><th scope=\"row\">状態</th>"
    for k in st_keys:
        st = stages[k]
        name = "自動化段階なし" if k == "0" else k
        out += f"<td class=\"mm-cell mm-stage-cell\" data-stage=\"{k}\" role=\"button\" tabindex=\"0\" aria-pressed=\"false\" aria-label=\"自動化段階を {name} として記録\"><span class=\"mm-mark\" aria-hidden=\"true\">選択中</span><p class=\"mm-state\">{html(st['state'])}</p></td>"
    out += "</tr>\n"
    out += "<tr><th scope=\"row\">具体例（架空PJ）</th>" + "".join(f"<td data-stage=\"{k}\">{html(stages[k]['example'])}</td>" for k in st_keys) + "</tr>\n"
    out += "<tr><th scope=\"row\">前提とするレベル</th>"
    for k in st_keys:
        st = stages[k]
        txt = "—" if k == "0" else f"レベル{st['min_level']}<br><span class=\"mm-sub\">{html(st['reason'])}</span>"
        out += f"<td data-stage=\"{k}\">{txt}</td>"
    out += "</tr>\n"
    out += "<tr><th scope=\"row\">確認する基準</th>"
    for k in st_keys:
        st = stages[k]
        if k == "0":
            txt = "—"
        elif st["requires"]:
            txt = "、".join(f"<a href=\"../checklist/automation.html\"><code>{cid}</code></a> {html(by_id[cid]['text'])}" for cid in st["requires"])
        else:
            txt = "本カタログでは判定しない。レベル4のベースライン（停止・再試行・確認の条件を数値で定めること）が前提"
        out += f"<td data-stage=\"{k}\">{txt}</td>"
    out += "</tr>\n"
    out += "</tbody></table></div>\n\n"

    # 3. 成熟度レベル
    out += "## 成熟度レベル\n\n"
    out += "列がPJのレベルです。この表は選択しません。上の軸別レベルで選んだ5軸の最小値が、PJのレベルとして強調表示されます。各欄は[レベル別ビュー](levels.md)と[効果の目安](../effect/estimate.md)と同じ内容です。\n\n"
    pj_keys = ["1", "2", "3", "4", "5"]
    out += "<div class=\"mm-matrix-wrap\"><table class=\"mm-matrix mm-matrix-levels\" aria-label=\"成熟度レベル\">\n"
    out += "<thead><tr><th scope=\"col\">項目</th>" + "".join(lv_head(k) for k in pj_keys) + "</tr></thead>\n<tbody>\n"
    out += "<tr><th scope=\"row\">全体像</th>" + "".join(f"<td data-level=\"{k}\"><a href=\"levels.html#{anchor('レベル' + k + '-' + levels[k]['name'])}\">{html(levels[k]['summary'])}</a></td>" for k in pj_keys) + "</tr>\n"
    out += "<tr><th scope=\"row\">自動化段階の上限</th>" + "".join(f"<td data-level=\"{k}\">{html(levels[k]['max_stage'])}</td>" for k in pj_keys) + "</tr>\n"
    out += "<tr><th scope=\"row\">次のレベルへ上がる条件</th>"
    for k in pj_keys:
        nxt = levels[k]["next"]
        out += f"<td data-level=\"{k}\">{html(nxt) if nxt else '最高レベル。' + html(model['org_levels_note'])}</td>"
    out += "</tr>\n"
    out += "<tr><th scope=\"row\">効果の目安（AI適用作業の工数削減率／案件全体）</th>"
    for k in pj_keys:
        e = model["effects"][k]
        out += f"<td data-level=\"{k}\">{html(e['task'])}／{html(e['project'])}<br><span class=\"mm-sub\">{html(e['handling'])}</span></td>"
    out += "</tr>\n"
    out += "<tr><th scope=\"row\">具体例（架空PJ）</th>" + "".join(f"<td data-level=\"{k}\"><details><summary>開く</summary><p>{html(levels[k]['example'])}</p></details></td>" for k in pj_keys) + "</tr>\n"
    out += "</tbody></table></div>\n\n"
    out += "効果の目安は実績値ではなく初期仮説です。見積もりで使える削減率は、見積もり・PJ収支を除く4軸の最小レベルに対応する目安値を上限とします（[自動化段階](automation.md#見積もりとの関係)）。\n"
    return out


def build():
    crit = json.loads(CRITERIA.read_text(encoding="utf-8"))
    proc = json.loads(PROCESS.read_text(encoding="utf-8"))
    model = json.loads(MODEL.read_text(encoding="utf-8"))
    ids = [c["id"] for c in crit["criteria"]]
    assert len(ids) == len(set(ids)), "基準IDが重複しています"
    for st in crit["stages"].values():
        for r in st["requires"]:
            assert r in ids, f"stages が未定義の基準を参照しています: {r}"
    for p in proc["processes"]:
        for g, _ in p["items"]:
            assert g in proc["tags"], f"未定義のタグ: {g}"
    assert [a["id"] for a in model["axes"]] == list(crit["axes"]), "model.json の軸が criteria.json と一致しません"
    for a in model["axes"]:
        assert a["name"] == crit["axes"][a["id"]], f"軸名が criteria.json と異なります: {a['id']}"
        assert set(a["states"]) == set(a["examples"]) == {"0", "1", "2", "3", "4", "5"}, f"状態の定義が欠けています: {a['id']}"
    for k, st in crit["stages"].items():
        assert model["stages"][k]["requires"] == st["requires"], f"stages の必須基準が criteria.json と異なります: {k}"
        assert model["stages"][k]["min_level"] == st["min_level"], f"stages の前提レベルが criteria.json と異なります: {k}"
    for k, v in model["levels"].items():
        if k != "0":
            assert v["name"] == crit["levels"][k], f"レベル名が criteria.json と異なります: {k}"
    outs = {SKILL_COPY: CRITERIA.read_text(encoding="utf-8")}
    for i, ax in enumerate(crit["axes"], 1):
        outs[ROOT / "docs" / "checklist" / f"{AXIS_SLUG[ax]}.md"] = axis_page(crit, ax, i)
    outs[ROOT / "docs" / "checklist" / "automation.md"] = stage_page(crit, len(crit["axes"]) + 1)
    outs[ROOT / "docs" / "model" / "matrix.md"] = matrix_page(crit, model, 5)
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
