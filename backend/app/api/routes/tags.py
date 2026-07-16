from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUserDep, SessionDep, SettingsDep
from app.core.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
from app.models import Tag
from app.schemas.tags import TagCreateIn, TagListOut, TagOut, TagPatchIn, TagUsageOut
from app.services.tags import create_tag, delete_tag, get_tag_usage, list_tags, patch_tag

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=TagListOut)
def get_tags(
    session: SessionDep,
    current_user: CurrentUserDep,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, list[Tag] | int]:
    tags, total = list_tags(session, current_user.id, limit=limit, offset=offset)
    return {"items": tags, "total": total, "limit": limit, "offset": offset}


@router.post("", response_model=TagOut)
def post_tag(
    tag: TagCreateIn,
    session: SessionDep,
    current_user: CurrentUserDep,
    settings: SettingsDep,
) -> Tag:
    return create_tag(session, current_user.id, tag.name, tag.description, settings)


@router.patch("/{tag_id}", response_model=TagOut)
def update_tag(
    tag_id: str,
    patch: TagPatchIn,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Tag:
    return patch_tag(
        session,
        current_user.id,
        tag_id,
        patch.name,
        patch.description,
        description_provided="description" in patch.model_fields_set,
    )


@router.get("/{tag_id}/usage", response_model=TagUsageOut)
def tag_usage(
    tag_id: str,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> TagUsageOut:
    return get_tag_usage(session, current_user.id, tag_id)


@router.delete("/{tag_id}", response_model=TagOut)
def remove_tag(
    tag_id: str,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Tag:
    return delete_tag(session, current_user.id, tag_id)
