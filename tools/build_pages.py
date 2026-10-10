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
    "成熟度モデルを一枚で見渡す表です。行がレベル、列が評価軸で、1行が「そのレベルのPJの姿」を表します。\n\n"
    "各軸で現状に最も近いセルを選ぶと、[判定規則](rules.md)（PJのレベルは5軸の最小値、統制不足の有無）に基づく自己評価が上の集計に表示されます。"
    "記録はこのブラウザにだけ保存されます。\n\n"
    "**自己評価は申告に基づく暫定です。** 確定には[評価の進め方](../assess/howto.md)の手順で証拠を確認してください。\n\n"
)


def matrix_page(crit, model, order):
    """成熟度マトリクス。行＝レベル（または段階）、列＝評価軸（または属性）。軸別レベルと自動化段階はセルを選べる。"""
    lv_keys = ["0", "1", "2", "3", "4", "5"]
    levels = model["levels"]
    stages = model["stages"]
    org = set(model["org_levels"])
    by_id = {c["id"]: c for c in crit["criteria"]}
    counts = {}
    for c in crit["criteria"]:
        counts[(c["axis"], c["level"])] = counts.get((c["axis"], c["level"]), 0) + 1

    def lv_label(k):
        return "未到達" if k == "0" else f"レベル{k}"

    def lv_row_head(k):
        name = "" if k == "0" else f"<span class=\"mm-lv-name\">{html(levels[k]['name'])}</span>"
        return f"<th scope=\"row\" class=\"mm-row-head\">{lv_label(k)}{name}</th>"

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

    # 1. 軸別レベル（行＝レベル、列＝軸）
    out += "## 軸別レベル\n\n"
    out += "行がレベル、列が評価軸です。各セルの文は[軸別ビュー](axes.md)の「状態」と同じで、「具体例（架空PJ）」はセル内で開きます。架空PJは[はじめに](../guide/index.md)で設定した販売管理システム更改PJです。"
    out += "「基準 n 件」は[軸別チェックリスト](../checklist/index.md)の該当レベルへ移動します。レベル4・5は、複数PJの実績によるベースラインが必要なため、PJ単独では判定しません。\n\n"
    out += "<details class=\"mm-axis-help\"><summary>各軸が何を見るか</summary><ul>"
    for a in model["axes"]:
        out += f"<li><a href=\"axes.html#{anchor(a['anchor'])}\">{html(a['name'])}</a>：{html(a['plain'])}</li>"
    out += "</ul></details>\n\n"
    out += "<div class=\"mm-matrix-wrap\"><table class=\"mm-matrix mm-matrix-axes\" aria-label=\"軸別レベル\">\n"
    out += "<thead><tr><th scope=\"col\" class=\"mm-row-head\">レベル</th>"
    for a in model["axes"]:
        out += f"<th scope=\"col\" data-axis=\"{a['id']}\" title=\"{html(a['plain'])}\"><a href=\"axes.html#{anchor(a['anchor'])}\">{html(a['name'])}</a></th>"
    out += "</tr></thead>\n<tbody>\n"
    for k in lv_keys:
        cls = " class=\"mm-org\"" if int(k) in org else ""
        out += f"<tr data-level=\"{k}\"{cls}>" + lv_row_head(k)
        for a in model["axes"]:
            out += f"<td class=\"mm-cell\" data-axis=\"{a['id']}\" data-level=\"{k}\" role=\"button\" tabindex=\"0\" aria-pressed=\"false\" aria-label=\"{html(a['name'])} を {lv_label(k)} として記録\">"
            out += f"<span class=\"mm-mark\" aria-hidden=\"true\">選択中</span><p class=\"mm-state\">{html(a['states'][k])}</p>"
            out += f"<div class=\"mm-foot\"><details><summary>具体例（架空PJ）</summary><p>{html(a['examples'][k])}</p></details>"
            n = counts.get((a["id"], int(k)))
            if n:
                out += f"<a class=\"mm-more\" href=\"../checklist/{a['checklist']}.html#{anchor('レベル' + k + '-' + levels[k]['name'])}\">基準 {n} 件</a>"
            elif int(k) in org:
                out += "<span class=\"mm-more mm-org-note\">組織側の整備が到達条件</span>"
            out += "</div></td>"
        out += "</tr>\n"
    out += "</tbody></table></div>\n\n"

    # 2. 自動化段階（行＝段階、列＝属性）
    out += "## 自動化段階\n\n"
    out += "行が段階です。「状態」のセルを選ぶと、実行記録で確認できた最上位の段階として記録されます。各段階の定義は[自動化段階](automation.md)、必須基準は[自動化段階の判定基準](../checklist/automation.md)にあります。\n\n"
    st_keys = ["0", "A1", "A2", "A3", "A4"]
    out += "<div class=\"mm-matrix-wrap\"><table class=\"mm-matrix mm-matrix-stages\" aria-label=\"自動化段階\">\n"
    out += "<thead><tr><th scope=\"col\" class=\"mm-row-head\">段階</th><th scope=\"col\">状態</th><th scope=\"col\">具体例（架空PJ）</th><th scope=\"col\">確認する基準</th></tr></thead>\n<tbody>\n"
    for k in st_keys:
        st = stages[k]
        head = html(st["posture"]) if k == "0" else f"{k}<span class=\"mm-lv-name\">{html(st['posture'])}</span>"
        name = "自動化段階なし" if k == "0" else k
        out += f"<tr data-stage=\"{k}\"><th scope=\"row\" class=\"mm-row-head\">{head}</th>"
        out += f"<td class=\"mm-cell mm-stage-cell\" data-stage=\"{k}\" role=\"button\" tabindex=\"0\" aria-pressed=\"false\" aria-label=\"自動化段階を {name} として記録\"><span class=\"mm-mark\" aria-hidden=\"true\">選択中</span><p class=\"mm-state\">{html(st['state'])}</p></td>"
        out += f"<td>{html(st['example'])}</td>"
        if k == "0":
            req = "—"
        elif st["requires"]:
            req = "<br>".join(f"<a href=\"../checklist/automation.html\"><code>{cid}</code></a> {html(by_id[cid]['text'])}" for cid in st["requires"])
        else:
            req = "本カタログでは判定しない。レベル4のベースライン（停止・再試行・確認の条件を数値で定めること）が前提"
        out += f"<td>{req}</td></tr>\n"
    out += "</tbody></table></div>\n\n"

    # 3. 成熟度レベル（行＝レベル、列＝属性）
    out += "## 成熟度レベル\n\n"
    out += "行がPJのレベルです。この表は選択しません。上の軸別レベルで選んだ5軸の最小値が、PJのレベルとして強調表示されます。各欄は[レベル別ビュー](levels.md)と[効果の目安](../effect/estimate.md)と同じ内容です。\n\n"
    pj_keys = ["1", "2", "3", "4", "5"]
    out += "<div class=\"mm-matrix-wrap\"><table class=\"mm-matrix mm-matrix-levels\" aria-label=\"成熟度レベル\">\n"
    out += "<thead><tr><th scope=\"col\" class=\"mm-row-head\">レベル</th><th scope=\"col\">全体像</th><th scope=\"col\" class=\"mm-col-narrow\">自動化段階の上限</th><th scope=\"col\">次のレベルへ上がる条件</th><th scope=\"col\" class=\"mm-col-narrow\">効果の目安<span class=\"mm-lv-name\">AI適用作業／案件全体の工数削減率</span></th><th scope=\"col\">具体例（架空PJ）</th></tr></thead>\n<tbody>\n"
    for k in pj_keys:
        cls = " class=\"mm-org\"" if int(k) in org else ""
        e = model["effects"][k]
        nxt = levels[k]["next"]
        out += f"<tr data-level=\"{k}\"{cls}>" + lv_row_head(k)
        out += f"<td><a href=\"levels.html#{anchor('レベル' + k + '-' + levels[k]['name'])}\">{html(levels[k]['summary'])}</a></td>"
        out += f"<td class=\"mm-col-narrow\">{html(levels[k]['max_stage'])}</td>"
        out += f"<td>{html(nxt) if nxt else '最高レベル。' + html(model['org_levels_note'])}</td>"
        out += f"<td class=\"mm-col-narrow\">{html(e['task'])}／{html(e['project'])}<span class=\"mm-sub\">{html(e['handling'])}</span></td>"
        out += f"<td><details><summary>開く</summary><p>{html(levels[k]['example'])}</p></details></td></tr>\n"
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
