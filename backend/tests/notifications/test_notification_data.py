from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Notification, NotificationEntityType, NotificationType
from app.notifications.notification_data import (
    ImportFailedNotification,
    ImportStartedNotification,
    ImportSucceededNotification,
    build_notification,
)


def create_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_notification_data_uses_class_defaults() -> None:
    notification = ImportStartedNotification(owner_id="owner-1", entity_id="job-1").to_notification()

    assert notification.owner_id == "owner-1"
    assert notification.entity_id == "job-1"
    assert notification.type == NotificationType.IMPORT_STARTED
    assert notification.entity_type == NotificationEntityType.IMPORT_JOB
    assert notification.title == "Import started"
    assert notification.message == "Recipe import started."


def test_notification_data_constructor_overrides_non_none_values() -> None:
    notification = ImportFailedNotification(
        owner_id="owner-1",
        entity_id="job-1",
        title="Custom title",
        message="Custom message",
        data={"reason": "test"},
    ).to_notification()

    assert notification.type == NotificationType.IMPORT_FAILED
    assert notification.title == "Custom title"
    assert notification.message == "Custom message"
    assert notification.data == {"reason": "test"}


def test_notification_data_constructor_ignores_none_overrides() -> None:
    notification = ImportSucceededNotification(
        owner_id="owner-1",
        entity_id="recipe-1",
        title=None,
        message=None,
    ).to_notification()

    assert notification.title == "Import completed"
    assert notification.message == "Recipe import completed."


def test_notification_data_build_overrides_non_none_values() -> None:
    notification = ImportSucceededNotification.build(
        owner_id="owner-1",
        entity_id="recipe-1",
        title="Done",
        message="Custom done message.",
    )

    assert notification.type == NotificationType.IMPORT_SUCCEEDED
    assert notification.title == "Done"
    assert notification.message == "Custom done message."


def test_build_notification_adds_notification_to_session() -> None:
    session = create_session()

    notification = build_notification(
        session,
        ImportStartedNotification,
        owner_id="owner-1",
        entity_id="job-1",
    )

    assert notification in session.new
    assert notification.type == NotificationType.IMPORT_STARTED

    session.commit()

    saved = session.get(Notification, notification.id)
    assert saved is not None
    assert saved.type == NotificationType.IMPORT_STARTED
