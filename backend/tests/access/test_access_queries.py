from datetime import datetime, timezone

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


def test_list_access_users_searches_email_internal_id_and_auth_user_id() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        session.add_all(
            [
                User(id="internal-alpha", auth_user_id="auth-one", email="alpha@example.test"),
                User(id="internal-beta", auth_user_id="auth-two", email="beta@example.test"),
                User(id="internal-gamma", auth_user_id=None, email="gamma@example.test"),
            ]
        )

    with Session(engine) as session:
        assert [user.id for user in queries.list_access_users(session, q="ALPHA")] == ["internal-alpha"]
        assert [user.id for user in queries.list_access_users(session, q="internal-BETA")] == ["internal-beta"]
        assert [user.id for user in queries.list_access_users(session, q="AUTH-TWO")] == ["internal-beta"]


def test_list_access_users_filters_by_one_role_and_status() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        session.add_all(
            [
                User(
                    id="active-debug",
                    email="active-debug@example.test",
                    role_assignments=[UserRoleAssignment(role=UserRole.DEBUG)],
                ),
                User(
                    id="deactivated-debug",
                    email="deactivated-debug@example.test",
                    status=UserStatus.DEACTIVATED,
                    role_assignments=[UserRoleAssignment(role=UserRole.DEBUG)],
                ),
                User(
                    id="active-user",
                    email="active-user@example.test",
                ),
            ]
        )

    with Session(engine) as session:
        users = queries.list_access_users(session, role=UserRole.DEBUG, status=UserStatus.DEACTIVATED)
        assert [user.id for user in users] == ["deactivated-debug"]


def test_list_access_users_sorts_paginates_and_counts_filtered_rows() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    oldest = datetime(2026, 1, 1, tzinfo=timezone.utc)
    middle = datetime(2026, 2, 1, tzinfo=timezone.utc)
    newest = datetime(2026, 3, 1, tzinfo=timezone.utc)
    with Session(engine) as session, session.begin():
        session.add_all(
            [
                User(id="oldest", email="c@example.test", created_at=oldest, updated_at=oldest),
                User(id="middle", email="a@example.test", created_at=middle, updated_at=middle),
                User(id="newest", email="b@example.test", created_at=newest, updated_at=newest),
            ]
        )

    with Session(engine) as session:
        users = queries.list_access_users(
            session,
            q="example.test",
            sort_by="updated_at",
            sort_order="desc",
            limit=1,
            offset=1,
        )
        total = queries.count_access_users(session, q="example.test")
        users_by_email = queries.list_access_users(session, sort_by="email", sort_order="asc")

        assert [user.id for user in users] == ["middle"]
        assert total == 3
        assert [user.id for user in users_by_email] == ["middle", "newest", "oldest"]
