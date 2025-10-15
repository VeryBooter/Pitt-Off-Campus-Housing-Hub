import os, requests  # ensure these imports are present at the top
import sqlite3
from contextlib import closing
from pathlib import Path
import requests
from flask import Flask, jsonify, request, send_from_directory
from flask import request, jsonify
from dotenv import load_dotenv
from flask_cors import CORS  # <-- add this


# --- Setup ---
load_dotenv()
APP_ROOT = Path(__file__).resolve().parent
DB_PATH = APP_ROOT / "data.db"
SCHEMA_PATH = APP_ROOT / "schema.sql"

app = Flask(__name__, static_folder=str(APP_ROOT / "static"), static_url_path="/static")

# --- DB helpers ---
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(get_db()) as conn, open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
        conn.commit()

# --- Routes ---
@app.route("/")
def root():
    return send_from_directory(app.static_folder, "index.html")

@app.get("/api/health")
def health():
    return jsonify({"ok": True})

@app.get("/api/geocode")
def geocode():
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"error": "Missing 'q' parameter"}), 400

    # Respect Nominatim usage policy
    email = os.getenv("NOMINATIM_EMAIL", "admin@example.com")
    ua = f"PittOffCampusHousingHub/1.0 ({email})"

    params = {
        "format": "jsonv2",
        "q": q,
        "limit": 5,
        "addressdetails": 1,
        "bounded": 1,
        # west,south,east,north — bounds around Oakland/Pitt
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

    def to_item(it):
        return {
            "external_id": f"osm:{it['place_id']}",
            "name": it.get("name") or it.get("display_name", "Unknown"),
            "address": it.get("display_name"),
            "lat": float(it["lat"]),
            "lng": float(it["lon"]),
        }

    return jsonify([to_item(it) for it in raw])

@app.get("/api/reviews")
def list_reviews():
    external_id = request.args.get("external_id")
    with closing(get_db()) as conn:
        cur = conn.cursor()
        if external_id:
            cur.execute(
                """
                SELECT r.id, r.rating, r.comment, r.created_at
                FROM reviews r
                WHERE r.external_id = ?
                ORDER BY r.created_at DESC
                """,
                (external_id,),
            )
            reviews = [dict(row) for row in cur.fetchall()]
            cur.execute(
                "SELECT AVG(rating), COUNT(*) FROM reviews WHERE external_id = ?",
                (external_id,),
            )
            avg, count = cur.fetchone()
            return jsonify({
                "external_id": external_id,
                "avg_rating": round(avg, 2) if avg else None,
                "count": count,
                "reviews": reviews,
            })
        else:
            cur.execute(
                """
                SELECT p.name, p.address, p.external_id, p.lat, p.lng,
                       AVG(r.rating) as avg_rating, COUNT(r.id) as count
                FROM places p
                JOIN reviews r ON r.external_id = p.external_id
                GROUP BY p.external_id
                ORDER BY MAX(r.created_at) DESC
                LIMIT 25
                """
            )
            return jsonify([dict(row) for row in cur.fetchall()])

@app.post("/api/reviews")
def create_review():
    data = request.get_json(force=True, silent=True) or {}
    required = ["external_id", "rating", "name", "lat", "lng"]
    missing = [k for k in required if k not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    rating = int(data["rating"])
    if rating < 1 or rating > 5:
        return jsonify({"error": "rating must be 1..5"}), 400

    with closing(get_db()) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO places (external_id, name, address, lat, lng)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(external_id) DO UPDATE SET
              name=excluded.name,
              address=excluded.address,
              lat=excluded.lat,
              lng=excluded.lng
            """,
            (data["external_id"], data["name"], data.get("address"), float(data["lat"]), float(data["lng"])),
        )
        cur.execute(
            "INSERT INTO reviews (external_id, rating, comment) VALUES (?, ?, ?)",
            (data["external_id"], rating, data.get("comment")),
        )
        conn.commit()
    return jsonify({"ok": True}), 201

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Pitt Off-Campus Housing Hub API")
    parser.add_argument("--init-db", action="store_true", help="Initialize SQLite schema")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=5000, type=int)
    args = parser.parse_args()

    if args.init_db:
        init_db()
        print("DB initialized at:", DB_PATH)
    else:
        if not DB_PATH.exists():
            print("Initializing DB...")
            init_db()
        app.run(host=args.host, port=args.port, debug=True)
