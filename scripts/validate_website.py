"""Check the static website's links, assets and download archives."""

from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from zipfile import ZipFile
import hashlib
import json


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "docs"


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.refs = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        self.refs.extend(attrs[key] for key in ("href", "src", "poster") if attrs.get(key))


pages = {}
for path in DIST.rglob("*.html"):
    page = Page()
    page.feed(path.read_text())
    duplicates = [key for key, count in Counter(page.ids).items() if count > 1]
    assert not duplicates, f"Duplicate IDs in {path}: {duplicates}"
    pages[path] = page

reference_count = 0
for path, page in pages.items():
    for ref in page.refs:
        url = urlsplit(ref)
        if url.scheme or url.netloc:
            continue
        assert not url.path.startswith("/"), f"Root-relative link will break a project site: {ref}"
        destination = path.parent / unquote(url.path) if url.path else path
        assert destination.exists(), f"Missing file: {path}: {ref}"
        if url.fragment and destination in pages:
            assert url.fragment in pages[destination].ids, f"Missing anchor: {ref}"
        reference_count += 1

for path in DIST.rglob("*"):
    if path.is_file():
        assert path.stat().st_size < 100 * 1024**2, f"Asset exceeds GitHub's file limit: {path}"

for path in (DIST / "downloads").glob("*.zip"):
    with ZipFile(path) as archive:
        assert archive.testzip() is None, f"Invalid ZIP: {path}"

with ZipFile(DIST / "downloads/zoomer3d-print-files.zip") as archive:
    assert archive.read("PRINTING.html") == (DIST / "downloads/PRINTING.html").read_bytes()
    for path in (DIST / "downloads/assembly").glob("*.png"):
        assert archive.read("assembly/" + path.name) == path.read_bytes()

manifest = json.loads((ROOT / "website-source-manifest.json").read_text())
for relative, expected in manifest["unchanged_files"].items():
    actual = hashlib.sha256((DIST / relative).read_bytes()).hexdigest()
    assert actual == expected, f"Original asset changed: {relative}"

index = (DIST / "index.html").read_text()
assert "chatgpt.site" not in index, "Export still points to the original host"
assert not (DIST / ".openai").exists(), "Hosting metadata must stay outside the public bundle"
print(f"PASS: {len(pages)} HTML pages, {reference_count} local links, {len(manifest['unchanged_files'])} unchanged source files, ZIP integrity")
