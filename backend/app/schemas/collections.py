from pydantic import BaseModel, ConfigDict

from app.schemas.recipes import RecipeListItemOut


class CollectionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None


class CollectionOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    recipeCount: int


class CollectionListOut(BaseModel):
    items: list[CollectionOut]


class CollectionDetailOut(CollectionOut):
    recipes: list[RecipeListItemOut]
