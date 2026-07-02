from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models import Recipe
from app.schemas.base import CamelModel
from app.schemas.pagination import PaginatedOutMixin
from app.schemas.recipes import RecipeListItemOut


class CollectionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None


class CollectionOut(CamelModel):
    id: str
    name: str
    description: str | None = None
    recipe_items: list[Recipe] = Field(default_factory=list, validation_alias="recipes", exclude=True)

    @computed_field
    @property
    def recipe_count(self) -> int:
        return len(self.recipe_items)


class CollectionListOut(PaginatedOutMixin):
    items: list[CollectionOut]


class CollectionDetailOut(CollectionOut):
    @computed_field
    @property
    def recipes(self) -> list[RecipeListItemOut]:  # type: ignore[no-redef]
        return [RecipeListItemOut.model_validate(recipe) for recipe in self.recipe_items]
