#!/usr/bin/env python3
"""
Erzeugt ein sdist (.tar.gz) für das Python-Projekt.

Aufruf:
  python scripts/build_sdist.py            # baut sdist für das Projekt im parent-dir und legt es in <project>/output/
  python scripts/build_sdist.py --project-dir /pfad/zum/projekt --outdir /pfad/zu/output

Voraussetzung:
  pip install build
Das Skript fällt zurück auf "python -m build --sdist", falls die programmgesteuerte API nicht verfügbar ist.
"""

from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path
from enum import Enum
from typing import List, Union
from package_list import distribution_packages, integration_test_packages


class Package(Enum):
    All = 'all'
    Distribution = 'distribution'
    Test = 'test'

    def __call__(self):
        return self.value


class PackageType(Enum):
    Name = 0
    SetupDirPath = 1
    InitDirPath = 2

    def __call__(self):
        return self.value


def _compute_package_list(package_type: Package, type: PackageType) -> Union[List[str], List[Path]]:
    if package_type == Package.Distribution:
        packages = distribution_packages
    elif package_type == Package.All:
        packages = distribution_packages
        packages.extend(integration_test_packages)
    else:
        packages = integration_test_packages

    if type == PackageType.Name:
        return list(map(lambda entry: entry['name'], packages))
    elif type == PackageType.SetupDirPath:
        return list(map(lambda entry: entry['dir'], packages))
    else:
        # directory path to __init__.py package file
        return list(map(lambda entry: Path(entry['dir'], entry['namespace']), packages))


def _package_from_string(value: str) -> Package:
    if value == Package.All():
        return Package.All
    elif value == Package.Test():
        return Package.Test
    else:
        return Package.Distribution


def tag_version(packages: Package, version: str):
    package_list = _compute_package_list(packages, PackageType.InitDirPath)
    for p in package_list:
        path = Path(p, '__init__.py')
        licence_path = Path(Path(__file__).parent, '../LICENSE')
        with path.open('a+') as init_file:
            init_file.write('__license__ = """\n')
            with licence_path.open('r') as license_file:
                for line in license_file:
                    init_file.write(line)
            init_file.write('"""\n')
            init_file.write(f'__version__ = \'{version}\'\n')


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
    parser.add_argument('--packages', choices=[Package.Distribution(), Package.Test(), Package.All()], help='packages that should be processed')
    parser.add_argument('--tag-version', type=str, help='Version to write into "__init__.py" package files. This option is used during CICD-build')

    args = parser.parse_args(argv)

    project_dir = args.project_dir.resolve()
    outdir = (args.outdir.resolve() if args.outdir else project_dir / "output")
    packages = Package.All if args.packages is None else _package_from_string(args.packages)

    if args.tag_version is not None:
        tag_version(packages, args.tag_version)
        return 0

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
