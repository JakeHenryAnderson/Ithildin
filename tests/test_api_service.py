from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from ithildin_api.app import create_app
from ithildin_api.config import Settings
from ithildin_api.database import initialize_database
from pydantic import ValidationError


def make_settings(tmp_path: Path, token: str = "test-admin-token") -> Settings:
    return Settings(admin_token=token, db_path=tmp_path / "ithildin.sqlite3")


def test_healthz_returns_service_health(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path))

    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ithildin-api"}


def test_missing_admin_token_fails_startup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ITHILDIN_ADMIN_TOKEN", raising=False)

    app = create_app()

    with pytest.raises(ValidationError):
        with TestClient(app):
            pass


def test_admin_status_requires_authentication(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path))

    with TestClient(app) as client:
        response = client.get("/admin/status")

    assert response.status_code == 401
    assert response.json()["detail"] == "missing bearer token"


def test_admin_status_rejects_wrong_bearer_token(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path, token="correct-token"))

    with TestClient(app) as client:
        response = client.get(
            "/admin/status",
            headers={"Authorization": "Bearer wrong-token"},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "invalid bearer token"


def test_admin_status_accepts_correct_bearer_token(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path, token="correct-token"))

    with TestClient(app) as client:
        response = client.get(
            "/admin/status",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ithildin-api",
        "admin": "authenticated",
    }


def test_database_initialization_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "ithildin.sqlite3"

    initialize_database(db_path)
    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            "SELECT key, value FROM app_metadata WHERE key = 'schema_version'"
        ).fetchall()

    assert rows == [("schema_version", "1")]
