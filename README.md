# WebGuard

Scanner de vulnérabilités web — plateforme SaaS qui scanne une URL et produit un rapport détaillé des vulnérabilités détectées, avec sévérité et recommandations.

> Projet portfolio — Master IGOV, FSR-UM5 Rabat.

## Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2
- **Workers:** Celery + Redis (scans asynchrones)
- **DB:** PostgreSQL 15
- **Frontend:** React 18 + TypeScript + Vite + TailwindCSS + shadcn/ui
- **Auth:** JWT (argon2 hashing)
- **PDF:** WeasyPrint
- **Infra:** Docker + docker-compose

## Démarrage rapide

```bash
git clone <repo> webguard
cd webguard
cp .env.example .env       # ajuste les valeurs si besoin
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Services exposés:

| Service     | URL                            |
|-------------|--------------------------------|
| Frontend    | http://localhost:5173          |
| API         | http://localhost:8000          |
| API docs    | http://localhost:8000/docs     |
| PostgreSQL  | localhost:5432                 |
| Redis       | localhost:6379                 |

Smoke test rapide:

```bash
curl http://localhost:8000/health
# {"status":"ok","environment":"development"}
```

## État d'avancement

- [x] **Étape 1** — Bootstrap (structure, Docker, FastAPI `/health`, React skeleton)
- [ ] Étape 2 — Authentification (JWT + argon2)
- [ ] Étape 3 — Premier scanner (headers de sécurité)
- [ ] Étape 4 — Système asynchrone avec Celery
- [ ] Étape 5 — Vérification d'ownership de domaine
- [ ] Étape 6 — Modules de scan Phase 1
- [ ] Étape 7 — Crawler + modules de scan Phase 2
- [ ] Étape 8 — Rapports PDF / JSON
- [ ] Étape 9 — Polissage et documentation

Spec de design complète: [`docs/superpowers/specs/2026-05-17-webguard-design.md`](docs/superpowers/specs/2026-05-17-webguard-design.md)

## Structure

```
webguard/
├── backend/             # FastAPI + Celery workers
│   ├── app/
│   │   ├── api/v1/      # Routes
│   │   ├── core/        # Config, sécurité, JWT
│   │   ├── db/          # Modèles SQLAlchemy
│   │   ├── schemas/     # Schémas Pydantic
│   │   ├── services/    # Logique métier
│   │   ├── scanners/    # Modules de scan
│   │   ├── workers/     # Tâches Celery
│   │   ├── reports/     # Génération PDF/JSON
│   │   └── main.py
│   ├── tests/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/            # React + Vite + Tailwind + shadcn/ui
│   ├── src/
│   ├── Dockerfile
│   └── package.json
├── docs/                # Specs, design docs
├── docker-compose.yml
├── docker-compose.dev.yml
└── .env.example
```

## Tests

Backend:

```bash
docker compose exec backend pytest
```

## Licence

À définir.
