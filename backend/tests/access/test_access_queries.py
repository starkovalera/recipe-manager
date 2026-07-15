from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.access import queries
from app.access.constants import UserRole
from app.db.base import Base
from app.models import User, UserRoleAssignment, UserStatus


def test_list_active_superadmin_ids_for_update_excludes_non_active_users() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        session.add_all(
            [
                User(
                    id="active-admin",
                    email="active@example.test",
                    role_assignments=[UserRoleAssignment(role=UserRole.SUPERADMIN)],
                ),
                User(
                    id="pending-admin",
                    email="pending@example.test",
                    status=UserStatus.DELETION_PENDING,
                    role_assignments=[UserRoleAssignment(role=UserRole.SUPERADMIN)],
                ),
                User(id="ordinary-user", email="ordinary@example.test"),
            ]
        )

    with Session(engine) as session, session.begin():
        assert queries.list_active_superadmin_ids_for_update(session) == ["active-admin"]
