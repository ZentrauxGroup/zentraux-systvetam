# SPRINT 4 — Operations Brief
**SYSTVETAM Deployment | Zentraux Group LLC**
**Operator: Levi C. Haynes (AGT-001)**

---

## Prerequisites
- [ ] GitHub account: Zentraux-Group org or personal
- [ ] Railway account (already have from ASC Enterprise)
- [ ] Cloudflare access (already configured)
- [ ] OpenRouter API key (already have)

---

## STEP 1 — GitHub Repository

1. Go to github.com → New Repository
2. Name: `zentraux-systvetam`
3. Visibility: **Private**
4. Do NOT initialize with README (we have one)
5. Copy the repo URL (e.g. `https://github.com/your-org/zentraux-systvetam.git`)

Then from your terminal, unzip the monorepo and push:

```bash
# Unzip the monorepo package
unzip zentraux-systvetam-monorepo.zip -d zentraux-systvetam
cd zentraux-systvetam

# Initialize and push
git init
git add .
git commit -m "SYSTVETAM Sprint 1-3 — all 10 floors live"
git branch -M main
git remote add origin https://github.com/YOUR-ORG/zentraux-systvetam.git
git push -u origin main
```

---

## STEP 2 — Railway Project

1. Go to railway.app → New Project
2. Name: `zentraux-systvetam`
3. Do NOT use a template — we add services manually

### Service A: Dispatch (Backend)
1. New Service → GitHub Repo → `zentraux-systvetam`
2. Name the service: `dispatch`
3. Settings → Source → **Root Directory**: `dispatch`
4. Builder: Dockerfile (auto-detected)
5. Do NOT deploy yet — set env vars first

### Service B: Database
1. New Service → Database → **PostgreSQL**
2. Name: `postgres` (Railway auto-provisions)

### Service C: Redis
1. New Service → Database → **Redis**
2. Name: `redis` (Railway auto-provisions)

### Service D: Dashboard (Frontend)
1. New Service → GitHub Repo → `zentraux-systvetam`
2. Name the service: `dashboard`
3. Settings → Source → **Root Directory**: `dashboard`
4. Builder: Dockerfile (auto-detected)
5. Do NOT deploy yet — set env vars first

---

## STEP 3 — Environment Variables

### Dispatch Service Variables
Go to dispatch service → Variables tab:

| Variable | Value |
|---|---|
| `DATABASE_URL` | `${{postgres.DATABASE_URL}}` |
| `REDIS_URL` | `${{redis.REDIS_URL}}` |
| `JWT_SECRET` | Generate: `openssl rand -hex 32` (SAVE THIS — it is your login password) |
| `OPENROUTER_API_KEY` | Your OpenRouter API key |
| `CORS_ORIGINS` | `https://tower.zentrauxgroup.com,https://dashboard.railway.app` |
| `ENVIRONMENT` | `production` |

### Dashboard Service Variables
Go to dashboard service → Variables tab:

| Variable | Value |
|---|---|
| `VITE_API_URL` | `https://dispatch-production-XXXX.up.railway.app` (get from dispatch service after first deploy) |
| `PORT` | `3000` |

> ⚠️ VITE_API_URL is baked into the build. Set it BEFORE the dashboard first deploys.
> Get the dispatch URL from the dispatch service → Settings → Networking → Public URL.

---

## STEP 4 — Deploy Dispatch First

1. Deploy dispatch service
2. Wait for health check: GET `https://your-dispatch-url/health` → `{"status": "ok"}`
3. Copy the public dispatch URL
4. Set `VITE_API_URL` on dashboard service to that URL

---

## STEP 5 — Database Migration + Crew Seed

Once dispatch is live:

1. Railway → dispatch service → Shell tab
2. Run:
```bash
# Create all tables
alembic upgrade head

# Seed 16 crew members
python scripts/seed_crew.py
```

3. Verify: GET `https://your-dispatch-url/crew` → should return 16 members

---

## STEP 6 — Deploy Dashboard

1. Trigger dashboard deploy (or it auto-deploys after VITE_API_URL is set)
2. Wait for health check: GET `https://your-dashboard-url/health` → `ok`
3. Open dashboard URL → Login screen should appear

---

## STEP 7 — First Login

**Username:** `levi`
**Password:** [your JWT_SECRET value — the one you generated in Step 3]

You should land on the Tower Lobby floor.
All 10 floors are navigable.
Crew Pulse Bar shows 16 members.

---

## STEP 8 — Custom Subdomain

1. Railway → dashboard service → Settings → Networking → Custom Domain
2. Add: `tower.zentrauxgroup.com`
3. Railway gives you a CNAME target
4. Cloudflare → zentrauxgroup.com → DNS → Add CNAME:
   - Name: `tower`
   - Target: [Railway CNAME value]
   - Proxy: **DNS only** (grey cloud, not orange) to start
5. Wait 2-5 min → visit `https://tower.zentrauxgroup.com`

---

## STEP 9 — Verification Checklist

- [ ] `https://tower.zentrauxgroup.com` loads login screen
- [ ] Login with `levi` / [JWT_SECRET] succeeds
- [ ] Tower Lobby renders with gold ZEN-CIRCUIT aesthetic
- [ ] All 10 floors navigable (no placeholder floors)
- [ ] Crew Pulse Bar shows 16 members
- [ ] Create a test task → verify it appears in task list
- [ ] Gate queue fires for QA_GATE
- [ ] Receipt files after RECEIPTED state
- [ ] Receipt Vault shows the receipt
- [ ] WebSocket live feed active (check network tab for ws:// connection)

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Dashboard shows blank / API errors | Check VITE_API_URL is set correctly, no trailing slash |
| Login fails | Verify JWT_SECRET matches between dispatch env and what you type as password |
| Crew Pulse Bar empty | Run `python scripts/seed_crew.py` in dispatch Railway shell |
| DB tables don't exist | Run `alembic upgrade head` in dispatch Railway shell |
| WebSocket not connecting | Check CORS_ORIGINS includes dashboard URL |
| tower.zentrauxgroup.com not resolving | DNS propagation — wait 5-10 min, check Cloudflare |

---

## Sprint 4 — Definition of Done

> Levi opens `tower.zentrauxgroup.com` from anywhere,
> logs in as AGT-001, and commands Zentraux Group from it.
> Live data. Live crew. Live task state. The company, operational.

---
*SYSTVETAM is private infrastructure. Operators only.*
*Zentraux Group LLC — Arizona | March 2026*
