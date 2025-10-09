-- SQLite schema for reviews
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    address TEXT NOT NULL,
    housing_type TEXT,
    overall INTEGER NOT NULL,
    afford INTEGER,
    maint INTEGER,
    safety INTEGER,
    noise INTEGER,
    note TEXT,
    created_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_reviews_lat_lng ON reviews(lat, lng);
