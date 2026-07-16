from app.core.config import AppEnv, get_settings
from app.db.session import db_session
from app.local.users import seed_preview_users


def main() -> None:
    settings = get_settings()
    if settings.app_env is not AppEnv.PREVIEW:
        raise RuntimeError("Preview user seeding requires APP_ENV=PREVIEW.")
    with db_session() as session:
        count = seed_preview_users(session, settings.preview_users_file, recipe_language=settings.recipe_language)
    print(f"Seeded {count} preview users from {settings.preview_users_file}.")


if __name__ == "__main__":
    main()
