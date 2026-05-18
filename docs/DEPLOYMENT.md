# Deploying WebGuard to Fly.io

Three Fly apps need to be created:

| App              | Role                  | Config             |
|------------------|-----------------------|--------------------|
| `webguard-api`   | FastAPI + uvicorn     | `fly.toml`         |
| `webguard-worker`| Celery worker + Beat  | `fly.worker.toml`  |
| `webguard-web`   | Frontend (nginx)      | `frontend/fly.toml`|

Plus two managed services :

- **PostgreSQL 15** (Fly Postgres, free hobby tier)
- **Redis** (Upstash via Fly extension, free tier)

---

## 1. Prerequisites

```bash
# Install the Fly CLI
brew install flyctl                 # macOS
# OR
curl -L https://fly.io/install.sh | sh   # Linux/WSL

flyctl auth login
```

---

## 2. Create the managed services

```bash
# Postgres
flyctl postgres create --name webguard-db --region cdg --vm-size shared-cpu-1x --initial-cluster-size 1

# Redis (Upstash extension)
flyctl redis create --name webguard-redis --region cdg --enable-eviction
```

Each command prints a `DATABASE_URL` / `REDIS_URL`. Keep them — you'll set them as secrets below.

---

## 3. Deploy the API

```bash
flyctl apps create webguard-api
flyctl secrets set \
  DATABASE_URL='postgresql+asyncpg://...'  \
  REDIS_URL='redis://...' \
  CELERY_BROKER_URL='redis://...' \
  CELERY_RESULT_BACKEND='redis://...' \
  SECRET_KEY="$(openssl rand -hex 32)" \
  BACKEND_CORS_ORIGINS='https://webguard-web.fly.dev' \
  --app webguard-api

flyctl deploy --config fly.toml --app webguard-api
```

---

## 4. Deploy the worker

```bash
flyctl apps create webguard-worker
flyctl secrets set \
  DATABASE_URL='postgresql+asyncpg://...'  \
  REDIS_URL='redis://...' \
  CELERY_BROKER_URL='redis://...' \
  CELERY_RESULT_BACKEND='redis://...' \
  SECRET_KEY="<same as API>" \
  --app webguard-worker

flyctl deploy --config fly.worker.toml --app webguard-worker
```

The worker app has no `[http_service]` — Fly will run it as a long-lived process.

---

## 5. Deploy the frontend

The frontend bundles the API URL at build time via `VITE_API_BASE_URL`. Edit `frontend/fly.toml` if you used a different app name for the API.

```bash
flyctl apps create webguard-web
cd frontend
flyctl deploy --config fly.toml --app webguard-web
```

---

## 6. Verify

```bash
curl https://webguard-api.fly.dev/health
# {"status":"ok"}

open https://webguard-web.fly.dev
```

---

## Required secrets (summary)

| Secret              | Where         | Notes                                     |
|---------------------|---------------|-------------------------------------------|
| `DATABASE_URL`      | api, worker   | `postgresql+asyncpg://...`                |
| `REDIS_URL`         | api, worker   | `redis://...`                             |
| `CELERY_BROKER_URL` | api, worker   | usually = `REDIS_URL`                     |
| `CELERY_RESULT_BACKEND` | api, worker | usually = `REDIS_URL`                  |
| `SECRET_KEY`        | api, worker   | 32-byte hex string                        |
| `BACKEND_CORS_ORIGINS` | api        | URL of frontend (`https://...`)           |
| `SMTP_HOST`         | worker        | optional, defaults to Mailpit in dev only |
| `EMAIL_NOTIFICATIONS_ENABLED` | worker | set `false` in prod until SMTP provider configured |

---

## Updates

```bash
flyctl deploy --config fly.toml --app webguard-api
flyctl deploy --config fly.worker.toml --app webguard-worker
flyctl deploy --config frontend/fly.toml --app webguard-web
```

## Logs

```bash
flyctl logs --app webguard-api
flyctl logs --app webguard-worker
```
