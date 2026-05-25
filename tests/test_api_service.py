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
    manifest_dir = tmp_path / "tool-manifests"
    manifest_dir.mkdir()
    return Settings(
        admin_token=token,
        db_path=tmp_path / "ithildin.sqlite3",
        manifest_dir=manifest_dir,
    )


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


def test_tools_requires_authentication(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path))

    with TestClient(app) as client:
        response = client.get("/tools")

    assert response.status_code == 401


def test_tools_returns_empty_list_without_manifests(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path))

    with TestClient(app) as client:
        response = client.get(
            "/tools",
            headers={"Authorization": "Bearer test-admin-token"},
        )

    assert response.status_code == 200
    assert response.json() == {"tools": []}


def test_tools_returns_manifest_summaries(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    (settings.manifest_dir / "fs-read.yaml").write_text(
        """
name: fs.read
version: 1.0.0
title: Read file
risk: read
category: filesystem
mcp:
  exposed: true
input_schema:
  type: object
  required: ["path"]
  properties:
    path:
      type: string
""",
        encoding="utf-8",
    )
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.get(
            "/tools?principal=agent:local-dev",
            headers={"Authorization": "Bearer test-admin-token"},
        )

    assert response.status_code == 200
    assert response.json()["tools"] == [
        {
            "name": "fs.read",
            "version": "1.0.0",
            "title": "Read file",
            "risk": "read",
            "category": "filesystem",
            "manifest_hash": response.json()["tools"][0]["manifest_hash"],
            "mcp": {"exposed": True},
        }
    ]
    assert response.json()["tools"][0]["manifest_hash"].startswith("sha256:")


def test_app_startup_fails_for_invalid_manifest(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    (settings.manifest_dir / "invalid.yaml").write_text("name: fs.read\n", encoding="utf-8")
    app = create_app(settings)

    with pytest.raises(RuntimeError):
        with TestClient(app):
            pass


def test_database_initialization_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "ithildin.sqlite3"

    initialize_database(db_path)
    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            "SELECT key, value FROM app_metadata WHERE key = 'schema_version'"
        ).fetchall()

    assert rows == [("schema_version", "1")]
