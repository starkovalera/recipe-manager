import json
from typing import Any

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.ai.prompt import recipe_extraction_prompt
from app.ai.provider import RecipeExtractionProvider
from app.ai.schemas import ExtractedRecipe, ExtractionResult, ReadySource
from app.core.config import Settings


def _source_text(source: ReadySource) -> str:
    if source.type == "TEXT":
        return f"TEXT source text:{source.text or ''}"
    if source.type == "URL":
        return f"URL source url={source.url or ''} text:{source.text or ''}"
    return f"IMAGE sourceRef={source.sourceRef or ''} originalName={source.originalName or ''}"


def _content_for_sources(sources: list[ReadySource]) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": "\n\n".join(
                [
                    "Return strict JSON with either:",
                    '{"not_a_recipe": true}',
                    "or",
                    '{"recipe": {"title": "...", "ingredients": [{"name": "..."}], "instructions": ["..."], "quality": {"confidence": 0.9, "hasConflicts": false, "hasIgnored": false, "primarySourceRefs": [], "ignoredSourceRefs": []}, "coverCandidate": null}}',
                    "Use source refs exactly as described below.",
                    *[_source_text(source) for source in sources],
                ]
            ),
        }
    ]
    for source in sources:
        if source.type == "IMAGE" and source.dataUrl:
            content.append({"type": "image_url", "image_url": {"url": source.dataUrl}})
    return content


def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("notARecipe") is True:
        payload["not_a_recipe"] = True
    return payload


class OpenAIRecipeExtractionProvider(RecipeExtractionProvider):
    def __init__(self, settings: Settings, client: AsyncOpenAI | None = None):
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when AI_PROVIDER=openai.")
        self.settings = settings
        self.client = client or AsyncOpenAI(api_key=settings.openai_api_key)

    async def extract(self, sources: list[ReadySource]) -> ExtractionResult:
        completion = await self.client.chat.completions.create(
            model=self.settings.openai_recipe_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": recipe_extraction_prompt},
                {"role": "user", "content": _content_for_sources(sources)},
            ],
        )
        text = completion.choices[0].message.content or "{}"
        try:
            payload = _normalize_payload(json.loads(text))
            result = ExtractionResult.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as error:
            return ExtractionResult(not_a_recipe=True, error_code="INVALID_EXTRACTION_RESULT", error_message=str(error))
        if result.recipe is not None:
            # Force a full validation path for nested recipe payloads coming from model JSON.
            result = result.model_copy(update={"recipe": ExtractedRecipe.model_validate(result.recipe)})
        return result
