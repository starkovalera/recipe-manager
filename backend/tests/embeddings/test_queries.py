from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from app.db.base import Base
from app.embeddings.queries import (
    build_active_recipe_for_embedding_for_update_statement,
    get_active_recipe_for_embedding_for_update,
    get_recipe_for_embedding,
)
from app.local.users import ensure_default_user
from app.models import (
    Ingredient,
    Recipe,
    RecipeEmbedding,
    RecipeEmbeddingStatus,
    RecipeReviewFlag,
    RecipeReviewFlagStatus,
    RecipeReviewFlagType,
    RecipeStatus,
    User,
)


def test_get_recipe_for_embedding_applies_owner_filter_only_when_provided():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        owner = ensure_default_user(session)
        other_owner = User(id="other-user", email="other@example.test")
        recipe = Recipe(owner_id=owner.id, title="Soup", instructions=["Heat water"])
        session.add_all([other_owner, recipe])
        session.commit()

        assert get_recipe_for_embedding(session, recipe.id) is recipe
        assert get_recipe_for_embedding(session, recipe.id, owner_id=owner.id) is recipe
        assert get_recipe_for_embedding(session, recipe.id, owner_id=other_owner.id) is None


def test_get_recipe_for_embedding_excludes_pending_recipes_by_default():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        owner = ensure_default_user(session)
        recipe = Recipe(
            owner_id=owner.id,
            title="Soup",
            instructions=["Heat water"],
            status=RecipeStatus.DELETION_PENDING,
        )
        session.add(recipe)
        session.commit()

        assert get_recipe_for_embedding(session, recipe.id) is None
        assert get_recipe_for_embedding(session, recipe.id, status=None) is recipe


def test_get_active_recipe_for_embedding_for_update_loads_claim_dependencies() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        owner = ensure_default_user(session)
        recipe = Recipe(owner_id=owner.id, title="Soup", instructions=["Heat water"])
        recipe.ingredients.append(Ingredient(name="Water", search_name="water", position=0))
        recipe.review_flags.append(
            RecipeReviewFlag(
                owner_id=owner.id,
                type=RecipeReviewFlagType.CONTENT_WARNING,
                status=RecipeReviewFlagStatus.RESOLVED,
                reason_code="CONTENT_WARNING",
                message="Resolved.",
            )
        )
        recipe.embedding = RecipeEmbedding(model="test-model", status=RecipeEmbeddingStatus.STALE)
        session.add(recipe)
        session.commit()

        loaded = get_active_recipe_for_embedding_for_update(session, recipe.id)

        assert loaded is recipe
        assert [ingredient.name for ingredient in loaded.ingredients] == ["Water"]
        assert len(loaded.review_flags) == 1
        assert loaded.embedding is recipe.embedding


def test_get_active_recipe_for_embedding_for_update_excludes_pending_recipe() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        owner = ensure_default_user(session)
        recipe = Recipe(
            owner_id=owner.id,
            title="Soup",
            instructions=["Heat water"],
            status=RecipeStatus.DELETION_PENDING,
        )
        session.add(recipe)
        session.commit()

        assert get_active_recipe_for_embedding_for_update(session, recipe.id) is None
        assert get_active_recipe_for_embedding_for_update(session, "missing") is None


def test_active_recipe_embedding_claim_statement_locks_recipe_row() -> None:
    statement = build_active_recipe_for_embedding_for_update_statement("recipe-1")
    sql = str(statement.compile(dialect=postgresql.dialect()))

    assert "recipes.status =" in sql
    assert "FOR UPDATE" in sql
