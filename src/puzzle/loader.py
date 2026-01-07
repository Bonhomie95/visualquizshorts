from __future__ import annotations

import json
from pathlib import Path
from typing import List, TypedDict

from ..config.settings import DATA_DIR


# =========================================================
# TYPES (AUTHORITATIVE)
# =========================================================


class Puzzle(TypedDict):
    id: str
    prompt: str
    rule: str
    letter: str
    items: list[str]


# =========================================================
# LOADERS
# =========================================================


def load_all_puzzles() -> List[Puzzle]:
    path = DATA_DIR / "puzzles.json"

    if not path.exists():
        raise FileNotFoundError(f"Puzzles file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("puzzles.json must contain a list")

    return data  # type: ignore[return-value] (validated below)


def validate_puzzle(puzzle: Puzzle) -> None:
    if len(puzzle["items"]) != 4:
        raise ValueError("Puzzle must contain exactly 4 items")

    letter = puzzle["letter"].lower()

    for item in puzzle["items"]:
        if not item.lower().startswith(letter):
            raise ValueError(f"Item '{item}' does not start with letter '{letter}'")


def load_valid_puzzles() -> List[Puzzle]:
    puzzles = load_all_puzzles()
    valid: List[Puzzle] = []

    for p in puzzles:
        validate_puzzle(p)
        valid.append(p)

    if not valid:
        raise RuntimeError("No valid puzzles found")

    return valid


def select_next_puzzle(used_ids: set[str] | None = None) -> Puzzle:
    puzzles = load_valid_puzzles()

    if used_ids:
        for p in puzzles:
            if p["id"] not in used_ids:
                return p

    return puzzles[0]
