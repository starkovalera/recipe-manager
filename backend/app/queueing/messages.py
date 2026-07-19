from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

EntityId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=255,
    ),
]


class QueueMessage(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )


class ImportJobQueueMessage(QueueMessage):
    import_job_id: EntityId = Field(alias="importJobId")


class RecipeEmbeddingQueueMessage(QueueMessage):
    recipe_id: EntityId = Field(alias="recipeId")


class AccountDeletionQueueMessage(QueueMessage):
    user_id: EntityId = Field(alias="userId")
