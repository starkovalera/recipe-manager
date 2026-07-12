from app.embeddings.input import build_recipe_embedding_input
from app.models import Recipe
from app.schemas.recipes import (
    EmbeddingInputPreviewOut,
    RecipeDebugOut,
    RecipeDetailOut,
    RecipeEmbeddingOut,
    RecipeResourceOut,
)


def build_recipe_detail_response(recipe: Recipe, *, include_debug: bool) -> RecipeDetailOut:
    response = RecipeDetailOut.model_validate(recipe)
    if not include_debug:
        return response

    embedding_input = build_recipe_embedding_input(recipe)
    response.debug = RecipeDebugOut(
        resources=[RecipeResourceOut.model_validate(resource) for resource in recipe.resources],
        embedding=RecipeEmbeddingOut.model_validate(recipe.embedding) if recipe.embedding is not None else None,
        embedding_input=EmbeddingInputPreviewOut(
            recipe_id=recipe.id,
            input=embedding_input.text,
            input_hash=embedding_input.input_hash,
        ),
    )
    return response
