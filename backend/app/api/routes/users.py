from fastapi import APIRouter

from app.access.constants import ADMIN_PAGE_ROLES, UserRole
from app.access.rules import has_any_role, has_role
from app.api.deps import CurrentUserDep
from app.schemas.users import CurrentUserFeaturesOut, CurrentUserOut

router = APIRouter(tags=["users"])


@router.get("/me", response_model=CurrentUserOut)
def get_me(current_user: CurrentUserDep) -> CurrentUserOut:
    return CurrentUserOut(
        id=current_user.id,
        email=current_user.email,
        features=CurrentUserFeaturesOut(
            show_admin_pages=has_any_role(current_user, ADMIN_PAGE_ROLES),
            show_role_management=has_role(current_user, UserRole.SUPERADMIN),
            show_recipe_debug=has_role(current_user, UserRole.DEBUG),
        ),
    )
