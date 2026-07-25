import pytest
from pydantic import ValidationError

from app.schemas.media import MediaAccessRequest


def test_media_access_request_requires_between_one_and_one_hundred_strict_items() -> None:
    with pytest.raises(ValidationError):
        MediaAccessRequest.model_validate({"items": []})
    with pytest.raises(ValidationError):
        MediaAccessRequest.model_validate({"items": [{"type": "recipe_image", "id": str(index)} for index in range(101)]})
    with pytest.raises(ValidationError):
        MediaAccessRequest.model_validate({"items": [{"type": "recipe_image", "id": "image-1", "extra": True}]})
    with pytest.raises(ValidationError):
        MediaAccessRequest.model_validate({"items": [{"type": "unsupported", "id": "image-1"}]})
    with pytest.raises(ValidationError):
        MediaAccessRequest.model_validate({"items": [{"type": "recipe_image", "id": "   "}]})
