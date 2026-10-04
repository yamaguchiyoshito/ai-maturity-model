---
title: 改訂履歴
nav_order: 4
---

# 改訂履歴

## 未公開

- 公開の仕組みを、Jekyll（just-the-docs、`/docs` ブランチ公開）からVitePressとGitHub Actions（`actions/deploy-pages`）による公開へ変更
- PRの検査（Validate documentation）と `main` の公開（Publish GitHub Pages）を分離し、ブラウザ検証を追加

## v0.1.0

- レベル構成を、CMMIの成熟度レベルの構成を参考にした5段階へ再定義
- 自動化段階（A1〜A4）を制度化レベルから分離し、統制不足の概念を追加
- 評価軸に「AI前提の開発プロセス」「AI前提の見積もり・PJ収支」を追加（3軸から5軸へ）
- 測定と権限定義をレベル2へ前倒し
- 判定基準を `criteria/criteria.json` に一本化し、チェックリストのページを生成に変更
- 工程別チェックリストにレベル・自動化段階のタグを付与（初期割当）
- 算定式の二重控除を修正
- 評価下書きを作るAgent Skill `ai-maturity-assessor` を追加

### 既知の制約

- レベル4・5、自動化段階A4の判定基準は、カタログに未収録
- 工程別チェックリストのタグは初期割当で、Skillの判定対象外
- 効果の目安は初期仮説で、実績による検証前
