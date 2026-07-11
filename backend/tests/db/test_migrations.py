import importlib.util
from pathlib import Path
from types import SimpleNamespace

from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command


def test_import_creation_error_postgres_migration_maps_value_during_enum_cast(monkeypatch):
    migration_path = Path(__file__).resolve().parents[2] / "alembic" / "versions" / "20260710_0018_remove_import_creation_error_code.py"
    spec = importlib.util.spec_from_file_location("migration_0018", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    statements: list[str] = []
    fake_op = SimpleNamespace(
        get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="postgresql")),
        execute=statements.append,
    )
    monkeypatch.setattr(migration, "op", fake_op)

    migration.upgrade()

    assert not any(statement.startswith("UPDATE import_jobs SET error_code = 'IMPORT_FAILED'") for statement in statements)
    assert any("CASE error_code::text WHEN 'IMPORT_CREATION_FAILED' THEN 'IMPORT_FAILED'" in statement for statement in statements)


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
        event_row = connection.execute(text("SELECT event_type, status_after FROM embedding_events WHERE id = 'event-1'")).one()
    assert embedding_row.status == "READY"
    assert event_row.event_type == "SAVED"
    assert event_row.status_after == "READY"

    command.downgrade(config, "20260710_0016")
    with engine.connect() as connection:
        embedding_row = connection.execute(text("SELECT status FROM recipe_embeddings WHERE recipe_id = 'recipe-1'")).one()
        event_row = connection.execute(text("SELECT event_type, status_after FROM embedding_events WHERE id = 'event-1'")).one()
    assert embedding_row.status == "ready"
    assert event_row.event_type == "saved"
    assert event_row.status_after == "ready"


def test_import_creation_error_migration_maps_existing_rows_and_does_not_restore_classification(tmp_path: Path):
    db_path = tmp_path / "import-creation-error-migration.db"
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    config.set_main_option("script_location", str(backend_root / "alembic"))

    command.upgrade(config, "20260710_0017")
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users (id, email) VALUES ('user-1', 'user@example.com')"))
        connection.execute(
            text(
                """
                INSERT INTO import_jobs (
                    id, owner_id, client_id, client_import_id, dedupe_key, status, error_code
                ) VALUES (
                    'job-1', 'user-1', 'client-1', 'import-1', 'import-1', 'FAILED', 'IMPORT_CREATION_FAILED'
                )
                """
            )
        )

    command.upgrade(config, "head")
    with engine.connect() as connection:
        error_code = connection.execute(text("SELECT error_code FROM import_jobs WHERE id = 'job-1'")).scalar_one()
    assert error_code == "IMPORT_FAILED"

    command.downgrade(config, "20260710_0017")
    with engine.connect() as connection:
        error_code = connection.execute(text("SELECT error_code FROM import_jobs WHERE id = 'job-1'")).scalar_one()
    assert error_code == "IMPORT_FAILED"


def test_import_attempt_count_migration_backfills_existing_jobs_and_downgrades(tmp_path: Path):
    db_path = tmp_path / "import-attempt-count-migration.db"
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    config.set_main_option("script_location", str(backend_root / "alembic"))

    command.upgrade(config, "20260710_0018")
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users (id, email) VALUES ('user-1', 'user@example.com')"))
        connection.execute(
            text(
                """
                INSERT INTO import_jobs (id, owner_id, client_id, status)
                VALUES ('job-1', 'user-1', 'client-1', 'FAILED')
                """
            )
        )

    command.upgrade(config, "head")
    with engine.connect() as connection:
        attempt_count = connection.execute(text("SELECT attempt_count FROM import_jobs WHERE id = 'job-1'")).scalar_one()
    assert attempt_count == 0

    command.downgrade(config, "20260710_0018")
    assert "attempt_count" not in {column["name"] for column in inspect(engine).get_columns("import_jobs")}


def test_secondary_resource_failure_event_migration_adds_postgres_enum_value(monkeypatch):
    migration_path = Path(__file__).resolve().parents[2] / "alembic" / "versions" / "20260711_0020_secondary_resource_failure_event.py"
    spec = importlib.util.spec_from_file_location("migration_0020", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    statements: list[str] = []
    fake_op = SimpleNamespace(
        get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="postgresql")),
        execute=statements.append,
        alter_column=lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(migration, "op", fake_op)

    migration.upgrade()

    assert any("ADD VALUE IF NOT EXISTS 'IMPORT_SECONDARY_RESOURCE_UPLOAD_FAILED'" in statement for statement in statements)
