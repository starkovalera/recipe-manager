from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import ApiError, ErrorCode
from app.db.defaults import DEFAULT_USER_ID
from app.db.init import ensure_default_user
from app.db.session import get_session
from app.models import User

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_current_user(session: SessionDep) -> User:
    return ensure_default_user(session)


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_admin_user(current_user: CurrentUserDep) -> User:
    # Temporary local-first policy. Replace this dependency when real auth/user roles land.
    if current_user.id != DEFAULT_USER_ID:
        raise ApiError(ErrorCode.FORBIDDEN, "Admin access is required.", status_code=403)
    return current_user


CurrentAdminUserDep = Annotated[User, Depends(require_admin_user)]
