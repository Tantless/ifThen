from fastapi.testclient import TestClient

from if_then_mvp.api import create_app


def test_health_returns_ok(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path))
    with TestClient(create_app()) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_create_app_does_not_emit_startup_deprecation_warning(tmp_path, monkeypatch, recwarn):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path))

    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert not [
        warning
        for warning in recwarn
        if issubclass(warning.category, DeprecationWarning)
        and "on_event is deprecated" in str(warning.message)
    ]


def test_settings_endpoint_allows_desktop_renderer_cors_preflight(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path))

    with TestClient(create_app()) as client:
        response = client.options(
            "/settings",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "PUT",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "PUT" in response.headers["access-control-allow-methods"]
