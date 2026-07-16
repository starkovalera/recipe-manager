import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.access.constants import UserRole
from app.auth.constants import AuthProviderType
from app.core.errors import AccessUserNotFoundError
from app.db.base import Base
from app.local.users import assign_role_to_auth_user
from app.models import User


def test_assign_role_to_auth_user_is_idempotent():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    user = User(id="internal-1", auth_user_id="user_1", email="one@example.test")
    session.add(user)
    session.commit()

    assert assign_role_to_auth_user(session, AuthProviderType.CLERK, "user_1", UserRole.SUPERADMIN) is user
    assert assign_role_to_auth_user(session, AuthProviderType.CLERK, "user_1", UserRole.SUPERADMIN) is user
    session.commit()
    assert user.roles == {UserRole.SUPERADMIN}

    with pytest.raises(AccessUserNotFoundError):
        assign_role_to_auth_user(session, AuthProviderType.CLERK, "missing", UserRole.DEBUG)
