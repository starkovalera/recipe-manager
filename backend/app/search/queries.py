from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Recipe, Tag


def list_active_tag_suggestion_rows(session: Session, owner_id: str) -> list[Tag]:
    return session.scalars(
        select(Tag)
        .where(Tag.owner_id == owner_id, Tag.deleted_at.is_(None))
        .order_by(Tag.name, Tag.id)
    ).all()


def list_recipe_suggestion_rows(session: Session, owner_id: str) -> list[Recipe]:
    return session.scalars(
        select(Recipe)
        .where(Recipe.owner_id == owner_id)
        .order_by(Recipe.title, Recipe.id)
    ).all()

