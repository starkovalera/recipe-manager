from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2] / "app"
ALLOWED_LOCAL_STORAGE_IMPORTS = {
    APP_ROOT / "media" / "access" / "local.py",
    APP_ROOT / "media" / "access" / "runtime.py",
    APP_ROOT / "storage" / "runtime.py",
}


def test_storage_implementation_selection_is_centralized() -> None:
    offenders = []
    for path in APP_ROOT.rglob("*.py"):
        if path in ALLOWED_LOCAL_STORAGE_IMPORTS or path == APP_ROOT / "storage" / "local.py":
            continue
        source = path.read_text(encoding="utf-8")
        if "app.storage.local import LocalStorageService" in source:
            offenders.append(path.relative_to(APP_ROOT).as_posix())

    assert offenders == []
