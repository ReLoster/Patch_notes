def test_create_note(auth_client):
    r = auth_client.post("/api/notes", json={"title": "Hi", "text": "World"})
    assert r.status_code == 201
    assert r.json["note"]["title"] == "Hi"
    assert r.json["note"]["deleted"] is False


def test_list_notes(auth_client):
    auth_client.post("/api/notes", json={"title": "A", "text": "1"})
    auth_client.post("/api/notes", json={"title": "B", "text": "2"})
    r = auth_client.get("/api/notes")
    assert r.status_code == 200
    assert len(r.json["notes"]) == 2


def test_update_note(auth_client):
    r = auth_client.post("/api/notes", json={"title": "Old", "text": "x"})
    nid = r.json["note"]["id"]
    r = auth_client.patch(f"/api/notes/{nid}", json={"title": "New"})
    assert r.status_code == 200
    assert r.json["note"]["title"] == "New"


def test_move_to_trash(auth_client):
    r = auth_client.post("/api/notes", json={"title": "X", "text": "y"})
    nid = r.json["note"]["id"]
    r = auth_client.patch(f"/api/notes/{nid}", json={"deleted": True})
    assert r.json["note"]["deleted"] is True


def test_cannot_delete_active_note(auth_client):
    r = auth_client.post("/api/notes", json={"title": "X", "text": "y"})
    nid = r.json["note"]["id"]
    r = auth_client.delete(f"/api/notes/{nid}")
    assert r.status_code == 400


def test_delete_from_trash(auth_client):
    r = auth_client.post("/api/notes", json={"title": "X", "text": "y"})
    nid = r.json["note"]["id"]
    auth_client.patch(f"/api/notes/{nid}", json={"deleted": True})
    r = auth_client.delete(f"/api/notes/{nid}")
    assert r.status_code == 200
    r = auth_client.get("/api/notes")
    assert len(r.json["notes"]) == 0


def test_reorder(auth_client):
    ids = [auth_client.post("/api/notes",
                            json={"title": f"N{i}", "text": ""}).json["note"]["id"]
           for i in range(3)]
    r = auth_client.post("/api/notes/reorder", json={"order": list(reversed(ids))})
    assert r.status_code == 200
    got = [n["id"] for n in auth_client.get("/api/notes").json["notes"]]
    assert got == list(reversed(ids))


def test_unauthorized_notes(client):
    assert client.get("/api/notes").status_code == 401
    assert client.post("/api/notes", json={"title": "x"}).status_code == 401
    assert client.patch("/api/notes/1", json={"title": "x"}).status_code == 401
    assert client.delete("/api/notes/1").status_code == 401


def test_user_isolation(client):
    """Чужие заметки не видны и не редактируются."""
    # Пользователь A создаёт заметку
    client.post("/api/auth/register",
                json={"login": "user_a", "password": "secret123"})
    nid = client.post("/api/notes",
                      json={"title": "A secret", "text": "xxx"}).json["note"]["id"]
    client.post("/api/auth/logout")

    # Пользователь B не видит и не трогает
    client.post("/api/auth/register",
                json={"login": "user_b", "password": "secret123"})
    assert len(client.get("/api/notes").json["notes"]) == 0
    assert client.patch(f"/api/notes/{nid}",
                        json={"title": "hack"}).status_code == 404
    assert client.delete(f"/api/notes/{nid}").status_code == 404