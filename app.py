from flask import Flask, render_template_string
import requests
from datetime import datetime
from dateutil import parser
import pytz
import os

app = Flask(__name__)

BASE_URL = "https://sportia-api.onrender.com/api/v1"
LOCAL_TZ = pytz.timezone("UTC")

# ================= API SEGURA =================

def safe_json(r):
    try:
        return r.json()
    except:
        return []

def get_upcoming_matches(sport):
    try:
        r = requests.get(f"{BASE_URL}/matches/upcoming", params={"sport": sport}, timeout=8)
        r.raise_for_status()
        return safe_json(r)
    except Exception as e:
        print("❌ Match fetch error:", e)
        return []

def get_prediction(match, sport):
    payload = {
        "sport": sport,
        "league": match["league"],
        "event_id": match["event_id"],
        "home_team": match["home"],
        "away_team": match["away"]
    }
    try:
        r = requests.post(f"{BASE_URL}/ai/predict", json=payload, timeout=12)
        r.raise_for_status()
        return safe_json(r)
    except Exception as e:
        print("❌ Prediction error:", e)
        return {}

# ================= FECHA HOY =================

def is_today(start_time):
    match_time = parser.isoparse(start_time).astimezone(LOCAL_TZ)
    return match_time.date() == datetime.now(LOCAL_TZ).date()

# ================= RUTA HOME =================

@app.route("/")
def home():
    matches = []

    for sport in ["nba", "soccer"]:
        for m in get_upcoming_matches(sport):
            if is_today(m["start_time"]):
                matches.append({
                    "sport": "basketball" if sport == "nba" else "soccer",
                    "event_id": m["event_id"],
                    "home": m["home"],
                    "away": m["away"]
                })

    html = """
    <html>
    <head>
    <title>QuantumBetLab - Selecciona Partido</title>
    <style>
    body { font-family: Arial; background:#0a0f1e; color:white; padding:30px;}
    h1 { color:#00ffcc; }
    .card { background:#11182e; padding:15px; margin:15px 0; border-radius:10px; }
    a { color:#00ffcc; text-decoration:none; font-weight:bold; }
    </style>
    </head>
    <body>
    <h1>📅 Partidos de Hoy</h1>
    {% if matches %}
        {% for m in matches %}
            <div class="card">
                {{m.home}} vs {{m.away}}<br>
                <a href="/predict/{{m.sport}}/{{m.event_id}}/{{m.home}}/{{m.away}}">
                    ▶ Ver predicción IA
                </a>
            </div>
        {% endfor %}
    {% else %}
        <div class="card">No hay partidos hoy.</div>
    {% endif %}
    </body>
    </html>
    """
    return render_template_string(html, matches=matches)

# ================= PREDICCIÓN =================

@app.route("/predict/<sport>/<event_id>/<home>/<away>")
def predict(sport, event_id, home, away):

    match = {
        "league": "",
        "event_id": event_id,
        "home": home,
        "away": away
    }

    pred = get_prediction(match, sport)

    html = """
    <html>
    <head>
    <title>Predicción IA</title>
    <style>
    body { font-family: Arial; background:#0a0f1e; color:white; padding:30px;}
    h1 { color:#00ffcc; }
    .card { background:#11182e; padding:15px; margin:15px 0; border-radius:10px; }
    a { color:#00ffcc; }
    </style>
    </head>
    <body>
    <h1>🤖 Predicción IA</h1>
    <h2>{{home}} vs {{away}}</h2>

    {% if pred.player_props %}
        {% for p in pred.player_props %}
            <div class="card">
                {{p.name}} {{p.bet_decision}} {{p.line}} {{p.type}}<br>
                Prob Modelo: {{ (p.model_prob_over * 100)|round(1) }}%<br>
                Edge: +{{ (p.edge_over * 100)|round(1) }}%
            </div>
        {% endfor %}
    {% else %}
        <div class="card">No hay props disponibles.</div>
    {% endif %}

    <br><a href="/">⬅ Volver</a>
    </body>
    </html>
    """
    return render_template_string(html, pred=pred, home=home, away=away)

# ================= RUN =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
