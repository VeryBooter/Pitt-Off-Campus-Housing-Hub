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


limiter = Limiter(get_remote_address, app=app, default_limits=["200/hour"]) # global cap


# CORS only for Live Server use; off by default
if os.getenv("ENABLE_CORS", "0") == "1":
from flask_cors import CORS
CORS(app, resources={r"/auth/*": {"origins": ["http://127.0.0.1:5500", "http://localhost:5500"]}})


# ----------------------------------------------------------------------------
# DB helpers & schema
# ----------------------------------------------------------------------------


def _db():
conn = getattr(app, "_db", None)
if conn is None:
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
app._db = conn
return conn




def init_db():
conn = _db(); cur = conn.cursor()


# Reviews (existing feature)
cur.execute(
"""
CREATE TABLE IF NOT EXISTS reviews (
id INTEGER PRIMARY KEY AUTOINCREMENT,
lat REAL,
lng REAL,
address TEXT,
housingType TEXT,
overall INTEGER,
created_at TEXT NOT NULL
)
"""
)


# Users + verification
cur.execute(
"""
CREATE TABLE IF NOT EXISTS users (
id INTEGER PRIMARY KEY AUTOINCREMENT,
pitt_email TEXT UNIQUE,
verified_at TEXT,
created_at TEXT NOT NULL
)
"""
)


cur.execute(
"""
CREATE TABLE IF NOT EXISTS email_verification_tokens (
id INTEGER PRIMARY KEY AUTOINCREMENT,
email TEXT NOT NULL,
token_hash TEXT NOT NULL,
expires_at TEXT NOT NULL,
used_at TEXT,
created_ip TEXT,
created_ua TEXT
app.run(host="127.0.0.1", port=5000)