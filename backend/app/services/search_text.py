import hashlib
import json
import re
from typing import Any

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_search_text(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value.strip()).casefold()


def build_ingredient_search_name(name: str) -> str:
    return normalize_search_text(name)


def _source_name_value(value: Any) -> str:
    return getattr(value, "value", value) or ""


def _nutrition_value(value: dict[str, Any] | None) -> str:
    if not value:
        return ""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_recipe_search_text(recipe: Any) -> str:
    parts: list[str] = [
        recipe.title or "",
        _source_name_value(recipe.source_name),
        recipe.author_name or "",
    ]
    parts.extend(ingredient.search_name for ingredient in sorted(recipe.ingredients, key=lambda item: item.position))
    parts.extend(recipe.instructions or [])
    parts.append(_nutrition_value(recipe.nutrition_estimate))
    if recipe.cook_time_minutes is not None:
        parts.append(str(recipe.cook_time_minutes))
    return normalize_search_text(" ".join(part for part in parts if part))


def build_recipe_search_hash(recipe: Any) -> str:
    return hashlib.sha256(build_recipe_search_text(recipe).encode("utf-8")).hexdigest()


def refresh_recipe_search_text(recipe: Any) -> bool:
    previous_hash = recipe.search_text_hash
    recipe.search_text = build_recipe_search_text(recipe)
    recipe.search_text_hash = hashlib.sha256(recipe.search_text.encode("utf-8")).hexdigest()
    return recipe.search_text_hash != previous_hash
