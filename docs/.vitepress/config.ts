import { defineConfig } from 'vitepress'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

// 公開先のベースパスは GitHub Pages の設定（configure-pages）から受け取る。所有者名やリポジトリ名を固定しない。
const root = new URL('../../', import.meta.url)
const docs = fileURLToPath(new URL('../', import.meta.url))
const { version } = JSON.parse(readFileSync(new URL('package.json', root), 'utf8'))
const repository = process.env.GITHUB_REPOSITORY || ''
const [owner, repo] = repository.split('/')
const defaultBase = repo ? (repo.toLowerCase() === `${owner}.github.io`.toLowerCase() ? '/' : `/${repo}/`) : '/ai-maturity-model/'
const requestedBase = process.env.SITE_BASE_PATH ?? defaultBase
const base = '/' + requestedBase.replace(/^\/+|\/+$/g, '') + (requestedBase.replace(/\//g, '') ? '/' : '')
const origin = (process.env.SITE_ORIGIN || '').replace(/\/$/, '')

// ナビゲーションは各ページの front matter（title, nav_order）から組み立てる。
type Page = { title: string; order: number; link: string }
const frontmatter = (file: string) => {
  const text = readFileSync(file, 'utf8')
  const m = text.match(/^---\n([\s\S]*?)\n---/)
  const fm: Record<string, string> = {}
  for (const line of (m ? m[1] : '').split('\n')) {
    const i = line.indexOf(':')
    if (i > 0) fm[line.slice(0, i).trim()] = line.slice(i + 1).trim().replace(/^["']|["']$/g, '')
  }
  if (!fm.title) throw new Error(`title がありません: ${path.relative(docs, file)}`)
  return fm
}
const page = (file: string): Page => {
  const fm = frontmatter(file)
  const rel = path.relative(docs, file).replace(/\\/g, '/')
  return { title: fm.title, order: Number(fm.nav_order ?? 999), link: '/' + rel.replace(/index\.md$/, '').replace(/\.md$/, '') }
}
const sections = readdirSync(docs)
  .filter(name => !name.startsWith('.') && name !== 'public' && statSync(path.join(docs, name)).isDirectory() && statSync(path.join(docs, name, 'index.md'), { throwIfNoEntry: false }))
  .map(name => {
    const dir = path.join(docs, name)
    const index = page(path.join(dir, 'index.md'))
    const children = readdirSync(dir).filter(f => f.endsWith('.md') && f !== 'index.md').map(f => page(path.join(dir, f))).sort((a, b) => a.order - b.order)
    return { name, index, children }
  })
  .sort((a, b) => a.index.order - b.index.order)
const home = page(path.join(docs, 'index.md'))
const sidebar = [
  { text: home.title, link: '/' },
  ...sections.map(s => ({ text: s.index.title, link: s.index.link, collapsed: false, items: s.children.map(p => ({ text: p.title, link: p.link })) }))
]
const nav = sections.map(s => ({ text: s.index.title, link: s.index.link, activeMatch: `^/${s.name}/` }))

export default defineConfig({
  lang: 'ja-JP',
  title: 'SI受託開発のAI利用成熟度モデル',
  titleTemplate: ':title | AI利用成熟度モデル',
  description: 'PJ単位でAI利用の成熟度を評価し、制約工程の特定と効果測定に使うためのモデル',
  base,
  cleanUrls: false,
  appearance: true,
  srcExclude: ['public/**'],
  head: [['link', { rel: 'icon', type: 'image/svg+xml', href: `${base}assets/favicon.svg` }]],
  ...(origin ? { sitemap: { hostname: origin + base } } : {}),
  markdown: { lineNumbers: false },
  themeConfig: {
    siteTitle: 'AI利用成熟度モデル',
    nav,
    sidebar,
    ...(repository ? { socialLinks: [{ icon: 'github', link: `https://github.com/${repository}` }], editLink: { pattern: `https://github.com/${repository}/edit/main/docs/:path`, text: 'GitHubで編集を提案' } } : {}),
    outline: { level: [2, 3], label: 'このページの内容' },
    docFooter: { prev: '前のページ', next: '次のページ' },
    sidebarMenuLabel: '目次',
    returnToTopLabel: 'ページの先頭へ',
    darkModeSwitchLabel: '表示モード',
    lightModeSwitchTitle: 'ライトモード',
    darkModeSwitchTitle: 'ダークモード',
    skipToContentLabel: '本文へ移動',
    footer: { message: 'CMMIは、ISACAの登録商標です。', copyright: `SI受託開発のAI利用成熟度モデル · 文書版 ${version}` },
    search: {
      provider: 'local',
      options: {
        locales: { root: { translations: {
          button: { buttonText: '検索', buttonAriaLabel: '文書を検索' },
          modal: { displayDetails: '詳細を表示', resetButtonTitle: '検索をクリア', backButtonTitle: '検索を閉じる', noResultsText: '結果が見つかりません', footer: { selectText: '選択', selectKeyAriaLabel: 'Enter', navigateText: '移動', navigateUpKeyAriaLabel: '上矢印', navigateDownKeyAriaLabel: '下矢印', closeText: '閉じる', closeKeyAriaLabel: 'Escape' } }
        } } },
        miniSearch: {
          options: {
            // VitePress はこの関数をブラウザ向けに直列化する。外部参照を持たない自己完結の実装にする。
            tokenize: (text: string) => {
              const input = text.normalize('NFKC').toLowerCase()
              const terms = new Set<string>()
              // 英数字と ID（SK-1-01 など）はそのまま、日本語は 1〜2 文字の組で索引を作る。Node とブラウザの ICU 差を避ける。
              for (const match of input.matchAll(/[a-z0-9]+(?:[.\-][a-z0-9]+)*/g)) {
                terms.add(match[0])
                for (const part of match[0].split(/[.\-]/)) terms.add(part)
              }
              for (const match of input.matchAll(/[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}ー]+/gu)) {
                const chars = Array.from(match[0])
                for (let i = 0; i < chars.length; i++) {
                  terms.add(chars[i])
                  if (i + 1 < chars.length) terms.add(chars[i] + chars[i + 1])
                }
              }
              return [...terms]
            },
            processTerm: (term: string) => term.toLowerCase()
          },
          searchOptions: { prefix: true, fuzzy: false, combineWith: 'AND' }
        }
      }
    }
  }
})
