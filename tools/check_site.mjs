// 生成した公開用HTMLを、静的検査（tools/check_html.py）とブラウザ（Playwright）で確認する。
import { chromium, expect } from '@playwright/test';
import { createServer } from 'node:http';
import { readFile, stat, mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const validation = spawnSync('python3', ['tools/check_html.py'], { stdio: 'inherit' });
if (validation.status !== 0) process.exit(validation.status ?? 1);

const directory = path.resolve('docs/.vitepress/dist');
const homeHtml = await readFile(path.join(directory, 'index.html'), 'utf8');
const base = homeHtml.match(/href="([^"]*)assets\/favicon.svg"/)[1];
const mime = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.xml': 'application/xml' };
const server = createServer(async (req, res) => {
  try {
    const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    if (!pathname.startsWith(base)) { res.writeHead(404); res.end(); return; }
    let file = path.resolve(directory, pathname.slice(base.length));
    if (!file.startsWith(directory + path.sep) && file !== directory) { res.writeHead(404); res.end(); return; }
    if (pathname.endsWith('/')) file = path.join(file, 'index.html');
    const info = await stat(file);
    if (!info.isFile()) throw Error('Not a file');
    res.writeHead(200, { 'Content-Type': mime[path.extname(file)] || 'application/octet-stream' });
    res.end(await readFile(file));
  } catch { res.writeHead(404); res.end('Not found'); }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
const url = origin + base;
const results = { base, checks: [] };
let browser;
try {
  browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH, args: JSON.parse(process.env.PLAYWRIGHT_CHROMIUM_ARGS || '["--no-sandbox","--disable-dev-shm-usage"]') } : {}) });
  results.browser = browser.version();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
  const errors = []; const networkErrors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('response', response => { if (response.url().startsWith(origin) && response.status() >= 400) networkErrors.push(response.url()); });

  await page.goto(url);
  await expect(page.locator('h1')).toHaveText('SI受託開発のAI利用成熟度モデル');
  await expect(page.locator('.VPNavBarMenu').getByRole('link', { name: '成熟度モデル', exact: true })).toBeVisible();
  await expect(page.locator('.VPSidebar').getByRole('link', { name: '軸別チェックリスト', exact: true })).toBeVisible();
  await mkdir('artifacts', { recursive: true });
  await page.screenshot({ path: 'artifacts/home-desktop.png', fullPage: true });
  results.checks.push('desktop home, navigation and sidebar');

  // 深いリンク：見出しアンカーへ移動し、再読み込みしても同じ位置が表示されること
  await page.goto(url + 'model/levels.html');
  await expect(page.locator('h1')).toHaveText('レベル別ビュー');
  const anchors = await page.locator('h2 a.header-anchor').evaluateAll(list => list.map(a => a.getAttribute('href')));
  if (anchors.length < 5) throw Error(`Expected level headings, got ${anchors.length}`);
  await page.goto(url + 'model/levels.html' + anchors[1]); await page.reload();
  await expect(page.locator(`[id="${decodeURIComponent(anchors[1].slice(1))}"]`)).toBeVisible();
  await page.goto(url + 'checklist/skill.html');
  await expect(page.locator('h1')).toHaveText('Agent Skill');
  await expect(page.locator('.vp-doc table').first()).toBeVisible();
  await expect(page.locator('.vp-doc code', { hasText: 'SK-1-01' }).first()).toBeVisible();
  results.checks.push('deep links, anchor navigation, refresh and generated checklist tables');

  // 読む順路：はじめに → 成熟度モデル。サイドバーの最初の節が「はじめに」で、前後ページのリンクが順路に従うこと
  await page.goto(url + 'guide/ai-development.html');
  await expect(page.locator('h1')).toHaveText('AIを含む開発とは');
  await expect(page.locator('.VPSidebarItem.level-0 .text').first()).toHaveText('ホーム');
  await expect(page.locator('.VPSidebarItem.level-0').nth(1).locator('h2.text')).toHaveText('はじめに');
  await expect(page.locator('.pager-link.next .title')).toHaveText('開発の基本用語');
  await page.goto(url + 'guide/terms.html#契約と収支'); await page.reload();
  await expect(page.locator('[id="契約と収支"]')).toBeVisible();
  await page.goto(url + 'guide/overview.html');
  await expect(page.locator('.pager-link.next .title')).toHaveText('成熟度モデル');
  results.checks.push('reading order: guide section first, prev/next follows it, glossary anchors');

  await page.goto(url + 'process/');
  await expect(page.locator('.VPSidebar').getByRole('link', { name: '要件整理', exact: true })).toBeVisible();
  await page.locator('.VPSidebar').getByRole('link', { name: '要件整理', exact: true }).click();
  await expect(page.locator('h1')).toHaveText('要件整理');
  await expect(page.locator('.pager-link.prev')).toBeVisible();
  await expect(page.locator('.pager-link.next')).toBeVisible();
  results.checks.push('sidebar navigation and prev/next pager');

  for (const [query, target] of [['SK-1-01', 'checklist/skill'], ['自動化段階', 'automation'], ['算定式', 'effect/formula']]) {
    await page.locator('button.DocSearch-Button').click();
    const input = page.locator('#localsearch-input');
    await expect(input).toBeVisible(); await input.fill(query);
    const result = page.locator(`.VPLocalSearchBox a[href*="${target}"]`).first();
    try { await expect(result).toBeVisible({ timeout: 15000 }); } catch (e) { console.error('Search diagnostics', query, await page.locator('.VPLocalSearchBox').innerText(), errors, networkErrors); await page.screenshot({ path: 'artifacts/search-failure.png' }); throw e; }
    await result.click();
    await expect(input).toBeHidden();
    results.checks.push(`search ${query}`);
  }
  await page.locator('button.DocSearch-Button').click();
  await page.locator('#localsearch-input').fill('存在しない検索語zzzzzzzz');
  await expect(page.getByText('結果が見つかりません')).toBeVisible();
  await page.keyboard.press('Escape');
  results.checks.push('empty search and keyboard close');

  await page.goto(url + 'model/axes.html');
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.screenshot({ path: 'artifacts/axes-dark.png', fullPage: true });
  results.checks.push('dark theme');

  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ colorScheme: 'light' });
  await page.goto(url + 'checklist/environment.html');
  await expect(page.locator('h1')).toHaveText('環境との接続');
  await page.getByRole('button', { name: '目次', exact: true }).click();
  await expect(page.locator('.VPSidebar')).toBeVisible();
  await page.locator('.VPBackdrop').click({ position: { x: 370, y: 300 } });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  if (overflow) throw Error('Horizontal page overflow on mobile');
  await page.screenshot({ path: 'artifacts/checklist-mobile.png', fullPage: true });
  results.checks.push('mobile sidebar and no page overflow');

  await page.locator('button.DocSearch-Button').click();
  await page.locator('#localsearch-input').fill('SK-1-01');
  await expect(page.locator('.VPLocalSearchBox a[href*="checklist/skill"]').first()).toBeVisible();
  await page.keyboard.press('Escape');
  results.checks.push('mobile search');

  if (errors.length || networkErrors.length) throw Error(JSON.stringify({ errors, networkErrors }));
  results.checks.push('no browser exceptions or failed local requests');
  await writeFile('artifacts/site-check-results.json', JSON.stringify(results, null, 2) + '\n');
  console.log(`Browser OK: ${results.checks.length} checks; base=${base}`);
} finally {
  if (browser) await browser.close();
  await new Promise(resolve => server.close(resolve));
}
