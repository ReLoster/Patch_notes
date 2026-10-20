import os
import time
from functools import wraps
from pathlib import Path

import jwt
from flask import request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash

COOKIE_NAME = "token"
COOKIE_MAX_AGE = 30 * 24 * 60 * 60

_SECRET_KEY = None
BASE_DIR = Path(__file__).resolve().parent


def get_secret_key() -> str:
    global _SECRET_KEY
    if _SECRET_KEY is not None:
        return _SECRET_KEY
    key = os.environ.get("SECRET_KEY")
    if key:
        _SECRET_KEY = key
        return key
    key_file = BASE_DIR / ".secret_key"
    if key_file.exists():
        _SECRET_KEY = key_file.read_text(encoding="utf-8").strip()
        return _SECRET_KEY
    _SECRET_KEY = os.urandom(32).hex()
    key_file.write_text(_SECRET_KEY, encoding="utf-8")
    os.chmod(key_file, 0o600)
    return _SECRET_KEY


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return check_password_hash(password_hash, password)


def sign_token(user: dict) -> str:
    payload = {
        "id": user["id"],
        "login": user["login"],
        "exp": int(time.time()) + COOKIE_MAX_AGE,
    }
    return jwt.encode(payload, get_secret_key(), algorithm="HS256")


def decode_token(token: str):
    try:
        return jwt.decode(token, get_secret_key(), algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.cookies.get(COOKIE_NAME)
        if not token:
            return jsonify(error="Не авторизован"), 401
        data = decode_token(token)
        if not data:
            return jsonify(error="Сессия истекла"), 401
        g.user = data
        return f(*args, **kwargs)
    return wrapper


def set_auth_cookie(response, token: str):
    response.set_cookie(
        COOKIE_NAME, token,
        max_age=COOKIE_MAX_AGE, httponly=True, samesite="Lax",
        secure=os.environ.get("FLASK_ENV") == "production", path="/",
    )
    return response


def clear_auth_cookie(response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return response