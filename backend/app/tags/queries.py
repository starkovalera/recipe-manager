from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.query_utils import list_scalars_with_optional_pagination
from app.models import RecipeTag, Tag


def get_tag(session: Session, tag_id: str, owner_id: str) -> Tag | None:
    return session.scalar(select(Tag).where(Tag.id == tag_id, Tag.owner_id == owner_id))


def list_active_tags(session: Session, owner_id: str, *, limit: int | None = None, offset: int | None = None) -> list[Tag]:
    query = select(Tag).where(Tag.owner_id == owner_id, Tag.deleted_at.is_(None)).order_by(func.lower(Tag.name), Tag.id)
    return list_scalars_with_optional_pagination(session, query, limit=limit, offset=offset)


def list_active_tags_for_duplicate_check(session: Session, owner_id: str) -> list[Tag]:
    return session.scalars(select(Tag).where(Tag.owner_id == owner_id, Tag.deleted_at.is_(None))).all()


def count_active_tags(session: Session, owner_id: str) -> int:
    return session.scalar(select(func.count(Tag.id)).where(Tag.owner_id == owner_id, Tag.deleted_at.is_(None))) or 0


def count_recipes_for_tag(session: Session, owner_id: str, tag_id: str) -> int:
    return (
        session.scalar(
            select(func.count(RecipeTag.recipe_id))
            .join(Tag, Tag.id == RecipeTag.tag_id)
            .where(Tag.owner_id == owner_id, RecipeTag.tag_id == tag_id)
        )
        or 0
    )


def list_active_tags_by_ids(session: Session, owner_id: str, tag_ids: list[str]) -> list[Tag]:
    if not tag_ids:
        return []
    return session.scalars(
        select(Tag).where(
            Tag.owner_id == owner_id,
            Tag.id.in_(tag_ids),
            Tag.deleted_at.is_(None),
        )
    ).all()
