import time
from flask import Blueprint, request, jsonify, g

from db import get_db
from extensions import limiter
from auth_utils import (
    hash_password, verify_password, sign_token,
    require_auth, set_auth_cookie, clear_auth_cookie,
)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("30 per 15 minutes")
def register():
    data = request.get_json(silent=True) or {}
    login = str(data.get("login", "")).strip()
    password = str(data.get("password", ""))

    if not (3 <= len(login) <= 32):
        return jsonify(error="Логин должен быть от 3 до 32 символов"), 400
    if len(password) < 6:
        return jsonify(error="Пароль должен быть не менее 6 символов"), 400

    conn = get_db()
    try:
        if conn.execute("SELECT id FROM users WHERE login = ?", (login,)).fetchone():
            return jsonify(error="Такой логин уже занят"), 409
        cur = conn.execute(
            "INSERT INTO users (login, password_hash, created_at) VALUES (?, ?, ?)",
            (login, hash_password(password), int(time.time() * 1000)),
        )
        conn.commit()
        user = {"id": cur.lastrowid, "login": login}
    finally:
        conn.close()

    resp = jsonify(user=user)
    set_auth_cookie(resp, sign_token(user))
    return resp, 201


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("30 per 15 minutes")
def login():
    data = request.get_json(silent=True) or {}
    login = str(data.get("login", "")).strip()
    password = str(data.get("password", ""))

    if not login or not password:
        return jsonify(error="Введите логин и пароль"), 400

    conn = get_db()
    try:
        user = conn.execute("SELECT * FROM users WHERE login = ?", (login,)).fetchone()
    finally:
        conn.close()

    if not user or not verify_password(password, user["password_hash"]):
        return jsonify(error="Неверный логин или пароль"), 401

    payload = {"id": user["id"], "login": user["login"]}
    resp = jsonify(user=payload)
    set_auth_cookie(resp, sign_token(payload))
    return resp


@auth_bp.route("/logout", methods=["POST"])
def logout():
    resp = jsonify(ok=True)
    clear_auth_cookie(resp)
    return resp


@auth_bp.route("/me", methods=["GET"])
@require_auth
def me():
    conn = get_db()
    try:
        user = conn.execute(
            "SELECT id, login FROM users WHERE id = ?", (g.user["id"],)
        ).fetchone()
    finally:
        conn.close()
    if not user:
        return jsonify(error="Не авторизован"), 401
    return jsonify(user={"id": user["id"], "login": user["login"]})