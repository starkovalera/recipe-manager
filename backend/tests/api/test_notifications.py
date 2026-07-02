from collections.abc import Generator
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.init import ensure_default_user
from app.db.session import get_session
from app.main import create_app
from app.models import Notification, User


def client_with_session_factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    def override_session() -> Generator[Session, None, None]:
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    return TestClient(app), SessionLocal


def test_notifications_list_returns_current_user_notifications_newest_first():
    client, SessionLocal = client_with_session_factory()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        other_user = User(id="other-user", email="other@example.test")
        session.add(other_user)
        old_notification = Notification(
            owner_id=user.id,
            type="import_started",
            title="Import started",
            message="Import queued.",
            entity_type="import_job",
            entity_id="job-1",
            data={"importJobId": "job-1"},
            created_at=datetime(2026, 6, 27, 10, 0, tzinfo=timezone.utc),
        )
        new_notification = Notification(
            owner_id=user.id,
            type="import_succeeded",
            title="Import completed",
            message="Recipe imported.",
            entity_type="recipe",
            entity_id="recipe-1",
            data={"importJobId": "job-1", "createdRecipeId": "recipe-1", "hasReviewFlags": False},
            created_at=datetime(2026, 6, 27, 10, 1, tzinfo=timezone.utc),
        )
        other_notification = Notification(
            owner_id=other_user.id,
            type="import_failed",
            title="Hidden",
            message="Should not be returned.",
        )
        session.add_all([old_notification, new_notification, other_notification])
        session.commit()

    response = client.get("/notifications")

    assert response.status_code == 200
    payload = response.json()
    assert [item["type"] for item in payload["items"]] == ["import_succeeded", "import_started"]
    assert payload["items"][0]["status"] == "unread"
    assert payload["items"][0]["entityType"] == "recipe"
    assert payload["items"][0]["entityId"] == "recipe-1"
    assert payload["items"][0]["data"]["createdRecipeId"] == "recipe-1"
    assert "createdAt" in payload["items"][0]
    assert "updatedAt" in payload["items"][0]
    assert all(item["title"] != "Hidden" for item in payload["items"])


def test_notification_can_be_marked_read():
    client, SessionLocal = client_with_session_factory()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        notification = Notification(
            owner_id=user.id,
            type="import_succeeded",
            title="Import completed",
            message="Recipe imported.",
            entity_type="recipe",
            entity_id="recipe-1",
        )
        session.add(notification)
        session.commit()
        notification_id = notification.id

    response = client.patch(f"/notifications/{notification_id}", json={"status": "read"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == notification_id
    assert payload["status"] == "read"
    assert payload["readAt"] is not None

    with SessionLocal() as session:
        saved = session.get(Notification, notification_id)
        assert saved is not None
        assert saved.status == "read"
        assert saved.read_at is not None


def test_notifications_can_be_marked_read_up_to_target_notification_only():
    client, SessionLocal = client_with_session_factory()
    with SessionLocal() as session:
        user = ensure_default_user(session)
        old_notification = Notification(
            owner_id=user.id,
            type="import_started",
            status="unread",
            title="Import started",
            message="Import queued.",
            created_at=datetime(2026, 6, 27, 10, 0, tzinfo=timezone.utc),
        )
        target_notification = Notification(
            owner_id=user.id,
            type="import_succeeded",
            status="unread",
            title="Import completed",
            message="Recipe imported.",
            created_at=datetime(2026, 6, 27, 10, 1, tzinfo=timezone.utc),
        )
        newer_notification = Notification(
            owner_id=user.id,
            type="import_failed",
            status="unread",
            title="New import failed",
            message="This arrived after the frontend snapshot.",
            created_at=datetime(2026, 6, 27, 10, 2, tzinfo=timezone.utc),
        )
        already_read_notification = Notification(
            owner_id=user.id,
            type="import_started",
            status="read",
            title="Already read",
            message="Already read.",
            created_at=datetime(2026, 6, 27, 9, 59, tzinfo=timezone.utc),
        )
        session.add_all([old_notification, target_notification, newer_notification, already_read_notification])
        session.commit()
        target_notification_id = target_notification.id
        ids = {
            "old": old_notification.id,
            "target": target_notification.id,
            "newer": newer_notification.id,
            "already_read": already_read_notification.id,
        }

    response = client.patch("/notifications/read-all", json={"lastNotificationId": target_notification_id})

    assert response.status_code == 200
    assert response.json()["updatedCount"] == 2

    with SessionLocal() as session:
        saved = {name: session.get(Notification, notification_id) for name, notification_id in ids.items()}
        assert saved["old"].status == "read"
        assert saved["old"].read_at is not None
        assert saved["target"].status == "read"
        assert saved["target"].read_at is not None
        assert saved["newer"].status == "unread"
        assert saved["newer"].read_at is None
        assert saved["already_read"].status == "read"
