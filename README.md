# SYSTVETAM — Central Dispatch + Tower Dashboard
**Zentraux Group LLC | Private Infrastructure**

> The engine room. No client ever sees this screen.

## Architecture

```
zentraux-systvetam/
├── dispatch/     FastAPI Central Dispatch (Python 3.12)
├── dashboard/    Tower Dashboard React/Vite (TypeScript)
├── scripts/      Seed scripts (crew, superuser)
├── infra/        Local dev docker-compose
└── Makefile      Dev tooling
```

## Local Development

```bash
# Start all services (Postgres + Redis + Dispatch)
make up

# Run migrations
make migrate

# Seed 16 crew members
make seed

# Start dashboard dev server
cd dashboard && npm install && npm run dev
```

Dashboard: http://localhost:3000
Dispatch API: http://localhost:8000
API Docs: http://localhost:8000/docs

## Authentication (Phase 1)

Login: `username=levi` | `password=[JWT_SECRET env var value]`

## Deployment

See: `SPRINT4_OPS_BRIEF.md`

---
*Zentraux Group LLC — Arizona | Founded March 2026*
