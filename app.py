from flask import Flask, render_template_string, request
import requests
from datetime import datetime
from dateutil import parser
import pytz

app = Flask(__name__)

BASE_URL = "https://sportia-api.onrender.com/api/v1"
LOCAL_TZ = pytz.timezone("UTC")


# ================= API SEGURA =================

def safe_get(url, params=None, timeout=8):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("❌ Match fetch error:", e)
        return []


def safe_post(url, payload, timeout=12):
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("❌ Prediction error:", e)
        return None


# ================= PARTIDOS DE HOY =================

def get_today_matches(sport):
    matches = safe_get(f"{BASE_URL}/matches/upcoming", {"sport": sport})
    today = datetime.now(LOCAL_TZ).date()

    result = []
    for m in matches:
        match_time = parser.isoparse(m["start_time"]).astimezone(LOCAL_TZ)
        if match_time.date() == today:
            m["time"] = match_time.strftime("%H:%M")
            m["sport"] = sport
            result.append(m)
    return result


# ================= PREDICCIÓN =================

def get_prediction(match, sport):
    payload = {
        "sport": sport,
        "league": match["league"],
        "event_id": match["event_id"],
        "home_team": match["home"],
        "away_team": match["away"]
    }
    return safe_post(f"{BASE_URL}/ai/predict", payload)


# ================= HOME =================

@app.route("/")
def home():
    nba = get_today_matches("nba")
    soccer = get_today_matches("soccer")
    matches = nba + soccer

    template = """
    <html>
    <head>
        <title>Quantum IA Bets</title>
        <style>
            body { background:#0b0f1a; color:white; font-family:Arial; padding:40px }
            h1 { color:#00ffe1 }
            .match { background:#121a2b; padding:15px; margin:10px 0; border-radius:10px }
            a { color:#00ffe1; text-decoration:none; font-weight:bold }
        </style>
    </head>
    <body>
        <h1>📅 Partidos de Hoy</h1>
        {% if matches %}
            {% for m in matches %}
                <div class="match">
                    <a href="/predict/{{m.sport}}/{{m.event_id}}?league={{m.league}}&home={{m.home}}&away={{m.away}}">
                        {{m.home}} vs {{m.away}} — {{m.time}}
                    </a>
                </div>
            {% endfor %}
        {% else %}
            <p>No hay partidos hoy.</p>
        {% endif %}
    </body>
    </html>
    """
    return render_template_string(template, matches=matches)


# ================= PREDICT PAGE =================

@app.route("/predict/<sport>/<event_id>")
def predict(sport, event_id):
    league = request.args.get("league")
    home = request.args.get("home")
    away = request.args.get("away")

    match = {
        "league": league,
        "event_id": event_id,
        "home": home,
        "away": away
    }

    pred = get_prediction(match, sport)

    if not pred:
        return "<h2>Error obteniendo predicción</h2>"

    picks = []

    if sport == "nba":
        for p in pred.get("player_props", []):
            if p.get("bet_tier") == "VALUE BET" and p.get("confidence",0) >= 60:
                picks.append({
                    "market": f"{p['name']} OVER {p['line']} {p['type']}",
                    "prob": p["model_prob_over"],
                    "edge": p["edge_over"]
                })

    else:  # Soccer
        for m in pred.get("player_props", []):
            if m.get("bet_tier") == "VALUE BET":
                if m["bet_decision"] == "UNDER":
                    prob = m["model_prob_under"]
                    edge = m["edge_under"]
                    side = "UNDER"
                else:
                    prob = m["model_prob_over"]
                    edge = m["edge_over"]
                    side = "OVER"

                picks.append({
                    "market": f"{m['type']} {side} {m['line']}",
                    "prob": prob,
                    "edge": edge
                })

    template = """
    <html>
    <head>
        <style>
            body { background:#0b0f1a; color:white; font-family:Arial; padding:40px }
            h1 { color:#00ffe1 }
            .pick { background:#121a2b; padding:15px; margin:10px 0; border-radius:10px }
        </style>
    </head>
    <body>
        <h1>🔥 {{home}} vs {{away}}</h1>

        {% if picks %}
            {% for p in picks %}
                <div class="pick">
                    {{p.market}}<br>
                    Prob: {{ (p.prob*100)|round(1) }}% | Edge: +{{ (p.edge*100)|round(1) }}%
                </div>
            {% endfor %}
        {% else %}
            <p>No hay VALUE BETS fuertes.</p>
        {% endif %}

        <br><a href="/" style="color:#00ffe1">⬅ Volver</a>
    </body>
    </html>
    """
    return render_template_string(template, picks=picks, home=home, away=away)


# ================= RUN =================

if __name__ == "__main__":
    app.run()
