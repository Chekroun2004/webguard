# WebGuard — Design Spec

**Date:** 2026-05-17
**Author:** omarc (Master IGOV, FSR-UM5 Rabat)
**Status:** Draft — pending user approval

---

## 1. Purpose

WebGuard is a SaaS web vulnerability scanner. A user submits a target URL; the platform runs a battery of passive and active scans, and produces a vulnerability report (severity-ranked, with remediation advice) viewable in-app and exportable as PDF/JSON.

The project is built as a portfolio piece to demonstrate full-stack architecture, async task processing, and applied cybersecurity practices.

---

## 2. Scope decisions (locked in 2026-05-17)

| Decision | Choice | Rationale |
|---|---|---|
| Deployment target | **Localhost / portfolio demo** | `docker-compose up` must work end-to-end on a clean clone; no prod VPS investment. |
| PDF generation | **WeasyPrint** | HTML/CSS templates → styled PDFs; system deps installed in the backend Dockerfile. |
| Password hashing | **argon2** | OWASP-recommended modern KDF; via `passlib[argon2]`. |
| Frontend routing | **React Router v6** | De-facto standard, composes cleanly with TanStack Query. |
| Realtime progress | **SSE** | Simpler than WebSocket for a unidirectional progress stream; via `sse-starlette`. |
| Auth model | JWT access (15 min) + refresh (7 days) | Per brief. |
| UI language | **French** | Project audience is FR; code/identifiers remain English. |

---

## 3. Architecture

```
┌─────────────┐    REST/SSE   ┌──────────────┐  enqueue   ┌──────────────┐
│  Frontend   │ ────────────▶ │  Backend API │ ─────────▶ │ Celery Worker│
│  React 18   │ ◀──────────── │   FastAPI    │            │  (scanners)  │
└─────────────┘               └──────┬───────┘            └──────┬───────┘
                                     │                           │
                                     ▼                           ▼
                              ┌──────────────┐            ┌──────────────┐
                              │ PostgreSQL   │ ◀──────────│    Redis     │
                              │  (15+)       │   results  │ (broker+kv)  │
                              └──────────────┘            └──────────────┘
                                                                 │
                                                                 ▼
                                                          ┌──────────────┐
                                                          │ target sites │
                                                          │ (HTTP probes)│
                                                          └──────────────┘
```

Backend layering: **routes → services → repositories → DB**. Scanners live under `app/scanners/` and inherit from `BaseScanner` (abstract `async scan(target_url, config) -> List[Vulnerability]`).

---

## 4. Tech stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, Celery, Redis, `passlib[argon2]`, `python-jose` (JWT), `sse-starlette`, `httpx` (async HTTP for scanners), WeasyPrint.
- **Frontend:** React 18, TypeScript (strict), Vite, TailwindCSS, shadcn/ui, React Router v6, TanStack Query, (Zustand only if global client state proves necessary).
- **Infra:** Docker, docker-compose (dev + base files), PostgreSQL 15, Redis 7.
- **Tooling:** ruff + black (Python), eslint + prettier (TS), pytest (backend), Vitest (frontend), Alembic for migrations.

---

## 5. Data model (target shape — refined per stage)

- **User** — `id, email, password_hash, full_name, role (user/admin), is_active, created_at`
- **Scan** — `id, user_id, target_url, status, started_at, completed_at, total_vulnerabilities, severity_summary (JSONB), config (JSONB)`
- **Vulnerability** — `id, scan_id, type, severity, title, description, affected_url, evidence (JSONB), recommendation, cwe_id, cvss_score, created_at`
- **DomainOwnership** — `id, user_id, domain, verification_method (file/dns), verification_token, verified_at, is_verified`

---

## 6. Security & legal posture

- Mandatory **domain ownership verification** (file at `/webguard-verify-{token}.txt` OR `webguard-verify={token}` DNS TXT record) before *active* scans (Phase 2 modules).
- Passive scans (Phase 1) may run without ownership verification but are still rate-limited and audit-logged.
- Rate limiting at two layers: per-user API quota (e.g. 5 scans/h, configurable) and per-target probe throttle (≤10 req/s default).
- Audit log for every scan: who, when, target, source IP.
- Terms of Service gate at registration: user attests to only scanning their own systems.
- App-side: argon2 hashing, JWT rotation, strict Pydantic validation, CORS allowlist, secrets in `.env`.

---

## 7. Build roadmap (9 stages, gated)

After each stage I stop, post a recap (what was built, how to test, what's deferred), and wait for an explicit "ok" before moving on.

1. **Setup** — repo structure, docker-compose, Dockerfiles, FastAPI `/health`, React+Vite+Tailwind+shadcn skeleton, `.env.example`, README scaffold.
2. **Auth** — `User` model + migration, register/login/refresh/me endpoints, argon2 hashing, JWT, Login/Register pages, protected Dashboard shell, pytest auth coverage.
3. **First scanner (headers)** — `BaseScanner` abstract, `headers.py` module, `Scan`/`Vulnerability` models + migrations, synchronous `POST /scans` for validation, scan-result UI.
4. **Async with Celery** — Celery + Redis wiring, `run_scan(scan_id)` task, async `POST /scans`, `GET /scans/{id}/status`, SSE for live progress, frontend progress bar.
5. **Ownership verification** — `DomainOwnership` model + migration, verify/check endpoints, frontend domain-verification flow, block active scans on unverified domains.
6. **Phase 1 scanners complete** — `cookies`, `ssl_tls`, `sensitive_files`, `technologies`, `http_methods` (each with tests).
7. **Crawler + Phase 2 scanners** — `crawler` (robots.txt-aware, depth-configurable), `xss`, `sqli`, `open_redirect`, `csrf`, `directory_listing`.
8. **Reports** — WeasyPrint PDF template, JSON export, scan-detail page with severity filters and charts (recharts), scan diff view.
9. **Polish** — slowapi rate limiting, Slack/Discord webhooks, OpenAPI doc refinement, README with screenshots/GIF, deployment notes.

Stages 1–5 are foundational; 6–8 expand feature surface; 9 is presentation polish.

---

## 8. Success criteria

- `git clone && docker-compose up` reaches a working app within ~10 minutes on a clean machine.
- ≥10 working scanner modules at completion.
- ≥70% test coverage on critical business logic (auth, scan orchestration, scanner core, report generation).
- PDF report renders cleanly with severity breakdown and remediation guidance.
- README walks a third-party dev to a running demo in ≤10 minutes.

---

## 9. Out of scope (explicit)

- Real production deployment, multi-region, HA, autoscaling.
- Paid tiers / Stripe billing.
- Authenticated scans (scanning behind login walls).
- Mobile / native clients.
- Phase 3 modules (`subdomain_enum`, `cve_lookup`) — possible future extension, not part of the gated 9 stages.
