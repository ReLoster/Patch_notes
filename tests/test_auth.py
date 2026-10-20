def test_register_ok(client):
    r = client.post("/api/auth/register",
                    json={"login": "bob", "password": "secret123"})
    assert r.status_code == 201
    assert r.json["user"]["login"] == "bob"
    assert "token" in r.headers.get("Set-Cookie", "")


def test_register_login_too_short(client):
    r = client.post("/api/auth/register",
                    json={"login": "ab", "password": "secret123"})
    assert r.status_code == 400


def test_register_password_too_short(client):
    r = client.post("/api/auth/register",
                    json={"login": "bob", "password": "12345"})
    assert r.status_code == 400


def test_register_duplicate_login(client):
    client.post("/api/auth/register",
                json={"login": "bob", "password": "secret123"})
    r = client.post("/api/auth/register",
                    json={"login": "bob", "password": "other123"})
    assert r.status_code == 409


def test_login_ok(client):
    client.post("/api/auth/register",
                json={"login": "bob", "password": "secret123"})
    client.post("/api/auth/logout")
    r = client.post("/api/auth/login",
                    json={"login": "bob", "password": "secret123"})
    assert r.status_code == 200


def test_login_wrong_password(client):
    client.post("/api/auth/register",
                json={"login": "bob", "password": "secret123"})
    client.post("/api/auth/logout")
    r = client.post("/api/auth/login",
                    json={"login": "bob", "password": "wrong"})
    assert r.status_code == 401


def test_login_unknown_user(client):
    r = client.post("/api/auth/login",
                    json={"login": "ghost", "password": "secret123"})
    assert r.status_code == 401


def test_me_requires_auth(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_ok(auth_client):
    r = auth_client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json["user"]["login"] == "alice"


def test_logout_invalidates_session(auth_client):
    auth_client.post("/api/auth/logout")
    r = auth_client.get("/api/auth/me")
    assert r.status_code == 401


def test_password_not_leaked(client):
    r = client.post("/api/auth/register",
                    json={"login": "bob", "password": "secret123"})
    body = r.get_data(as_text=True)
    assert "secret123" not in body
    assert "password_hash" not in body