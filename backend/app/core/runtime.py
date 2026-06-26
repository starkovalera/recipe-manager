from pathlib import Path
import shutil
import logging

from app.core.logging import log_info
from app.core.config import Settings

logger = logging.getLogger(__name__)


def sqlite_path(database_url: str) -> Path | None:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return None
    return Path(database_url.removeprefix(prefix)).resolve()


def _preview_root_for(upload_dir: Path) -> Path:
    if upload_dir.name == "uploads":
        root = upload_dir.parent.resolve()
    else:
        root = upload_dir.resolve()
    if root.name != "preview":
        raise RuntimeError(f"Refusing preview cleanup outside preview storage: {root}")
    return root


def _ensure_under(path: Path, root: Path) -> None:
    resolved = path.resolve()
    if root != resolved and root not in resolved.parents:
        raise RuntimeError(f"Refusing preview cleanup outside preview storage: {resolved}")


def prepare_runtime(settings: Settings) -> None:
    upload_dir = Path(settings.upload_dir).resolve()
    db_path = sqlite_path(settings.database_url or "")

    log_info(
        logger,
        "[recipes.runtime] Runtime preparation started",
        appEnv=settings.app_env,
        databaseUrl=settings.database_url,
        databasePath=str(db_path) if db_path else None,
        uploadDir=str(upload_dir),
    )
    if settings.app_env == "preview":
        root = _preview_root_for(upload_dir)
        _ensure_under(upload_dir, root)
        deleted_db = False
        deleted_upload_dir = False
        if db_path is not None:
            _ensure_under(db_path, root)
            if db_path.exists():
                db_path.unlink()
                deleted_db = True
        if upload_dir.exists():
            shutil.rmtree(upload_dir)
            deleted_upload_dir = True
        log_info(
            logger,
            "[recipes.runtime] Preview cleanup completed",
            databasePath=str(db_path) if db_path else None,
            deletedDatabase=deleted_db,
            uploadDir=str(upload_dir),
            deletedUploadDir=deleted_upload_dir,
        )

    upload_dir.mkdir(parents=True, exist_ok=True)
    if db_path is not None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    log_info(
        logger,
        "[recipes.runtime] Runtime preparation completed",
        appEnv=settings.app_env,
        databasePath=str(db_path) if db_path else None,
        uploadDir=str(upload_dir),
    )
