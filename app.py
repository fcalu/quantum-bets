from flask import Flask, render_template_string, request, jsonify
import requests
from datetime import datetime
from dateutil import parser
import pytz

app = Flask(__name__)

BASE_URL = "https://sportia-api.onrender.com/api/v1"
LOCAL_TZ = pytz.timezone("UTC")


# ================= PARTIDOS (RÁPIDO) =================

def get_today_matches(sport):
    try:
        r = requests.get(f"{BASE_URL}/matches/upcoming", params={"sport": sport}, timeout=5)
        r.raise_for_status()
        matches = r.json()
    except:
        return []

    today = datetime.now(LOCAL_TZ).date()
    result = []

    for m in matches:
        match_time = parser.isoparse(m["start_time"]).astimezone(LOCAL_TZ)
        if match_time.date() == today:
            m["time"] = match_time.strftime("%H:%M")
            m["sport"] = sport
            result.append(m)

    return result


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
            button { background:#00ffe1; border:none; padding:10px; cursor:pointer }
            .pred { margin-top:10px; padding:10px; background:#1a2336; border-radius:10px }
        </style>
    </head>
    <body>
        <h1>📅 Partidos de Hoy</h1>

        {% for m in matches %}
            <div class="match">
                {{m.home}} vs {{m.away}} — {{m.time}}
                <button onclick="getPred('{{m.sport}}','{{m.event_id}}','{{m.league}}','{{m.home}}','{{m.away}}')">
                    Ver Predicción
                </button>
                <div id="pred_{{m.event_id}}" class="pred"></div>
            </div>
        {% endfor %}

        <script>
        function getPred(sport,id,league,home,away){
            fetch(`/api/predict?sport=${sport}&id=${id}&league=${league}&home=${home}&away=${away}`)
            .then(r=>r.json())
            .then(data=>{
                let box = document.getElementById("pred_"+id)
                if(data.error){
                    box.innerHTML = "⚠️ API no disponible"
                }else{
                    box.innerHTML = data.html
                }
            })
        }
        </script>
    </body>
    </html>
    """
    return render_template_string(template, matches=matches)


# ================= PREDICCIÓN AJAX =================

@app.route("/api/predict")
def api_predict():
    sport = request.args.get("sport")
    event_id = request.args.get("id")
    league = request.args.get("league")
    home = request.args.get("home")
    away = request.args.get("away")

    payload = {
        "sport": sport,
        "league": league,
        "event_id": event_id,
        "home_team": home,
        "away_team": away
    }

    try:
        r = requests.post(f"{BASE_URL}/ai/predict", json=payload, timeout=10)
        r.raise_for_status()
        pred = r.json()
    except:
        return jsonify({"error": True})

    html = ""

    if sport == "nba":
        for p in pred.get("player_props", []):
            if p.get("bet_tier") == "VALUE BET":
                html += f"{p['name']} OVER {p['line']} {p['type']}<br>"

    else:
        for m in pred.get("player_props", []):
            if m.get("bet_tier") == "VALUE BET":
                side = "UNDER" if m["bet_decision"] == "UNDER" else "OVER"
                html += f"{m['type']} {side} {m['line']}<br>"

    return jsonify({"html": html})


if __name__ == "__main__":
    app.run()
