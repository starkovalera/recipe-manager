import hashlib
from dataclasses import FrozenInstanceError

import pytest

from app.embeddings.input import build_recipe_embedding_input
from app.models import Ingredient, Recipe, SourceName


def test_embedding_input_uses_only_approved_fields():
    recipe = Recipe(
        title="Soup",
        source_name=SourceName.INSTAGRAM,
        author_name="chef",
        instructions=["Heat water"],
        nutrition_estimate={"calories": 120, "proteinGrams": 18.5, "fatGrams": 6.9, "carbsGrams": 10.5},
        cook_time_minutes=25,
    )
    recipe.ingredients = [
        Ingredient(name="Water", search_name="water", quantity="1", unit="cup", note="filtered", position=0),
    ]

    embedding_input = build_recipe_embedding_input(recipe)
    text = embedding_input.text

    assert "soup" in text
    assert "water" in text
    assert "heat water" in text
    assert "120 calories per serving" in text
    assert "18.5 grams of proteins per serving" in text
    assert "6.9 grams of fat per serving" in text
    assert "10.5 grams of carbs per serving" in text
    assert "cooking time 25 minutes" in text
    assert "instagram" not in text
    assert "chef" not in text
    assert "filtered" not in text
    assert "cup" not in text
    assert embedding_input.input_hash == hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_embedding_input_is_immutable():
    recipe = Recipe(title="Soup", instructions=["Heat water"])

    embedding_input = build_recipe_embedding_input(recipe)

    with pytest.raises(FrozenInstanceError):
        embedding_input.text = "changed"
