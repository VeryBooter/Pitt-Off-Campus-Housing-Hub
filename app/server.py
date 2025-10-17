import os, sqlite3, hashlib, smtplib, ssl, secrets
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from urllib.parse import urlencode


from flask import Flask, jsonify, request, redirect, Blueprint
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from itsdangerous import URLSafeSerializer
from email_validator import validate_email, EmailNotValidError
from dotenv import load_dotenv


# ----------------------------------------------------------------------------
# App & config
# ----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DB_PATH = os.path.join(BASE_DIR, "data.sqlite3")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


load_dotenv()
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:5000")


# Flask‑Limiter v3+ init pattern (avoids __init__ signature issues across versions)
limiter = Limiter(key_func=get_remote_address)
limiter.init_app(app)


# Optional CORS (only if you serve frontend via VS Code Live Server on 5500)
if os.getenv("ENABLE_CORS", "0") == "1":
try:
from flask_cors import CORS
CORS(app, resources={r"/auth/*": {"origins": ["http://127.0.0.1:5500", "http://localhost:5500"]}})
except Exception as e:
print("CORS disabled:", e)
app.run(host="127.0.0.1", port=5000)