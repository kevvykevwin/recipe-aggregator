import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services.extractor import _parse_ingredients, _parse_instructions


def test_parse_ingredients_uses_unknown_for_null_name() -> None:
    ingredients = _parse_ingredients([{"name": None, "quantity": "1"}])

    assert len(ingredients) == 1
    assert ingredients[0].name == "Unknown"
    assert ingredients[0].quantity == "1"


def test_parse_instructions_splits_multiline_string() -> None:
    assert _parse_instructions("Mix ingredients.\n\nBake until done.") == [
        "Mix ingredients.",
        "Bake until done.",
    ]


def test_parse_instructions_drops_blank_items_and_stringifies_values() -> None:
    assert _parse_instructions(["Prep pan", "", None, 3]) == [
        "Prep pan",
        "3",
    ]
