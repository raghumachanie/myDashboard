"""
Stock Terminal — backend
------------------------------------------------------------------
Serves cached technical-analysis results and refreshes them on demand.

Endpoints:
  GET  /api/data            -> latest cached results + meta (no token needed to read)
  POST /api/refresh         -> kicks off a background refresh (requires X-Token header)
  GET  /api/status          -> {"running": bool, "last_updated": iso, "count": int}
  GET  /                    -> serves the built frontend (static)

Env vars:
  REFRESH_TOKEN   shared secret; the frontend must send it to trigger /refresh
  PORT            provided by the host (Render sets this automatically)
"""
import os
import json
import threading
import datetime as dt
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

import analysis  # local module (the refactored ta_analysis)

DATA_FILE = Path(__file__).parent / "ta_results.json"
STATIC_DIR = Path(__file__).parent / "static"
TOKEN = os.environ.get("REFRESH_TOKEN", "")

app = FastAPI(title="Stock Terminal")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # personal app; tighten to your domain if you want
    allow_methods=["*"],
    allow_headers=["*"],
)

_state = {"running": False, "last_updated": None}
_lock = threading.Lock()


def _load():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text())
        except Exception:
            return []
    return []


def _do_refresh():
    """Runs in a background thread so the HTTP request returns instantly."""
    try:
        results = analysis.run()          # heavy: yfinance fetch + indicators
        DATA_FILE.write_text(json.dumps(results, indent=2))
        _state["last_updated"] = dt.datetime.utcnow().isoformat() + "Z"
    except Exception as e:
        print("Refresh failed:", e)
    finally:
        with _lock:
            _state["running"] = False


@app.get("/api/data")
def get_data():
    return JSONResponse({
        "results": _load(),
        "last_updated": _state["last_updated"],
        "count": len(_load()),
    })


@app.get("/api/status")
def status():
    return {
        "running": _state["running"],
        "last_updated": _state["last_updated"],
        "count": len(_load()),
    }


@app.post("/api/refresh")
def refresh(x_token: str = Header(default="")):
    if not TOKEN or x_token != TOKEN:
        raise HTTPException(status_code=401, detail="Bad or missing token")
    with _lock:
        if _state["running"]:
            return {"started": False, "reason": "already running"}
        _state["running"] = True
    threading.Thread(target=_do_refresh, daemon=True).start()
    return {"started": True}


# ---- serve the built frontend if present ----
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html")
