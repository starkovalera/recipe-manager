import json

import pytest
from pydantic import ValidationError

from app.queueing.messages import (
    AccountDeletionQueueMessage,
    ImportJobQueueMessage,
    RecipeEmbeddingQueueMessage,
)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (
            ImportJobQueueMessage(import_job_id="job-1"),
            {"importJobId": "job-1"},
        ),
        (
            RecipeEmbeddingQueueMessage(recipe_id="recipe-1"),
            {"recipeId": "recipe-1"},
        ),
        (
            AccountDeletionQueueMessage(user_id="user-1"),
            {"userId": "user-1"},
        ),
    ],
)
def test_queue_messages_serialize_to_id_only_camel_case_json(
    message,
    expected,
):
    body = message.model_dump_json(by_alias=True)

    assert json.loads(body) == expected
    assert set(json.loads(body)) == set(expected)


@pytest.mark.parametrize(
    ("model", "wire_key", "attribute"),
    [
        (ImportJobQueueMessage, "importJobId", "import_job_id"),
        (RecipeEmbeddingQueueMessage, "recipeId", "recipe_id"),
        (AccountDeletionQueueMessage, "userId", "user_id"),
    ],
)
def test_queue_messages_validate_wire_aliases_and_strip_ids(
    model,
    wire_key,
    attribute,
):
    message = model.model_validate({wire_key: "  entity-1  "})

    assert getattr(message, attribute) == "entity-1"


@pytest.mark.parametrize(
    ("model", "field_name"),
    [
        (ImportJobQueueMessage, "import_job_id"),
        (RecipeEmbeddingQueueMessage, "recipe_id"),
        (AccountDeletionQueueMessage, "user_id"),
    ],
)
def test_queue_messages_reject_blank_ids(model, field_name):
    with pytest.raises(ValidationError):
        model(**{field_name: "   "})


@pytest.mark.parametrize(
    ("model", "field_name"),
    [
        (ImportJobQueueMessage, "import_job_id"),
        (RecipeEmbeddingQueueMessage, "recipe_id"),
        (AccountDeletionQueueMessage, "user_id"),
    ],
)
def test_queue_messages_reject_ids_longer_than_255(model, field_name):
    with pytest.raises(ValidationError):
        model(**{field_name: "x" * 256})


def test_queue_messages_forbid_extra_fields():
    with pytest.raises(ValidationError):
        ImportJobQueueMessage.model_validate(
            {
                "importJobId": "job-1",
                "messageType": "IMPORT_JOB",
            }
        )
