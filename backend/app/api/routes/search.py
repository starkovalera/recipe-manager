from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUserDep, SessionDep
from app.schemas.search import SearchRequestIn, SearchResponseOut, SearchSuggestionListOut, SearchSuggestionOut
from app.search.constants import DEFAULT_SEARCH_SUGGESTION_LIMIT, MAX_SEARCH_SUGGESTION_LIMIT
from app.services.search import list_search_suggestions, search_recipes

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/suggestions", response_model=SearchSuggestionListOut)
def get_search_suggestions(
    session: SessionDep,
    current_user: CurrentUserDep,
    q: Annotated[str, Query(min_length=1)],
    limit: Annotated[int, Query(ge=1, le=MAX_SEARCH_SUGGESTION_LIMIT)] = DEFAULT_SEARCH_SUGGESTION_LIMIT,
) -> dict[str, list[SearchSuggestionOut]]:
    return {"items": list_search_suggestions(session, current_user.id, query=q, limit=limit)}


@router.post("", response_model=SearchResponseOut)
def search_recipes_endpoint(
    request: SearchRequestIn,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> SearchResponseOut:
    return search_recipes(session, current_user.id, request)
