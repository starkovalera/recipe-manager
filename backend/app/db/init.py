from sqlalchemy.orm import Session

from app.models import User

DEFAULT_USER_ID = "local-user"
DEFAULT_USER_EMAIL = "local@example.test"


def ensure_default_user(session: Session) -> User:
    user = session.get(User, DEFAULT_USER_ID)
    if user is not None:
        return user
    user = User(id=DEFAULT_USER_ID, email=DEFAULT_USER_EMAIL)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
