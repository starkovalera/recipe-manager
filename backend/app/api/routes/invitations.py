from fastapi import APIRouter, status

from app.access.constants import UserRole
from app.access.rules import require_role
from app.api.deps import CurrentUserDep, SessionDep, SettingsDep
from app.invitations.queries import list_invitations
from app.invitations.service import create_invitation, revoke_invitation
from app.models import Invitation
from app.schemas.invitations import InvitationCreateIn, InvitationListOut, InvitationOut

router = APIRouter(prefix="/internal/invitations", tags=["invitations"])


@router.get("", response_model=InvitationListOut)
def get_invitations(session: SessionDep, current_user: CurrentUserDep) -> dict[str, list[Invitation]]:
    require_role(current_user, UserRole.SUPERADMIN)
    return {"items": list_invitations(session)}


@router.post("", response_model=InvitationOut, status_code=status.HTTP_201_CREATED)
def post_invitation(
    request: InvitationCreateIn,
    session: SessionDep,
    current_user: CurrentUserDep,
    settings: SettingsDep,
) -> Invitation:
    require_role(current_user, UserRole.SUPERADMIN)
    return create_invitation(
        session,
        email=str(request.email),
        created_by=current_user,
        redirect_url=settings.frontend_invitation_url,
    )


@router.post("/{invitation_id}/revoke", response_model=InvitationOut)
def post_revoke_invitation(
    invitation_id: str,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Invitation:
    require_role(current_user, UserRole.SUPERADMIN)
    return revoke_invitation(session, invitation_id)
