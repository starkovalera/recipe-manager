from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.init import ensure_default_user
from app.embeddings.events import EmbeddingEventType, add_embedding_event
from app.models import Recipe, RecipeEmbedding, RecipeEmbeddingEvent, RecipeEmbeddingStatus


def session_factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_add_embedding_event_snapshots_current_embedding_status():
    SessionLocal = session_factory()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        recipe = Recipe(owner_id=user.id, title="Soup", instructions=["Heat water"])
        recipe.embedding = RecipeEmbedding(model="test-embedding", status=RecipeEmbeddingStatus.RUNNING.value)
        session.add(recipe)
        session.flush()

        event = add_embedding_event(
            session,
            embedding=recipe.embedding,
            owner_id=user.id,
            event_type=EmbeddingEventType.STARTED,
            payload={"inputHash": "hash-1"},
        )
        session.commit()

        saved = session.get(RecipeEmbeddingEvent, event.id)
        assert saved is not None
        assert saved.recipe_id == recipe.id
        assert saved.owner_id == user.id
        assert saved.event_type == EmbeddingEventType.STARTED
        assert saved.status_after == RecipeEmbeddingStatus.RUNNING.value
        assert saved.payload == {"inputHash": "hash-1"}
