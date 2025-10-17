import os
import sqlite3
from contextlib import closing
from flask import Flask, request, jsonify, send_from_directory, g
from flask_cors import CORS

# -----------------------------------------------------------------------------
# App setup
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "occh.sqlite3")

app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "static"),
    static_url_path="/static",
)
app.config["JSON_SORT_KEYS"] = False

# Allow the Live Server origin (127.0.0.1:5500), localhost:5500, and fall back to *
# This is DEV-friendly; tighten for prod if needed.
CORS(
    app,
    resources={r"/api/*": {"origins": ["http://127.0.0.1:5500", "http://localhost:5500", "*"]}},
    supports_credentials=False,
    max_age=3600,
)

# -----------------------------------------------------------------------------
# DB helpers
# -----------------------------------------------------------------------------
def get_db():
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db

@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                lat REAL,
                lng REAL,
                address TEXT,
                housingType TEXT,
                overall INTEGER,
                comment TEXT,
                landlord TEXT,
                cleanliness INTEGER,
                bugs INTEGER,
                furniture INTEGER,
                proximity INTEGER
            )
            """
        )

# Flask CLI: `flask --app app/server.py init-db`
@app.cli.command("init-db")
def _init_db_cmd():
    init_db()
    print("Initialized SQLite at", DB_PATH)

# -----------------------------------------------------------------------------
# Static: allow opening the frontend from Flask as well (same-origin option)
# -----------------------------------------------------------------------------
@app.route("/")
def root():
    # Serve your existing app/static/index.html if you open 5000 instead of 5500
    return send_from_directory(app.static_folder, "index.html")

# -----------------------------------------------------------------------------
# API
# -----------------------------------------------------------------------------
@app.route("/api/reviews", methods=["GET"])
def list_reviews():
    """
    Returns all reviews as a JSON array.
    Optional bbox query params supported for future use:
      ?minLat=&minLng=&maxLat=&maxLng=
    """
    db = get_db()

    q = "SELECT * FROM reviews"
    params = []
    # Optional bounding box filter (non-breaking if frontend doesn't send it)
    minLat = request.args.get("minLat")
    minLng = request.args.get("minLng")
    maxLat = request.args.get("maxLat")
    maxLng = request.args.get("maxLng")
    if all(v is not None for v in [minLat, minLng, maxLat, maxLng]):
        q += " WHERE lat BETWEEN ? AND ? AND lng BETWEEN ? AND ?"
        params = [float(minLat), float(maxLat), float(minLng), float(maxLng)]

    rows = db.execute(q, params).fetchall()
    data = [dict(r) for r in rows]
    return jsonify(data), 200

@app.route("/api/reviews", methods=["POST"])
def create_review():
    """
    Accepts JSON body.
    Minimal fields (from your README example): lat, lng, address, housingType, overall
    Optional: comment, landlord, cleanliness, bugs, furniture, proximity
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Invalid JSON"}), 400

    lat = payload.get("lat")
    lng = payload.get("lng")
    address = payload.get("address")
    housingType = payload.get("housingType")
    overall = payload.get("overall")

    # Minimal validation
    missing = [k for k in ["lat", "lng", "address", "housingType", "overall"] if payload.get(k) is None]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    comment = payload.get("comment")
    landlord = payload.get("landlord")
    cleanliness = payload.get("cleanliness")
    bugs = payload.get("bugs")
    furniture = payload.get("furniture")
    proximity = payload.get("proximity")

    db = get_db()
    cur = db.execute(
        """
        INSERT INTO reviews (lat, lng, address, housingType, overall, comment,
                             landlord, cleanliness, bugs, furniture, proximity)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            float(lat),
            float(lng),
            str(address),
            str(housingType),
            int(overall),
            comment if comment is not None else None,
            landlord if landlord is not None else None,
            int(cleanliness) if cleanliness is not None else None,
            int(bugs) if bugs is not None else None,
            int(furniture) if furniture is not None else None,
            int(proximity) if proximity is not None else None,
        ),
    )
    db.commit()
    new_id = cur.lastrowid
    row = db.execute("SELECT * FROM reviews WHERE id = ?", (new_id,)).fetchone()
    return jsonify(dict(row)), 201

# -----------------------------------------------------------------------------
# Entry point (safe to call via `flask run` or `python app/server.py`)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=True)
