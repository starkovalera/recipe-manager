from typing import Literal

from pydantic import BaseModel, Field


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
    sourcePosition: int = Field(ge=0)
    crop: dict[str, float] | None = None
    confidence: float = Field(default=0, ge=0, le=1)
    reason: str | None = None


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


class ReadySource(BaseModel):
    type: Literal["IMAGE", "URL", "TEXT"]
    position: int
    sourceRef: str | None = None
    storageKey: str | None = None
    dataUrl: str | None = None
    mimeType: str | None = None
    originalName: str | None = None
    url: str | None = None
    authorName: str | None = None
    text: str | None = None


def ready_source_id(source: ReadySource) -> str:
    if source.type == "IMAGE":
        return f"image:{source.sourceRef}"
    if source.type == "URL":
        return f"url:{source.position}"
    return f"text:{source.position}"
