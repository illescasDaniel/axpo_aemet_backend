#!/usr/bin/env python3
"""Render PlantUML diagrams and build Marp slides (HTML + vector PDF)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from plantuml_render import render_diagrams


ROOT = Path(__file__).resolve().parent
SLIDES = ROOT / "slides"
OUT = ROOT / "out"
TMP = ROOT / ".tmp"
DECK = SLIDES / "deck.md"

# Chromium print CSS: keep code readable (override theme light-dark()) and paginate bare sections.
PRINT_CSS = """
:root, html, body, section { color-scheme: only light !important; }
@media print {
  section {
    page-break-after: always;
    break-after: page;
  }
  section:last-of-type {
    page-break-after: auto;
    break-after: auto;
  }
  pre, pre *, code, code *, .hljs, .hljs * {
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }
  pre, pre code, .hljs {
    background: #f4f6f8 !important;
    color: #1a1a1a !important;
  }
  .hljs-keyword, .hljs-selector-tag { color: #cf222e !important; }
  .hljs-string, .hljs-attr, .hljs-attribute { color: #0a3069 !important; }
  .hljs-comment { color: #6e7781 !important; }
  .hljs-title, .hljs-section, .hljs-title.function_ { color: #8250df !important; }
  .hljs-built_in, .hljs-type { color: #953800 !important; }
  .hljs-literal, .hljs-number { color: #0550ae !important; }
  .hljs-meta, .hljs-meta .hljs-keyword { color: #1f2328 !important; }
}
"""


def run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(cmd))
    merged = {**os.environ, **(env or {})}
    subprocess.run(cmd, cwd=cwd, check=True, env=merged)


def find_marp() -> list[str]:
    bun = shutil.which("bun")
    if bun:
        return [bun, "x", "--bun", "@marp-team/marp-cli@4.1.2"]
    npx = shutil.which("npx")
    if npx:
        return [npx, "--yes", "@marp-team/marp-cli@4.1.2"]
    raise SystemExit("Need bun or npx to run @marp-team/marp-cli")


def html_to_pdf_playwright(html_path: Path, pdf_path: Path) -> None:
    """Print bare Marp HTML via Chromium so text and SVGs stay vector (not screenshots)."""
    from playwright.sync_api import sync_playwright

    uri = html_path.resolve().as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        )
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(uri, wait_until="networkidle")
        page.add_style_tag(content=PRINT_CSS)
        page.emulate_media(media="print")
        # 16:9 at 96dpi — matches Marp `size: 16:9` viewport.
        page.pdf(
            path=str(pdf_path),
            width="13.333in",
            height="7.5in",
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        browser.close()
    print(f"Wrote vector PDF via Chromium print → {pdf_path}")


def build_marp() -> None:
    if not DECK.is_file():
        raise SystemExit(f"Missing deck: {DECK}")
    OUT.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    marp = find_marp()
    # Write HTML beside generated/ so relative diagram paths resolve.
    html_local = SLIDES / "meteo-service-slides.html"
    # Must live under slides/ so relative `generated/*.svg` paths resolve for print.
    html_print = SLIDES / "meteo-service-slides-print.html"
    html_out = OUT / "meteo-service-slides.html"
    pdf_out = OUT / "meteo-service-slides.pdf"
    env = {
        "TMPDIR": str(TMP.resolve()),
        "TMP": str(TMP.resolve()),
        "TEMP": str(TMP.resolve()),
    }
    # Bespoke HTML for presenting in a browser.
    run([*marp, str(DECK), "--html", "-o", str(html_local), "--allow-local-files"], env=env)
    shutil.copy2(html_local, html_out)
    # Bare template prints cleanly (no SVG foreignObject slides) → sharp vector PDF.
    run(
        [
            *marp,
            str(DECK),
            "--html",
            "--template",
            "bare",
            "-o",
            str(html_print),
            "--allow-local-files",
        ],
        env=env,
    )
    print("Printing vector PDF with Playwright Chromium…")
    html_to_pdf_playwright(html_print, pdf_out)
    html_print.unlink(missing_ok=True)
    if not pdf_out.is_file() or pdf_out.stat().st_size < 1000:
        raise SystemExit(f"PDF was not written correctly: {pdf_out}")
    print(f"Wrote {html_out}")
    print(f"Wrote {pdf_out}")


def main() -> None:
    render_diagrams(formats=("svg", "png"))
    build_marp()


if __name__ == "__main__":
    main()
