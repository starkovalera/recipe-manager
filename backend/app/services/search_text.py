import hashlib
import re
from typing import Any

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_search_text(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value.strip()).casefold()


def build_ingredient_search_name(name: str) -> str:
    return normalize_search_text(name)


def _source_name_value(value: Any) -> str:
    return getattr(value, "value", value) or ""


def _nutrition_item(value: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in value:
            return value[key]
    return None


def format_nutrition_for_search(value: dict[str, Any] | None) -> str:
    if not value:
        return ""
    parts: list[str] = []
    calories = _nutrition_item(value, "calories")
    protein_grams = _nutrition_item(value, "proteinGrams", "protein_grams", "proteingrams")
    fat_grams = _nutrition_item(value, "fatGrams", "fat_grams", "fatgrams")
    carbs_grams = _nutrition_item(value, "carbsGrams", "carbs_grams", "carbsgrams")
    if calories is not None:
        parts.append(f"{calories} calories per serving")
    if protein_grams is not None:
        parts.append(f"{protein_grams} grams of proteins per serving")
    if fat_grams is not None:
        parts.append(f"{fat_grams} grams of fat per serving")
    if carbs_grams is not None:
        parts.append(f"{carbs_grams} grams of carbs per serving")
    return ", ".join(parts)


def build_recipe_search_text(recipe: Any) -> str:
    parts: list[str] = [
        recipe.title or "",
        _source_name_value(recipe.source_name),
        recipe.author_name or "",
    ]
    parts.extend(ingredient.search_name for ingredient in sorted(recipe.ingredients, key=lambda item: item.position))
    parts.extend(recipe.instructions or [])
    parts.append(format_nutrition_for_search(recipe.nutrition_estimate))
    if recipe.cook_time_minutes is not None:
        parts.append(f"Cooking time {recipe.cook_time_minutes} minutes.")
    return normalize_search_text(" ".join(part for part in parts if part))


def _hash_search_text(search_text: str) -> str:
    return hashlib.sha256(search_text.encode("utf-8")).hexdigest()


def build_recipe_search_hash(recipe: Any) -> str:
    return _hash_search_text(build_recipe_search_text(recipe))


def refresh_recipe_search_text(recipe: Any) -> bool:
    previous_hash = recipe.search_text_hash
    recipe.search_text = build_recipe_search_text(recipe)
    recipe.search_text_hash = _hash_search_text(recipe.search_text)
    return recipe.search_text_hash != previous_hash
