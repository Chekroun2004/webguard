# Scan Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Empêcher les scans de rester bloqués en `pending`/`running` indéfiniment via deux mécanismes : récupération au démarrage du backend et watchdog Celery Beat toutes les 5 minutes.

**Architecture:** Au démarrage FastAPI, une fonction `recover_stuck_scans(session)` re-dispatche tous les scans `pending`/`running`. Un task Celery `watchdog_stuck_scans` tourne toutes les 5 minutes (via Beat) et re-dispatche les scans bloqués depuis plus de 10 minutes. Le worker est lancé avec `-B` pour intégrer Beat dans le même process.

**Tech Stack:** FastAPI lifespan, SQLAlchemy async, Celery Beat, pytest avec AsyncMock.

---

## Fichiers touchés

| Fichier | Action | Rôle |
|---|---|---|
| `backend/app/main.py` | Modifier | Ajouter `lifespan` + `recover_stuck_scans` |
| `backend/app/workers/tasks/watchdog.py` | Créer | Task Celery + logique async |
| `backend/app/workers/celery_app.py` | Modifier | Ajouter `beat_schedule` |
| `backend/docker-compose.yml` | Modifier | Ajouter `-B --include=...watchdog` au worker |
| `backend/docker-compose.dev.yml` | Modifier | Idem pour le dev |
| `backend/tests/test_scan_recovery.py` | Créer | Tests TDD pour les deux mécanismes |

---

## Task 1 — Startup recovery dans `main.py`

**Files:**
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_scan_recovery.py`

- [ ] **Step 1 : Écrire le test qui échoue**

```python
# backend/tests/test_scan_recovery.py
import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.db.models.scan import Scan
from app.main import recover_stuck_scans, app


@pytest.mark.asyncio
async def test_recover_dispatches_pending_scans(db_session, registered_user):
    scan = Scan(user_id=registered_user["id"], url="https://example.com", status="pending")
    db_session.add(scan)
    await db_session.commit()
    await db_session.refresh(scan)

    with patch("app.main.run_scan_task") as mock_task:
        await recover_stuck_scans(db_session)
        mock_task.delay.assert_called_once_with(scan.id)


@pytest.mark.asyncio
async def test_recover_dispatches_running_scans(db_session, registered_user):
    scan = Scan(user_id=registered_user["id"], url="https://example.com", status="running")
    db_session.add(scan)
    await db_session.commit()
    await db_session.refresh(scan)

    with patch("app.main.run_scan_task") as mock_task:
        await recover_stuck_scans(db_session)
        mock_task.delay.assert_called_once_with(scan.id)


@pytest.mark.asyncio
async def test_recover_resets_running_to_pending(db_session, registered_user):
    scan = Scan(user_id=registered_user["id"], url="https://example.com", status="running")
    db_session.add(scan)
    await db_session.commit()
    await db_session.refresh(scan)

    with patch("app.main.run_scan_task"):
        await recover_stuck_scans(db_session)

    await db_session.refresh(scan)
    assert scan.status == "pending"


@pytest.mark.asyncio
async def test_recover_ignores_completed_scans(db_session, registered_user):
    scan = Scan(user_id=registered_user["id"], url="https://example.com", status="completed")
    db_session.add(scan)
    await db_session.commit()

    with patch("app.main.run_scan_task") as mock_task:
        await recover_stuck_scans(db_session)
        mock_task.delay.assert_not_called()
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
docker compose exec backend pytest tests/test_scan_recovery.py -v
```
Expected: `ImportError: cannot import name 'recover_stuck_scans' from 'app.main'`

- [ ] **Step 3 : Implémenter dans `main.py`**

Remplacer le contenu de `backend/app/main.py` par :

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

import app.workers.celery_app
from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.db.models.scan import Scan
from app.db.session import AsyncSessionLocal
from app.workers.tasks.scan import run_scan_task


async def recover_stuck_scans(session: AsyncSession) -> None:
    result = await session.execute(
        select(Scan).where(Scan.status.in_(["pending", "running"]))
    )
    stuck = result.scalars().all()
    for scan in stuck:
        scan.status = "pending"
    await session.commit()
    for scan in stuck:
        run_scan_task.delay(scan.id)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncSessionLocal() as db:
        await recover_stuck_scans(db)
    yield


app = FastAPI(
    title="WebGuard API",
    description="Scanner de vulnérabilités web — backend API.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
docker compose exec backend pytest tests/test_scan_recovery.py -v
```
Expected: 4 tests PASSED

- [ ] **Step 5 : Commit**

```bash
git add backend/app/main.py backend/tests/test_scan_recovery.py
git commit -m "feat(recovery): re-dispatch stuck scans on FastAPI startup"
```

---

## Task 2 — Watchdog Celery Beat

**Files:**
- Create: `backend/app/workers/tasks/watchdog.py`
- Test: `backend/tests/test_scan_recovery.py` (ajout de tests)

- [ ] **Step 1 : Ajouter les tests watchdog**

Ajouter à `backend/tests/test_scan_recovery.py` :

```python
from datetime import UTC, datetime, timedelta
from app.workers.tasks.watchdog import _watchdog_async


@pytest.mark.asyncio
async def test_watchdog_redispatches_old_pending_scan(db_session, registered_user):
    old_time = datetime.now(UTC) - timedelta(minutes=15)
    scan = Scan(user_id=registered_user["id"], url="https://example.com", status="pending")
    db_session.add(scan)
    await db_session.commit()
    await db_session.refresh(scan)
    # Forcer created_at dans le passé
    await db_session.execute(
        update(Scan).where(Scan.id == scan.id).values(created_at=old_time)
    )
    await db_session.commit()

    with patch("app.workers.tasks.watchdog.run_scan_task") as mock_task:
        await _watchdog_async(db_session)
        mock_task.delay.assert_called_once_with(scan.id)


@pytest.mark.asyncio
async def test_watchdog_ignores_recent_pending_scan(db_session, registered_user):
    scan = Scan(user_id=registered_user["id"], url="https://example.com", status="pending")
    db_session.add(scan)
    await db_session.commit()

    with patch("app.workers.tasks.watchdog.run_scan_task") as mock_task:
        await _watchdog_async(db_session)
        mock_task.delay.assert_not_called()


@pytest.mark.asyncio
async def test_watchdog_ignores_completed_scans(db_session, registered_user):
    old_time = datetime.now(UTC) - timedelta(minutes=15)
    scan = Scan(user_id=registered_user["id"], url="https://example.com", status="completed")
    db_session.add(scan)
    await db_session.commit()
    await db_session.execute(
        update(Scan).where(Scan.id == scan.id).values(created_at=old_time)
    )
    await db_session.commit()

    with patch("app.workers.tasks.watchdog.run_scan_task") as mock_task:
        await _watchdog_async(db_session)
        mock_task.delay.assert_not_called()
```

Ajouter l'import `update` en haut du fichier test :
```python
from sqlalchemy import select, update
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
docker compose exec backend pytest tests/test_scan_recovery.py::test_watchdog_redispatches_old_pending_scan -v
```
Expected: `ImportError: cannot import name '_watchdog_async' from 'app.workers.tasks.watchdog'`

- [ ] **Step 3 : Créer `backend/app/workers/tasks/watchdog.py`**

```python
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.scan import Scan
from app.workers.celery_app import celery_app

STUCK_THRESHOLD_MINUTES = 10


async def _watchdog_async(session: AsyncSession) -> None:
    cutoff = datetime.now(UTC) - timedelta(minutes=STUCK_THRESHOLD_MINUTES)
    result = await session.execute(
        select(Scan).where(
            Scan.status.in_(["pending", "running"]),
            Scan.created_at < cutoff,
        )
    )
    stuck = result.scalars().all()
    for scan in stuck:
        scan.status = "pending"
    await session.commit()

    from app.workers.tasks.scan import run_scan_task
    for scan in stuck:
        run_scan_task.delay(scan.id)


@celery_app.task(name="watchdog_stuck_scans")
def watchdog_stuck_scans() -> None:
    from app.db.session import sync_session_factory

    async def _run() -> None:
        async with sync_session_factory() as session:
            await _watchdog_async(session)

    asyncio.run(_run())
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
docker compose exec backend pytest tests/test_scan_recovery.py -v
```
Expected: 7 tests PASSED

- [ ] **Step 5 : Commit**

```bash
git add backend/app/workers/tasks/watchdog.py backend/tests/test_scan_recovery.py
git commit -m "feat(watchdog): detect and re-dispatch scans stuck >10 min"
```

---

## Task 3 — Beat schedule + Docker

**Files:**
- Modify: `backend/app/workers/celery_app.py`
- Modify: `backend/docker-compose.yml`
- Modify: `backend/docker-compose.dev.yml`

- [ ] **Step 1 : Ajouter le beat schedule dans `celery_app.py`**

Ajouter à la fin de `backend/app/workers/celery_app.py` :

```python
celery_app.conf.beat_schedule = {
    "watchdog-stuck-scans": {
        "task": "watchdog_stuck_scans",
        "schedule": 300.0,  # toutes les 5 minutes
    },
}
```

- [ ] **Step 2 : Mettre à jour la commande worker dans `docker-compose.yml`**

Changer :
```yaml
command: celery -A app.workers.celery_app worker --loglevel=info --include=app.workers.tasks.scan
```
Par :
```yaml
command: celery -A app.workers.celery_app worker --loglevel=info --include=app.workers.tasks.scan,app.workers.tasks.watchdog -B
```

- [ ] **Step 3 : Mettre à jour `docker-compose.dev.yml`**

Changer :
```yaml
command: celery -A app.workers.celery_app worker --loglevel=debug --include=app.workers.tasks.scan
```
Par :
```yaml
command: celery -A app.workers.celery_app worker --loglevel=debug --include=app.workers.tasks.scan,app.workers.tasks.watchdog -B
```

- [ ] **Step 4 : Rebuild et vérifier que le worker démarre avec Beat**

```bash
docker compose up -d --build worker
docker compose logs worker --tail=20
```

Expected dans les logs :
```
[tasks]
  . run_scan_task
  . watchdog_stuck_scans
  ...
beat: Starting...
```

- [ ] **Step 5 : Vérifier tous les tests passent**

```bash
docker compose exec backend pytest -v
```
Expected: 148 passed (141 + 7 nouveaux)

- [ ] **Step 6 : Commit**

```bash
git add backend/app/workers/celery_app.py backend/docker-compose.yml backend/docker-compose.dev.yml
git commit -m "feat(beat): schedule watchdog every 5 min, enable Beat in worker"
```
