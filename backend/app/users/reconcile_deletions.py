from app.users.deletion import requeue_pending_account_deletions


def main() -> int:
    return 1 if requeue_pending_account_deletions() else 0


if __name__ == "__main__":
    raise SystemExit(main())
