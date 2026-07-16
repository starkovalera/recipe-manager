from fastapi import APIRouter

from app.api.deps import SessionDep, SettingsDep
from app.auth.webhooks import VerifiedClerkWebhookDep, process_clerk_webhook
from app.db.session import db_transaction
from app.users.deletion import enqueue_account_deletion

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/clerk", response_model=dict[str, bool])
def handle_clerk_webhook(
    event: VerifiedClerkWebhookDep,
    session: SessionDep,
    settings: SettingsDep,
) -> dict[str, bool]:
    with db_transaction(session):
        result = process_clerk_webhook(session, event, recipe_language=settings.recipe_language)
    if result.deletion_user_id is not None:
        enqueue_account_deletion(result.deletion_user_id)
    return {"processed": result.processed}
