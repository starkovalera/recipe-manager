from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.init import ensure_default_user
from app.embeddings.queries import get_recipe_for_embedding
from app.models import Recipe, User


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
