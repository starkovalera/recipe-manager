from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.embeddings.events import add_embedding_event
from app.local.users import ensure_default_user
from app.models import Recipe, RecipeEmbedding, RecipeEmbeddingEvent, RecipeEmbeddingEventType, RecipeEmbeddingStatus


def session_factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_add_embedding_event_snapshots_current_embedding_status():
    SessionLocal = session_factory()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        recipe = Recipe(owner_id=user.id, title="Soup", instructions=["Heat water"])
        recipe.embedding = RecipeEmbedding(model="test-embedding", status=RecipeEmbeddingStatus.RUNNING)
        session.add(recipe)
        session.flush()

        event = add_embedding_event(
            session,
            embedding=recipe.embedding,
            owner_id=user.id,
            event_type=RecipeEmbeddingEventType.STARTED,
            payload={"inputHash": "hash-1"},
        )
        session.commit()

        saved = session.get(RecipeEmbeddingEvent, event.id)
        assert saved is not None
        assert saved.recipe_id == recipe.id
        assert saved.owner_id == user.id
        assert saved.event_type is RecipeEmbeddingEventType.STARTED
        assert saved.status_after is RecipeEmbeddingStatus.RUNNING
        assert saved.payload == {"inputHash": "hash-1"}
