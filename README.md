# Stock Terminal — live personal NSE technical screen

A small full-stack app: FastAPI backend runs your technical analysis on demand,
React frontend shows the ranked table with a Refresh button. Phone-accessible
once deployed to the cloud.

```
stock-terminal/
├── main.py            FastAPI server (serves data + frontend, /api/refresh)
├── analysis.py        your TA engine, wrapped as run()
├── requirements.txt   Python deps
├── render.yaml        cloud deploy config
└── frontend/          React app (Vite) -> builds into ../static/
```

---

## A. Run locally first (5 min — do this before deploying)

You have Python + Node already.

**Terminal 1 — backend:**
```bash
cd stock-terminal
pip install -r requirements.txt
export REFRESH_TOKEN=pickanything123      # Windows: set REFRESH_TOKEN=pickanything123
uvicorn main:app --reload --port 8000
```

**Terminal 2 — frontend (dev mode):**
```bash
cd stock-terminal/frontend
npm install
npm run dev
```
Open the URL Vite prints (usually http://localhost:5173). Tap **Refresh**,
enter your token, wait ~30s — real NSE data fills in.

To test the *production* shape (frontend served by FastAPI, single URL):
```bash
cd frontend && npm run build      # outputs to ../static/
cd .. && uvicorn main:app --port 8000
# now open http://localhost:8000  — everything on one port
```

---

## B. Deploy to the cloud (Render free tier — phone-accessible)

**You do these steps — I can't create accounts or click deploy for you.**

1. Push this folder to a **GitHub repo** (private is fine):
   ```bash
   cd stock-terminal
   git init && git add . && git commit -m "stock terminal"
   git branch -M main
   git remote add origin <your-repo-url>
   git push -u origin main
   ```
2. Go to **render.com** → sign up (free) → **New → Blueprint** → connect the repo.
   Render reads `render.yaml` automatically.
3. When prompted, set the **REFRESH_TOKEN** env var to a secret string only you know.
4. Click **Apply**. First build takes a few minutes (installs Python + builds React).
5. You get a URL like `https://stock-terminal-xxxx.onrender.com`. Open it on your
   phone, tap Refresh, enter the token once (it's remembered on that device).

---

## Things to know (honest limitations)

- **Free tier sleeps** after ~15 min idle. First visit after that = 30–60s cold
  start. Normal for free hosting. Upgrade to a paid plan (~$7/mo) to keep it warm.
- **Refresh runs in the background** so the button never blocks — the page polls
  and shows a spinner until the new data lands (~30s for 15 stocks).
- **Data is yfinance** = Yahoo's NSE feed, ~15 min delayed, occasionally rate-
  limited. Fine for end-of-day / swing screening. Not real-time tick data.
- **The token is light protection**, not real auth — enough to stop a random
  visitor triggering your data job. Don't put anything sensitive here.
- **Not investment advice.** The score is a mechanical trend-alignment composite.

## Change the stock list
Edit the `STOCKS` dict at the top of `analysis.py`, commit, push. Render redeploys.
