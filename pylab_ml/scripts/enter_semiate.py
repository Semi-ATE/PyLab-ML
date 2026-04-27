#!/usr/bin/env python3
"""
semi-ate

Usage:
  semi-ate project version [-w name] 

"""
import shlex
from pathlib import Path
import yaml
import argparse
import os
import subprocess
import sys
import platform
from typing import Optional


class SemiAte:
    def __init__(self, args):
        optionfile = str(Path(__file__).with_suffix('')) + '.yaml'
        if not os.path.isfile(optionfile) or args.edit:                 # search for the optionfile, if not found, create it
            while True:
                path = input('no path to projects defined, please enter the path: ')
                if path != "" and os.path.isdir(path):
                    break
                print(f"path {path} not valid")
            with open(optionfile, 'w', encoding='utf-8') as file:
                yaml.safe_dump(path, file, sort_keys=False, allow_unicode=True)
        else:
            with open(optionfile, 'r', encoding='utf-8') as file:
                path = yaml.safe_load(file)
                
        self._validate_version(args.version)
        
        if not os.path.isdir(os.path.join(path, args.project)):
            print(f'project {args.project} not found')
            return
        path = os.path.join(path, args.project)
        if not os.path.isdir(os.path.join(path, "harness")):
            os.makedirs(os.path.join(path, "harness"))
        project_file = os.path.join(path, "harness", "project_info.yaml")
        
        if  os.path.isfile(project_file):
            with open(project_file, 'r', encoding='utf-8') as file:
                project_info = yaml.safe_load(file)
        else:
            project_info = {"PROJECT": args.project,
                            "VERSION": args.version,
                            "USER": args.who}
            
        project_info["PROJECT"] = args.project
        project_info["VERSION"] = args.version
        project_info["USER"] = args.who
        
        with open(project_file, 'w', encoding='utf-8') as file:
            yaml.safe_dump(project_info, file, sort_keys=False, allow_unicode=True)
            
        print(project_info)

        # self.start_spyder_in_env("", args.project.upper(), args.version.upper(), args.who)


    def _validate_version(self, v: str) -> str:
        if len(v) != 4 or not v.isdigit():
            print("The version must be a 4-digit number, e.g. 0001")
            exit()
        return v


    def start_spyder_in_env(self, env_name: str, project: str, version: str, user: Optional[str] = None) -> int:
        """
        Start Spyder in the given conda env. Return exit code.
        Cross-platform:
          - On Windows: use `conda run -n <env> spyder` (and pass env vars via env)
          - On Unix: try to source conda.sh and `conda activate`, export vars and exec spyder.
                  if that fails, fallback to `conda run`.
        """
        env = os.environ.copy()
        env["PROJECT"] = project
        env["VERSION"] = version
        if user:
            env["USER"] = user

        system = platform.system().lower()
        # Try to find conda base
        conda_base = None
        try:
            p = subprocess.run(["conda", "info", "--base"], capture_output=True, text=True, check=True, env=env)
            conda_base = p.stdout.strip()
        except Exception:
            conda_base = None

        # Windows: use conda run (works with modern conda)
        if system.startswith("win"):
            try:
                cmd = ["conda", "run", "-n", env_name, "--no-capture-output", "spyder"]
                return subprocess.call(cmd, env=env)
            except FileNotFoundError:
                print("Fehler: 'conda' nicht gefunden. Stelle sicher, dass Anaconda/Miniconda installiert und in PATH ist.", file=sys.stderr)
                return 3
            except Exception as e:
                print(f"Fehler beim Starten von Spyder (Windows): {e}", file=sys.stderr)
                return 4

        # Unix-like
        if conda_base:
            conda_sh = os.path.join(conda_base, "etc", "profile.d", "conda.sh")
            if os.path.exists(conda_sh):
                # Build a bash command that sources conda.sh, activates env, exports vars, and exec spyder
                parts = [
                    f". {conda_sh}",
                    f"conda activate {env_name}",
                    f"export PROJECT='{project}'",
                    f"export VERSION='{version}'",
                ]
                if user:
                    parts.append(f"export USER='{user}'")
                parts.append("exec spyder")
                bash_cmd = " && ".join(parts)
                try:
                    return subprocess.call(["bash", "-lc", bash_cmd], env=env)
                except Exception as e:
                    print(f"Fehler beim Starten von Spyder über conda activate: {e}", file=sys.stderr)
                    # fall through to fallback
        # Fallback: conda run
        try:
            cmd = ["conda", "run", "-n", env_name, "--no-capture-output", "spyder"]
            return subprocess.call(cmd, env=env)
        except FileNotFoundError:
            print("Fehler: 'conda' nicht gefunden. Stelle sicher, dass Anaconda/Miniconda installiert und in PATH ist.", file=sys.stderr)
            return 3
        except Exception as e:
            print(f"Fehler beim Starten von Spyder: {e}", file=sys.stderr)
            return 4


def main():
    parser = argparse.ArgumentParser(prog="semi-ate", description="Wähle conda-env basierend auf project+version und starte Spyder.")
    parser.add_argument("project", nargs="?", help="Projektname (oder leer, wenn -e/-m benutzt wird)")
    parser.add_argument("version", nargs="?", help="Version als 4-stellige Zahl, z.B. 0001 (oder leer, wenn -e/-m benutzt wird)")
    parser.add_argument("-w", "--who", metavar="name", help="optional: USER=name setzen")
    parser.add_argument("-e", "--edit", action="store_true", help="optional: edit path to Projects")
    args = parser.parse_args()

    # Normaler Start: require project+version
    if not args.project or not args.version:
        parser.print_usage()
        print("\nError: project and version are required.", file=sys.stderr)
        sys.exit(1)
        
    sa = SemiAte(args)

    if args.who:
        print(f"USER set to: {args.who}")

    #rc = sa.start_spyder_in_env(env_name, args.project, args.version, args.who)
    # sys.exit(rc)


if __name__ == "__main__":
    main()
