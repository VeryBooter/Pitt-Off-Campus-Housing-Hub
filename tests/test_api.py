import json
import tempfile
import os
import sqlite3
import pytest

from app import server


@pytest.fixture
def client(tmp_path, monkeypatch):
    # create temp db
    db_file = tmp_path / "test_reviews.db"
    monkeypatch.setenv('DATABASE_PATH', str(db_file))
    # init schema
    server.init_db()
    app = server.make_app()
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


def test_post_and_get_review(client):
    payload = {
        'lat': 40.444,
        'lng': -79.956,
        'address': 'PyTest Address',
        'housingType': 'Apartment',
        'overall': 5
    }
    rv = client.post('/api/reviews', data=json.dumps(payload), content_type='application/json')
    assert rv.status_code == 201
    data = rv.get_json()
    assert data['type'] == 'Feature'
    assert data['geometry']['coordinates'][0] == payload['lng']

    # now GET
    rv2 = client.get('/api/reviews')
    assert rv2.status_code == 200
    fc = rv2.get_json()
    assert fc['type'] == 'FeatureCollection'
    assert len(fc['features']) >= 1
