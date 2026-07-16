import json
import logging
from types import SimpleNamespace

import pytest

from app.ai.openai_provider import RECIPE_JSON_SCHEMA, OpenAIRecipeExtractionProvider
from app.ai.schemas import ExtractionSource
from app.core.config import Settings


class FakeResponses:
    def __init__(self, output_text: str):
        self.output_text = output_text
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=self.output_text)


class FakeClient:
    def __init__(self, output_text: str):
        self.responses = FakeResponses(output_text)


def test_openai_response_schema_only_requests_cover_candidate_source_ref():
    cover_schema = RECIPE_JSON_SCHEMA["properties"]["coverCandidate"]
    cover_properties = cover_schema["properties"]

    assert cover_schema["required"] == ["sourceRef", "confidence"]
    assert "sourceRef" in cover_properties
    assert "confidence" in cover_properties
    assert "sourcePosition" not in cover_properties
    assert "crop" not in cover_properties
    assert "reason" not in cover_properties


@pytest.mark.anyio
async def test_openai_provider_uses_reference_responses_input_and_logs_output(caplog):
    raw_output = json.dumps(
        {
            "title": "Roulade",
            "ingredients": [{"name": "Яйцо", "quantity": "1", "unit": "pc", "note": None}],
            "instructions": ["Beat the egg."],
            "servings": 1,
            "cookTimeMinutes": 20,
            "nutritionEstimate": {"calories": 475, "proteinGrams": 33, "fatGrams": 14, "carbsGrams": 55},
            "authorName": "wollmer_fun",
            "tags": ["dessert"],
            "quality": {
                "confidence": 0.91,
                "hasConflicts": True,
                "hasIgnored": True,
                "primarySourceRefs": ["image:source_1"],
                "ignoredSourceRefs": ["image:source_0"],
            },
            "coverCandidate": {
                "sourceRef": "source_1",
                "confidence": 0.87,
            },
        }
    )
    client = FakeClient(raw_output)
    settings = Settings(openai_api_key="test-key", openai_recipe_model="gpt-test")
    provider = OpenAIRecipeExtractionProvider(settings, client=client)
    caplog.set_level(logging.INFO, logger="recipes.ai.openai")

    result = await provider.extract(
        [
            ExtractionSource(
                id="image-source-0",
                type="IMAGE",
                source_ref="source_0",
                storage_key="uploads/source-0.png",
                data_url="data:image/png;base64,SECRET_IMAGE_DATA",
                mime_type="image/png",
                original_name="first.png",
                position=0,
            ),
            ExtractionSource(
                id="image-source-1",
                type="IMAGE",
                source_ref="source_1",
                storage_key="uploads/source-1.png",
                data_url="data:image/png;base64,SECRET_IMAGE_DATA_2",
                mime_type="image/png",
                original_name="second.png",
                position=1,
            ),
        ],
        language="ru",
        tags="десерт, аэрогриль",
    )

    assert result.recipe is not None
    assert result.recipe.title == "Roulade"
    request = client.responses.calls[0]
    content = request["input"][0]["content"]
    assert request["model"] == "gpt-test"
    assert content[0]["type"] == "input_text"
    assert "Return the recipe in ru." in content[0]["text"]
    assert "десерт, аэрогриль" in content[0]["text"]
    assert "{language}" not in content[0]["text"]
    assert "{tags}" not in content[0]["text"]
    assert content[1]["text"] == "Source type=image, id=image-source-0, content:"
    assert content[2] == {"type": "input_image", "detail": "auto", "image_url": "data:image/png;base64,SECRET_IMAGE_DATA"}
    assert content[3]["text"] == "Source type=image, id=image-source-1, content:"
    assert content[4] == {"type": "input_image", "detail": "auto", "image_url": "data:image/png;base64,SECRET_IMAGE_DATA_2"}

    joined_logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "[recipes.ai.openai] Recipe extraction request" in joined_logs
    assert '"input":' in joined_logs
    assert '"content":' in joined_logs
    assert '"data_url": "<redacted>"' in joined_logs
    assert "[recipes.ai.openai] Recipe extraction response" in joined_logs
    assert '"rawOutput":' in joined_logs
    assert '\\"title\\": \\"Roulade\\"' in joined_logs
    assert "SECRET_IMAGE_DATA" not in joined_logs
    assert "image-source-0" in joined_logs


@pytest.mark.anyio
async def test_openai_provider_sends_reference_mixed_source_labels_once():
    raw_output = json.dumps(
        {
            "title": "Pilaf",
            "ingredients": [{"name": "Rice"}],
            "instructions": ["Cook rice."],
            "servings": None,
            "cookTimeMinutes": None,
            "nutritionEstimate": None,
            "authorName": None,
            "tags": [],
            "quality": {
                "confidence": 0.9,
                "hasConflicts": False,
                "hasIgnored": False,
                "primarySourceRefs": ["text-url", "text-manual", "image-manual"],
                "ignoredSourceRefs": [],
            },
            "coverCandidate": None,
        }
    )
    client = FakeClient(raw_output)
    provider = OpenAIRecipeExtractionProvider(Settings(openai_api_key="test-key", openai_recipe_model="gpt-test"), client=client)

    await provider.extract(
        [
            ExtractionSource(id="text-url", type="TEXT", text="URL recipe body", position=0),
            ExtractionSource(id="text-manual", type="TEXT", text="User pasted recipe body", position=1),
            ExtractionSource(
                id="image-manual",
                type="IMAGE",
                source_ref="source_0",
                storage_key="uploads/source-0.png",
                data_url="data:image/png;base64,SECRET_IMAGE_DATA",
                mime_type="image/png",
                original_name="first.png",
                position=2,
            ),
        ],
        language="ru",
        tags="десерт",
    )

    content = client.responses.calls[0]["input"][0]["content"]
    text_blocks = [item for item in content if item["type"] == "input_text"]
    image_blocks = [item for item in content if item["type"] == "input_image"]

    assert len([item for item in text_blocks if "URL recipe body" in item["text"]]) == 1
    assert len([item for item in text_blocks if "User pasted recipe body" in item["text"]]) == 1
    assert any(item["text"] == "Source type=text, id=text-url, content:\nURL recipe body" for item in text_blocks)
    assert any(item["text"] == "Source type=text, id=text-manual, content:\nUser pasted recipe body" for item in text_blocks)
    assert any(item["text"] == "Source type=image, id=image-manual, content:" for item in text_blocks)
    assert image_blocks == [{"type": "input_image", "detail": "auto", "image_url": "data:image/png;base64,SECRET_IMAGE_DATA"}]
