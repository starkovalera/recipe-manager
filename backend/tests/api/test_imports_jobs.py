from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from PIL import Image
from io import BytesIO

from app.db.base import Base
from app.db.session import get_session
from app.main import create_app


def client_with_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    def override_session() -> Generator[Session, None, None]:
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def image_bytes() -> bytes:
    out = BytesIO()
    Image.new("RGB", (20, 20), color=(255, 0, 0)).save(out, format="JPEG")
    return out.getvalue()


def test_text_import_creates_job_and_polling_returns_recipe():
    client = client_with_session()

    created = client.post(
        "/imports",
        data={"clientImportId": "import-1", "text": "Tomato soup recipe"},
        headers={"X-Client-Id": "client-1"},
    )
    job_id = created.json()["jobId"]
    polled = client.get(f"/imports/{job_id}")

    assert created.status_code == 200
    assert created.json()["status"] in {"pending", "processing", "succeeded"}
    assert polled.status_code == 200
    assert polled.json()["status"] == "succeeded"
    assert polled.json()["createdRecipeId"]


def test_duplicate_client_import_id_returns_existing_job():
    client = client_with_session()

    first = client.post("/imports", data={"clientImportId": "same", "text": "Recipe"}, headers={"X-Client-Id": "client-1"})
    second = client.post("/imports", data={"clientImportId": "same", "text": "Recipe"}, headers={"X-Client-Id": "client-1"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["jobId"] == first.json()["jobId"]


def test_import_requires_at_least_one_source():
    client = client_with_session()

    response = client.post("/imports", data={"clientImportId": "empty"}, headers={"X-Client-Id": "client-1"})

    assert response.status_code == 400
    assert response.json()["errorCode"] == "NOT_A_RECIPE"


def test_import_rejects_text_over_limit_before_job_creation():
    client = client_with_session()

    response = client.post(
        "/imports",
        data={"clientImportId": "long-text", "text": "x" * 501},
        headers={"X-Client-Id": "client-1"},
    )

    assert response.status_code == 400
    assert response.json()["errorCode"] == "TEXT_TOO_LONG"


def test_import_rejects_too_many_files_before_processing():
    client = client_with_session()
    files = [("files", (f"{index}.jpg", b"not-real-image", "image/jpeg")) for index in range(11)]

    response = client.post(
        "/imports",
        data={"clientImportId": "too-many"},
        files=files,
        headers={"X-Client-Id": "client-1"},
    )

    assert response.status_code == 400
    assert response.json()["errorCode"] == "TOO_MANY_FILES"


def test_import_rejects_unsupported_file_type():
    client = client_with_session()

    response = client.post(
        "/imports",
        data={"clientImportId": "bad-file"},
        files=[("files", ("recipe.txt", b"hello", "text/plain"))],
        headers={"X-Client-Id": "client-1"},
    )

    assert response.status_code == 400
    assert response.json()["errorCode"] == "INVALID_FILE_TYPE"


def test_image_attachment_import_creates_image_source():
    client = client_with_session()

    response = client.post(
        "/imports",
        data={"clientImportId": "image-import"},
        files=[("files", ("recipe.jpg", image_bytes(), "image/jpeg"))],
        headers={"X-Client-Id": "client-1"},
    )
    recipe_id = response.json()["createdRecipeId"]
    detail = client.get(f"/recipes/{recipe_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"
    assert detail.json()["sources"][0]["type"] == "IMAGE"
    assert detail.json()["sources"][0]["status"] == "used"
