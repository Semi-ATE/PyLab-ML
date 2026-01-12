#!/usr/bin/env python3
"""
Erzeugt ein sdist (.tar.gz) für das Python-Projekt.

Aufruf:
  python scripts/build_sdist.py            # baut sdist für das Projekt im parent-dir und legt es in <project>/dist/
  python scripts/build_sdist.py --project-dir /pfad/zum/projekt --outdir /pfad/zu/dist

Voraussetzung:
  pip install build
Das Skript fällt zurück auf "python -m build --sdist", falls die programmgesteuerte API nicht verfügbar ist.
"""

from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path


def build_with_api(project_dir: Path, outdir: Path) -> int:
    try:
        # Programmierschnittstelle des 'build'-Pakets
        from build import ProjectBuilder
    except Exception:
        return 2  # signalisiert, dass API nicht verfügbar ist

    project_dir = project_dir.resolve()
    outdir = outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"Building sdist (using build.ProjectBuilder) for {project_dir} -> {outdir}")
    try:
        builder = ProjectBuilder(str(project_dir))
        # builder.build(distribution, outdir) unterstützt 'sdist' und 'wheel'
        created = builder.build('output', str(outdir))
        print(f"Erzeugt: {created}")
        return 0
    except Exception as exc:
        print("Fehler beim Erzeugen des sdist mit API:", exc, file=sys.stderr)
        return 3


def build_with_subprocess(project_dir: Path, outdir: Path) -> int:
    project_dir = project_dir.resolve()
    outdir = outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    cmd = [sys.executable, "-m", "build", "--sdist", "--outdir", str(outdir)]
    print(f"Building sdist (subprocess) in {project_dir} -> {outdir}")
    try:
        result = subprocess.run(cmd, cwd=str(project_dir))
        return result.returncode
    except FileNotFoundError as exc:
        print("Fehler: 'build' Modul/Paket nicht installiert und 'python -m build' nicht verfügbar.", file=sys.stderr)
        print("Bitte installiere das build-Paket: pip install build", file=sys.stderr)
        return 4
    except Exception as exc:
        print("Unerwarteter Fehler beim Aufruf von 'python -m build':", exc, file=sys.stderr)
        return 5


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Erzeuge sdist für ein Python-Projekt.")
    parser.add_argument("--project-dir", "-p", type=Path, default=Path.cwd().parent,
                        help="Pfad zum Projektordner (Standard: parent von diesem Skript / aktuelles working dir parent).")
    parser.add_argument("--outdir", "-o", type=Path, default=None,
                        help="Ausgabeverzeichnis für die distribution (Standard: <project>/dist).")
    args = parser.parse_args(argv)

    project_dir = args.project_dir.resolve()
    outdir = (args.outdir.resolve() if args.outdir else project_dir / "output")

    # Versuch 1: programmgesteuerte API
    rc = build_with_api(project_dir, outdir)
    if rc == 0:
        return 0

    # Versuch 2: Kommandozeilen-Aufruf 'python -m build --sdist'
    rc2 = build_with_subprocess(project_dir, outdir)
    if rc2 == 0:
        return 0

    # Fallback: wenn setup.py existiert, versuche legacy-Aufruf
    setup_py = project_dir / "setup.py"
    if setup_py.exists():
        print("Versuche legacy 'python setup.py sdist' als letzte Option.")
        try:
            rc3 = subprocess.run([sys.executable, "setup.py", "sdist"], cwd=str(project_dir)).returncode
            return rc3
        except Exception as exc:
            print("Fehler beim legacy-Aufruf:", exc, file=sys.stderr)
            return 6

    print("Erzeugung des sdist fehlgeschlagen.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
