#!/usr/bin/env python3
"""生成した公開用HTMLを、ネットワークなしで検査する。

ページ数が docs/ の Markdown と一致すること、ページ内リンク・アセット・アンカーがすべてサイト内に存在すること、
lang 属性が ja-JP であることを確認する。Python標準ライブラリのみを使用する。
"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SITE = DOCS / ".vitepress" / "dist"


class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.refs = []
        self.lang = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "html":
            self.lang = attrs.get("lang")
        for a in ("href", "src"):
            if a in attrs:
                self.refs.append(attrs[a])


def main():
    first = (SITE / "index.html").read_text(encoding="utf-8")
    base = re.search(r'href="([^"]*)assets/favicon\.svg"', first).group(1)
    origin = "https://site.test"
    parsers = {}
    for path in SITE.rglob("*.html"):
        parser = Parser()
        parser.feed(path.read_text(encoding="utf-8"))
        parsers[path] = parser
        assert parser.lang == "ja-JP", f"lang 属性がありません: {path}"
    count = 0
    for path, parser in parsers.items():
        current = origin + base + path.relative_to(SITE).as_posix()
        for ref in parser.refs:
            if ref.startswith(("mailto:", "tel:", "data:")):
                continue
            url = urlparse(urljoin(current, ref))
            if url.netloc != "site.test":
                continue
            decoded = unquote(url.path)
            assert decoded.startswith(base), f"{path}: リンクがサイトのベースパス外を指しています: {ref}"
            relative = decoded[len(base):]
            target = SITE / relative
            if relative.endswith("/") or target.is_dir():
                target = target / "index.html"
            elif not target.suffix:
                target = target.with_suffix(".html")
            assert target.is_file(), f"{path.relative_to(SITE)}: リンク先がありません: {ref}"
            if url.fragment and target.suffix == ".html":
                assert unquote(url.fragment) in parsers[target].ids, f"{path.relative_to(SITE)}: アンカーがありません: {ref}"
            count += 1
    sources = [p for p in DOCS.rglob("*.md") if ".vitepress" not in p.parts and "public" not in p.parts]
    expected = len(sources) + 1  # 404.html
    assert len(parsers) == expected, f"ページ数が一致しません: 期待 {expected}（Markdown {len(sources)} + 404）、実際 {len(parsers)}"
    print(f"HTML OK: {len(parsers)} ページ（404 を含む）、サイト内リンク・アセット・アンカー {count} 件、base={base}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
