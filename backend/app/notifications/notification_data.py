from typing import Any

from sqlalchemy.orm.session import Session

from app.models import Notification, NotificationEntityType, NotificationType


class NotificationData:
    type: NotificationType
    owner_id: str
    title: str | None = None
    message: str | None = None
    entity_type: NotificationEntityType | None
    entity_id: str | None = None
    data: dict[str, Any] | None = None

    def __init__(
        self,
        type: NotificationType | None = None,
        owner_id: str | None = None,
        entity_type: NotificationEntityType | None = None,
        title: str | None = None,
        message: str | None = None,
        entity_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        for param_name, param in locals().items():
            if param_name != "self" and param is not None:
                setattr(self, param_name, param)

    def to_notification(self) -> Notification:
        return Notification(
            owner_id=self.owner_id,
            type=self.type,
            title=self.title,
            message=self.message,
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            data=self.data,
        )

    @classmethod
    def build(
        cls,
        type: NotificationType | None = None,
        owner_id: str | None = None,
        entity_type: NotificationEntityType | None = None,
        title: str | None = None,
        message: str | None = None,
        entity_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> Notification:
        notification_data = cls(
            type=type,
            owner_id=owner_id,
            entity_type=entity_type,
            title=title,
            message=message,
            entity_id=entity_id,
            data=data,
        )
        return notification_data.to_notification()


class ImportNotification(NotificationData):
    pass


class ImportStartedNotification(ImportNotification):
    type = NotificationType.IMPORT_STARTED
    entity_type = NotificationEntityType.IMPORT_JOB
    title = "Import started"
    message = "Recipe import started."


class ImportFailedNotification(ImportNotification):
    type = NotificationType.IMPORT_FAILED
    entity_type = NotificationEntityType.IMPORT_JOB
    title = "Import failed"
    message = "Recipe import failed."


class ImportSucceededNotification(ImportNotification):
    type = NotificationType.IMPORT_SUCCEEDED
    entity_type = NotificationEntityType.RECIPE
    title = "Import completed"
    message = "Recipe import completed."


class ImportSucceededWithFlagsNotification(ImportNotification):
    type = NotificationType.IMPORT_SUCCEEDED_WITH_FLAGS
    entity_type = NotificationEntityType.RECIPE
    title = "Import completed with warning"
    message = "Recipe import completed and needs review."


def build_notification(
    session: Session,
    data_cls: type[NotificationData],
    owner_id: str,
    entity_id: str,
    type: NotificationType | None = None,
    entity_type: NotificationEntityType | None = None,
    title: str | None = None,
    message: str | None = None,
    data: dict[str, Any] | None = None,
) -> Notification:
    notification = data_cls.build(
        type=type,
        owner_id=owner_id,
        entity_type=entity_type,
        title=title,
        message=message,
        entity_id=entity_id,
        data=data,
    )
    session.add(notification)
    return notification
