from collections.abc import Sequence
from typing import Protocol

from app.core.config import get_settings
from app.core.errors import ApiError, ErrorCode


class IngredientLike(Protocol):
    name: str


def instructions_text_length(instructions: Sequence[str]) -> int:
    return len("\n".join(step.strip() for step in instructions if step.strip()))


def validate_recipe_size(ingredients: Sequence[IngredientLike], instructions: Sequence[str]) -> None:
    settings = get_settings()
    if len([ingredient for ingredient in ingredients if ingredient.name.strip()]) > settings.max_recipe_ingredients:
        raise ApiError(ErrorCode.RECIPE_TOO_LONG, "Recipe is too long.")
    if instructions_text_length(instructions) > settings.max_recipe_instruction_chars:
        raise ApiError(ErrorCode.RECIPE_TOO_LONG, "Recipe is too long.")


def validate_recipe_note(note: str | None) -> None:
    if note is not None and len(note.strip()) > get_settings().max_recipe_note_chars:
        raise ApiError(ErrorCode.NOTE_TOO_LONG, "Recipe note is too long.")
