#!/usr/bin/env python3
"""Merge chapters/*.md into a syntax-highlighted PDF and EPUB."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

import markdown
from bs4 import BeautifulSoup
from ebooklib import epub
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound
from pypdf import PdfReader

from plantuml_render import GENERATED as DIAGRAM_GENERATED
from plantuml_render import render_diagrams


ROOT = Path(__file__).resolve().parent
CHAPTERS_DIR = ROOT / "chapters"
OUT_DIR = ROOT / "out"
TMP_DIR = ROOT / ".tmp"
TITLE = "meteo-service — Handbook"
AUTHOR = "Daniel Illescas Romero"

FENCE_RE = re.compile(
    r"```([a-zA-Z0-9_+-]*)\n(.*?)```",
    re.DOTALL,
)
PLACEHOLDER_TMPL = "<!--CODEBLOCK_{i}-->"

BASE_CSS = """
@page { size: A4; margin: 1.8cm; }
body {
  font-family: Helvetica, Arial, sans-serif;
  font-size: 10.5pt;
  line-height: 1.45;
  color: #1a1a1a;
}
h1 {
  font-size: 18pt;
  margin-top: 0;
  page-break-before: always;
}
h2 { font-size: 13pt; margin-top: 1.2em; }
h3 { font-size: 11pt; }
a { color: #0b57d0; text-decoration: none; }
.toc-table a { color: #0b57d0; text-decoration: underline; }
code {
  font-family: Courier, monospace;
  font-size: 8.5pt;
  background: #f4f4f4;
  padding: 0 2px;
}
div.highlight, pre.codehilite {
  background: #f7f7f7;
  border: 1px solid #ddd;
  padding: 8px;
  margin: 0.8em 0;
  font-family: Courier, monospace;
  font-size: 8pt;
  line-height: 1.35;
  white-space: pre-wrap;
}
div.highlight pre, pre.codehilite {
  background: transparent;
  border: none;
  padding: 0;
  margin: 0;
  font-family: Courier, monospace;
  font-size: 8pt;
  white-space: pre-wrap;
}
pre code { background: transparent; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 0.8em 0; font-size: 9.5pt; }
th, td { border: 1px solid #ccc; padding: 4px 6px; vertical-align: top; }
th { background: #eee; }
blockquote {
  border-left: 3px solid #999;
  margin-left: 0;
  padding-left: 10px;
  color: #333;
  font-style: italic;
}
sup { font-size: 7pt; }
.title-page {
  text-align: center;
  margin-top: 30%;
  page-break-after: always;
}
.title-page h1 {
  page-break-before: avoid;
  font-size: 22pt;
}
.toc-page {
  page-break-before: avoid;
}
.toc-page h1 {
  page-break-before: avoid;
  font-size: 18pt;
}
.toc-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1em;
}
.toc-table td {
  border: none;
  padding: 6px 0;
  font-size: 11pt;
  vertical-align: bottom;
}
.toc-table td.toc-title { width: 85%; }
.toc-table td.toc-page-num {
  width: 15%;
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.toc-leaders {
  border-bottom: 1px dotted #999;
  margin: 0 6px 2px 6px;
}
.chapter > h1:first-child { page-break-before: always; }
img.diagram {
  display: block;
  width: 16cm;
  max-width: 100%;
  height: auto;
  margin: 0.8em auto 0.4em auto;
}
p.diagram-caption {
  text-align: center;
  font-size: 9pt;
  color: #555;
  margin: 0 0 1em 0;
  font-style: italic;
}
"""


@dataclass(frozen=True)
class Chapter:
    stem: str
    title: str
    html_fragment: str


def chapter_files() -> list[Path]:
    files = sorted(CHAPTERS_DIR.glob("*.md"))
    if not files:
        raise SystemExit(f"No chapters found in {CHAPTERS_DIR}")
    return files


def highlight_code(lang: str, code: str) -> str:
    if code.endswith("\n"):
        code = code[:-1]
    if lang in {"mermaid", "text", "plain", ""}:
        escaped = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f'<pre class="codehilite"><code>{escaped}</code></pre>'
    try:
        lexer = get_lexer_by_name(lang)
    except ClassNotFound:
        try:
            lexer = guess_lexer(code)
        except ClassNotFound:
            lexer = get_lexer_by_name("text")
    formatter = HtmlFormatter(noclasses=True, style="default", nowrap=False)
    return highlight(code, lexer, formatter)


def md_to_html_fragment(md_text: str) -> str:
    """Convert markdown to HTML; fence blocks highlighted after MD so they stay intact."""
    blocks: list[str] = []

    def stash(match: re.Match[str]) -> str:
        lang = (match.group(1) or "").strip() or "text"
        blocks.append(highlight_code(lang, match.group(2)))
        return PLACEHOLDER_TMPL.format(i=len(blocks) - 1)

    stashed = FENCE_RE.sub(stash, md_text)
    html = markdown.markdown(
        stashed,
        extensions=["tables", "sane_lists", "smarty"],
        output_format="html5",
    )
    for i, block in enumerate(blocks):
        html = html.replace(PLACEHOLDER_TMPL.format(i=i), block)
    return html


def local_path_from_src(src: str) -> Path:
    if src.startswith("file:"):
        return Path(unquote(urlparse(src).path))
    return Path(src)


def resolve_diagram_images(soup: BeautifulSoup, chapter_path: Path) -> None:
    """Point <img> at absolute file:// SVG paths (Chromium PDF keeps them vector)."""
    for img in soup.find_all("img"):
        raw = (img.get("src") or "").strip()
        if not raw:
            continue
        src = Path(raw)
        if not src.is_absolute():
            src = (chapter_path.parent / src).resolve()
        if not src.is_file():
            fallback = DIAGRAM_GENERATED / Path(raw).name
            if fallback.is_file():
                src = fallback.resolve()
            else:
                svg_fallback = DIAGRAM_GENERATED / f"{Path(raw).stem}.svg"
                if svg_fallback.is_file():
                    src = svg_fallback.resolve()
                else:
                    raise SystemExit(f"Missing diagram image for {chapter_path.name}: {raw} (tried {src})")
        img["src"] = src.as_uri()
        classes = img.get("class") or []
        if isinstance(classes, str):
            classes = classes.split()
        if "diagram" not in classes:
            img["class"] = [*classes, "diagram"]
        alt = (img.get("alt") or "").strip()
        if alt and img.find_parent("figure") is None:
            parent = img.parent
            caption = soup.new_tag("p")
            caption["class"] = "diagram-caption"
            caption.string = alt
            if parent is not None and parent.name == "p" and list(parent.children) == [img]:
                parent.insert_after(caption)
            else:
                img.insert_after(caption)


def load_chapters() -> list[Chapter]:
    chapters: list[Chapter] = []
    for index, path in enumerate(chapter_files(), start=1):
        fragment = md_to_html_fragment(path.read_text(encoding="utf-8"))
        soup = BeautifulSoup(fragment, "html.parser")
        resolve_diagram_images(soup, path)
        h1 = soup.find("h1")
        bare = h1.get_text(strip=True) if h1 else path.stem
        bare = re.sub(r"^\d+\.\s*", "", bare).strip() or bare
        title = f"{index}. {bare}"
        if h1 is not None:
            h1.clear()
            h1.append(title)
            h1["id"] = path.stem
            anchor = soup.new_tag("a", attrs={"name": path.stem, "id": f"anchor-{path.stem}"})
            h1.insert_before(anchor)
        chapters.append(Chapter(stem=path.stem, title=title, html_fragment=str(soup)))
    return chapters


def toc_html(chapters: list[Chapter], page_numbers: dict[str, int] | None) -> str:
    rows: list[str] = []
    for chapter in chapters:
        page = page_numbers.get(chapter.stem) if page_numbers else None
        page_cell = str(page) if page is not None else "—"
        link = f'<a name="toc-{chapter.stem}" href="#{chapter.stem}">'
        rows.append(
            "<tr>"
            f'<td class="toc-title">{link}{chapter.title}</a>'
            '<span class="toc-leaders"></span></td>'
            f'<td class="toc-page-num">{link}{page_cell}</a></td>'
            "</tr>"
        )
    return (
        '<div class="toc-page" id="contents">'
        "<h1>Contents</h1>"
        f'<table class="toc-table">{"".join(rows)}</table>'
        "</div>"
    )


def build_document_html(chapters: list[Chapter], page_numbers: dict[str, int] | None) -> str:
    parts: list[str] = [
        '<div class="title-page">',
        f"<h1>{TITLE}</h1>",
        f"<p>{AUTHOR}</p>",
        "<p>Backend architecture notes</p>",
        "</div>",
        toc_html(chapters, page_numbers),
    ]
    for chapter in chapters:
        parts.append(f'<div class="chapter" id="chapter-{chapter.stem}">')
        parts.append(chapter.html_fragment)
        parts.append("</div>")
    body_html = "\n".join(parts)
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'/>"
        f"<title>{TITLE}</title><style>{BASE_CSS}</style></head>"
        f"<body>{body_html}</body></html>"
    )


def html_to_pdf_bytes(html: str) -> bytes:
    """Print book HTML with Chromium so text and SVG diagrams stay vector."""
    from playwright.sync_api import sync_playwright

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    html_path = TMP_DIR / "handbook-book-print.html"
    html_path.write_text(html, encoding="utf-8")
    uri = html_path.resolve().as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        )
        page = browser.new_page()
        page.goto(uri, wait_until="networkidle")
        page.emulate_media(media="print")
        pdf_bytes = page.pdf(
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        browser.close()
    return pdf_bytes


def write_pdf_bytes(data: bytes, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)


def normalize_pdf_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def find_chapter_pages(pdf_bytes: bytes, chapters: list[Chapter]) -> dict[str, int]:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages_text = [normalize_pdf_text(page.extract_text() or "") for page in reader.pages]

    start = 0
    for idx, text in enumerate(pages_text):
        if text.startswith("Contents"):
            start = idx + 1
            break
    while start < len(pages_text) and not pages_text[start]:
        start += 1

    found: dict[str, int] = {}
    search_from = start
    for chapter in chapters:
        needle = normalize_pdf_text(chapter.title)
        page_num: int | None = None
        for idx in range(search_from, len(pages_text)):
            text = pages_text[idx]
            if text.startswith(needle):
                page_num = idx + 1
                search_from = idx + 1
                break
        if page_num is None:
            for idx in range(search_from, len(pages_text)):
                if needle in pages_text[idx]:
                    page_num = idx + 1
                    search_from = idx + 1
                    break
        if page_num is None:
            raise SystemExit(f"Could not locate chapter title in PDF: {chapter.title!r}")
        found[chapter.stem] = page_num
    return found


def build_pdf_with_toc(chapters: list[Chapter], dest: Path) -> dict[str, int]:
    pass1 = html_to_pdf_bytes(build_document_html(chapters, page_numbers=None))
    pages = find_chapter_pages(pass1, chapters)
    pass2 = html_to_pdf_bytes(build_document_html(chapters, page_numbers=pages))
    pages2 = find_chapter_pages(pass2, chapters)
    if pages2 != pages:
        pass2 = html_to_pdf_bytes(build_document_html(chapters, page_numbers=pages2))
        pages = find_chapter_pages(pass2, chapters)
    else:
        pages = pages2
    clickable = make_contents_clickable(pass2, chapters)
    write_pdf_bytes(clickable, dest)
    return pages


def _contents_page_index(reader: PdfReader) -> int:
    for idx, page in enumerate(reader.pages):
        text = normalize_pdf_text(page.extract_text() or "")
        if text.startswith("Contents"):
            return idx
    raise SystemExit("Contents page not found in PDF")


def make_contents_clickable(pdf_bytes: bytes, chapters: list[Chapter]) -> bytes:
    """Widen Contents link hotspots when the printer emitted Dest annotations."""
    from pypdf import PdfWriter
    from pypdf.generic import ArrayObject, FloatObject, NameObject

    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter(clone_from=reader)
    contents_idx = _contents_page_index(reader)
    contents_page = writer.pages[contents_idx]
    page_width = float(contents_page.mediabox.width)
    left = 48.0
    right = page_width - 40.0

    annots = contents_page.get("/Annots")
    if not annots:
        # Chromium often uses /A GoTo actions instead of Dest; leave links as-is.
        return pdf_bytes

    seen_dest_pages: set[int] = set()
    widened = ArrayObject()
    for annot_ref in annots:
        annot = annot_ref.get_object()
        if annot.get("/Subtype") != "/Link":
            continue
        dest = annot.get("/Dest")
        action = annot.get("/A")
        if not dest and not action:
            continue
        dest_page = dest[0] if dest else None
        if dest_page is None and action:
            # Keep original Chromium link; still widen the clickable rect.
            dest_id = id(annot)
        else:
            dest_id = dest_page.idnum if hasattr(dest_page, "idnum") else id(dest_page)
        if dest_id in seen_dest_pages:
            continue
        seen_dest_pages.add(dest_id)

        rect = [float(x) for x in annot.get("/Rect")]
        y0, y1 = rect[1], rect[3]
        mid = (y0 + y1) / 2
        half = max(8.0, (y1 - y0) / 2 + 2.0)
        annot[NameObject("/Rect")] = ArrayObject(
            [
                FloatObject(left),
                FloatObject(mid - half),
                FloatObject(right),
                FloatObject(mid + half),
            ]
        )
        widened.append(annot_ref)

    if len(widened) == 0:
        return pdf_bytes
    if len(widened) < len(chapters):
        # Partial widen is still useful; don't fail the build.
        pass
    contents_page[NameObject("/Annots")] = widened

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def write_epub(chapters: list[Chapter], dest: Path) -> None:
    book = epub.EpubBook()
    book.set_identifier("meteo-service-handbook")
    book.set_title(TITLE)
    book.set_language("en")
    book.add_author(AUTHOR)

    pygments_css = HtmlFormatter(style="default").get_style_defs(".highlight")
    nav_css = epub.EpubItem(
        uid="style",
        file_name="style/main.css",
        media_type="text/css",
        content=(
            "body{font-family:serif;line-height:1.45;}"
            "code,pre{font-family:monospace;font-size:0.9em;}"
            "pre{background:#f7f7f7;padding:0.6em;white-space:pre-wrap;}"
            "div.highlight{background:#f7f7f7;padding:0.6em;margin:0.8em 0;}"
            "table{border-collapse:collapse;width:100%;}"
            "th,td{border:1px solid #ccc;padding:0.3em;}"
            "blockquote{border-left:3px solid #999;padding-left:0.8em;font-style:italic;}"
            "nav#toc ul{line-height:1.8;list-style:none;padding-left:0;}"
            "img.diagram{display:block;max-width:100%;height:auto;margin:0.8em auto;}"
            "p.diagram-caption{text-align:center;font-size:0.9em;color:#555;font-style:italic;}"
            f"{pygments_css}"
        ).encode("utf-8"),
    )
    book.add_item(nav_css)

    spine: list[object] = ["nav"]
    toc_items: list[epub.EpubHtml] = []
    embedded_images: set[str] = set()

    title_chapter = epub.EpubHtml(title="Title", file_name="title.xhtml", lang="en")
    title_chapter.content = (
        f"<html><head><link rel='stylesheet' href='style/main.css'/></head>"
        f"<body><h1>{TITLE}</h1><p>{AUTHOR}</p>"
        "<p>Backend architecture notes</p></body></html>"
    )
    title_chapter.add_item(nav_css)
    book.add_item(title_chapter)
    spine.append(title_chapter)

    contents_links = "".join(
        f'<li><a href="{chapter.stem}.xhtml">{chapter.title}</a></li>' for chapter in chapters
    )
    contents_chapter = epub.EpubHtml(title="Contents", file_name="contents.xhtml", lang="en")
    contents_chapter.content = (
        "<html><head><link rel='stylesheet' href='style/main.css'/></head>"
        f"<body><h1>Contents</h1><nav id='toc'><ul>{contents_links}</ul></nav></body></html>"
    )
    contents_chapter.add_item(nav_css)
    book.add_item(contents_chapter)
    spine.append(contents_chapter)
    toc_items.append(contents_chapter)

    for chapter in chapters:
        soup = BeautifulSoup(chapter.html_fragment, "html.parser")
        for img in soup.find_all("img"):
            raw = img.get("src") or ""
            src = local_path_from_src(raw)
            # EPUB readers are happier with PNG; use the sibling raster of each SVG.
            if src.suffix.lower() == ".svg":
                png = src.with_suffix(".png")
                if png.is_file():
                    src = png
            if not src.is_file():
                continue
            name = src.name
            epub_path = f"images/{name}"
            if name not in embedded_images:
                suffix = src.suffix.lower()
                media = {
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".svg": "image/svg+xml",
                }.get(suffix, "application/octet-stream")
                book.add_item(
                    epub.EpubItem(
                        uid=f"img-{name}",
                        file_name=epub_path,
                        media_type=media,
                        content=src.read_bytes(),
                    )
                )
                embedded_images.add(name)
            img["src"] = epub_path

        item = epub.EpubHtml(
            title=chapter.title,
            file_name=f"{chapter.stem}.xhtml",
            lang="en",
        )
        item.content = (
            "<html><head><link rel='stylesheet' href='style/main.css'/></head>"
            f"<body>{soup}</body></html>"
        )
        item.add_item(nav_css)
        book.add_item(item)
        spine.append(item)
        toc_items.append(item)

    book.toc = tuple(toc_items)
    book.spine = spine
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    dest.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(dest), book)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    render_diagrams(formats=("svg", "png"))
    chapters = load_chapters()
    pdf_path = OUT_DIR / "meteo-service-handbook.pdf"
    epub_path = OUT_DIR / "meteo-service-handbook.epub"
    pages = build_pdf_with_toc(chapters, pdf_path)
    write_epub(chapters, epub_path)
    print(f"Wrote {pdf_path}")
    print(f"Wrote {epub_path}")
    print("Contents page map:")
    for chapter in chapters:
        print(f"  p.{pages[chapter.stem]:>3}  {chapter.title}")


if __name__ == "__main__":
    main()
