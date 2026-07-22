from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import session as session_module
from app.db.base import Base
from app.models import Recipe, RecipeImage, RecipeStatus, User
from app.recipes.deletion import RecipeDeletionProcessingDisposition, process_recipe_deletion
from app.storage.constants import StorageLocation


def _factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


class RecordingStorage:
    def __init__(self, failing_key: str | None = None) -> None:
        self.failing_key = failing_key
        self.deleted: list[tuple[StorageLocation, str]] = []

    def delete(self, location: StorageLocation, storage_key: str) -> None:
        self.deleted.append((location, storage_key))
        if storage_key == self.failing_key:
            raise OSError("failure")


def _add_pending_recipe(factory) -> None:
    with factory() as session:
        user = User(id="user-1", email="user@example.test")
        recipe = Recipe(id="recipe-1", owner=user, title="Recipe", status=RecipeStatus.DELETION_PENDING)
        recipe.images = [
            RecipeImage(storage_key="one.jpg", original_name="one.jpg", mime_type="image/jpeg", size_bytes=1, position=0),
            RecipeImage(storage_key="two.jpg", original_name="two.jpg", mime_type="image/jpeg", size_bytes=1, position=1),
            RecipeImage(storage_key="one.jpg", original_name="copy.jpg", mime_type="image/jpeg", size_bytes=1, position=2),
        ]
        session.add(recipe)
        session.commit()


def test_recipe_deletion_removes_each_unique_key_and_recipe(monkeypatch) -> None:
    factory = _factory()
    _add_pending_recipe(factory)
    monkeypatch.setattr(session_module, "SessionLocal", factory)
    storage = RecordingStorage()

    result = process_recipe_deletion("recipe-1", storage=storage)

    assert result.disposition is RecipeDeletionProcessingDisposition.COMPLETED
    assert storage.deleted == [
        (StorageLocation.USER_MEDIA, "one.jpg"),
        (StorageLocation.USER_MEDIA, "two.jpg"),
    ]
    with factory() as session:
        assert session.get(Recipe, "recipe-1") is None


def test_recipe_deletion_storage_failure_leaves_recipe_pending_and_attempts_all_keys(monkeypatch) -> None:
    factory = _factory()
    _add_pending_recipe(factory)
    monkeypatch.setattr(session_module, "SessionLocal", factory)
    storage = RecordingStorage(failing_key="one.jpg")

    result = process_recipe_deletion("recipe-1", storage=storage)

    assert result.disposition is RecipeDeletionProcessingDisposition.RETRYABLE_FAILURE
    assert result.failed_storage_key_count == 1
    assert storage.deleted == [
        (StorageLocation.USER_MEDIA, "one.jpg"),
        (StorageLocation.USER_MEDIA, "two.jpg"),
    ]
    with factory() as session:
        assert session.get(Recipe, "recipe-1").status is RecipeStatus.DELETION_PENDING


def test_recipe_deletion_is_noop_for_missing_or_active_recipe(monkeypatch) -> None:
    factory = _factory()
    with factory() as session:
        session.add(Recipe(id="active", owner=User(id="user-1", email="user@example.test"), title="Recipe"))
        session.commit()
    monkeypatch.setattr(session_module, "SessionLocal", factory)

    assert process_recipe_deletion("missing", storage=RecordingStorage()).disposition is RecipeDeletionProcessingDisposition.NOOP
    assert process_recipe_deletion("active", storage=RecordingStorage()).disposition is RecipeDeletionProcessingDisposition.NOOP
