"""Resolve the per-run wrapper output folder (export / export(n)).

Each run writes into a single dedicated folder so runs stay separated. This is
orthogonal to the naming strategy (which groups files *inside* the folder), so
it lives here rather than in `naming/`.
"""

from __future__ import annotations

from pathlib import Path


def resolve_export_dir(parent: Path, base: str = "export") -> Path:
    """First non-existing `<parent>/export`, then `export(1)`, `export(2)`, …."""
    candidate = parent / base
    n = 1
    while candidate.exists():
        candidate = parent / f"{base}({n})"
        n += 1
    return candidate
