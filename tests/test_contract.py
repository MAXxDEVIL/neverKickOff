"""Guard the frozen cross-language contract.

tests/fixtures/contract.json is the behaviour Rust and Java must reproduce. This
re-derives it from the live Python code and fails on the first difference, so a
change to engine.py/main.py/etc. cannot silently move the contract.

    .venv/bin/python tests/test_contract.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from gen_fixtures import build  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "contract.json"


def first_difference(live, frozen, path=""):
    """Describe the first place two JSON-shaped values differ, or None."""
    if isinstance(live, bool) != isinstance(frozen, bool) or type(live) is not type(frozen):
        return f"{path}: {type(live).__name__} {live!r} != {type(frozen).__name__} {frozen!r}"
    if isinstance(live, dict):
        for key in sorted(set(live) | set(frozen)):
            if key not in live:
                return f"{path}.{key}: missing from Python output"
            if key not in frozen:
                return f"{path}.{key}: new in Python output (regenerate the fixture)"
            found = first_difference(live[key], frozen[key], f"{path}.{key}")
            if found:
                return found
        return None
    if isinstance(live, list):
        if len(live) != len(frozen):
            return f"{path}: length {len(live)} != frozen {len(frozen)}"
        for i, (a, b) in enumerate(zip(live, frozen)):
            found = first_difference(a, b, f"{path}[{i}]")
            if found:
                return found
        return None
    if live != frozen:
        return f"{path}: {live!r} != frozen {frozen!r}"
    return None


def test_contract_is_current():
    frozen = json.loads(FIXTURE.read_text())
    live = build()
    found = first_difference(live, frozen)
    assert not found, (
        f"Python behaviour no longer matches tests/fixtures/contract.json at {found}\n"
        "If the change was deliberate, re-run tests/gen_fixtures.py."
    )


if __name__ == "__main__":
    test_contract_is_current()
    print("ok test_contract_is_current")
    print("all passed")
