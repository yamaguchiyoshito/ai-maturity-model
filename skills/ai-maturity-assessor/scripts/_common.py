"""共通処理。Python標準ライブラリのみを使用する。"""
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
CRITERIA_PATH = SKILL_ROOT / "references" / "criteria.json"
SKIP_DIRS = {".git", "node_modules", "vendor", "dist", "build", "target", ".venv", "venv",
             "__pycache__", ".next", ".gradle", ".idea", "maturity-out"}
MAX_FILE_BYTES = 1_000_000
MAX_CANDIDATES = 5


def load_criteria():
    data = json.loads(CRITERIA_PATH.read_text(encoding="utf-8"))
    sha = hashlib.sha256(CRITERIA_PATH.read_bytes()).hexdigest()
    return data, sha


def glob_to_regex(pattern):
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
        elif pattern.startswith("**", i):
            out += ".*"
            i += 2
        elif pattern[i] == "*":
            out += "[^/]*"
            i += 1
        elif pattern[i] == "?":
            out += "[^/]"
            i += 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return re.compile("^" + out + "$", re.IGNORECASE)


def list_files(repo):
    repo = Path(repo)
    files = []
    for root, dirs, names in os.walk(repo):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for n in sorted(names):
            files.append((Path(root) / n).relative_to(repo).as_posix())
    return files


def match_files(files, patterns):
    regs = [glob_to_regex(p) for p in patterns]
    return [f for f in files if any(r.match(f) for r in regs)]


def read_lines(repo, rel):
    p = Path(repo) / rel
    try:
        if p.stat().st_size > MAX_FILE_BYTES:
            return []
        return p.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []


def git(repo, *args):
    try:
        r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=60)
        return r.stdout if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def is_git_repo(repo):
    out = git(repo, "rev-parse", "--is-inside-work-tree")
    return bool(out and out.strip() == "true")
