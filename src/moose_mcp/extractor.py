"""
Console command:  extract-objects "Steady heat conduction in a 2-D plate"

It returns a JSON list of the smallest set of MOOSE objects the LLM thinks
are needed.  A quick *prefilter* reduces the enum (and model context window).
"""

import json
import os
import sys
import openai
from dotenv import load_dotenv

load_dotenv()

# MODEL = "gpt-3.5-turbo-0125"
MODEL = "gpt-4o-mini"  # 128 k-token context
OBJECT_FILE = os.getenv("MCP_OBJECT_LIST", "artifacts/objects.json")

# ------------------------------------------------------------------ helpers


def load_object_names(path: str) -> list[str]:
    """Loads the object names."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure(pfx: str, default: str, picked: list[str]) -> None:
    "Ensures that some objects are included"
    if not any(o.startswith(pfx) for o in picked):
        picked.append(default)


CORE_BLOCKS = (
    "Mesh/",
    "Variables/",
    "Kernels/",
    "AuxKernels/",
    "BCs/",
    "Materials/",
    "Outputs/",
    "Postprocessors/",
)


def prefilter(prompt: str, all_objects: list[str], min_keep: int = 200) -> list[str]:
    """
    Return a trimmed list of object names likely relevant to the prompt.
    Heuristics:
      • keep any name whose *parent block* appears in the prompt;
      • keep any name whose own identifier appears verbatim;
      • always keep a small core set so the model has basics to choose from.
    """
    prompt_lc = prompt.lower()

    keep: list[str] = []
    for full in all_objects:
        parent, _, child = full.partition("/")
        if parent.lower() in prompt_lc or child.lower() in prompt_lc:
            keep.append(full)

    # guarantee the core basics are present
    core = [o for o in all_objects if o.startswith(CORE_BLOCKS)]
    keep.extend(core)

    # if we filtered too much, pad back up to `min_keep`
    if len(keep) < min_keep:
        keep.extend(all_objects[: min_keep - len(keep)])

    # deduplicate while preserving order
    seen: set[str] = set()
    result = [o for o in keep if not (o in seen or seen.add(o))]
    return result


def call_extractor(prompt: str, allowed: list[str]) -> list[str]:
    """
    One function-call to an LLM with an enum list.
    """
    schema = {
        "name": "pick_moose_objects",
        "description": (
            "Return the MOOSE object names needed to satisfy the request. "
            "Choose ONLY from the provided list."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "objects": {
                    "type": "array",
                    "items": {"type": "string", "enum": allowed},
                }
            },
            "required": ["objects"],
        },
    }

    client = openai.OpenAI()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a selector of MOOSE objects.\n"
                    "RULES:\n"
                    "• If you choose any HeatConduction kernel you should also pick:\n"
                    "    - at least one Variables/* object.\n"
                    "    - at least one BCs/* object (e.g. DirichletBC or NeumannBC).\n"
                    "• Always pick one Mesh/* generator and one Outputs/* block.\n"
                    "Return the shortest list that satisfies the request and these rules.\n"
                    "• If unsure, include the mesh generator, a primary variable, appropriate"
                    " boundary conditions, and a basic output block."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        functions=[schema],  # type: ignore[arg-type]
        function_call={"name": "pick_moose_objects"},
    )

    args = json.loads(response.choices[0].message.function_call.arguments)  # type: ignore[arg-type]
    return args.get("objects", [])


def extract_objects(prompt: str) -> list[str]:
    """Run the extractor pipeline and post-process the list a bit."""
    all_objects = load_object_names(OBJECT_FILE)
    allowed = prefilter(prompt, all_objects)

    picked = call_extractor(prompt, allowed)
    picked = [n for n in picked if n in allowed]  # drop strays

    ensure("Mesh/", "Mesh/GeneratedMeshGenerator", picked)
    ensure("Outputs/", "Outputs/CSV", picked)

    return picked


# ------------------------------------------------------------------ entry-point


def main() -> None:
    """Main function for extractor"""
    if len(sys.argv) < 2:
        sys.exit('Usage: extract-objects "<job description>"')

    user_prompt = sys.argv[1]
    picked = extract_objects(user_prompt)

    print(json.dumps(picked, indent=2))


if __name__ == "__main__":
    main()
