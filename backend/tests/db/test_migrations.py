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
    assert {
        "users",
        "user_settings",
        "user_role_assignments",
        "clerk_webhook_events",
        "invitations",
        "recipes",
        "import_jobs",
        "queue_outbox_messages",
        "recipe_resources",
        "recipe_review_flags",
    }.issubset(tables)
    user_columns = {column["name"]: column for column in inspector.get_columns("users")}
    recipe_columns = {column["name"]: column for column in inspector.get_columns("recipes")}
    assert {"auth_provider", "auth_user_id", "status", "deletion_requested_at"} <= set(user_columns)
    assert user_columns["auth_provider"]["nullable"] is False
    assert user_columns["auth_user_id"]["nullable"] is True
    assert user_columns["status"]["nullable"] is False
    assert recipe_columns["status"]["nullable"] is False
    assert any(index["column_names"] == ["auth_provider", "auth_user_id"] and index["unique"] for index in inspector.get_indexes("users"))
    assert set(inspector.get_pk_constraint("user_role_assignments")["constrained_columns"]) == {"user_id", "role"}
    assert inspector.get_pk_constraint("clerk_webhook_events")["constrained_columns"] == ["event_id"]
    webhook_columns = {column["name"]: column for column in inspector.get_columns("clerk_webhook_events")}
    assert set(webhook_columns) == {"event_id", "event_type", "processed_at"}
    assert webhook_columns["processed_at"]["nullable"] is False
    invitation_columns = {column["name"] for column in inspector.get_columns("invitations")}
    assert {
        "id",
        "auth_provider",
        "auth_invitation_id",
        "email",
        "status",
        "created_by_user_id",
        "expires_at",
        "accepted_at",
        "created_at",
        "updated_at",
    } == invitation_columns
    assert any(
        foreign_key["constrained_columns"] == ["created_by_user_id"]
        and foreign_key["referred_table"] == "users"
        and foreign_key["options"].get("ondelete") == "SET NULL"
        for foreign_key in inspector.get_foreign_keys("invitations")
    )
    assert any(
        foreign_key["constrained_columns"] == ["user_id"]
        and foreign_key["referred_table"] == "users"
        and foreign_key["options"].get("ondelete") == "CASCADE"
        for foreign_key in inspector.get_foreign_keys("user_role_assignments")
    )
    assert any(
        foreign_key["constrained_columns"] == ["cover_image_id"]
        and foreign_key["referred_table"] == "recipe_images"
        and foreign_key["referred_columns"] == ["id"]
        and foreign_key["options"].get("ondelete") == "SET NULL"
        for foreign_key in inspector.get_foreign_keys("recipes")
    )
    assert any(
        foreign_key["constrained_columns"] == ["created_recipe_id"]
        and foreign_key["referred_table"] == "recipes"
        and foreign_key["referred_columns"] == ["id"]
        and foreign_key["options"].get("ondelete") == "SET NULL"
        for foreign_key in inspector.get_foreign_keys("import_jobs")
    )
    outbox_columns = {column["name"]: column for column in inspector.get_columns("queue_outbox_messages")}
    assert set(outbox_columns) == {
        "id",
        "message_type",
        "entity_id",
        "status",
        "attempt_count",
        "last_attempt_at",
        "last_error_type",
        "published_at",
        "created_at",
    }
    assert outbox_columns["id"]["nullable"] is False
    assert outbox_columns["message_type"]["nullable"] is False
    assert outbox_columns["entity_id"]["nullable"] is False
    assert outbox_columns["status"]["nullable"] is False
    assert outbox_columns["attempt_count"]["nullable"] is False
    assert outbox_columns["created_at"]["nullable"] is False
    assert inspector.get_pk_constraint("queue_outbox_messages")["constrained_columns"] == ["id"]
    assert any(
        index["name"] == "ix_queue_outbox_status_created_at" and index["column_names"] == ["status", "created_at"]
        for index in inspector.get_indexes("queue_outbox_messages")
    )


def test_queue_outbox_migration_upgrades_previous_revision_to_head(tmp_path: Path):
    db_path = tmp_path / "queue-outbox-migration.db"
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    config.set_main_option("script_location", str(backend_root / "alembic"))

    command.upgrade(config, "20260715_0028")
    engine = create_engine(f"sqlite:///{db_path}")
    assert "queue_outbox_messages" not in inspect(engine).get_table_names()

    command.upgrade(config, "head")

    inspector = inspect(engine)
    assert "queue_outbox_messages" in inspector.get_table_names()


def test_clerk_webhook_event_migration_upgrades_previous_revision_to_head(tmp_path: Path):
    db_path = tmp_path / "clerk-webhook-migration.db"
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    config.set_main_option("script_location", str(backend_root / "alembic"))

    command.upgrade(config, "20260714_0025")
    engine = create_engine(f"sqlite:///{db_path}")
    assert "clerk_webhook_events" not in inspect(engine).get_table_names()

    command.upgrade(config, "head")

    inspector = inspect(engine)
    assert "clerk_webhook_events" in inspector.get_table_names()
    assert inspector.get_pk_constraint("clerk_webhook_events")["constrained_columns"] == ["event_id"]


def test_invitation_migration_upgrades_previous_revision_to_head(tmp_path: Path):
    db_path = tmp_path / "invitation-migration.db"
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    config.set_main_option("script_location", str(backend_root / "alembic"))

    command.upgrade(config, "20260714_0026")
    engine = create_engine(f"sqlite:///{db_path}")
    assert "invitations" not in inspect(engine).get_table_names()

    command.upgrade(config, "head")

    inspector = inspect(engine)
    assert "invitations" in inspector.get_table_names()
    assert inspector.get_pk_constraint("invitations")["constrained_columns"] == ["id"]


def test_recipe_status_migration_backfills_existing_recipes(tmp_path: Path):
    db_path = tmp_path / "recipe-status-migration.db"
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    config.set_main_option("script_location", str(backend_root / "alembic"))

    command.upgrade(config, "20260715_0027")
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users (id, email) VALUES ('user-1', 'user@example.test')"))
        connection.execute(
            text(
                "INSERT INTO recipes (id, owner_id, title, instructions, source_name) "
                "VALUES ('recipe-1', 'user-1', 'Toast', '[]', 'MANUAL')"
            )
        )

    command.upgrade(config, "head")

    with engine.connect() as connection:
        status = connection.execute(text("SELECT status FROM recipes WHERE id = 'recipe-1'")).scalar_one()
    assert status == "ACTIVE"


def test_generic_auth_identity_migration_preserves_existing_provider_user_id(tmp_path: Path):
    db_path = tmp_path / "migration.db"
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    config.set_main_option("script_location", str(backend_root / "alembic"))

    command.upgrade(config, "20260713_0023")
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (id, email, clerk_user_id, status) "
                "VALUES ('internal-1', 'person@example.test', 'provider-user-1', 'active')"
            )
        )

    command.upgrade(config, "head")

    with engine.connect() as connection:
        row = connection.execute(text("SELECT auth_provider, auth_user_id, status FROM users WHERE id = 'internal-1'")).one()
    assert row.auth_provider == "CLERK"
    assert row.auth_user_id == "provider-user-1"
    assert row.status == "ACTIVE"


def test_alembic_cli_uses_database_url_env(monkeypatch, tmp_path: Path):
    db_path = tmp_path / "env-migration.db"
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{db_path}")
    assert {"users", "recipes", "import_jobs"}.issubset(set(inspect(engine).get_table_names()))


def test_user_roles_migration_seeds_existing_local_user(tmp_path: Path):
    db_path = tmp_path / "user-roles-migration.db"
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    config.set_main_option("script_location", str(backend_root / "alembic"))
    command.upgrade(config, "20260712_0021")
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users (id, email) VALUES ('local-user', 'local@example.test')"))

    command.upgrade(config, "head")

    with engine.connect() as connection:
        roles = (
            connection.execute(text("SELECT role FROM user_role_assignments WHERE user_id = 'local-user' ORDER BY role")).scalars().all()
        )
    assert roles == ["DEBUG", "SUPERADMIN"]


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


def test_failed_import_artifact_cleanup_migration_adds_postgres_enum_values(monkeypatch):
    migration_path = Path(__file__).resolve().parents[2] / "alembic" / "versions" / "20260723_0030_failed_import_artifact_cleanup.py"
    spec = importlib.util.spec_from_file_location("migration_0030", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    statements: list[str] = []
    fake_op = SimpleNamespace(
        get_context=lambda: SimpleNamespace(dialect=SimpleNamespace(name="postgresql")),
        execute=statements.append,
    )
    monkeypatch.setattr(migration, "op", fake_op)

    migration.upgrade()

    assert any("'FAILED_ARTIFACTS_REMOVED'" in statement for statement in statements)
    assert any("'IMPORT_ARTIFACTS_REMOVED'" in statement for statement in statements)
