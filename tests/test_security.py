def test_sql_injection_in_login(client):
    r = client.post("/api/auth/login",
                    json={"login": "' OR '1'='1", "password": "x"})
    assert r.status_code == 401


def test_sql_injection_in_note(client):
    client.post("/api/auth/register",
                json={"login": "bob", "password": "secret123"})
    r = client.post("/api/notes",
                    json={"title": "'; DROP TABLE notes; --", "text": "x"})
    assert r.status_code == 201
    # Таблица жива
    assert client.get("/api/notes").status_code == 200


def test_tampered_jwt_rejected(client):
    client.post("/api/auth/register",
                json={"login": "bob", "password": "secret123"})
    client.set_cookie("token", "fake.jwt.token", domain="localhost")
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_xss_in_note_is_stored_as_text(auth_client):
    payload = "<script>alert(1)</script>"
    r = auth_client.post("/api/notes", json={"title": payload, "text": ""})
    assert r.status_code == 201
    assert r.json["note"]["title"] == payload  # бэкенд не портит текст, XSS-экранирование делает фронт