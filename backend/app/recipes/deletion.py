import logging
from dataclasses import dataclass
from enum import StrEnum

from app.core.logging import log_error, log_info
from app.db.session import db_session
from app.models import RecipeStatus
from app.recipes.deletion_storage import get_recipe_deletion_storage
from app.recipes.queries import get_recipe_for_deletion
from app.storage.base import StorageService

logger = logging.getLogger(__name__)


class RecipeDeletionProcessingDisposition(StrEnum):
    COMPLETED = "COMPLETED"
    NOOP = "NOOP"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"


@dataclass(frozen=True)
class RecipeDeletionProcessingResult:
    recipe_id: str
    disposition: RecipeDeletionProcessingDisposition
    failed_storage_key_count: int = 0


def process_recipe_deletion(
    recipe_id: str,
    *,
    storage: StorageService | None = None,
) -> RecipeDeletionProcessingResult:
    with db_session() as session:
        recipe = get_recipe_for_deletion(
            session,
            recipe_id,
            owner_id=None,
            status=RecipeStatus.DELETION_PENDING,
        )
        if recipe is None:
            return RecipeDeletionProcessingResult(recipe_id, RecipeDeletionProcessingDisposition.NOOP)
        storage_keys = tuple(sorted({image.storage_key for image in recipe.images}))

    try:
        resolved_storage = storage if storage is not None else get_recipe_deletion_storage()
    except Exception as error:
        log_error(logger, "Recipe deletion storage is unavailable.", recipe_id=recipe_id, error_type=type(error).__name__)
        return RecipeDeletionProcessingResult(recipe_id, RecipeDeletionProcessingDisposition.RETRYABLE_FAILURE)

    failed_storage_key_count = 0
    for storage_key in storage_keys:
        try:
            resolved_storage.delete(storage_key)
        except Exception as error:
            failed_storage_key_count += 1
            log_error(
                logger,
                "Recipe media cleanup failed.",
                recipe_id=recipe_id,
                storage_key=storage_key,
                error_type=type(error).__name__,
            )
    if failed_storage_key_count:
        return RecipeDeletionProcessingResult(
            recipe_id,
            RecipeDeletionProcessingDisposition.RETRYABLE_FAILURE,
            failed_storage_key_count,
        )

    try:
        with db_session() as session:
            recipe = get_recipe_for_deletion(
                session,
                recipe_id,
                owner_id=None,
                status=RecipeStatus.DELETION_PENDING,
                for_update=True,
            )
            if recipe is None:
                return RecipeDeletionProcessingResult(recipe_id, RecipeDeletionProcessingDisposition.NOOP)
            session.delete(recipe)
    except Exception as error:
        log_error(logger, "Recipe database deletion failed.", recipe_id=recipe_id, error_type=type(error).__name__)
        return RecipeDeletionProcessingResult(recipe_id, RecipeDeletionProcessingDisposition.RETRYABLE_FAILURE)

    log_info(logger, "Recipe deletion completed.", recipe_id=recipe_id)
    return RecipeDeletionProcessingResult(recipe_id, RecipeDeletionProcessingDisposition.COMPLETED)
