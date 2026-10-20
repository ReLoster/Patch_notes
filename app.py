import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, send_from_directory, request

load_dotenv()

from db import init_db
from extensions import limiter
from routes.auth import auth_bp
from routes.notes import notes_bp
from routes.folders import folders_bp # <--- НОВОЕ

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")
limiter.init_app(app)

app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(notes_bp, url_prefix="/api/notes")
app.register_blueprint(folders_bp, url_prefix="/api/folders") # <--- НОВОЕ


@app.route("/")
def index_page():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/login.html")
def login_page():
    return send_from_directory(STATIC_DIR, "login.html")


@app.route("/register.html")
def register_page():
    return send_from_directory(STATIC_DIR, "register.html")


@app.errorhandler(404)
def not_found(_):
    if request.path.startswith("/api/"):
        return jsonify(error="Not found"), 404
    return send_from_directory(STATIC_DIR, "index.html")


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 3000))
    debug = os.environ.get("FLASK_DEBUG") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)