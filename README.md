# SI受託開発のAI利用成熟度モデル

SI受託開発におけるAI利用の成熟度を、PJ単位で評価するためのモデルです。文書（GitHub Pages）、判定基準の正本、評価下書きを作るAgent Skillを、このリポジトリで管理します。

- **制度化レベル**：CMMIのレベル構成を参考にした5段階（属人的／プロセス確立／組織標準化／定量管理／継続的最適化）
- **評価軸**：Agent Skill、環境との接続、開発標準資産、AI前提の開発プロセス、AI前提の見積もり・PJ収支
- **自動化段階**：A1〜A4。レベルを超えた自動化を「統制不足」として検出

## 構成

```text
.
├── criteria/
│   ├── criteria.json        判定基準の正本（軸別、55件）
│   └── process.json         工程別チェックリストの正本（9工程、119項目）
├── tools/
│   ├── build_pages.py       正本 → チェックリストのページとSkill同梱の基準を生成
│   ├── selftest.py          Skillの自己テスト、報告書の例の生成
│   ├── build_docs.mjs       一致検査、自己テスト、静的サイト生成を順に実行
│   ├── check_html.py        生成したHTMLのページ数・リンク・アンカーの検査
│   └── check_site.mjs       ブラウザ（Playwright）での表示・検索・モバイル確認
├── skills/
│   └── ai-maturity-assessor/  評価下書きを作るAgent Skill
├── docs/                    文書の正本（Markdown）。GitHub Pagesのサイトを生成する
│   ├── index.md             ホーム（読む順、目的別の入口、早見表）
│   ├── guide/               はじめに：AIを含む開発とは、開発の基本用語、なぜ測るのか、モデルの全体像
│   ├── model/               レベル別ビュー、軸別ビュー、自動化段階、判定規則
│   ├── assess/              評価の進め方、Skillの使い方、報告書の例【生成】
│   ├── checklist/           【生成】軸別チェックリスト
│   ├── process/             【生成】工程別チェックリスト
│   ├── effect/              効果の目安、算定式、全社集計
│   ├── appendix/            CMMIとの対応、用語集、改訂履歴
│   ├── .vitepress/          サイト設定（ナビゲーション、日本語検索、テーマ）
│   └── public/assets/       公開する静的アセット
├── package.json / .nvmrc    実行コマンド、固定した依存関係、Node.jsの版
└── .github/workflows/
    ├── docs.yml             PRの検査（ルート・サブディレクトリの2構成）
    └── pages.yml            mainへのpushを契機に、ビルド、ブラウザ確認、Pagesへの公開
```

## 基準を変更する

基準の正本は `criteria/` の2ファイルだけです。`docs/checklist/`、`docs/process/`、`skills/ai-maturity-assessor/references/criteria.json` は生成物なので、手で編集しません。

```bash
# 1. criteria/criteria.json または criteria/process.json を編集する
# 2. 生成する
npm run docs:generate
# 3. 確認する
npm run docs:check
```

CIは、生成物が正本と一致しない場合と、自己テストが失敗した場合に不合格になります。

## ローカルで読む

Node.js **24**（`.nvmrc`）、Python **3.12以降**を使用します。

```bash
npm ci
npm run docs:dev
```

## 検査と生成

```bash
npm run docs:build
npx playwright install --with-deps chromium
npm run test:site
npm run docs:preview
```

| コマンド | 処理 |
|---|---|
| `docs:generate` | 正本からチェックリストのページとSkill同梱の基準を生成する |
| `docs:check` | 生成物が正本と一致するか検査し、Skillの自己テストを実行する |
| `docs:build` | `docs:check` のあと、VitePressで `docs/.vitepress/dist/` に静的サイトを生成する |
| `test:site` | 生成したHTMLのページ数・リンク・アンカーを検査し、ブラウザで表示・検索・モバイル表示を確認する |
| `docs:preview` | 生成したサイトをローカルで配信する |

文書は、AIを含む開発に不慣れな読者がサイドバーの上から順に読んで理解できるように構成しています。各ページの末尾に「次に読む」を置き、説明には架空の「販売管理システム更改PJ」を一貫して使います。ナビゲーションは各ページの front matter（`title`、`nav_order`）から組み立てます。ページを追加するときは、節のディレクトリに `title` と `nav_order` を持つMarkdownを置きます。生成物（`docs/.vitepress/dist/`、`artifacts/`）と `node_modules` はコミットしません。

## 公開する（GitHub Pages）

1. **Settings → Pages → Build and deployment → Source** で **GitHub Actions** を選択します。
2. **Settings → Environments → github-pages** の公開元は `main` のみで問題ありません。

`main` へのpushを契機に **Publish GitHub Pages** がビルド・ブラウザ検証後に公開します。PRでは **Validate documentation** が検査だけを行い、公開サイトを変更しません。標準URLは `https://<owner>.github.io/ai-maturity-model/` です。

公開先のベースパスとオリジンは `actions/configure-pages` から受け取るため、リポジトリ名を変えてもソースの修正は不要です。ローカルで別のベースパスを検証するには `SITE_BASE_PATH=/ npm run docs:build` のように指定します。

旧版へ戻すには、`main` で該当する変更を取り消す（revert）PRをマージします。再公開だけが必要な場合は **Publish GitHub Pages → Run workflow** を `main` から実行します。

## Skillを使う

`skills/ai-maturity-assessor/` をエージェントのSkillディレクトリへ配置します。使い方は `docs/assess/skill.md` を参照してください。

## 公開前の確認事項

- [ ] ライセンスと著作権者を確定する（`LICENSE.md`）
- [ ] CMMIの商標表記を法務部門で確認する（`docs/appendix/cmmi-mapping.md`）
- [ ] 効果の目安（`docs/effect/estimate.md`）を公開範囲に含めるか決める
- [ ] 実際のリポジトリでSkillを実行し、証拠候補の検出パターンを調整する
