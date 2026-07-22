# meteo-service handbook

Architecture notes, diagrams, and slides for this backend.

## How to read

1. Read `chapters/` in order (`01` → `10`).
2. Open the referenced source files while you read.
3. Use chapter 09 (Q&A) for short spoken answers; use the glossary (chapter 10) when a term is unclear.
4. Superscripts like FastAPI<sup>17</sup> point to glossary entry **17**.

## Build PDF + EPUB (long-form handbook)

Uses an isolated uv project in this folder (own `.venv`):

```bash
cd docs/handbook
uv sync
uv run playwright install chromium   # once, for PDF printing
uv run python build_docs.py
```

Outputs:

- `out/meteo-service-handbook.pdf`
- `out/meteo-service-handbook.epub`

Code examples are syntax-highlighted with Pygments. PlantUML diagrams (same sources as the slides) are embedded as **SVG** in the PDF (vector, via Chromium print) and as PNG in the EPUB.

## Slides

Short Marp slides with PlantUML diagrams.

Needs: **Java** (PlantUML), **bun** or **npx** (Marp CLI), and Playwright Chromium (for PDF):

```bash
cd docs/handbook
uv sync
uv run playwright install chromium
uv run python build_slides.py
```

Outputs:

- `out/meteo-service-slides.html` — open in a browser; fullscreen (or Marp controls) for presenting
- `out/meteo-service-slides.pdf` — shareable handout; Chromium print so text + PlantUML stay vector

Sources: `slides/deck.md`, `slides/diagrams/*.puml`. Generated SVG/PNG land in `slides/generated/`. PlantUML jar (and any local browser cache) live under `slides/tools/` (gitignored). The handbook build reuses the same diagrams.

## Fact basis

Chapters and slides describe the code under `../../src/` and `../../tests/` as implemented. Older notes in the monorepo `plan-docs/` are ideas only — do not treat them as truth if they disagree with the code.
