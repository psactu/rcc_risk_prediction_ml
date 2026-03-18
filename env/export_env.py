#!/usr/bin/env python3
"""
Export a conda environment to requirements.txt with:
- Only explicitly installed conda packages (from --from-history)
- Only explicitly installed pip packages
- Clean version strings (name==version, no build strings or conda constraints)
- Unresolved conda history entries skipped
- Conda history entries skipped when the current installed package is from pip

Usage:
    python export_env.py                        # prints to stdout
    python export_env.py -o requirements.txt    # saves to file
"""

import argparse
import json
import re
import subprocess
import sys
from importlib import metadata

try:
    import yaml
except ImportError:
    print("PyYAML not found. Installing...", file=sys.stderr)
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml", "-q"])
    import yaml


def get_conda_export(extra_args=None):
    cmd = ["conda", "env", "export"] + (extra_args or [])
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return yaml.safe_load(result.stdout)


def normalize_dist_name(name):
    """Normalize package names for reliable matching."""
    return re.sub(r"[-_.]+", "-", name).lower()


def extract_conda_name(dep):
    """Extract bare conda package name from a dep string or YAML-parsed dict."""
    if isinstance(dep, dict):
        dep = list(dep.keys())[0]

    name = re.split(r"[=\[]", str(dep), maxsplit=1)[0].strip()
    if "::" in name:
        name = name.split("::", 1)[1]
    return name.lower()


def clean_version(dep_str):
    """
    Convert conda dep strings like:
      - pkg=1.2.3=build   -> pkg==1.2.3
      - channel::pkg=1.2  -> pkg==1.2
      - pkg               -> pkg
    """
    dep_str = str(dep_str).strip()

    m = re.match(r"^([^=\[\s]+)=([^=]+)(?:=.*)?$", dep_str)
    if m:
        name = m.group(1).strip()
        version = m.group(2).strip()
        if "::" in name:
            name = name.split("::", 1)[1]
        return f"{name}=={version}"

    return extract_conda_name(dep_str)


def build_conda_version_map(full_export):
    """Map normalized conda package name -> clean versioned string from full export."""
    version_map = {}
    for dep in full_export.get("dependencies", []):
        if isinstance(dep, str):
            name = normalize_dist_name(extract_conda_name(dep))
            version_map[name] = clean_version(dep)
    return version_map


def parse_pip_name(req):
    """
    Extract distribution name from a pip requirement line.
    Handles lines like:
      - package==1.2.3
      - package>=1.0
      - package[extra]==1.2
    Skips direct references like:
      - package @ file:///...
    """
    req = req.strip()
    if " @ " in req:
        return None

    m = re.match(r"^([A-Za-z0-9_.-]+)", req)
    return m.group(1) if m else None


def collect_pip_packages(full_export):
    all_pip = []
    for dep in full_export.get("dependencies", []):
        if isinstance(dep, dict) and "pip" in dep:
            for pkg in dep["pip"]:
                if " @ " in pkg:
                    continue
                all_pip.append(pkg)
    return all_pip


def get_pip_explicit(full_export):
    """
    Resolve explicitly installed pip packages.
    Uses pip REQUESTED markers when available.
    Falls back to pip list --not-required.
    """
    all_pip = collect_pip_packages(full_export)
    if not all_pip:
        return []

    print("Resolving explicit pip packages...", file=sys.stderr)

    explicit = []
    for pkg in all_pip:
        name = parse_pip_name(pkg)
        if not name:
            continue
        try:
            dist = metadata.distribution(name)
            if dist.read_text("REQUESTED") is not None:
                explicit.append(pkg)
        except metadata.PackageNotFoundError:
            pass

    if explicit:
        print("Using pip REQUESTED markers.", file=sys.stderr)
        return explicit

    print(
        "No pip REQUESTED markers found; falling back to pip list --not-required.",
        file=sys.stderr,
    )
    result = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--not-required", "--format=json"],
        capture_output=True,
        text=True,
        check=True,
    )

    not_required = {
        normalize_dist_name(item["name"]) for item in json.loads(result.stdout)
    }

    filtered = []
    for pkg in all_pip:
        name = parse_pip_name(pkg)
        if name and normalize_dist_name(name) in not_required:
            filtered.append(pkg)

    return filtered


def build_pip_name_map(pip_pkgs):
    """Map normalized pip package name -> requirement string."""
    out = {}
    for pkg in pip_pkgs:
        name = parse_pip_name(pkg)
        if name:
            out[normalize_dist_name(name)] = pkg
    return out


def main():
    parser = argparse.ArgumentParser(
        description="Export conda env to requirements.txt."
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output file path (default: print to stdout)",
        default=None,
    )
    args = parser.parse_args()

    print("Fetching full environment export...", file=sys.stderr)
    full_export = get_conda_export()

    print("Fetching history-based export...", file=sys.stderr)
    history_export = get_conda_export(["--from-history"])

    print("Merging conda packages...", file=sys.stderr)
    version_map = build_conda_version_map(full_export)

    pip_pkgs = get_pip_explicit(full_export)
    pip_name_map = build_pip_name_map(pip_pkgs)

    lines = ["# conda packages"]
    emitted_conda_names = set()
    seen_history_names = set()

    for dep in history_export.get("dependencies", []):
        raw_name = extract_conda_name(dep)
        if not raw_name:
            continue

        name = normalize_dist_name(raw_name)
        if name in seen_history_names:
            continue
        seen_history_names.add(name)

        if name in version_map:
            lines.append(version_map[name])
            emitted_conda_names.add(name)
        elif name in pip_name_map:
            print(
                f"Skipping '{raw_name}' from conda history because the current installed package is from pip: {pip_name_map[name]}",
                file=sys.stderr,
            )
        else:
            print(
                f"Skipping unresolved conda history entry: {raw_name}",
                file=sys.stderr,
            )

    if pip_pkgs:
        lines.append("")
        lines.append("# pip packages")
        seen_pip_names = set()

        for pkg in pip_pkgs:
            name = parse_pip_name(pkg)
            norm_name = normalize_dist_name(name) if name else None

            if norm_name and norm_name in emitted_conda_names:
                continue
            if norm_name and norm_name in seen_pip_names:
                continue

            lines.append(pkg)

            if norm_name:
                seen_pip_names.add(norm_name)

    output = "\n".join(lines) + "\n"

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"✅ Saved to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
