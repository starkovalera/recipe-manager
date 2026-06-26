from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.init import ensure_default_user
from app.db.session import get_session
from app.models import User


def get_current_user(session: Session = Depends(get_session)) -> User:
    return ensure_default_user(session)
