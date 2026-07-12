from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.init import ensure_default_user
from app.db.session import get_session
from app.models import User

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_current_user(session: SessionDep) -> User:
    return ensure_default_user(session)


CurrentUserDep = Annotated[User, Depends(get_current_user)]
