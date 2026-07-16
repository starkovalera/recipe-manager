from app.ai.schemas import ExtractedRecipe
from app.imports.job_context import ImportJobContext
from app.imports.logging import log_recipe_tags_built
from app.models import Ingredient, Recipe, Tag
from app.services.search_text import build_ingredient_search_name


def build_recipe(
    recipe: Recipe,
    extracted_recipe: ExtractedRecipe,
    available_tags: list[Tag],
    job: ImportJobContext,
) -> None:
    recipe.title = extracted_recipe.title
    recipe.instructions = extracted_recipe.instructions
    recipe.servings = extracted_recipe.servings
    recipe.cook_time_minutes = extracted_recipe.cook_time_minutes
    recipe.nutrition_estimate = extracted_recipe.nutrition_estimate.model_dump() if extracted_recipe.nutrition_estimate else None
    if not recipe.author_name and extracted_recipe.author_name:
        recipe.author_name = extracted_recipe.author_name

    matched, ignored, duplicate = _build_tags(recipe, available_tags, extracted_recipe.tags)
    log_recipe_tags_built(job, extracted_recipe.tags, matched, ignored, duplicate)

    for index, ingredient in enumerate(extracted_recipe.ingredients):
        recipe.ingredients.append(
            Ingredient(
                name=ingredient.name,
                search_name=build_ingredient_search_name(ingredient.name),
                quantity=ingredient.quantity,
                unit=ingredient.unit,
                note=ingredient.note,
                position=index,
            )
        )


def _normalize_tag_name(value: str) -> str:
    """Normalize both tag sets for comparison."""
    return " ".join(value.strip().casefold().split())


def _build_tags(recipe: Recipe, tags: list[Tag], extracted_tags: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Filter out extracted tags based on the allowed recipe tags."""
    tag_by_normalized_name = {_normalize_tag_name(tag.name): tag for tag in tags}

    matched_tags: list[Tag] = []
    seen_tags: set[str] = set()
    ignored_tags: list[str] = []
    duplicate_tags: list[str] = []
    for extracted_tag in extracted_tags:
        normalized_name = _normalize_tag_name(extracted_tag)
        tag = tag_by_normalized_name.get(normalized_name)
        if tag is None:
            ignored_tags.append(extracted_tag)
            continue
        if normalized_name in seen_tags:
            duplicate_tags.append(extracted_tag)
            continue
        matched_tags.append(tag)
        seen_tags.add(normalized_name)
    recipe.tags = matched_tags
    return [tag.name for tag in matched_tags], ignored_tags, duplicate_tags
