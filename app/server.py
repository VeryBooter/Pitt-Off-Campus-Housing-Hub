import os
import sqlite3
from datetime import datetime
from flask import Flask, g, jsonify, request, abort
from flask_cors import CORS

BASE_DIR = os.path.dirname(__file__)
DEFAULT_DB = os.environ.get('DATABASE_PATH') or os.path.join(BASE_DIR, 'reviews.db')


def get_db():
    db_path = os.environ.get('DATABASE_PATH', DEFAULT_DB)
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
    return db


def init_db():
    db = sqlite3.connect(os.environ.get('DATABASE_PATH', DEFAULT_DB))
    schema_path = os.path.join(BASE_DIR, 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        db.executescript(f.read())
    db.commit()
    db.close()


def make_app():
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    CORS(app)

    @app.teardown_appcontext
    def close_connection(exception):
        db = getattr(g, '_database', None)
        if db is not None:
            db.close()

    @app.cli.command('init-db')
    def init_db_command():
        """Initialize the database from schema.sql"""
        init_db()
        print('Initialized the database.')

    @app.route('/api/reviews', methods=['GET'])
    def list_reviews():
        # Optional query params: bbox=west,south,east,north  limit
        bbox = request.args.get('bbox')
        limit = int(request.args.get('limit') or 100)
        db = get_db()
        qs = 'SELECT * FROM reviews'
        params = []
        if bbox:
            try:
                west, south, east, north = [float(x) for x in bbox.split(',')]
                qs += ' WHERE lng BETWEEN ? AND ? AND lat BETWEEN ? AND ?'
                params.extend([west, east, south, north])
            except Exception:
                return jsonify({'error': 'invalid bbox'}), 400
        qs += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        cur = db.execute(qs, params)
        rows = cur.fetchall()

        features = []
        for r in rows:
            props = {
                'address': r['address'],
                'housingType': r['housing_type'],
                'overall': r['overall'],
                'afford': r['afford'],
                'maint': r['maint'],
                'safety': r['safety'],
                'noise': r['noise'],
                'note': r['note'],
                'created_at': r['created_at']
            }
            feature = {
                'type': 'Feature',
                'id': r['id'],
                'geometry': { 'type': 'Point', 'coordinates': [r['lng'], r['lat']] },
                'properties': props
            }
            features.append(feature)

        return jsonify({ 'type': 'FeatureCollection', 'features': features })

    @app.route('/api/reviews', methods=['POST'])
    def create_review():
        data = request.get_json() or {}
        # Basic validation
        try:
            lat = float(data.get('lat'))
            lng = float(data.get('lng'))
        except Exception:
            return jsonify({'error': 'lat and lng required and must be numbers'}), 400

        address = (data.get('address') or '').strip()
        if not address or len(address) < 3:
            return jsonify({'error': 'address required'}), 400

        try:
            overall = int(data.get('overall'))
            if not (1 <= overall <= 5):
                raise ValueError()
        except Exception:
            return jsonify({'error': 'overall rating must be an integer between 1 and 5'}), 400

        housingType = data.get('housingType')
        afford = data.get('afford') or None
        maint = data.get('maint') or None
        safety = data.get('safety') or None
        noise = data.get('noise') or None
        note = data.get('note') or None

        created_at = datetime.utcnow().isoformat() + 'Z'

        db = get_db()
        cur = db.execute(
            'INSERT INTO reviews (lat, lng, address, housing_type, overall, afford, maint, safety, noise, note, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
            (lat, lng, address, housingType, overall, afford, maint, safety, noise, note, created_at)
        )
        db.commit()
        new_id = cur.lastrowid

        feature = {
            'type': 'Feature',
            'id': new_id,
            'geometry': { 'type': 'Point', 'coordinates': [lng, lat] },
            'properties': {
                'address': address,
                'housingType': housingType,
                'overall': overall,
                'afford': afford,
                'maint': maint,
                'safety': safety,
                'noise': noise,
                'note': note,
                'created_at': created_at
            }
        }
        return jsonify(feature), 201

    return app


if __name__ == '__main__':
    app = make_app()
    app.run(host='127.0.0.1', port=5000, debug=True)
