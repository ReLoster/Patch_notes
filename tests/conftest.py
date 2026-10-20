import pytest
import db as db_module
from app import app as flask_app
from extensions import limiter


@pytest.fixture
def app(tmp_path, monkeypatch):
    # Изолированная БД для каждого теста
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(db_module, "DB_PATH", db_file)
    db_module.init_db()

    flask_app.config.update(TESTING=True)
    limiter.enabled = False  # чтобы тесты не упирались в rate-limit
    yield flask_app
    limiter.enabled = True


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """Клиент, уже залогиненный как alice."""
    r = client.post("/api/auth/register",
                    json={"login": "alice", "password": "secret123"})
    assert r.status_code == 201
    return client