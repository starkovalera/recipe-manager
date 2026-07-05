from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import ApiError, ApiErrorCode
from app.models import Tag
from app.schemas.tags import TagUsageOut
from app.tags.queries import count_active_tags, count_recipes_for_tag, get_tag, list_active_tags, list_active_tags_for_duplicate_check


def _normalize_tag_name(name: str) -> str:
    return " ".join(name.strip().split()).casefold()


def _clean_tag_name(name: str) -> str:
    return " ".join(name.strip().split())


def _get_owner_tag(session: Session, owner_id: str, tag_id: str) -> Tag:
    tag = get_tag(session, tag_id, owner_id)
    if tag is None:
        raise ApiError(ApiErrorCode.TAG_NOT_FOUND, "Tag not found.", status_code=404)
    return tag


def _find_active_by_normalized_name(session: Session, owner_id: str, normalized_name: str, exclude_tag_id: str | None = None) -> Tag | None:
    tags = list_active_tags_for_duplicate_check(session, owner_id)
    for tag in tags:
        if exclude_tag_id is not None and tag.id == exclude_tag_id:
            continue
        if _normalize_tag_name(tag.name) == normalized_name:
            return tag
    return None


def list_tags(session: Session, owner_id: str, *, limit: int, offset: int) -> tuple[list[Tag], int]:
    return list_active_tags(session, owner_id, limit=limit, offset=offset), count_active_tags(session, owner_id)


def create_tag(session: Session, owner_id: str, name: str, description: str | None, settings: Settings) -> Tag:
    if count_active_tags(session, owner_id) >= settings.max_tags_per_user:
        raise ApiError(ApiErrorCode.TAG_LIMIT_EXCEEDED, "Tag limit exceeded.", status_code=400)

    clean_name = _clean_tag_name(name)
    if _find_active_by_normalized_name(session, owner_id, _normalize_tag_name(clean_name)) is not None:
        raise ApiError(ApiErrorCode.DUPLICATE_TAG, "Tag already exists.", status_code=409)

    tag = Tag(owner_id=owner_id, name=clean_name, description=description)
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return tag


def patch_tag(
    session: Session,
    owner_id: str,
    tag_id: str,
    name: str | None,
    description: str | None,
    *,
    description_provided: bool,
) -> Tag:
    tag = _get_owner_tag(session, owner_id, tag_id)
    if tag.deleted_at is not None:
        raise ApiError(ApiErrorCode.TAG_NOT_FOUND, "Tag not found.", status_code=404)

    if name is not None:
        clean_name = _clean_tag_name(name)
        duplicate = _find_active_by_normalized_name(session, owner_id, _normalize_tag_name(clean_name), exclude_tag_id=tag.id)
        if duplicate is not None:
            raise ApiError(ApiErrorCode.DUPLICATE_TAG, "Tag already exists.", status_code=409)
        tag.name = clean_name
    if description_provided:
        tag.description = description
    session.commit()
    session.refresh(tag)
    return tag


def get_tag_usage(session: Session, owner_id: str, tag_id: str) -> TagUsageOut:
    _get_owner_tag(session, owner_id, tag_id)
    return TagUsageOut(recipe_count=count_recipes_for_tag(session, owner_id, tag_id))


def delete_tag(session: Session, owner_id: str, tag_id: str) -> Tag:
    tag = _get_owner_tag(session, owner_id, tag_id)
    if tag.deleted_at is None:
        tag.deleted_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(tag)
    return tag
