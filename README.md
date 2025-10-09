# Pitt Off-Campus Housing Hub — Local backend

This repository contains a minimal Flask backend to support the static frontend in `app/static/index.html`.

Local quickstart

1. Create and activate a virtualenv (macOS):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Initialize the database:

```bash
python -c "from app import server; server.init_db()"
# or: flask --app app/server.py init-db
```

3. Run the server:

```bash
export FLASK_APP=app/server.py
export FLASK_ENV=development
flask run --host=127.0.0.1 --port=5000
```

The server will serve static files from `app/static` at `/static` and provide the API endpoints:

- GET /api/reviews
- POST /api/reviews

Smoke test examples:

```bash
curl -X POST http://127.0.0.1:5000/api/reviews -H "Content-Type: application/json" -d '{"lat":40.444,"lng":-79.956,"address":"Test","housingType":"Apartment","overall":4}'
curl http://127.0.0.1:5000/api/reviews
```
# Pitt-Off-Campus-Housing-Hub
A student-built platform for Pitt undergraduates to rate and review off-campus housing. Includes Google Maps integration, property details, landlord info, and community feedback on proximity, cleanliness, bugs, furniture, and more—helping sophomores and beyond make smarter rental choices.
