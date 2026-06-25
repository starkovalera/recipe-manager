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


class RecipeSourceOut(BaseModel):
    id: str
    type: str
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


class RecipeListItemOut(BaseModel):
    id: str
    title: str
    note: str | None = None
    updatedAt: datetime | None = None


class RecipeListOut(BaseModel):
    items: list[RecipeListItemOut]


class RecipeDetailOut(RecipeListItemOut):
    servings: int | None = None
    cookTimeMinutes: int | None = None
    instructions: list[str]
    ingredients: list[IngredientOut]
    sources: list[RecipeSourceOut]
    reviewFlags: list[ReviewFlagOut]


class RecipePatchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    servings: int | None = None
    cookTimeMinutes: int | None = None
    instructions: list[str] | None = None
    note: str | None = None


class ReviewFlagPatchIn(BaseModel):
    status: Literal["open", "resolved"] = Field(...)
