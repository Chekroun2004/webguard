# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Projet — WebGuard

Scanner de vulnérabilités web SaaS (projet portfolio — Master IGOV, FSR-UM5 Rabat).
L'utilisateur soumet une URL → le système scanne → génère un rapport PDF/JSON avec sévérités et recommandations.

**Communication avec l'utilisateur : en français.**
**Code, commits, identifiants : en anglais.**

---

## Commandes essentielles

### Démarrer la stack complète (dev, hot-reload)
```bash
cp .env.example .env          # une seule fois
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

### Tests backend
```bash
# Tous les tests (SQLite in-memory, sans Postgres)
docker compose exec backend pytest -v

# Un seul test / une seule classe
docker compose exec backend pytest tests/test_auth.py::TestLogin -v

# Avec couverture
docker compose exec backend pytest --cov=app --cov-report=term-missing
```

### Linting / formatage backend
```bash
docker compose exec backend ruff check app tests
docker compose exec backend black --check app tests
```

### Migrations Alembic
```bash
# Appliquer les migrations en attente
docker compose exec backend alembic upgrade head

# Générer une nouvelle migration (après modification d'un modèle)
docker compose exec backend alembic revision --autogenerate -m "describe change"

# Historique
docker compose exec backend alembic history
```

### Frontend
```bash
# Déjà lancé via docker compose ; accès sur http://localhost:5173
# Linting local (si Node installé)
cd frontend && npm run lint
```

### Smoke tests API (PowerShell)
```powershell
curl.exe http://localhost:8000/health
curl.exe http://localhost:8000/docs   # Swagger UI
```

---

## Architecture

### Vue d'ensemble
```
Frontend (React 18 + Vite)  ──REST──▶  Backend (FastAPI)  ──queue──▶  Worker (Celery)
        :5173                               :8000                           │
                                               │                            │
                                               ▼                            ▼
                                         PostgreSQL 15                  Redis 7
```

### Layering backend (strict, à respecter)
```
Routes (app/api/v1/)
  └─▶ Services (app/services/)       ← logique métier, validations
        └─▶ Repositories (app/repositories/)  ← accès DB uniquement
              └─▶ Models (app/db/models/)      ← SQLAlchemy ORM
```

Les routes ne font **jamais** de requêtes DB directement.
Les repositories ne contiennent **aucune** logique métier.

### Fichiers clés à connaître

| Fichier | Rôle |
|---|---|
| `backend/app/core/config.py` | `Settings` (pydantic-settings) — toute config vient d'ici |
| `backend/app/core/security.py` | argon2 hashing + JWT encode/decode |
| `backend/app/api/deps.py` | `get_db`, `get_current_user` (FastAPI dependencies) |
| `backend/app/api/v1/router.py` | Agrège tous les routers v1 |
| `backend/app/db/models/__init__.py` | **Importer les modèles ici** pour qu'Alembic les découvre |
| `backend/alembic/env.py` | Config async Alembic (utilise `create_async_engine`) |
| `backend/prestart.sh` | Lancé au démarrage Docker : `alembic upgrade head` puis uvicorn |
| `frontend/src/lib/api.ts` | Client fetch typé avec `ApiError` |
| `frontend/src/hooks/useAuth.ts` | Hooks TanStack Query pour l'auth |
| `frontend/src/hooks/useScan.ts` | Hooks TanStack Query pour les scans |
| `frontend/src/components/ProtectedRoute.tsx` | Guard de route (redirige si pas de token) |
| `frontend/src/components/SeverityBadge.tsx` | Badge coloré par sévérité |
| `backend/app/scanners/base.py` | `BaseScanner` ABC + `Finding` dataclass |
| `backend/app/scanners/headers.py` | `HeadersScanner` — 5 headers de sécurité |
| `backend/app/services/scan.py` | `ScanService` : orchestration + erreurs métier |

### Conventions importantes
- `backend_cors_origins` est un `str` (pas `list[str]`) dans `Settings` — pydantic-settings v2 parse les `list[str]` comme du JSON. Utiliser `settings.cors_origins` (property) dans le code.
- Tests : base SQLite in-memory avec `StaticPool` (voir `tests/conftest.py`). Ne pas chercher à connecter Postgres dans les tests unitaires.
- Tous les modèles SQLAlchemy héritent de `app.db.base.Base` et doivent être importés dans `app/db/models/__init__.py`.
- Les Celery tasks vivront dans `app/workers/tasks/` (créé à l'Étape 4).
- Les scanners héritent tous de `BaseScanner` (`app/scanners/base.py`) : `async scan(url, config) -> list[Finding]`. `Finding` est un dataclass (name, severity, description, recommendation, evidence).
- Pour tester un scanner : `patch.object(scanner, '_fetch', AsyncMock(return_value={...}))` — pas de vraies requêtes HTTP.
- `AnyHttpUrl` (Pydantic v2) normalise en ajoutant un `/` final — les assertions de test doivent utiliser `.rstrip("/")`.
- Nouveaux hooks frontend : `useScan.ts` → `useCreateScan`, `useScanList`, `useScan`.
- `SeverityBadge` component dans `frontend/src/components/`.

### Stack technique (décisions verrouillées)
- **PDF** : WeasyPrint (Étape 8, deps système dans Dockerfile)
- **Hashing** : argon2 via `passlib[argon2]`
- **JWT** : `python-jose[cryptography]`, HS256
- **Router frontend** : React Router v6
- **Realtime** : SSE via `sse-starlette` (Étape 4)
- **Déploiement cible** : localhost / démo portfolio (`docker compose up`)

---

## État d'avancement

### ✅ Étape 1 — Bootstrap (TERMINÉE)
- Structure complète du projet
- `docker-compose.yml` + `docker-compose.dev.yml` (5 services : postgres, redis, backend, worker, frontend)
- FastAPI avec `GET /health`
- React 18 + Vite + Tailwind + shadcn/ui (skeleton)
- `.env.example`, `.gitignore`, `README.md`

### ✅ Étape 2 — Authentification (TERMINÉE)
- Modèle `User` + migration Alembic `0001_add_users_table`
- `POST /api/v1/auth/register` — argon2, retourne profil (201)
- `POST /api/v1/auth/login` — retourne `{access_token, refresh_token}`
- `POST /api/v1/auth/refresh` — émet de nouveaux tokens
- `GET /api/v1/auth/me` — protégé par Bearer token
- 18 tests pytest ✅ (SQLite in-memory)
- Pages frontend : `LoginPage`, `RegisterPage`, `DashboardPage`
- `ProtectedRoute`, hooks `useLogin / useRegister / useCurrentUser / useLogout`

### ✅ Étape 3 — Premier scanner (headers) (TERMINÉE)
- `BaseScanner` ABC + `Finding` dataclass dans `app/scanners/base.py`
- `HeadersScanner` : détecte absence/mauvaise config de CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy
- Modèles `Scan` + `Vulnerability` + migration Alembic `0002_add_scans_table`
- `POST /api/v1/scans` (201), `GET /api/v1/scans`, `GET /api/v1/scans/{id}` — auth + isolation par user
- 39 tests pytest ✅ (21 nouveaux : 10 scanner + 11 routes)
- Frontend : formulaire de scan inline, historique des scans avec `SeverityBadge`, détail collapsible par vuln

### ✅ Étape 4 — Async avec Celery (TERMINÉE — bugs corrigés)
- `execute_scan(scan_id, session)` fonction async testable directement (sans broker)
- `run_scan_task` Celery task (`@celery_app.task`) : `asyncio.run(_run())` → crée session, délègue à `execute_scan`
- `POST /api/v1/scans` retourne 202 + `status=pending`, dispatche `run_scan_task.delay(scan_id)`
- `GET /api/v1/scans/{id}/status` — polling léger `{id, status}`
- `GET /api/v1/scans/{id}/events` — SSE via `sse-starlette`, émet événement `status` chaque seconde
- `deps.py` : accept `?token=` query param pour EventSource (pas de custom headers)
- Frontend : `useScanEvents` hook SSE, `ScanProgressBar` component, form bloqué pendant scan
- 48/48 tests pytest ✅ (20 nouveaux)
- **Bugs corrigés post-livraison** :
  - `@shared_task` → `@celery_app.task` (le shared_task utilisait le broker AMQP par défaut au lieu de Redis)
  - `import app.workers.celery_app` ajouté dans `main.py` (broker Redis initialisé au démarrage FastAPI)
  - `--include=app.workers.tasks.scan` ajouté à la commande worker dans `docker-compose.yml` (tâche non enregistrée)
- **Bug restant** : la barre de progression SSE ne se termine pas toujours côté frontend — à investiguer en Étape 5 ou en début de session suivante

### ✅ Étape 5 — Vérification d'ownership de domaine (TERMINÉE)
- Modèle `DomainOwnership` + migration Alembic `0003_add_domain_ownership_table`
- Vérification par fichier (`/webguard-verify-{token}.txt`) ou DNS TXT (`_webguard.{domain}`)
- `DomainService` : `register`, `verify` (file + DNS via `dnspython`)
- Routes : `POST /domains`, `GET /domains`, `GET /domains/{id}`, `POST /domains/{id}/verify`
- 20 tests pytest ✅
- Page frontend `DomainsPage` + `useDomains` hooks
- **Aussi corrigé** : bug barre progression SSE (fallback polling + reset `activeScanId`)

### ✅ Étape 6 — Scanners Phase 1 (passifs) (TERMINÉE)
- `cookies.py` : Secure, HttpOnly, SameSite, SameSite=None sans Secure
- `ssl_tls.py` : version TLS obsolète, expiry certificat (30j high / 90j medium), erreur SSL
- `sensitive_files.py` : 16 chemins sensibles (.git, .env, wp-config.php, etc.)
- `technologies.py` : Server header avec/sans version, X-Powered-By, X-Aspnet-Version
- `http_methods.py` : TRACE (high), PUT/DELETE/CONNECT (medium) via OPTIONS
- `execute_scan` mis à jour pour lancer les 6 scanners en parallèle (`asyncio.gather`)
- 31 nouveaux tests pytest ✅ (99 total)

### ✅ Étape 7 — Crawler + scanners Phase 2 (actifs) (TERMINÉE)
- `crawler.py` : BFS, respect robots.txt, filtrage domaine, extraction forms/links, max_depth/max_pages configurables
- `xss.py` : XSS réfléchi — injection dans chaque input de formulaire, détection par réflexion du payload
- `sqli.py` : SQL injection basée sur les erreurs — patterns MySQL/PostgreSQL/Oracle/SQLite
- `open_redirect.py` : détection des paramètres de redirection (url, next, redirect, etc.) + sonde externe
- `csrf.py` : formulaires POST sans token CSRF (_token, csrf_token, authenticity_token, etc.)
- `directory_listing.py` : "Index of /" dans 10 répertoires courants
- `execute_scan` mis à jour : Phase 1 passive + crawl + Phase 2 active avec asyncio.gather
- 31 nouveaux tests pytest ✅ (130 total)

### ✅ Étape 8 — Rapports PDF/JSON (TERMINÉE)
- `GET /api/v1/scans/{id}/report` → rapport JSON (summary + findings triés par sévérité)
- `GET /api/v1/scans/{id}/report.pdf` → PDF stylé généré par WeasyPrint + Jinja2
- Template HTML `app/templates/report.html` : cover, grille de sévérité, liste des vulnérabilités
- `ScanDetailPage` frontend (`/scans/:id`) : filtres par sévérité, PieChart recharts, boutons export PDF/JSON
- Lien "Rapport" depuis la ScanCard dans le Dashboard
- 11 nouveaux tests pytest ✅ (141 total)

### 🔲 Étape 9 — Polissage
- `slowapi` rate limiting (5 scans/h par user, ≤10 req/s vers cible)
- Webhooks Slack/Discord
- Logs d'audit complets
- README avec screenshots/GIF
- Tests Vitest frontend

---

## Workflow attendu (IMPORTANT)

- **Une étape à la fois.** Après chaque étape : récap de ce qui a été fait, comment tester, puis attendre "ok" avant de continuer.
- **Ne pas anticiper** les modules des étapes suivantes.
- **TDD** : écrire les tests avant le code de production. Vérifier qu'ils échouent (RED) puis implémentent (GREEN).
- **Commits conventionnels** : `feat:`, `fix:`, `docs:`, `chore:`, etc. Un commit = un changement logique.
- **Linter** : ruff + black (Python), eslint + prettier (TypeScript).

---

## Modèles de données (shape finale visée)

```python
# User (✅ créé Étape 2)
id, email, password_hash, full_name, is_active, role, created_at

# Scan (🔲 Étape 3)
id, user_id, target_url, status (pending/running/completed/failed),
started_at, completed_at, total_vulnerabilities, severity_summary (JSONB), config (JSONB)

# Vulnerability (🔲 Étape 3)
id, scan_id, type, severity (critical/high/medium/low/info),
title, description, affected_url, evidence (JSONB),
recommendation, cwe_id, cvss_score, created_at

# DomainOwnership (🔲 Étape 5)
id, user_id, domain, verification_method (file/dns),
verification_token, verified_at, is_verified
```

---

## Notes de session

- Ce fichier doit être mis à jour à chaque étape complétée et quand le contexte de session approche 90%.
- Spec de design complète : `docs/superpowers/specs/2026-05-17-webguard-design.md`
- Dernière session : Étapes 5, 6, 7 et 8 complétées. 141/141 tests ✅. Prochaine tâche : **Étape 9 — Polissage**.
- Note Celery task testing : appeler `execute_scan(scan_id, session)` directement, ne pas passer par le broker.
- Piège Celery : utiliser `@celery_app.task` (pas `@shared_task`) et importer `app.workers.celery_app` dans `main.py`. Le worker doit démarrer avec `--include=app.workers.tasks.scan`.
- Piège EventSource : ne supporte pas les headers custom → le token JWT est passé en `?token=` query param (voir `deps.py` et `useScanEvents.ts`).
