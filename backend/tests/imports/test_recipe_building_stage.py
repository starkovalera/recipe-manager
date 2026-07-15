from app.ai.schemas import ExtractedIngredient, ExtractedRecipe, ExtractionQuality
from app.imports.job_context import ImportJobContext
from app.imports.job_stages.recipe_building import build_recipe
from app.models import ImportJob, ImportJobStatus, Recipe, Tag


def extracted_recipe() -> ExtractedRecipe:
    return ExtractedRecipe(
        title="Recipe",
        ingredients=[
            ExtractedIngredient(name="Cottage Cheese", quantity="200", unit="g", note="soft"),
            ExtractedIngredient(name="Egg"),
        ],
        instructions=["Mix.", "Bake."],
        cook_time_minutes=25,
        author_name="ai_author",
        tags=["quick", " QUICK ", "unknown"],
        quality=ExtractionQuality(
            confidence=0.9,
            has_conflicts=False,
            has_ignored=False,
            primary_source_refs=[],
            ignored_source_refs=[],
        ),
    )


def available_tags() -> list[Tag]:
    return [Tag(name="quick"), Tag(name="dessert")]


def import_job_context() -> ImportJobContext:
    return ImportJobContext.from_job(ImportJob(owner_id="user-1", client_id="client-1", status=ImportJobStatus.RUNNING))


def test_build_recipe_applies_fields_tags_and_ingredients():
    recipe = Recipe(owner_id="user-1")

    build_recipe(recipe, extracted_recipe(), available_tags(), import_job_context())

    assert recipe.title == "Recipe"
    assert recipe.instructions == ["Mix.", "Bake."]
    assert recipe.cook_time_minutes == 25
    assert recipe.author_name == "ai_author"
    assert [tag.name for tag in recipe.tags] == ["quick"]
    assert [
        (ingredient.name, ingredient.search_name, ingredient.quantity, ingredient.unit, ingredient.note)
        for ingredient in recipe.ingredients
    ] == [
        ("Cottage Cheese", "cottage cheese", "200", "g", "soft"),
        ("Egg", "egg", None, None, None),
    ]


def test_build_recipe_keeps_existing_author_name():
    recipe = Recipe(owner_id="user-1", author_name="imported_author")

    build_recipe(recipe, extracted_recipe(), available_tags(), import_job_context())

    assert recipe.author_name == "imported_author"
