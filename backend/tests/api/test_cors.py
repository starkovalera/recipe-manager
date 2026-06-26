from fastapi.testclient import TestClient

from app.main import create_app


def test_local_vite_origin_is_allowed_for_api_requests():
    client = TestClient(create_app())

    response = client.options(
        "/recipes",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
