from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class IngredientOut(BaseModel):
    id: str
    name: str
    quantity: str | None = None
    unit: str | None = None
    note: str | None = None
    position: int


class IngredientIn(BaseModel):
    name: str
    quantity: str | None = None
    unit: str | None = None
    note: str | None = None


class NutritionEstimateIn(BaseModel):
    calories: float | None = None
    proteinGrams: float | None = None
    fatGrams: float | None = None
    carbsGrams: float | None = None


class RecipeSourceOut(BaseModel):
    id: str
    type: str
    source: str
    parentSourceId: str | None = None
    url: str | None = None
    text: str | None = None
    sourceRef: str | None = None
    position: int | None = None
    status: str
    assessmentReason: str | None = None
    assessmentConfidence: float | None = None


class ReviewFlagOut(BaseModel):
    id: str
    type: str
    status: str
    reasonCode: str
    message: str
    details: dict[str, Any] | None = None
    resolvedAt: datetime | None = None


class RecipeImageOut(BaseModel):
    id: str
    role: str
    mediaUrl: str
    sourceImageId: str | None = None


class CoverOptionOut(BaseModel):
    kind: str
    image: RecipeImageOut | None = None
    label: str
    selected: bool


class CoverSelectionIn(BaseModel):
    kind: Literal["DEFAULT", "IMAGE"]
    imageId: str | None = None


class RecipeCollectionOut(BaseModel):
    id: str
    name: str


class RecipeListItemOut(BaseModel):
    id: str
    title: str
    coverImage: RecipeImageOut | None = None
    note: str | None = None
    updatedAt: datetime | None = None


class RecipeListOut(BaseModel):
    items: list[RecipeListItemOut]


class RecipeDetailOut(RecipeListItemOut):
    servings: int | None = None
    cookTimeMinutes: int | None = None
    nutritionEstimate: dict[str, Any] | None = None
    authorName: str | None = None
    sourceName: str
    tags: list[str]
    instructions: list[str]
    ingredients: list[IngredientOut]
    images: list[RecipeImageOut]
    coverImage: RecipeImageOut | None = None
    coverImageSource: str | None = None
    coverOptions: list[CoverOptionOut]
    collections: list[RecipeCollectionOut]
    sources: list[RecipeSourceOut]
    reviewFlags: list[ReviewFlagOut]


class RecipePatchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    servings: int | None = None
    cookTimeMinutes: int | None = None
    nutritionEstimate: NutritionEstimateIn | None = None
    ingredients: list[IngredientIn] | None = None
    instructions: list[str] | None = None
    tags: list[str] | None = None
    note: str | None = None
    coverSelection: CoverSelectionIn | None = None


class ReviewFlagPatchIn(BaseModel):
    status: Literal["open", "resolved"] = Field(...)
