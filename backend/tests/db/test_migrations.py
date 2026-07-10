from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command


def test_alembic_upgrade_head_creates_core_tables(tmp_path: Path):
    db_path = tmp_path / "migration.db"
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    config.set_main_option("script_location", str(backend_root / "alembic"))

    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert {"users", "user_settings", "recipes", "import_jobs", "recipe_resources", "recipe_review_flags"}.issubset(tables)
    assert any(
        foreign_key["constrained_columns"] == ["cover_image_id"]
        and foreign_key["referred_table"] == "recipe_images"
        and foreign_key["referred_columns"] == ["id"]
        and foreign_key["options"].get("ondelete") == "SET NULL"
        for foreign_key in inspector.get_foreign_keys("recipes")
    )


def test_alembic_cli_uses_database_url_env(monkeypatch, tmp_path: Path):
    db_path = tmp_path / "env-migration.db"
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{db_path}")
    assert {"users", "recipes", "import_jobs"}.issubset(set(inspect(engine).get_table_names()))


def test_embedding_lifecycle_migration_converts_existing_values_and_downgrades(tmp_path: Path):
    db_path = tmp_path / "embedding-lifecycle-migration.db"
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    config.set_main_option("script_location", str(backend_root / "alembic"))

    command.upgrade(config, "20260710_0016")
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO recipe_embeddings (recipe_id, model, status, failed_attempts)
                VALUES ('recipe-1', 'test-embedding', 'ready', 0)
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO embedding_events (id, recipe_id, owner_id, event_type, status_after)
                VALUES ('event-1', 'recipe-1', 'local-user', 'saved', 'ready')
                """
            )
        )

    command.upgrade(config, "head")
    with engine.connect() as connection:
        embedding_row = connection.execute(text("SELECT status FROM recipe_embeddings WHERE recipe_id = 'recipe-1'")).one()
        event_row = connection.execute(
            text("SELECT event_type, status_after FROM embedding_events WHERE id = 'event-1'")
        ).one()
    assert embedding_row.status == "READY"
    assert event_row.event_type == "SAVED"
    assert event_row.status_after == "READY"

    command.downgrade(config, "20260710_0016")
    with engine.connect() as connection:
        embedding_row = connection.execute(text("SELECT status FROM recipe_embeddings WHERE recipe_id = 'recipe-1'")).one()
        event_row = connection.execute(
            text("SELECT event_type, status_after FROM embedding_events WHERE id = 'event-1'")
        ).one()
    assert embedding_row.status == "ready"
    assert event_row.event_type == "saved"
    assert event_row.status_after == "ready"
