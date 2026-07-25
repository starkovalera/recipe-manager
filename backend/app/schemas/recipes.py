from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import ConfigDict, Field, SerializerFunctionWrapHandler, computed_field, model_serializer

from app.models import (
    Collection,
    Ingredient,
    RecipeEmbeddingStatus,
    RecipeImage,
    RecipeResource,
    RecipeResourceStatus,
    RecipeReviewFlag,
    RecipeReviewFlagStatus,
    SourceName,
    SourceType,
    Tag,
)
from app.schemas.base import CamelModel
from app.schemas.pagination import PaginatedOutMixin
from app.schemas.tags import TagOut


class IngredientOut(CamelModel):
    id: str
    name: str
    quantity: str | None = None
    unit: str | None = None
    note: str | None = None
    position: int


class IngredientIn(CamelModel):
    id: str | None = None
    name: str
    quantity: str | None = None
    unit: str | None = None
    note: str | None = None


class NutritionEstimateIn(CamelModel):
    calories: float | None = None
    protein_grams: float | None = None
    fat_grams: float | None = None
    carbs_grams: float | None = None


class RecipeResourceOut(CamelModel):
    id: str
    type: str
    source: str
    role: str
    parent_resource_id: str | None = None
    url: str | None = None
    image_id: str | None = None
    text: str | None = None
    position: int | None = None
    status: str
    assessment_reason: str | None = None
    assessment_confidence: float | None = None


class ReviewFlagOut(CamelModel):
    id: str
    type: str
    status: str
    reason_code: str
    message: str
    details: dict[str, Any] | None = None
    resolved_at: datetime | None = None


class RecipeImageOut(CamelModel):
    id: str


class CoverOptionOut(CamelModel):
    kind: str
    image: RecipeImageOut | None = None
    label: str
    selected: bool


class CoverSelectionIn(CamelModel):
    kind: Literal["DEFAULT", "IMAGE"]
    image_id: str | None = None


class RecipeCollectionOut(CamelModel):
    id: str
    name: str


class RecipeListItemOut(CamelModel):
    id: str
    title: str
    note: str | None = None
    updated_at: datetime | None = None
    cover_image_item: RecipeImage | None = Field(default=None, validation_alias="cover_image", exclude=True)
    review_flag_items: list[RecipeReviewFlag] = Field(default_factory=list, validation_alias="review_flags", exclude=True)

    @computed_field
    @property
    def cover_image(self) -> RecipeImageOut | None:
        return RecipeImageOut.model_validate(self.cover_image_item) if self.cover_image_item is not None else None

    @computed_field
    @property
    def has_open_review_flags(self) -> bool:
        return any(flag.status == RecipeReviewFlagStatus.OPEN for flag in self.review_flag_items)


class RecipeListOut(PaginatedOutMixin):
    items: list[RecipeListItemOut]


def _resource_sort_key(resource) -> tuple[int, str]:
    return (resource.position if resource.position is not None else 9999, resource.id)


def _visible_image_resources(recipe) -> list:
    resources = getattr(recipe, "resource_items", getattr(recipe, "resources", []))
    cover_image_id = recipe.cover_image_item.id if recipe.cover_image_item is not None else None
    resources = [
        resource
        for resource in resources
        if resource.type == SourceType.IMAGE
        and resource.image is not None
        and (resource.status != RecipeResourceStatus.DELETED or resource.image_id == cover_image_id)
    ]
    return sorted(resources, key=_resource_sort_key)


def _cover_options(image_resources: list, cover_image) -> list[CoverOptionOut]:
    options: list[CoverOptionOut] = [
        CoverOptionOut(
            kind="DEFAULT",
            image=None,
            label="Default image",
            selected=cover_image is None,
        )
    ]
    label_index = 1
    for resource in image_resources:
        if resource.image is None:
            continue
        is_selected = cover_image is not None and resource.image_id == cover_image.id
        if is_selected:
            label = "Current cover"
        else:
            label = f"Image {label_index}"
            label_index += 1
        options.append(
            CoverOptionOut(
                kind="IMAGE",
                image=RecipeImageOut.model_validate(resource.image),
                label=label,
                selected=is_selected,
            )
        )
    return options


class RecipeDetailOut(RecipeListItemOut):
    source_name: str
    servings: int | None = None
    cook_time_minutes: int | None = None
    nutrition_estimate: dict[str, Any] | None = None
    author_name: str | None = None
    instructions: list[str]
    tag_items: list[Tag] = Field(default_factory=list, validation_alias="tags", exclude=True)
    ingredient_items: list[Ingredient] = Field(default_factory=list, validation_alias="ingredients", exclude=True)
    resource_items: list[RecipeResource] = Field(default_factory=list, validation_alias="resources", exclude=True)
    collection_items: list[Collection] = Field(default_factory=list, validation_alias="collections", exclude=True)
    debug: RecipeDebugOut | None = None

    @computed_field
    @property
    def tags(self) -> list[TagOut]:
        return [
            TagOut.model_validate(tag)
            for tag in sorted(
                [tag for tag in self.tag_items if tag.deleted_at is None],
                key=lambda item: (item.name.casefold(), item.id),
            )
        ]

    @computed_field
    @property
    def ingredients(self) -> list[IngredientOut]:
        return [IngredientOut.model_validate(ingredient) for ingredient in sorted(self.ingredient_items, key=lambda item: item.position)]

    @computed_field
    @property
    def images(self) -> list[RecipeImageOut]:
        return [RecipeImageOut.model_validate(resource.image) for resource in _visible_image_resources(self) if resource.image is not None]

    @computed_field
    @property
    def cover_options(self) -> list[CoverOptionOut]:
        return _cover_options(_visible_image_resources(self), self.cover_image_item)

    @computed_field
    @property
    def collections(self) -> list[RecipeCollectionOut]:
        return [RecipeCollectionOut.model_validate(collection) for collection in sorted(self.collection_items, key=lambda item: item.name)]

    @computed_field
    @property
    def resources(self) -> list[RecipeResourceOut]:
        visible_resources = [resource for resource in self.resource_items if resource.status != RecipeResourceStatus.DELETED]
        return [RecipeResourceOut.model_validate(resource) for resource in sorted(visible_resources, key=_resource_sort_key)]

    @computed_field
    @property
    def sources(self) -> list[RecipeResourceOut]:
        return self.resources

    @computed_field(alias="reviewFlags")
    @property
    def review_flags(self) -> list[ReviewFlagOut]:
        return [ReviewFlagOut.model_validate(flag) for flag in self.review_flag_items]

    @model_serializer(mode="wrap")
    def serialize_detail(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        data = handler(self)
        if self.debug is None:
            data.pop("debug", None)
        return data


class RecipePatchIn(CamelModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    source_name: SourceName | None = None
    author_name: str | None = None
    servings: int | None = None
    cook_time_minutes: int | None = None
    nutrition_estimate: NutritionEstimateIn | None = None
    ingredients: list[IngredientIn] | None = None
    instructions: list[str] | None = None
    tag_ids: list[str] | None = None
    note: str | None = None
    cover_selection: CoverSelectionIn | None = None


class ReviewFlagPatchIn(CamelModel):
    status: Literal["open", "resolved"]


class RecipeResourcePatchIn(CamelModel):
    status: Literal["used", "deleted"]


class RecipeEmbeddingOut(CamelModel):
    recipe_id: str
    status: RecipeEmbeddingStatus
    model: str
    input_hash: str | None = None
    failed_attempts: int
    error_message: str | None = None


class EmbeddingInputPreviewOut(CamelModel):
    recipe_id: str
    input: str
    input_hash: str


class RecipeDebugOut(CamelModel):
    resources: list[RecipeResourceOut]
    embedding: RecipeEmbeddingOut | None = None
    embedding_input: EmbeddingInputPreviewOut | None = None
