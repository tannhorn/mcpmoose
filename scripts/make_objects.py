"""
Regenerate the **clean inputs** that power MCP-MOOSE:

1. **objects.json** - flat, sorted list of real Moose objects in
   ``Block/Object`` form (e.g. ``Kernels/HeatConduction``).
2. **syntax_map.json** - mapping ``name → mini-syntax snippet`` used by
   the prompt helper.  Every entry in *objects.json* has a corresponding
   key in *syntax_map.json* and vice-versa.

Usage
-----

```bash
python scripts/make_objects.py            # default paths in ./artifacts
python scripts/make_objects.py --src ~/dump.json --dst ./artifacts
```

The script **only touches the two output files if the new content is
actually different**, so you can drop it into CI without creating noisy
git diffs.
"""

import argparse
import json
import pathlib
import sys

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
_EXCLUDE = {"star", "actions", "subblock_types"}


def _format_snippet(path: list[str], node: dict) -> str:
    """Return a prompt-friendly snippet for a single Moose object."""
    category, obj_name = path[:2]
    lines = [f"[{category}]", f"  type = {obj_name}"]

    for pname in node.get("parameters", {}).keys():
        if pname in {"type", "active", "inactive"}:  # noise parameters
            continue
        lines.append(f"  {pname} = ")

    lines.append("[../]")
    return "\n".join(lines)


def _walk(
    node: dict, chain: list[str], objects: set[str], syntax_map: dict[str, str]
) -> None:
    """Recursive DFS that populates *objects* and *syntax_map*."""
    if not isinstance(node, dict):
        return

    for key, sub in node.items():
        # Skip template layers but keep the current chain
        if key in _EXCLUDE:
            _walk(sub, chain, objects, syntax_map)
            continue

        next_chain = chain + [key]

        # Real Moose object: a dict with a 'parameters' entry
        if isinstance(sub, dict) and "parameters" in sub:
            obj_name = "/".join(next_chain[:2])
            objects.add(obj_name)
            syntax_map[obj_name] = _format_snippet(next_chain[:2], sub)

        _walk(sub, next_chain, objects, syntax_map)


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def build(src: pathlib.Path) -> tuple[list[str], dict[str, str]]:
    """Return (object_list, syntax_map) from a raw Moose app JSON dump."""
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"❌ {src} not found - run 'app-name --json > {src}' first")
    except json.JSONDecodeError as exc:
        sys.exit(f"❌ {src} is not valid JSON ({exc})")

    objects: set[str] = set()
    syntax_map: dict[str, str] = {}

    _walk(data.get("blocks", {}), [], objects, syntax_map)

    if not objects or not syntax_map:
        sys.exit("❌ No objects discovered - JSON layout may have changed.")

    # Return sorted list for reproducible outputs
    return sorted(objects), syntax_map


def write_if_changed(path: pathlib.Path, content: str) -> None:
    """Write *content* to *path* only if it differs from the current file."""
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return  # Unchanged - keep the mtime stable
    path.write_text(content, encoding="utf-8")
    print(f"✅ wrote {path.relative_to(path.parent.parent)}")


def main() -> None:
    """CLI entry-point - see module docstring for usage."""
    parser = argparse.ArgumentParser(
        description="Regenerate objects & syntax_map JSON files"
    )
    parser.add_argument(
        "--src",
        type=pathlib.Path,
        default=pathlib.Path("artifacts/syntax_full.json"),
        help="raw app JSON dump",
    )
    parser.add_argument(
        "--dst",
        type=pathlib.Path,
        default=pathlib.Path("artifacts"),
        help="output directory",
    )

    args = parser.parse_args()

    objects, syntax_map = build(args.src)

    args.dst.mkdir(parents=True, exist_ok=True)

    write_if_changed(args.dst / "objects.json", json.dumps(objects, indent=2))
    write_if_changed(args.dst / "syntax_map.json", json.dumps(syntax_map, indent=2))

    print(f"🔢 total objects: {len(objects)}  |  syntax snippets: {len(syntax_map)}")


if __name__ == "__main__":
    main()
