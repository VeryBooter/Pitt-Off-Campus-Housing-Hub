import os
import sqlite3
from contextlib import closing
from pathlib import Path
import requests
from flask import Flask, jsonify, request
from dotenv import load_dotenv

load_dotenv()

APP_ROOT = Path(__file__).resolve().parent
DB_PATH = APP_ROOT / "data.db"
SCHEMA_PATH = APP_ROOT / "schema.sql"

app = Flask(__name__, static_folder=str(APP_ROOT / "static"), static_url_path="/static")

# Serve the SPA index safely (prevents 403 path issues)
@app.route("/")
def root():
    return app.send_static_file("index.html")

@app.get("/api/health")
def health():
    return jsonify({"ok": True})

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SCHEMA_PATH.exists():
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f, get_db() as conn:
            conn.executescript(f.read())
            conn.commit()

# --- Geocoder needed by the search bar ---
@app.get("/api/geocode")
def geocode():
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"error": "Missing 'q' parameter"}), 400

    email = os.getenv("NOMINATIM_EMAIL", "admin@example.com")
    ua = f"PittOffCampusHousingHub/1.0 ({email})"

    params = {
        "format": "jsonv2",
        "q": q,
        "limit": 5,
        "addressdetails": 1,
        "bounded": 1,
        # west,south,east,north (bounds around Oakland/Pitt)
        "viewbox": ",".join([str(-80.05), str(40.40), str(-79.90), str(40.48)]),
    }
    r = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params=params,
        headers={"User-Agent": ua},
        timeout=10,
    )
    r.raise_for_status()
    raw = r.json()
    items = [{
        "external_id": f"osm:{it['place_id']}",
        "name": it.get("name") or it.get("display_name", "Unknown"),
        "address": it.get("display_name"),
        "lat": float(it["lat"]),
        "lng": float(it["lon"]),
    } for it in raw]
    return jsonify(items)

# --- Reviews (compatible with your README) ---
@app.get("/api/reviews")
def list_reviews():
    external_id = request.args.get("external_id")
    with get_db() as conn:
        cur = conn.cursor()
        if external_id:
            cur.execute(
                """SELECT id, rating, comment, created_at
                   FROM reviews WHERE external_id = ?
                   ORDER BY created_at DESC""",
                (external_id,),
            )
            reviews = [dict(row) for row in cur.fetchall()]
            cur.execute("SELECT AVG(rating), COUNT(*) FROM reviews WHERE external_id = ?", (external_id,))
            avg, count = cur.fetchone()
            return jsonify({
                "external_id": external_id,
                "avg_rating": round(avg, 2) if avg is not None else None,
                "count": count,
                "reviews": reviews,
            })
        else:
            # recent aggregates (optional)
            cur.execute(
                """SELECT external_id, AVG(rating) AS avg_rating, COUNT(*) AS count
                   FROM reviews GROUP BY external_id ORDER BY MAX(created_at) DESC LIMIT 25"""
            )
            return jsonify([dict(row) for row in cur.fetchall()])

@app.post("/api/reviews")
def create_review():
    data = request.get_json(force=True, silent=True) or {}
    for k in ["external_id","rating","name","lat","lng"]:
        if k not in data:
            return jsonify({"error": f"Missing fields: {k}"}), 400
    r = int(data["rating"])
    if not (1 <= r <= 5):
        return jsonify({"error": "rating must be 1..5"}), 400
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """CREATE TABLE IF NOT EXISTS places (
                   external_id TEXT PRIMARY KEY,
                   name TEXT NOT NULL,
                   address TEXT,
                   lat REAL NOT NULL,
                   lng REAL NOT NULL,
                   source TEXT DEFAULT 'nominatim'
               )"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS reviews (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   external_id TEXT NOT NULL,
                   rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                   comment TEXT,
                   created_at TEXT NOT NULL DEFAULT (datetime('now'))
               )"""
        )
        cur.execute(
            """INSERT INTO places (external_id, name, address, lat, lng)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(external_id) DO UPDATE SET
                 name=excluded.name, address=excluded.address, lat=excluded.lat, lng=excluded.lng""",
            (data["external_id"], data["name"], data.get("address"), float(data["lat"]), float(data["lng"]))
        )
        cur.execute(
            "INSERT INTO reviews (external_id, rating, comment) VALUES (?, ?, ?)",
            (data["external_id"], r, (data.get("comment") or "").strip())
        )
        conn.commit()
    return jsonify({"ok": True}), 201

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--init-db", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=5000, type=int)
    args = parser.parse_args()
    if args.init_db:
        init_db()
    else:
        if not DB_PATH.exists():
            init_db()
        app.run(host=args.host, port=args.port, debug=True)
