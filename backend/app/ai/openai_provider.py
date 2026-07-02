import json
import logging
from typing import Any

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.ai.prompt import recipe_extraction_prompt
from app.ai.provider import RecipeExtractionProvider
from app.ai.schemas import ExtractedRecipe, ExtractionResult, ReadySource, ready_source_id
from app.core.config import Settings
from app.core.logging import log_info

logger = logging.getLogger("recipes.ai.openai")


RECIPE_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "notARecipe": {"type": "boolean"},
        "title": {"type": "string"},
        "ingredients": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "quantity": {"type": ["string", "null"]},
                    "unit": {"type": ["string", "null"]},
                    "note": {"type": ["string", "null"]},
                },
                "required": ["name"],
            },
        },
        "instructions": {"type": "array", "items": {"type": "string"}},
        "servings": {"type": ["integer", "null"]},
        "cookTimeMinutes": {"type": ["integer", "null"]},
        "nutritionEstimate": {
            "type": ["object", "null"],
            "additionalProperties": False,
            "properties": {
                "calories": {"type": ["number", "null"]},
                "proteinGrams": {"type": ["number", "null"]},
                "fatGrams": {"type": ["number", "null"]},
                "carbsGrams": {"type": ["number", "null"]},
            },
        },
        "authorName": {"type": ["string", "null"]},
        "tags": {"type": "array", "items": {"type": "string"}},
        "quality": {
            "type": ["object", "null"],
            "additionalProperties": False,
            "properties": {
                "confidence": {"type": "number"},
                "hasConflicts": {"type": "boolean"},
                "hasIgnored": {"type": "boolean"},
                "primarySourceRefs": {"type": "array", "items": {"type": "string"}},
                "ignoredSourceRefs": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["confidence", "hasConflicts", "hasIgnored", "primarySourceRefs", "ignoredSourceRefs"],
        },
        "coverCandidate": {
            "type": ["object", "null"],
            "additionalProperties": False,
            "properties": {
                "sourceRef": {"type": "string"},
                "confidence": {"type": "number"},
            },
            "required": ["sourceRef", "confidence"],
        },
    },
}


def _source_log_summary(source: ReadySource) -> dict[str, Any]:
    if source.type == "IMAGE":
        return {
            "type": source.type,
            "sourceId": ready_source_id(source),
            "sourceRef": source.sourceRef,
            "position": source.position,
            "originalName": source.originalName,
            "mimeType": source.mimeType,
        }
    if source.type == "URL":
        return {
            "type": source.type,
            "sourceId": ready_source_id(source),
            "position": source.position,
            "url": source.url,
            "authorName": source.authorName,
        }
    return {"type": source.type, "sourceId": ready_source_id(source), "position": source.position}


def _source_label(source: ReadySource) -> dict[str, str]:
    if source.type == "IMAGE":
        text = f"Source type=image, id={ready_source_id(source)}, content:"
    else:
        text = f"Source type=text, id={ready_source_id(source)}, content:\n{source.text}"
    return {"type": "input_text", "text": text}


def _source_to_extraction_content(source: ReadySource) -> list[dict[str, Any]]:
    label = _source_label(source)
    if source.type == "IMAGE":
        return [
            label,
            {"type": "input_image", "detail": "auto", "image_url": source.dataUrl},
        ]
    return [label]


def _content_for_sources(sources: list[ReadySource], *, language: str, tags: str) -> list[dict[str, Any]]:
    prompt = recipe_extraction_prompt.format(language=language, tags=tags)
    content: list[dict[str, Any]] = [{"type": "input_text", "text": prompt}]
    for source in sources:
        content.extend(_source_to_extraction_content(source))
    return content


def _parse_recipe_json(text: str) -> ExtractionResult:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        return ExtractionResult(not_a_recipe=True, error_code="AI_PARSE_FAILED", error_message=str(error))
    if isinstance(payload, dict) and payload.get("notARecipe") is True:
        return ExtractionResult(not_a_recipe=True)
    try:
        return ExtractionResult(recipe=ExtractedRecipe.model_validate(payload))
    except ValidationError as error:
        return ExtractionResult(not_a_recipe=True, error_code="INVALID_EXTRACTION_RESULT", error_message=str(error))


class OpenAIRecipeExtractionProvider(RecipeExtractionProvider):
    def __init__(self, settings: Settings, client: AsyncOpenAI | None = None):
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when AI_PROVIDER=openai.")
        self.settings = settings
        self.client = client or AsyncOpenAI(api_key=settings.openai_api_key)

    async def extract(self, sources: list[ReadySource], *, language: str, tags: str) -> ExtractionResult:
        content = _content_for_sources(sources, language=language, tags=tags)
        log_info(
            logger,
            "[recipes.ai.openai] Recipe extraction request",
            model=self.settings.openai_recipe_model,
            language=language,
            tags=tags,
            sources=[source.model_dump() for source in sources],
            sourceCount=len(sources),
            imageSourceCount=len([source for source in sources if source.type == "IMAGE"]),
            input=[{"role": "user", "content": content}],
        )
        try:
            response = await self.client.responses.create(
                model=self.settings.openai_recipe_model,
                input=[{"role": "user", "content": content}],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "recipe_extraction_result",
                        "schema": RECIPE_JSON_SCHEMA,
                        "description": "Recipe extraction result or a not-a-recipe marker.",
                        "strict": False,
                    }
                },
            )
        except Exception as error:
            log_info(
                logger,
                "[recipes.ai.openai] Recipe extraction request failed",
                model=self.settings.openai_recipe_model,
                sources=[_source_log_summary(source) for source in sources],
                sourceCount=len(sources),
                imageSourceCount=len([source for source in sources if source.type == "IMAGE"]),
                error=repr(error),
            )
            return ExtractionResult(not_a_recipe=True, error_code="AI_UNAVAILABLE", error_message="AI extraction is unavailable.")

        text = response.output_text or "{}"
        result = _parse_recipe_json(text)
        if result.recipe is not None:
            parsed: Any = result.recipe.model_dump()
        elif result.not_a_recipe and not result.error_code:
            parsed = "NOT_A_RECIPE"
        else:
            parsed = {"errorCode": result.error_code, "errorMessage": result.error_message}
        log_info(
            logger,
            "[recipes.ai.openai] Recipe extraction response",
            model=self.settings.openai_recipe_model,
            sources=[_source_log_summary(source) for source in sources],
            sourceCount=len(sources),
            imageSourceCount=len([source for source in sources if source.type == "IMAGE"]),
            rawOutput=text,
            parsed=parsed,
        )
        return result
