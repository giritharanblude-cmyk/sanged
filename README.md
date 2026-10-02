# SANGAD — Admin Management Dashboard

Customized micro-SaaS for payslip, bills, inventory, employees, and company management.

**Stack:** Python 3.12 / FastAPI / PostgreSQL 16 / Redis / React 18 / TypeScript / Coolify

**Architecture:** Modular monolith on a single localhost machine. See `docs/SANGAD_ARCHITECTURE_v0_3.md`.

## Quick Start (development)

```bash
docker compose -f docker-compose.dev.yml up
```

## Deployment

All deployments go through Coolify. See `infra/runbooks/`.

## Project Structure

```
sanged/
├─ docs/                       # Architecture, ADRs, runbooks
├─ backend/
│  ├─ app/
│  │  ├─ main.py              # FastAPI entry point
│  │  ├─ core/                # Config, DB, security, errors, logging
│  │  ├─ kernel/              # Auth, audit, files, mail, jobs, ports
│  │  └─ modules/             # payslip, bills, inventory, employees, company
│  ├─ migrations/             # Alembic
│  └─ tests/
├─ frontend/
│  └─ src/
│     ├─ app/                 # Router, providers, shell
│     ├─ shared/              # UI kit, API client, hooks
│     └─ features/            # Per-module screens
└─ infra/
   ├─ coolify/                # Docker Compose, env template
   ├─ local/                  # Host setup notes
   ├─ runbooks/               # Deploy, restore, WhatsApp pairing
   └─ scripts/                # deploy.sh, backup.sh
```