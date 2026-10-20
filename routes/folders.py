import time
from flask import Blueprint, request, jsonify, g
from db import get_db
from auth_utils import require_auth

folders_bp = Blueprint("folders", __name__)


@folders_bp.route("", methods=["GET"])
@require_auth
def list_folders():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, name FROM folders WHERE user_id = ? ORDER BY name", 
            (g.user["id"],)
        ).fetchall()
    finally:
        conn.close()
    return jsonify(folders=[{"id": r["id"], "name": r["name"]} for r in rows])


@folders_bp.route("", methods=["POST"])
@require_auth
def create_folder():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    if not name:
        return jsonify(error="Название не может быть пустым"), 400

    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO folders (user_id, name, created_at) VALUES (?, ?, ?)",
            (g.user["id"], name, int(time.time() * 1000)),
        )
        conn.commit()
        folder = {"id": cur.lastrowid, "name": name}
    finally:
        conn.close()
    return jsonify(folder=folder), 201


@folders_bp.route("/<int:folder_id>", methods=["DELETE"])
@require_auth
def delete_folder(folder_id):
    conn = get_db()
    try:
        conn.execute(
            "DELETE FROM folders WHERE id = ? AND user_id = ?", 
            (folder_id, g.user["id"])
        )
        conn.commit()
    finally:
        conn.close()
    return jsonify(ok=True)