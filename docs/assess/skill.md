---
title: Skillの使い方
nav_order: 2
---

# Skillの使い方：ai-maturity-assessor

指定したリポジトリを走査し、評価の下書きを証拠付きで作るAgent Skillです。`skills/ai-maturity-assessor/` にあります。

このSkillは、[AIを含む開発とは](../guide/ai-development.md)で説明した「ファイルに書いた手順書」そのものです。Claude Code のようなAIエージェントにこの手順書を読ませると、エージェントが評価対象のリポジトリを読み、同梱のスクリプトを実行し、基準との照合結果を報告書の形で書き出します。評価者はその下書きを出発点に、ヒアリングと確定を行います。Skillが行うのは[評価の進め方](howto.md)の手順1だけです。

## できること・できないこと

| できること | できないこと |
|---|---|
| リポジトリ内の証拠の収集と、基準55件との照合 | レベル4・5の判定 |
| 軸別レベル、PJのレベル、自動化段階（A1〜A3）の算定 | 自動化段階A4の判定 |
| 統制不足の検出 | 工程別の判定 |
| ヒアリング事項の質問文付きの一覧化 | リポジトリ外の証拠（WBS、見積書、共有環境の設定）の確認 |

見積もり・PJ収支軸は証拠がリポジトリの外にあるため、リポジトリだけではPJの確定レベルは低く出ます。下書きは「確定」と「暫定上限」を併記します。

## 導入

Claude Codeの場合は、`skills/ai-maturity-assessor/` を、評価に使う環境のSkillディレクトリ（例：`.claude/skills/`）へ配置します。Python 3（3.12で動作確認）と `git` コマンドが必要です。追加のパッケージは不要です。

## 使い方

エージェントに次のように依頼します。

```text
/path/to/repo の成熟度を評価して。PJ名は「〇〇システム」。
```

Skillは次の3段を順に実行します。

| 段 | 担当 | 内容 |
|---|---|---|
| 1 | スクリプト | 基準ごとの証拠候補を収集する。Git履歴で判定できる基準はここで確定する |
| 2 | AI＋検証スクリプト | AIは証拠の所在だけを同定する。検証スクリプトが、ファイルの実在、行番号、抜粋の一致を検査する |
| 3 | スクリプト | レベルを算定し、報告書を生成する。検証に合格していなければ実行を拒否する |

AIはレベルを計算しません。証拠のない「充足」と、探索していない「未充足」は検証で不合格になります。

手動で実行する場合は次のとおりです。

```bash
cd skills/ai-maturity-assessor
python scripts/collect_evidence.py /path/to/repo
# findings.draft.json を findings.json に複写し、candidate と unresolved を解決する
python scripts/validate_findings.py /path/to/repo
python scripts/score_and_render.py /path/to/repo --project "〇〇システム"
```

出力は既定で `/path/to/repo/maturity-out/` に作られます。

## ヒアリング回答の反映

ヒアリングで得た回答は、`findings.json` の該当基準に申告として記録し、段2の検証から再実行します。

```json
{
  "id": "EST-2-02",
  "status": "met",
  "evidence": [
    {"attested_by": "回答者", "statement": "回答内容", "where": "証拠の所在"}
  ]
}
```

申告で充足とした基準は、報告書に「申告」と表示されます。リポジトリで判定する基準には、申告を使えません。

## 注意

- 証拠候補の検出パターンは初期版です。CIやエージェント設定の構成によっては、候補が見つからない場合があります。その場合もAIがリポジトリを探索して証拠を記録できます。
- 基準を変更する場合は `criteria/criteria.json` を編集し、`python tools/build_pages.py` を実行します。
