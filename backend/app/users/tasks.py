import dramatiq

from app.core.config import get_settings
from app.core.dramatiq import broker as _broker  # noqa: F401
from app.users.deletion import process_account_deletion


@dramatiq.actor(max_retries=get_settings().account_deletion_task_max_retries)
def delete_account_task(user_id: str) -> None:
    process_account_deletion(user_id)
