import hashlib
import json
from typing import Any

from app.services.search_text import normalize_search_text


def _nutrition_value(value: dict[str, Any] | None) -> str:
    if not value:
        return ""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_recipe_embedding_input(recipe: Any) -> str:
    parts: list[str] = [recipe.title or ""]
    parts.extend(ingredient.search_name for ingredient in sorted(recipe.ingredients, key=lambda item: item.position))
    parts.extend(recipe.instructions or [])
    parts.append(_nutrition_value(recipe.nutrition_estimate))
    if recipe.cook_time_minutes is not None:
        parts.append(str(recipe.cook_time_minutes))
    return normalize_search_text(" ".join(part for part in parts if part))


def build_recipe_embedding_hash(recipe: Any) -> str:
    return hashlib.sha256(build_recipe_embedding_input(recipe).encode("utf-8")).hexdigest()
