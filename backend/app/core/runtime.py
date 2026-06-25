from pathlib import Path
import shutil

from app.core.config import Settings


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

    if settings.app_env == "preview":
        root = _preview_root_for(upload_dir)
        _ensure_under(upload_dir, root)
        if db_path is not None:
            _ensure_under(db_path, root)
            if db_path.exists():
                db_path.unlink()
        if upload_dir.exists():
            shutil.rmtree(upload_dir)

    upload_dir.mkdir(parents=True, exist_ok=True)
    if db_path is not None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
