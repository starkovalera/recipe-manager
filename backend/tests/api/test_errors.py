from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import InvalidUrlError, TextTooLongError, install_error_handlers
from app.core.security import client_id_from_header


def test_api_error_response_shape():
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/boom")
    def boom():
        raise InvalidUrlError()

    response = TestClient(app).get("/boom")

    assert response.status_code == 400
    assert response.json() == {"errorCode": "INVALID_URL", "message": "URL is not supported."}


def test_api_error_response_includes_extra():
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/boom")
    def boom():
        raise TextTooLongError(max_length=1000)

    response = TestClient(app).get("/boom")

    assert response.status_code == 400
    assert response.json() == {
        "errorCode": "TEXT_TOO_LONG",
        "message": "Text input is too long.",
        "extra": {"max_length": 1000},
    }


def test_client_id_from_header_normalizes_and_limits_length():
    assert client_id_from_header("  abc  ") == "abc"
    assert len(client_id_from_header("x" * 200)) == 128
    assert client_id_from_header(None).startswith("anonymous-")
