from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExtractedIngredient(BaseModel):
    name: str = Field(min_length=1)
    quantity: str | None = None
    unit: str | None = None
    note: str | None = None


class NutritionEstimate(BaseModel):
    calories: float | None = None
    proteinGrams: float | None = None
    fatGrams: float | None = None
    carbsGrams: float | None = None


class ExtractionQuality(BaseModel):
    confidence: float = Field(ge=0, le=1)
    hasConflicts: bool
    hasIgnored: bool
    primarySourceRefs: list[str] = Field(default_factory=list)
    ignoredSourceRefs: list[str] = Field(default_factory=list)


class CoverCandidate(BaseModel):
    sourceRef: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    # Legacy compatibility only: OpenAI is instructed/schema-constrained to
    # return sourceRef and confidence. Keep these as None-only fields until the
    # old internal cover-candidate shape is removed from callers/tests.
    sourcePosition: None = None
    crop: None = None
    reason: None = None


class ExtractedRecipe(BaseModel):
    title: str = Field(min_length=1)
    ingredients: list[ExtractedIngredient] = Field(min_length=1)
    instructions: list[str] = Field(min_length=1)
    servings: int | None = Field(default=None, gt=0)
    cookTimeMinutes: int | None = Field(default=None, gt=0)
    nutritionEstimate: NutritionEstimate | None = None
    authorName: str | None = None
    tags: list[str] = Field(default_factory=list)
    quality: ExtractionQuality
    coverCandidate: CoverCandidate | None = None


class ExtractionResult(BaseModel):
    recipe: ExtractedRecipe | None = None
    not_a_recipe: bool = False
    error_code: str | None = None
    error_message: str | None = None


class ExtractionSource(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = None
    type: Literal["IMAGE", "URL", "TEXT"]
    position: int
    source_ref: str | None = Field(default=None, alias="sourceRef")
    storage_key: str | None = Field(default=None, alias="storageKey")
    data_url: str | None = Field(default=None, alias="dataUrl")
    mime_type: str | None = Field(default=None, alias="mimeType")
    original_name: str | None = Field(default=None, alias="originalName")
    url: str | None = None
    author_name: str | None = Field(default=None, alias="authorName")
    text: str | None = None


def extraction_source_id(source: ExtractionSource) -> str:
    if source.id:
        return source.id
    if source.type == "IMAGE":
        return f"image:{source.source_ref}"
    if source.type == "URL":
        return f"url:{source.position}"
    return f"text:{source.position}"
