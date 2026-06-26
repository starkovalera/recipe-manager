from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_alembic_upgrade_head_creates_core_tables(tmp_path: Path):
    db_path = tmp_path / "migration.db"
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    config.set_main_option("script_location", str(backend_root / "alembic"))

    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{db_path}")
    tables = set(inspect(engine).get_table_names())
    assert {"users", "recipes", "import_jobs", "recipe_resources", "recipe_review_flags"}.issubset(tables)
