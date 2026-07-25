from types import SimpleNamespace

from app.schemas.imports import ImportJobSourceOut
from app.schemas.recipes import RecipeImageOut


def test_recipe_image_output_exposes_only_stable_id() -> None:
    image = SimpleNamespace(id="image-1", storage_key="recipes/media/owner/recipe/secret.jpg")

    assert RecipeImageOut.model_validate(image).model_dump(by_alias=True) == {"id": "image-1"}


def test_import_source_output_exposes_id_without_storage_metadata() -> None:
    source = SimpleNamespace(
        id="source-1",
        type="IMAGE",
        url=None,
        original_name="recipe.jpg",
        text=None,
        image_storage_key="imports/source/owner/job/secret.jpg",
    )

    assert ImportJobSourceOut.model_validate(source).model_dump(by_alias=True) == {
        "id": "source-1",
        "type": "IMAGE",
        "url": None,
        "originalName": "recipe.jpg",
        "text": None,
    }
