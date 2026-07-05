from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from app.core.config import get_settings
from app.core.errors import NoteTooLongError, TextTooLongError


class IngredientLike(Protocol):
    name: str


@dataclass(frozen=True)
class RecipeSizeViolation:
    reason: str
    actual: int
    limit: int


def instructions_text_length(instructions: Sequence[str]) -> int:
    return len("\n".join(step.strip() for step in instructions if step.strip()))


def find_recipe_size_violation(ingredients: Sequence[IngredientLike], instructions: Sequence[str]) -> RecipeSizeViolation | None:
    settings = get_settings()
    ingredient_count = len([ingredient for ingredient in ingredients if ingredient.name.strip()])
    if ingredient_count > settings.max_recipe_ingredients:
        return RecipeSizeViolation(reason="too_many_ingredients", actual=ingredient_count, limit=settings.max_recipe_ingredients)
    instruction_chars = instructions_text_length(instructions)
    if instruction_chars > settings.max_recipe_instruction_chars:
        return RecipeSizeViolation(reason="instructions_too_long", actual=instruction_chars, limit=settings.max_recipe_instruction_chars)
    return None


def validate_recipe_size(ingredients: Sequence[IngredientLike], instructions: Sequence[str]) -> None:
    violation = find_recipe_size_violation(ingredients, instructions)
    if violation is not None:
        raise TextTooLongError(reason=violation.reason, actual=violation.actual, limit=violation.limit)


def validate_recipe_note(note: str | None) -> None:
    if note is not None and len(note.strip()) > get_settings().max_recipe_note_chars:
        raise NoteTooLongError(max_length=get_settings().max_recipe_note_chars)
