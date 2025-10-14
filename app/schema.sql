PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS places (
  external_id TEXT PRIMARY KEY,              -- e.g., "osm:123456789"
  name        TEXT NOT NULL,
  address     TEXT,
  lat         REAL NOT NULL,
  lng         REAL NOT NULL,
  source      TEXT DEFAULT 'nominatim'
);

CREATE TABLE IF NOT EXISTS reviews (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  external_id TEXT NOT NULL,
  rating      INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
  comment     TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (external_id) REFERENCES places(external_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_reviews_external_id ON reviews(external_id);
