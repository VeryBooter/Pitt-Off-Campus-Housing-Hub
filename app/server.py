# app/server.py
import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional
from flask_cors import CORS

from flask import Flask, request, jsonify, redirect, current_app
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_db_path() -> str:
    return os.getenv("DATABASE_PATH", os.path.join(BASE_DIR, "data.sqlite3"))

def init_db(db_path: Optional[str] = None) -> None:
    """Create DB file and tables if missing."""
    db_path = db_path or get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lat REAL,
                lng REAL,
                address TEXT,
                housingType TEXT,
                overall INTEGER,
                quick_comment TEXT,
                who_runs TEXT,
                proximity TEXT,
                cleanliness INTEGER,
                pests TEXT,
                furniture TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

def _db():
    conn = getattr(current_app, "_db", None)
    if conn is None:
        conn = sqlite3.connect(current_app.config["DATABASE_PATH"], check_same_thread=False)
        conn.row_factory = sqlite3.Row
        current_app._db = conn
    return conn

def make_app():
    load_dotenv()
    CORS(app, resources={r"/api/*": {"origins": ["http://127.0.0.1:5500", "http://localhost:5500"]}})

    # Serve your static files at /app/static so the URL matches your screenshot
    app = Flask(
        __name__,
        static_folder=os.path.join(BASE_DIR, "static"),
        static_url_path="/app/static",
    )
    app.config["DATABASE_PATH"] = get_db_path()

    # 🔑 Ensure the DB/table exists at startup (no manual step needed)
    with app.app_context():
        init_db(app.config["DATABASE_PATH"])

    @app.route("/")
    def root():
        return redirect("/app/static/index.html", code=302)

    @app.route("/api/health")
    def health():
        return jsonify({"ok": True}), 200

    @app.route("/api/reviews", methods=["POST"])
    def create_review():
        data = request.get_json(silent=True) or {}
        try:
            lat = float(data.get("lat"))
            lng = float(data.get("lng"))
        except (TypeError, ValueError):
            return jsonify({"error": "lat/lng required"}), 400

        def _int(x):
            try:
                return int(x) if x not in (None, "") else None
            except Exception:
                return None

        row = {
            "lat": lat,
            "lng": lng,
            "address": (data.get("address") or "").strip(),
            "housingType": (data.get("housingType") or "").strip(),
            "overall": _int(data.get("overall")),
            "quick_comment": (data.get("quick_comment") or "").strip(),
            "who_runs": (data.get("who_runs") or "").strip(),
            "proximity": (data.get("proximity") or "").strip(),
            "cleanliness": _int(data.get("cleanliness")),
            "pests": (data.get("pests") or "").strip(),
            "furniture": (data.get("furniture") or "").strip(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            conn = _db()
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO reviews
                   (lat,lng,address,housingType,overall,quick_comment,who_runs,proximity,cleanliness,pests,furniture,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    row["lat"], row["lng"], row["address"], row["housingType"], row["overall"],
                    row["quick_comment"], row["who_runs"], row["proximity"], row["cleanliness"],
                    row["pests"], row["furniture"], row["created_at"],
                ),
            )
            conn.commit()
        except sqlite3.OperationalError as e:
            # If table was missing for some reason, create it and try once more
            init_db(current_app.config["DATABASE_PATH"])
            conn = _db()
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO reviews
                   (lat,lng,address,housingType,overall,quick_comment,who_runs,proximity,cleanliness,pests,furniture,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    row["lat"], row["lng"], row["address"], row["housingType"], row["overall"],
                    row["quick_comment"], row["who_runs"], row["proximity"], row["cleanliness"],
                    row["pests"], row["furniture"], row["created_at"],
                ),
            )
            conn.commit()

        feature = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [row["lng"], row["lat"]]},
            "properties": {
                "address": row["address"],
                "housingType": row["housingType"],
                "overall": row["overall"],
                "quick_comment": row["quick_comment"],
                "who_runs": row["who_runs"],
                "proximity": row["proximity"],
                "cleanliness": row["cleanliness"],
                "pests": row["pests"],
                "furniture": row["furniture"],
                "created_at": row["created_at"],
            },
        }
        return jsonify(feature), 201

    @app.route("/api/reviews", methods=["GET"])
    def list_reviews():
        try:
            conn = _db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM reviews ORDER BY id DESC")
        except sqlite3.OperationalError:
            # auto-heal: create table then return empty list
            init_db(current_app.config["DATABASE_PATH"])
            return jsonify({"type": "FeatureCollection", "features": []})

        features = []
        for r in cur.fetchall():
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [r["lng"], r["lat"]]},
                "properties": {
                    "address": r["address"],
                    "housingType": r["housingType"],
                    "overall": r["overall"],
                    "quick_comment": r["quick_comment"],
                    "who_runs": r["who_runs"],
                    "proximity": r["proximity"],
                    "cleanliness": r["cleanliness"],
                    "pests": r["pests"],
                    "furniture": r["furniture"],
                    "created_at": r["created_at"],
                },
            })
        return jsonify({"type": "FeatureCollection", "features": features})

    return app

app = make_app()

if __name__ == "__main__":
    # run on 5500 so the page & API are same-origin
    app.run(host="127.0.0.1", port=5500, debug=True)
