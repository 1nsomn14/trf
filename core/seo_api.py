"""
core/seo_api.py
"""

import os
import json
import base64
import datetime as dt
import requests

# ==============================
# Config
# ==============================
MOZ_API_KEY = "mozscape-5aedce5b80:e1d3565b634d368dfc57a4c833bd4a62"
MOZ_API_URL = "https://lsapi.seomoz.com/v2/url_metrics"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
HISTORY_DIR = os.path.join(DATA_DIR, "seo_history")
os.makedirs(HISTORY_DIR, exist_ok=True)


# ==============================
# Get SEO Info (single snapshot)
# ==============================
def get_seo_info(domain: str, timeout: int = 10):
    if not domain:
        raise ValueError("Domain tidak boleh kosong")
    headers = {
        "Content-Type": "text/plain",
        "Authorization": "Basic " + base64.b64encode(MOZ_API_KEY.encode()).decode()
    }
    payload = json.dumps({"targets": [domain]})
    try:
        res = requests.post(MOZ_API_URL, headers=headers, data=payload, timeout=timeout)
        res.raise_for_status()
        data = res.json()
        # return first result object or whole data if shape berbeda
        if isinstance(data, dict) and "results" in data and len(data["results"]) > 0:
            return data["results"][0]
        return data
    except requests.RequestException as e:
        return {"error": str(e)}


# ==============================
# History helpers
# ==============================
def _history_path(domain: str) -> str:
    safe = domain.replace("/", "_").replace(":", "_")
    return os.path.join(HISTORY_DIR, f"{safe}.json")


def save_seo_snapshot(domain: str, snapshot: dict):
    """
    Save today's snapshot into data/seo_history/{domain}.json
    Snapshot stored as list of {"date":"YYYY-MM-DD","data":{...}}
    """
    path = _history_path(domain)
    today = dt.date.today().isoformat()
    history = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []
    # if today's already stored, replace it
    if history and history[-1].get("date") == today:
        history[-1]["data"] = snapshot
    else:
        history.append({"date": today, "data": snapshot})
    # keep only last 365 days to avoid file bloat
    if len(history) > 365:
        history = history[-365:]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def get_seo_history(domain: str, days: int = 30) -> list:
    """
    Return list of entries for last `days` days:
    [{"date":"YYYY-MM-DD","data":{...}}, ...] sorted oldest->newest
    """
    path = _history_path(domain)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception:
        return []
    # return last `days` entries
    if days <= 0:
        return history
    return history[-days:]
