#!/usr/bin/env python3
"""
Flatten MOOSE --json dump into objects.json

Keeps only real input-file objects, e.g.
    Kernels/HeatConduction
    Mesh/GeneratedMesh
    BCs/DirichletBC
Skips template layers: star, actions, subblock_types.
"""

import json
import pathlib
import sys

SRC = pathlib.Path("inputs/syntax_full.json")
DST = pathlib.Path("inputs/objects.json")

try:
    data = json.loads(SRC.read_text(encoding="UTF8"))
except FileNotFoundError:
    sys.exit(f"❌ {SRC} not found = run ./diglett-opt --json > {SRC} first")

objects: set[str] = set()


def maybe_add(chain) -> None:
    """Record 'Block/Object' if we have at least two levels."""
    if len(chain) >= 2:
        objects.add("/".join(chain[:2]))


def walk(node: dict, chain: list[str]) -> None:
    """Walks the JSON tree."""
    if not isinstance(node, dict):
        return  # guard against None / int / list

    for key, sub in node.items():
        if key in {"star", "actions", "subblock_types"}:
            walk(sub, chain)  # skip template layer but keep chain
            continue

        if isinstance(sub, dict) and "parameters" in sub:
            maybe_add(chain + [key])
        else:
            walk(sub, chain + [key])


walk(data.get("blocks", {}), [])

DST.write_text(json.dumps(sorted(objects), indent=2), encoding="UTF8")
print(f"✅ wrote {len(objects)} clean names → {DST}")
