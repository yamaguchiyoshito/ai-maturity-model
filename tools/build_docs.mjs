// 正本との一致検査、Skillの自己テスト、静的サイト生成を順に実行する。どれかが失敗したら止める。
import { spawnSync } from 'node:child_process';
for (const [command, args] of [
  ['python3', ['tools/build_pages.py', '--check']],
  ['python3', ['tools/selftest.py']],
  ['node', ['node_modules/vitepress/bin/vitepress.js', 'build', 'docs']]
]) {
  const result = spawnSync(command, args, { stdio: 'inherit', env: process.env });
  if (result.status !== 0) process.exit(result.status ?? 1);
}
