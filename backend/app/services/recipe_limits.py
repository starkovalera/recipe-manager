from collections.abc import Sequence
from typing import Protocol

from app.core.config import get_settings
from app.core.errors import NoteTooLongError, RecipeTooLongError


class IngredientLike(Protocol):
    name: str


def instructions_text_length(instructions: Sequence[str]) -> int:
    return len("\n".join(step.strip() for step in instructions if step.strip()))


def validate_recipe_size(ingredients: Sequence[IngredientLike], instructions: Sequence[str]) -> None:
    settings = get_settings()
    if len([ingredient for ingredient in ingredients if ingredient.name.strip()]) > settings.max_recipe_ingredients:
        raise RecipeTooLongError(max_ingredients=settings.max_recipe_ingredients)
    if instructions_text_length(instructions) > settings.max_recipe_instruction_chars:
        raise RecipeTooLongError(max_instruction_chars=settings.max_recipe_instruction_chars)


def validate_recipe_note(note: str | None) -> None:
    if note is not None and len(note.strip()) > get_settings().max_recipe_note_chars:
        raise NoteTooLongError(max_length=get_settings().max_recipe_note_chars)
