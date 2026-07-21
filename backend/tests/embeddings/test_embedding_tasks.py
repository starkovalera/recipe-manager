import pytest

from app.embeddings import tasks
from app.embeddings.constants import EmbeddingProcessingDisposition
from app.embeddings.outcomes import EmbeddingProcessingResult


def result(disposition: EmbeddingProcessingDisposition) -> EmbeddingProcessingResult:
    return EmbeddingProcessingResult(recipe_id="recipe-1", disposition=disposition)


@pytest.mark.parametrize(
    "disposition",
    [
        EmbeddingProcessingDisposition.SUCCEEDED,
        EmbeddingProcessingDisposition.NOOP,
        EmbeddingProcessingDisposition.REQUEUED,
    ],
)
def test_embedding_actor_acknowledges_completed_dispositions(
    monkeypatch,
    disposition: EmbeddingProcessingDisposition,
) -> None:
    monkeypatch.setattr(tasks, "process_recipe_embedding", lambda _recipe_id: result(disposition))

    assert tasks.embed_recipe_task.fn("recipe-1") is None


@pytest.mark.parametrize(
    "disposition",
    [
        EmbeddingProcessingDisposition.BUSY,
        EmbeddingProcessingDisposition.RETRYABLE_FAILURE,
    ],
)
def test_embedding_actor_raises_for_retryable_dispositions(
    monkeypatch,
    disposition: EmbeddingProcessingDisposition,
) -> None:
    monkeypatch.setattr(tasks, "process_recipe_embedding", lambda _recipe_id: result(disposition))

    with pytest.raises(tasks.RetryableEmbeddingTaskError, match=disposition.value):
        tasks.embed_recipe_task.fn("recipe-1")


def test_embedding_actor_uses_configured_default_retry_count() -> None:
    assert tasks.embed_recipe_task.options["max_retries"] == 2
