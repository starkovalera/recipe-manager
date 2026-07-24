import inspect
from pathlib import Path

from app.imports.jobs.create import create_import_job
from app.imports.jobs.process import process_import_job, save_import
from app.maintenance.constants import MaintenanceOperation
from app.storage.base import StorageService
from app.storage.runtime import get_storage_service

APP_ROOT = Path(__file__).resolve().parents[2] / "app"


def test_storage_factory_selects_provider_without_accepting_location() -> None:
    assert "location" not in inspect.signature(get_storage_service).parameters


def test_storage_operations_require_explicit_location() -> None:
    for operation_name in ("save", "read", "delete"):
        parameters = inspect.signature(getattr(StorageService, operation_name)).parameters
        assert "location" in parameters
        assert parameters["location"].default is inspect.Parameter.empty


def test_domain_modules_do_not_import_s3_adapter_or_bucket_settings() -> None:
    offenders: list[str] = []
    for path in APP_ROOT.rglob("*.py"):
        if (
            path.is_relative_to(APP_ROOT / "storage")
            or path.is_relative_to(APP_ROOT / "media" / "access")
            or path == APP_ROOT / "core" / "config.py"
        ):
            continue
        source = path.read_text(encoding="utf-8")
        if "S3StorageService" in source or "s3_user_media_bucket_name" in source:
            offenders.append(path.relative_to(APP_ROOT).as_posix())
    assert offenders == []


def test_import_storage_work_precedes_persistence_boundaries() -> None:
    creation_source = inspect.getsource(create_import_job)
    assert creation_source.index("_build_image_sources(") < creation_source.index("_persist_import_job(")

    processing_source = inspect.getsource(process_import_job)
    assert processing_source.index("prepare_cover_image(") < processing_source.index("save_import(")

    persistence_source = inspect.getsource(save_import)
    for forbidden_call in ("storage.save", "storage.read", "prepare_cover_image", "create_cover_image"):
        assert forbidden_call not in persistence_source


def test_destructive_orphan_and_temporary_cleanup_remain_deferred() -> None:
    assert "orphaned_upload_cleanup" not in {operation.value for operation in MaintenanceOperation}
    assert "temporary_resource_cleanup" not in {operation.value for operation in MaintenanceOperation}
