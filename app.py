from flask import Flask, render_template_string, jsonify
import requests
from datetime import datetime, timedelta
from dateutil import parser
import pytz

app = Flask(__name__)

BASE_URL = "https://sportia-api.onrender.com/api/v1"
LOCAL_TZ = pytz.timezone("UTC")

# ================= TIME FILTER =================

def is_today_or_tomorrow(start_time):
    match_time = parser.isoparse(start_time).astimezone(LOCAL_TZ)
    now = datetime.now(LOCAL_TZ)
    return match_time.date() in [now.date(), (now + timedelta(days=1)).date()]

# ================= FETCH MATCHES =================

def get_matches(sport):
    try:
        r = requests.get(f"{BASE_URL}/matches/upcoming", params={"sport": sport}, timeout=8)
        r.raise_for_status()
        return [m for m in r.json() if is_today_or_tomorrow(m["start_time"])]
    except Exception as e:
        print("❌ Match fetch error:", e)
        return []

# ================= FETCH PREDICTION =================

def get_prediction(match, sport_type):
    payload = {
        "sport": sport_type,
        "league": match["league"],
        "event_id": match["event_id"],
        "home_team": match["home"],
        "away_team": match["away"]
    }

    r = requests.post(f"{BASE_URL}/ai/predict", json=payload, timeout=15)
    r.raise_for_status()
    return r.json()

# ================= HOME =================

@app.route("/")
def home():
    nba_matches = get_matches("nba")
    soccer_matches = get_matches("soccer")

    return render_template_string("""
    <html>
    <head>
        <style>
            body { background:#0b1220; color:white; font-family:Arial; }
            h1 { color:#00ffd5; }
            .card { background:#111a2e; padding:15px; margin:10px; border-radius:8px; }
            a { color:#00ffd5; text-decoration:none; }
        </style>
    </head>
    <body>
        <h1>📅 Partidos Hoy & Mañana</h1>

        <h2>🏀 NBA</h2>
        {% for m in nba %}
            <div class="card">
                {{m.home}} vs {{m.away}}
                <br>
                <a href="/predict/basketball/{{m.event_id}}">Ver Predicción JSON</a>
            </div>
        {% endfor %}

        <h2>⚽ Soccer</h2>
        {% for m in soccer %}
            <div class="card">
                {{m.home}} vs {{m.away}}
                <br>
                <a href="/predict/soccer/{{m.event_id}}">Ver Predicción JSON</a>
            </div>
        {% endfor %}
    </body>
    </html>
    """, nba=nba_matches, soccer=soccer_matches)

# ================= PREDICTION ROUTE =================

@app.route("/predict/<sport>/<event_id>")
def predict(sport, event_id):

    sport_key = "nba" if sport == "basketball" else "soccer"
    matches = get_matches(sport_key)

    match = next((m for m in matches if m["event_id"] == event_id), None)

    if not match:
        return {"error": "Match not found"}, 404

    try:
        pred = get_prediction(match, sport)
        return jsonify(pred)
    except Exception as e:
        return {"error": str(e)}

# ================= RUN =================

if __name__ == "__main__":
    app.run()
