"""
syntax_srv - FastAPI micro-service + helper that serves mini-syntax
snippets **directly from the pre-built `syntax_map.json`.**

Environment variables
~~~~~~~~~~~~~~~~~~~~~
* ``SYNTAX_MAP`` - override the default path ``artifacts/syntax_map.json``.

Each key in the map is a ``Block/Object`` name and each value is the
prompt-ready snippet (exactly what *make_objects.py* produced).
"""

import json
import os
import pathlib

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# 1. Load the pre-built map once at start-up
# ---------------------------------------------------------------------------
MAP_PATH = pathlib.Path(os.getenv("SYNTAX_MAP", "artifacts/syntax_map.json"))

try:
    _SYNTAX_MAP: dict[str, str] = json.loads(MAP_PATH.read_text(encoding="utf-8"))
except FileNotFoundError as exc:
    raise RuntimeError(
        f"Syntax map '{MAP_PATH}' not found. Have you run scripts/make_objects.py?"
    ) from exc
except json.JSONDecodeError as exc:
    raise RuntimeError(f"Syntax map '{MAP_PATH}' is not valid JSON.") from exc

if not _SYNTAX_MAP:
    raise RuntimeError("Loaded syntax map is empty - something went wrong.")

__all__ = ["get_syntax_text"]

# ---------------------------------------------------------------------------
# 2. Public helper - importable by CLI / tests
# ---------------------------------------------------------------------------


def get_syntax_text(objects: list[str]) -> str:
    """Return concatenated snippets for *objects*.

    Raises:
        ValueError - if *objects* is empty.
        KeyError  - if any name is missing in the map.
    """

    if not objects:
        raise ValueError("Empty object list")

    missing = [o for o in objects if o not in _SYNTAX_MAP]
    if missing:
        raise KeyError(f"Objects not found in syntax map: {', '.join(missing)}")

    return "\n".join(_SYNTAX_MAP[o] for o in objects)


# ---------------------------------------------------------------------------
# 3. Optional FastAPI wrapper for remote callers
# ---------------------------------------------------------------------------
app = FastAPI(title="syntax_srv (syntax_map)")


class SyntaxRequest(BaseModel):
    """Syntax request for FastAPI"""

    objects: list[str]


class SyntaxReply(BaseModel):
    """Syntax reply for FastAPI"""

    syntax: str


@app.post("/get_syntax", response_model=SyntaxReply)
def get_syntax(req: SyntaxRequest) -> SyntaxReply:
    """Get syntax API wrapper"""
    try:
        snippet = get_syntax_text(req.objects)
        return SyntaxReply(syntax=snippet)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
