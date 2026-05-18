# Déployer WebGuard sur Render.com (100 % gratuit)

Le free tier de Render couvre tout le projet :

- **Web Service** (FastAPI backend) — 750 h/mois, sleep après 15 min d'inactivité
- **Static Site** (frontend React) — sans sleep, illimité
- **PostgreSQL** — 256 MB, expire après 90 jours
- **Key Value (Redis)** — 25 MB

> **Note worker** : le free tier de Render n'inclut pas les Background Workers. WebGuard détecte ça via `USE_CELERY=false` et exécute les scans en in-process via FastAPI `BackgroundTasks`. C'est limité à ~10 scans concurrents mais largement suffisant pour une démo portfolio.

---

## Méthode 1 — Blueprint (1-click, recommandée)

Le fichier `render.yaml` à la racine du repo décrit toute l'infrastructure.

1. Aller sur https://dashboard.render.com/blueprints
2. **New Blueprint Instance** → connecter le repo GitHub `Chekroun2004/webguard`
3. Render détecte `render.yaml` et liste les 4 ressources à créer :
   - `webguard-api` (web)
   - `webguard-web` (static)
   - `webguard-redis` (keyvalue)
   - `webguard-db` (postgres)
4. **Apply** → attendre ~5 minutes pour le premier build

---

## Méthode 2 — Manuel (si Blueprint pose problème)

### 1. PostgreSQL

- **New +** → **PostgreSQL**
- Name: `webguard-db`
- Database: `webguard`
- User: `webguard`
- Region: `Frankfurt`
- Plan: **Free**
- **Create Database** → noter l'**Internal Connection String**

### 2. Redis (Key Value)

- **New +** → **Key Value**
- Name: `webguard-redis`
- Region: `Frankfurt`
- Plan: **Free**
- IP allow list: laisser vide (interne)
- **Create**

### 3. Backend (Web Service)

- **New +** → **Web Service**
- Connect repo → branch `main`
- **Runtime** : Docker
- **Dockerfile path** : `backend/Dockerfile.prod`
- **Docker context** : `./backend`
- **Region** : Frankfurt
- **Plan** : Free
- **Health check path** : `/health`
- **Environment Variables** :
  ```
  USE_CELERY=false
  EMAIL_NOTIFICATIONS_ENABLED=false
  ENVIRONMENT=production
  DEBUG=false
  SECRET_KEY=<générer 32 chars hex avec openssl rand -hex 32>
  POSTGRES_HOST=<host du Render Postgres>
  POSTGRES_PORT=5432
  POSTGRES_DB=webguard
  POSTGRES_USER=webguard
  POSTGRES_PASSWORD=<mot de passe Render Postgres>
  REDIS_URL=<connection string Render Key Value>
  BACKEND_CORS_ORIGINS=https://webguard-web.onrender.com
  FRONTEND_URL=https://webguard-web.onrender.com
  ```

### 4. Frontend (Static Site)

- **New +** → **Static Site**
- Connect repo → branch `main`
- **Root directory** : `frontend`
- **Build command** : `npm ci && npm run build`
- **Publish directory** : `dist`
- **Environment Variables** :
  ```
  VITE_API_BASE_URL=https://webguard-api.onrender.com
  ```
- **Redirects / Rewrites** : ajouter une règle `/*` → `/index.html` (rewrite, code 200) pour le SPA fallback

---

## Après déploiement

1. **Première visite** : le backend free tier dort après 15 min — premier appel peut prendre ~30 s, ensuite c'est rapide.
2. **Migrations Alembic** : appliquées automatiquement au démarrage (`prestart` dans le `Dockerfile.prod`).
3. **Logs** : Dashboard Render → service → **Logs**.

---

## Limitations du free tier

| Limitation | Impact |
|------------|--------|
| Web service sleep après 15 min | Cold start ~30 s sur la première requête |
| Postgres 256 MB | Suffit pour des centaines de scans |
| Postgres expire à 90 jours | À recréer ou upgrader avant la fin |
| Pas de worker Celery | Scans en in-process, max ~5-10 concurrents |
| Pas d'email SMTP | `EMAIL_NOTIFICATIONS_ENABLED=false` en prod (Mailpit reste dispo en dev) |
