from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExtractedIngredient(BaseModel):
    name: str = Field(min_length=1)
    quantity: str | None = None
    unit: str | None = None
    note: str | None = None


class NutritionEstimate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    calories: float | None = None
    protein_grams: float | None = Field(default=None, alias="proteinGrams", validation_alias="proteinGrams")
    fat_grams: float | None = Field(default=None, alias="fatGrams", validation_alias="fatGrams")
    carbs_grams: float | None = Field(default=None, alias="carbsGrams", validation_alias="carbsGrams")


class ExtractionQuality(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    confidence: float = Field(ge=0, le=1)
    has_conflicts: bool = Field(alias="hasConflicts", validation_alias="hasConflicts")
    has_ignored: bool = Field(alias="hasIgnored", validation_alias="hasIgnored")
    primary_source_refs: list[str] = Field(default_factory=list, alias="primarySourceRefs", validation_alias="primarySourceRefs")
    ignored_source_refs: list[str] = Field(default_factory=list, alias="ignoredSourceRefs", validation_alias="ignoredSourceRefs")


class CoverCandidate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source_ref: str = Field(min_length=1, alias="sourceRef", validation_alias="sourceRef")
    confidence: float = Field(ge=0, le=1)
    # Legacy compatibility only: OpenAI is instructed/schema-constrained to
    # return sourceRef and confidence. Keep these as None-only fields until the
    # old internal cover-candidate shape is removed from callers/tests.
    source_position: None = Field(default=None, alias="sourcePosition", validation_alias="sourcePosition")
    crop: None = None
    reason: None = None


class ExtractedRecipe(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str = Field(min_length=1)
    ingredients: list[ExtractedIngredient] = Field(min_length=1)
    instructions: list[str] = Field(min_length=1)
    servings: int | None = Field(default=None, gt=0)
    cook_time_minutes: int | None = Field(default=None, gt=0, alias="cookTimeMinutes", validation_alias="cookTimeMinutes")
    nutrition_estimate: NutritionEstimate | None = Field(default=None, alias="nutritionEstimate", validation_alias="nutritionEstimate")
    author_name: str | None = Field(default=None, alias="authorName", validation_alias="authorName")
    tags: list[str] = Field(default_factory=list)
    quality: ExtractionQuality
    cover_candidate: CoverCandidate | None = Field(default=None, alias="coverCandidate", validation_alias="coverCandidate")


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
    source_ref: str | None = Field(default=None, alias="sourceRef", validation_alias="sourceRef")
    storage_key: str | None = Field(default=None, alias="storageKey", validation_alias="storageKey")
    data_url: str | None = Field(default=None, alias="dataUrl", validation_alias="dataUrl")
    mime_type: str | None = Field(default=None, alias="mimeType", validation_alias="mimeType")
    original_name: str | None = Field(default=None, alias="originalName", validation_alias="originalName")
    url: str | None = None
    author_name: str | None = Field(default=None, alias="authorName", validation_alias="authorName")
    text: str | None = None


def extraction_source_id(source: ExtractionSource) -> str:
    if source.id:
        return source.id
    if source.type == "IMAGE":
        return f"image:{source.source_ref}"
    if source.type == "URL":
        return f"url:{source.position}"
    return f"text:{source.position}"
