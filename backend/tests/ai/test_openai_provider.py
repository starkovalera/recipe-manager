import json
import logging
from types import SimpleNamespace

import pytest

from app.ai.openai_provider import OpenAIRecipeExtractionProvider
from app.ai.schemas import ReadySource
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


@pytest.mark.anyio
async def test_openai_provider_uses_reference_responses_input_and_logs_output(caplog):
    raw_output = json.dumps(
        {
            "title": "Roulade",
            "ingredients": [{"name": "Egg", "quantity": "1", "unit": "pc", "note": None}],
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
                "sourcePosition": 1,
                "crop": {"x": 0.05, "y": 0.02, "width": 0.55, "height": 0.45},
                "confidence": 0.87,
                "reason": "Finished dish photo is visible.",
            },
        }
    )
    client = FakeClient(raw_output)
    settings = Settings(openai_api_key="test-key", openai_recipe_model="gpt-test")
    provider = OpenAIRecipeExtractionProvider(settings, client=client)
    caplog.set_level(logging.INFO, logger="recipes.ai.openai")

    result = await provider.extract(
        [
            ReadySource(
                type="IMAGE",
                sourceRef="source_0",
                storageKey="uploads/source-0.png",
                dataUrl="data:image/png;base64,SECRET_IMAGE_DATA",
                mimeType="image/png",
                originalName="first.png",
                position=0,
            ),
            ReadySource(
                type="IMAGE",
                sourceRef="source_1",
                storageKey="uploads/source-1.png",
                dataUrl="data:image/png;base64,SECRET_IMAGE_DATA_2",
                mimeType="image/png",
                originalName="second.png",
                position=1,
            ),
        ]
    )

    assert result.recipe is not None
    assert result.recipe.title == "Roulade"
    request = client.responses.calls[0]
    content = request["input"][0]["content"]
    assert request["model"] == "gpt-test"
    assert content[0]["type"] == "input_text"
    assert content[1]["text"].startswith("Source sourceId=image:source_0")
    assert content[2] == {"type": "input_image", "detail": "auto", "image_url": "data:image/png;base64,SECRET_IMAGE_DATA"}
    assert content[3]["text"].startswith("Source sourceId=image:source_1")
    assert content[4] == {"type": "input_image", "detail": "auto", "image_url": "data:image/png;base64,SECRET_IMAGE_DATA_2"}

    joined_logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "[recipes.ai.openai] Recipe extraction response" in joined_logs
    assert '"rawOutput":' in joined_logs
    assert '\\"title\\": \\"Roulade\\"' in joined_logs
    assert "SECRET_IMAGE_DATA" not in joined_logs
    assert "image:source_0" in joined_logs
