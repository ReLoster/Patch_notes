import time
from flask import Blueprint, request, jsonify, g

from db import get_db
from auth_utils import require_auth

notes_bp = Blueprint("notes", __name__)


def map_note(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "text": row["text"],
        "deleted": bool(row["deleted"]),
        "position": row["position"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def find_note(conn, note_id, user_id):
    return conn.execute(
        "SELECT * FROM notes WHERE id = ? AND user_id = ?", (note_id, user_id)
    ).fetchone()


@notes_bp.route("", methods=["GET"])
@require_auth
def list_notes():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM notes WHERE user_id = ? ORDER BY position ASC, id ASC",
            (g.user["id"],),
        ).fetchall()
    finally:
        conn.close()
    return jsonify(notes=[map_note(r) for r in rows])


@notes_bp.route("", methods=["POST"])
@require_auth
def create_note():
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", ""))
    text = str(data.get("text", ""))
    now = int(time.time() * 1000)

    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO notes (user_id, title, text, deleted, position, created_at, updated_at) "
            "VALUES (?, ?, ?, 0, 0, ?, ?)",
            (g.user["id"], title, text, now, now),
        )
        note_id = cur.lastrowid
        conn.execute("UPDATE notes SET position = ? WHERE id = ?", (-note_id, note_id))
        conn.commit()
        row = find_note(conn, note_id, g.user["id"])
    finally:
        conn.close()
    return jsonify(note=map_note(row)), 201


@notes_bp.route("/<int:note_id>", methods=["PATCH"])
@require_auth
def update_note(note_id):
    data = request.get_json(silent=True) or {}
    conn = get_db()
    try:
        note = find_note(conn, note_id, g.user["id"])
        if not note:
            return jsonify(error="Заметка не найдена"), 404

        fields, values = [], []
        if isinstance(data.get("title"), str):
            fields.append("title = ?"); values.append(data["title"])
        if isinstance(data.get("text"), str):
            fields.append("text = ?"); values.append(data["text"])
        if isinstance(data.get("deleted"), bool):
            fields.append("deleted = ?"); values.append(1 if data["deleted"] else 0)

        if not fields:
            return jsonify(error="Нет полей для обновления"), 400

        fields.append("updated_at = ?")
        values.append(int(time.time() * 1000))
        values.append(note_id)
        conn.execute(f"UPDATE notes SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
        row = find_note(conn, note_id, g.user["id"])
    finally:
        conn.close()
    return jsonify(note=map_note(row))


@notes_bp.route("/<int:note_id>", methods=["DELETE"])
@require_auth
def delete_note(note_id):
    conn = get_db()
    try:
        note = find_note(conn, note_id, g.user["id"])
        if not note:
            return jsonify(error="Заметка не найдена"), 404
        if not note["deleted"]:
            return jsonify(error="Сначала переместите в корзину"), 400
        conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()
    finally:
        conn.close()
    return jsonify(ok=True)


@notes_bp.route("/reorder", methods=["POST"])
@require_auth
def reorder_notes():
    data = request.get_json(silent=True) or {}
    order = data.get("order")
    if not isinstance(order, list):
        return jsonify(error="order должен быть массивом"), 400

    conn = get_db()
    try:
        for idx, note_id in enumerate(order):
            conn.execute(
                "UPDATE notes SET position = ? WHERE id = ? AND user_id = ?",
                (idx, int(note_id), g.user["id"]),
            )
        conn.commit()
    finally:
        conn.close()
    return jsonify(ok=True)