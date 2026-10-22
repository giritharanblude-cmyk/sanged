# SANGAD — Admin Management Dashboard

Customized micro-SaaS for payslip, bills, inventory, employees, and company management.

**Stack:** Python 3.12 / FastAPI / PostgreSQL 16 / Redis / React 18 / TypeScript / Coolify

**Architecture:** Modular monolith on a single localhost machine. See `docs/SANGAD_ARCHITECTURE_v0_3.md`.

## Quick Start (development)

Requirements: Docker Compose v2 and a Node-compatible Docker runtime.

Create a local environment file and replace its `REPLACE_*` values with
random local-only values (use a URL-safe `POSTGRES_PASSWORD` so the database
URLs remain valid, and keep `.env` out of Git):

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

```bash
if [ ! -f .env ]; then cp .env.example .env; fi
```

Then start the development stack:

```bash
docker compose -f docker-compose.dev.yml up --build
```

The React/Vite UI is at `http://localhost:5173`; Mailpit is at
`http://127.0.0.1:8025`. The API is proxied through Vite, and the seeded
master account uses `ADMIN_USERNAME` / `ADMIN_PASSWORD` from `.env`. Local
file storage uses the unexposed SeaweedFS S3 service and the configured
`S3_BUCKET_FILES`; `/readyz` writes, reads, and deletes a probe object.
Production uses the configured S3-compatible bucket. The stack also creates isolated
`sangad_test` and `sangad_migration_test` databases for backend tests and
migration checks. The runtime API uses the restricted `APP_DB_USER` role;
`POSTGRES_USER` and `MIGRATION_DATABASE_URL` are reserved for schema changes.
On the first Compose start, the app role is created from the ignored `.env`
values, and Alembic grants it normal table access while denying UPDATE/DELETE
on `audit_log`.

To stop the stack without deleting local data:

```bash
docker compose -f docker-compose.dev.yml down
```

## Deployment

Production deployments go through Coolify. See
`infra/coolify/docker-compose.yml` and `docs/SANGAD_ARCHITECTURE_v0_3.md`.
The loopback-only override at `infra/coolify/docker-compose.local.yml` is for
manual local API testing and is not used by Coolify.

For an existing production PostgreSQL resource, provision `APP_DB_USER` and
`APP_DB_PASSWORD` once with the owner credentials by running
`psql "$MIGRATION_DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/create-app-role.sql`
from the repository root with those three environment variables set. Keep
`DATABASE_URL` on the app role and `MIGRATION_DATABASE_URL` on the schema owner;
the API startup command unsets the migration URL before starting the server.

## Project Structure

```
sanged/
├─ docs/                       # Architecture, build plan
├─ backend/
│  ├─ app/
│  │  ├─ main.py              # FastAPI entry point
│  │  ├─ core/                # Config, DB, security, errors, logging, money
│  │  ├─ kernel/              # Auth, audit, files, mail, jobs, ports
│  │  └─ modules/             # payslip, bills, inventory, employees, company
│  ├─ migrations/             # Alembic
│  └─ tests/
├─ frontend/
│  └─ src/
│     ├─ App.tsx              # Auth flow and five-module landing
│     ├─ api.ts               # Same-origin API client with CSRF token echo
│     ├─ components/          # Shared KpiCard and DataTable
│     └─ views/               # Login, OTP, payslip list and form
└─ infra/
   ├─ coolify/                # Docker Compose, env template
   ├─ local/                  # Host setup notes
   ├─ runbooks/               # Operations, local host, hardening record
   └─ scripts/                # deploy, backup, restore, LAN scan
```

## Validation

Backend lint and typing checks run from `backend/` with `ruff check app tests`
and `mypy app tests`. After the development stack is healthy, run the backend
suite inside its API container so it uses the isolated test database:

```bash
docker compose -f docker-compose.dev.yml exec -T api sh -c 'DATABASE_URL="$TEST_DATABASE_URL" REDIS_URL="$TEST_REDIS_URL" python -m pytest --cov=app --cov-fail-under=80'
```

The test fixture refuses any database whose name does not end in `_test`.
Frontend checks run from `frontend/` with `npm ci`, `npm run typecheck`,
`npm run lint`, `npm run test -- --coverage --run`, and `npm run build`.
The build regenerates `src/generated/api.ts` from the checked-in OpenAPI
schema; CI compares that schema with the running backend API.

`npm run test:e2e` drives the real OTP login flow in a browser against
the running stack, with Mailpit standing in for the mailbox.

## Operating the host

The host runbook, the reboot and power-loss drills, the backup and
restore drill and the LAN exposure check live in `infra/runbooks/` and
`infra/scripts/`:

| Document | What it covers |
|---|---|
| `infra/runbooks/local-host.md` | Reboot test (5 minute limit), sleep, power loss, UPS, host rebuild |
| `infra/runbooks/host-hardening-record.md` | Blank record of what was hardened on the host |
| `infra/runbooks/operations.md` | Deploy, rollback, restore, key escrow, breach response |
| `infra/scripts/restore.sh` | Restores a dump into a scratch database and compares the row counts |
| `infra/scripts/lan-portscan.sh` | Fails when any port answers from the LAN |

`infra/scripts/restore.sh` is exercised by the backend test suite, so a
backup that cannot be restored fails the build rather than the drill.
