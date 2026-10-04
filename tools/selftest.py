#!/usr/bin/env python3
"""Skillの自己テスト。ダミーのリポジトリを作り、3段のパイプラインを通す。

使い方:
  python tools/selftest.py                 テストのみ（失敗時 exit 1）
  python tools/selftest.py --write-sample  docs/assess/sample-report.md も更新する

確認すること:
  1. 収集→解決→検証→算定が通ること
  2. 未解決の下書きが検証で不合格になること
  3. 証拠の捏造、スクリプト判定の変更が検証で不合格になること
"""
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "ai-maturity-assessor" / "scripts"
SAMPLE = ROOT / "docs" / "assess" / "sample-report.md"

FILES = {
    ".claude/skills/review/SKILL.md": "---\nname: review\ndescription: コードレビューを行う\n---\n# review\n管理責任者: team-a\n",
    ".claude/skills/review/scripts/validate_output.py": "print(1)\n",
    ".claude/settings.json": '{"permissions":{"allow":["Bash(npm test)"],"deny":["Bash(rm -rf *)"]}}\n',
    "README.md": "# sample\n## セットアップ\nnpm install && npm test\nSkillの使い方は .claude/skills を参照\n",
    "CLAUDE.md": "# CLAUDE\n- テスト: npm test\n- 設計書は docs/ を参照\n- MR作成は gh を使う\n",
    ".github/workflows/ci.yml": 'on:\n  pull_request:\n  schedule:\n    - cron: "0 0 * * *"\njobs:\n  t:\n    steps:\n      - uses: anthropics/claude-code-action@v1\n      - uses: actions/upload-artifact@v4\n',
    "package.json": '{"name":"sample"}\n', "package-lock.json": "{}\n",
    "tests/a.test.js": "test('a',()=>{})\n", "docs/adr/0001.md": "# ADR 1\n",
}


def run(script, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, text=True)


def sh(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def main():
    fails = []
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "sample-pj"
        for rel, text in FILES.items():
            p = repo / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        sh(repo, "init", "-q")
        sh(repo, "add", "-A")
        sh(repo, "-c", "user.email=a@example.com", "-c", "user.name=a", "commit", "-qm", "init")
        (repo / "README.md").write_text(FILES["README.md"] + "\n", encoding="utf-8")
        skill = repo / ".claude/skills/review/SKILL.md"
        skill.write_text(FILES[".claude/skills/review/SKILL.md"] + "\n", encoding="utf-8")
        sh(repo, "-c", "user.email=b@example.com", "-c", "user.name=b", "commit", "-qam", "second")
        out = repo / "maturity-out"

        if run("collect_evidence.py", str(repo)).returncode != 0:
            fails.append("収集が失敗した")
        draft = json.loads((out / "findings.draft.json").read_text(encoding="utf-8"))

        (out / "findings.json").write_text(json.dumps(draft, ensure_ascii=False), encoding="utf-8")
        if run("validate_findings.py", str(repo)).returncode == 0:
            fails.append("未解決の下書きが合格した")

        good = copy.deepcopy(draft)
        for f in good["findings"]:
            if f["status"] == "candidate":
                f["status"] = "met"
            elif f["status"] == "unresolved":
                if f["source"] == "repo":
                    f["status"], f["searched"] = "not_met", ["リポジトリ全体"]
                else:
                    f["status"] = "hearing"
        (out / "findings.json").write_text(json.dumps(good, ensure_ascii=False), encoding="utf-8")
        if run("validate_findings.py", str(repo)).returncode != 0:
            fails.append("正しい判定が不合格になった")
        r = run("score_and_render.py", str(repo), "--project", "サンプルPJ")
        if r.returncode != 0:
            fails.append("算定が失敗した")
        report = (out / "maturity-report.md").read_text(encoding="utf-8") if (out / "maturity-report.md").exists() else ""
        score = json.loads((out / "score.json").read_text(encoding="utf-8")) if (out / "score.json").exists() else {}
        if score.get("automation_stage", {}).get("confirmed") != "A3" or score.get("control_deficit") != "確定":
            fails.append(f"算定結果が期待と異なる: {score.get('automation_stage')} / {score.get('control_deficit')}")

        def tamper(fn, label):
            bad = copy.deepcopy(good)
            fn({f["id"]: f for f in bad["findings"]})
            (out / "findings.json").write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
            if run("validate_findings.py", str(repo)).returncode == 0:
                fails.append(f"{label}が合格した")

        tamper(lambda m: m["EST-2-01"].update(status="met", evidence=[{"path": "docs/none.md", "line": 1, "excerpt": "x"}]), "実在しない証拠")
        tamper(lambda m: m["SK-1-02"]["evidence"][0].update(excerpt="捏造した抜粋"), "抜粋の捏造")
        tamper(lambda m: m["SK-2-03"].update(status="not_met", searched=["x"]), "スクリプト判定の変更")
        tamper(lambda m: m["EST-2-02"].update(status="not_met", searched=["x"]), "リポジトリ外基準の未充足判定")

        if "--write-sample" in sys.argv and not fails:
            body = report.replace(str(repo), "sample-pj")
            head = "---\ntitle: 報告書の例\nnav_order: 3\n---\n\n<!-- tools/selftest.py --write-sample が生成します。 -->\n\n"
            SAMPLE.write_text(head + body, encoding="utf-8")
            print(f"[OK] {SAMPLE.relative_to(ROOT)} を更新しました")

    if fails:
        print(f"[NG] {len(fails)} 件")
        for f in fails:
            print("  - " + f)
        return 1
    print("[OK] 自己テスト 7 項目に合格しました")
    return 0


if __name__ == "__main__":
    sys.exit(main())
