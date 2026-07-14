from fastapi import APIRouter, Response, status

from app.api.deps import AuthenticatedIdentityDep, CurrentUserDep, SessionDep, SettingsDep
from app.schemas.users import CurrentUserOut
from app.users.provisioning import provision_current_user

router = APIRouter(tags=["users"])


@router.get("/me", response_model=CurrentUserOut)
def get_me(current_user: CurrentUserDep) -> CurrentUserOut:
    return CurrentUserOut(user=current_user)


@router.post("/me/provision", response_model=CurrentUserOut, status_code=status.HTTP_201_CREATED)
def provision_me(
    response: Response,
    session: SessionDep,
    identity: AuthenticatedIdentityDep,
    settings: SettingsDep,
) -> CurrentUserOut:
    result = provision_current_user(session, identity, recipe_language=settings.recipe_language)
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return CurrentUserOut(user=result.user)
