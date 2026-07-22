"""Shared PlantUML jar download + render helpers for slides and the handbook book."""

from __future__ import annotations

import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIAGRAMS = ROOT / "slides" / "diagrams"
GENERATED = ROOT / "slides" / "generated"
TOOLS = ROOT / "slides" / "tools"

PLANTUML_VERSION = "1.2024.8"
PLANTUML_JAR_URL = (
    f"https://github.com/plantuml/plantuml/releases/download/v{PLANTUML_VERSION}/"
    f"plantuml-{PLANTUML_VERSION}.jar"
)
PLANTUML_JAR = TOOLS / f"plantuml-{PLANTUML_VERSION}.jar"


def run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(cmd))
    merged = {**os.environ, **(env or {})}
    subprocess.run(cmd, cwd=cwd, check=True, env=merged)


def ensure_plantuml_jar() -> Path:
    TOOLS.mkdir(parents=True, exist_ok=True)
    if PLANTUML_JAR.is_file() and PLANTUML_JAR.stat().st_size > 1_000_000:
        return PLANTUML_JAR
    print(f"Downloading PlantUML {PLANTUML_VERSION}…")
    urllib.request.urlretrieve(PLANTUML_JAR_URL, PLANTUML_JAR)  # noqa: S310
    if not PLANTUML_JAR.is_file() or PLANTUML_JAR.stat().st_size < 1_000_000:
        raise SystemExit(f"Failed to download PlantUML jar to {PLANTUML_JAR}")
    return PLANTUML_JAR


def render_diagrams(*, formats: tuple[str, ...] = ("svg", "png")) -> list[Path]:
    """Render slides/diagrams/*.puml into slides/generated/ (svg for Marp, png for xhtml2pdf)."""
    jar = ensure_plantuml_jar()
    java = shutil.which("java")
    if not java:
        raise SystemExit("java is required to render PlantUML diagrams")
    GENERATED.mkdir(parents=True, exist_ok=True)
    sources = sorted(DIAGRAMS.glob("*.puml"))
    if not sources:
        raise SystemExit(f"No .puml files in {DIAGRAMS}")
    for fmt in formats:
        run(
            [
                java,
                "-Djava.awt.headless=true",
                "-jar",
                str(jar),
                f"-t{fmt}",
                "-o",
                str(GENERATED.resolve()),
                *[str(p.resolve()) for p in sources],
            ]
        )
    outputs: list[Path] = []
    for fmt in formats:
        found = list(GENERATED.glob(f"*.{fmt}"))
        if len(found) < len(sources):
            raise SystemExit(f"Expected {len(sources)} .{fmt} files, found {len(found)} in {GENERATED}")
        outputs.extend(found)
    print(f"Rendered {len(sources)} diagram(s) × {list(formats)} → {GENERATED}")
    return outputs
