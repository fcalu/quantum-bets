from flask import Flask, render_template_string
import requests
from datetime import datetime, timedelta
from dateutil import parser
import pytz

app = Flask(__name__)

BASE_URL = "https://sportia-api.onrender.com/api/v1"
LOCAL_TZ = pytz.timezone("UTC")

def get_upcoming_matches(sport):
    r = requests.get(f"{BASE_URL}/matches/upcoming", params={"sport": sport})
    return r.json()

def get_prediction(match, sport):
    payload = {
        "sport": sport,
        "league": match["league"],
        "event_id": match["event_id"],
        "home_team": match["home"],
        "away_team": match["away"]
    }
    r = requests.post(f"{BASE_URL}/ai/predict", json=payload)
    return r.json()

def is_today_or_tomorrow(start_time):
    match_time = parser.isoparse(start_time).astimezone(LOCAL_TZ)
    now = datetime.now(LOCAL_TZ)
    return match_time.date() in [now.date(), (now + timedelta(days=1)).date()]

STAT_STABILITY = {"Rebounds": 1.25, "Assists": 1.1, "Points": 1.0}

def extract_nba(pred, match):
    picks = []
    for prop in pred.get("player_props", []):
        if prop["bet_tier"] == "VALUE BET" and prop["confidence"] >= 60:
            score = prop["edge_over"] * prop["model_prob_over"] * STAT_STABILITY.get(prop["type"], 1)
            picks.append({
                "sport": "NBA",
                "match": f"{match['home']} vs {match['away']}",
                "market": f"{prop['name']} OVER {prop['line']} {prop['type']}",
                "prob": round(prop["model_prob_over"] * 100, 1),
                "edge": round(prop["edge_over"] * 100, 1),
                "score": score
            })
    return picks

def extract_soccer(pred):
    picks = []
    for m in pred.get("player_props", []):
        if m["bet_tier"] == "VALUE BET":
            prob = m["model_prob_under"] if m["bet_decision"] == "UNDER" else m["model_prob_over"]
            edge = m["edge_under"] if m["bet_decision"] == "UNDER" else m["edge_over"]
            picks.append({
                "sport": "SOCCER",
                "match": pred["match"],
                "market": f"{m['type']} {m['bet_decision']} {m['line']}",
                "prob": round(prob * 100, 1),
                "edge": round(edge * 100, 1),
                "score": prob * edge
            })
    return picks

@app.route("/")
def home():
    all_picks = []

    for m in get_upcoming_matches("nba"):
        if is_today_or_tomorrow(m["start_time"]):
            pred = get_prediction(m, "basketball")
            all_picks.extend(extract_nba(pred, m))

    for m in get_upcoming_matches("soccer"):
        if is_today_or_tomorrow(m["start_time"]):
            pred = get_prediction(m, "soccer")
            all_picks.extend(extract_soccer(pred))

    top = sorted(all_picks, key=lambda x: x["score"], reverse=True)[:7]

    html = """
    <html>
    <head>
    <title>QuantumBetLab AI Picks</title>
    <style>
    body { font-family: Arial; background:#0a0f1e; color:white; padding:30px;}
    h1 { color:#00ffcc; }
    .card { background:#11182e; padding:15px; margin:15px 0; border-radius:10px; }
    </style>
    </head>
    <body>
    <h1>🔥 TOP AI PICKS MULTISPORT</h1>
    {% for p in picks %}
        <div class="card">
            <b>[{{p.sport}}]</b> {{p.match}}<br>
            {{p.market}}<br>
            Prob: {{p.prob}}% | Edge: +{{p.edge}}%
        </div>
    {% endfor %}
    </body>
    </html>
    """
    return render_template_string(html, picks=top)

if __name__ == "__main__":
    app.run()
