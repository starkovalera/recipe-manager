from typing import TypeVar

from sqlalchemy import Select
from sqlalchemy.orm import Session

T = TypeVar("T")


def list_scalars_with_optional_pagination(
    session: Session,
    query: Select[tuple[T]],
    *,
    limit: int | None = None,
    offset: int | None = None,
) -> list[T]:
    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)
    return list(session.scalars(query).all())
