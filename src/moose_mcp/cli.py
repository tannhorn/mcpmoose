"""
CLI helper: from a free-form job description → object list → mini syntax.

Usage:
    moose-mini "<job description>"
"""

import json
import sys

from moose_mcp.extractor import extract_objects
from moose_mcp.syntax_srv import get_syntax_text


def main() -> None:  # noqa: D401
    """Entry-point for the `moose-mini` command."""
    if len(sys.argv) < 2:
        sys.exit('Usage: moose-mini "<job description>"')

    prompt = sys.argv[1]

    objects = extract_objects(prompt)
    print("### Picked objects ###")
    print(json.dumps(objects, indent=2))

    syntax = get_syntax_text(objects)
    print("\n### Mini syntax ###")
    print(syntax)


if __name__ == "__main__":
    main()
