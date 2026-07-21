from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import session as session_module
from app.db.base import Base
from app.maintenance import recipes as maintenance_recipes
from app.maintenance.constants import MaintenanceProcessingDisposition
from app.models import Recipe, RecipeStatus, User
from app.recipes.deletion import RecipeDeletionProcessingDisposition, RecipeDeletionProcessingResult


def _factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _configure(monkeypatch, factory) -> None:
    monkeypatch.setattr(session_module, "SessionLocal", factory)
    monkeypatch.setattr(
        maintenance_recipes,
        "get_settings",
        lambda: SimpleNamespace(maintenance_batch_size=100, stale_recipe_deletion_minutes=60),
    )


def test_stale_recipe_deletion_processes_bounded_candidates(monkeypatch) -> None:
    factory = _factory()
    stale_at = datetime.now(timezone.utc) - timedelta(hours=2)
    with factory() as session:
        user = User(id="user-1", email="user@example.test")
        session.add_all(
            [
                Recipe(id="stale", owner=user, title="Stale", status=RecipeStatus.DELETION_PENDING, updated_at=stale_at),
                Recipe(id="fresh", owner=user, title="Fresh", status=RecipeStatus.DELETION_PENDING),
            ]
        )
        session.commit()
    _configure(monkeypatch, factory)
    processed: list[str] = []
    monkeypatch.setattr(
        maintenance_recipes,
        "process_recipe_deletion",
        lambda recipe_id: processed.append(recipe_id)
        or RecipeDeletionProcessingResult(recipe_id, RecipeDeletionProcessingDisposition.COMPLETED),
    )

    result = maintenance_recipes.reconcile_stale_recipe_deletions()

    assert result.disposition is MaintenanceProcessingDisposition.COMPLETED
    assert processed == ["stale"]
    assert result.changed_count == 1


def test_stale_recipe_deletion_continues_and_aggregates_retryable_failure(monkeypatch) -> None:
    factory = _factory()
    stale_at = datetime.now(timezone.utc) - timedelta(hours=2)
    with factory() as session:
        user = User(id="user-1", email="user@example.test")
        session.add_all(
            [
                Recipe(id="one", owner=user, title="One", status=RecipeStatus.DELETION_PENDING, updated_at=stale_at),
                Recipe(id="two", owner=user, title="Two", status=RecipeStatus.DELETION_PENDING, updated_at=stale_at),
            ]
        )
        session.commit()
    _configure(monkeypatch, factory)
    monkeypatch.setattr(
        maintenance_recipes,
        "process_recipe_deletion",
        lambda recipe_id: RecipeDeletionProcessingResult(
            recipe_id,
            RecipeDeletionProcessingDisposition.RETRYABLE_FAILURE
            if recipe_id == "one"
            else RecipeDeletionProcessingDisposition.NOOP,
        ),
    )

    result = maintenance_recipes.reconcile_stale_recipe_deletions()

    assert result.disposition is MaintenanceProcessingDisposition.RETRYABLE_FAILURE
    assert result.scanned_count == 2
    assert result.failure_count == 1
