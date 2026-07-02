from app.models import Ingredient, Recipe, SourceName
from app.services.search_text import build_recipe_search_hash, build_recipe_search_text, refresh_recipe_search_text


def test_build_recipe_search_text_uses_only_approved_fields():
    recipe = Recipe(
        title="  Banana Cake  ",
        source_name=SourceName.INSTAGRAM,
        author_name="baker",
        cook_time_minutes=45,
        instructions=["Mix batter", "Bake"],
        nutrition_estimate={"calories": 220, "proteinGrams": 6},
    )
    recipe.ingredients.append(
        Ingredient(
            name="Banana",
            search_name="banana",
            quantity="2",
            unit="pcs",
            note="ripe",
            position=0,
        )
    )

    search_text = build_recipe_search_text(recipe)

    assert "banana cake" in search_text
    assert "instagram" in search_text
    assert "baker" in search_text
    assert "45" in search_text
    assert "banana" in search_text
    assert "mix batter" in search_text
    assert "calories" in search_text
    assert "proteingrams" in search_text
    assert "ripe" not in search_text
    assert "pcs" not in search_text


def test_build_recipe_search_hash_is_stable_for_same_search_text():
    recipe = Recipe(title="Soup", source_name=SourceName.MANUAL, instructions=["Cook"])

    first_hash = build_recipe_search_hash(recipe)
    second_hash = build_recipe_search_hash(recipe)

    assert first_hash == second_hash
    assert len(first_hash) == 64


def test_refresh_recipe_search_text_returns_whether_hash_changed():
    recipe = Recipe(title="Soup", source_name=SourceName.MANUAL, instructions=["Cook"])

    assert refresh_recipe_search_text(recipe) is True
    first_hash = recipe.search_text_hash

    assert refresh_recipe_search_text(recipe) is False
    assert recipe.search_text_hash == first_hash

    recipe.title = "Better Soup"

    assert refresh_recipe_search_text(recipe) is True
    assert recipe.search_text_hash != first_hash
