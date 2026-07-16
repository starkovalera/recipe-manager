import hashlib
from dataclasses import dataclass

from app.models import Recipe
from app.services.search_text import format_nutrition_for_search, normalize_search_text


@dataclass(frozen=True)
class RecipeEmbeddingInput:
    text: str
    input_hash: str


def build_recipe_embedding_input(recipe: Recipe) -> RecipeEmbeddingInput:
    parts: list[str] = [recipe.title or ""]
    parts.extend(ingredient.search_name for ingredient in sorted(recipe.ingredients, key=lambda item: item.position))
    parts.extend(recipe.instructions or [])
    parts.append(format_nutrition_for_search(recipe.nutrition_estimate))
    if recipe.cook_time_minutes is not None:
        parts.append(f"Cooking time {recipe.cook_time_minutes} minutes.")
    text = normalize_search_text(" ".join(part for part in parts if part))
    return RecipeEmbeddingInput(
        text=text,
        input_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )
