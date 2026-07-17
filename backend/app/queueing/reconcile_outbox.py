from app.core.config import get_settings
from app.queueing.outbox import reconcile_pending_outbox_messages


def main() -> int:
    settings = get_settings()
    failed_ids = reconcile_pending_outbox_messages(
        batch_size=settings.outbox_reconcile_batch_size,
    )
    return 1 if failed_ids else 0


if __name__ == "__main__":
    raise SystemExit(main())
