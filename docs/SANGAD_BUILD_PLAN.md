# SANGAD — Build Plan

Derived from architecture v0.3. This is the actionable execution plan.

---

## Phase 0: Platform Foundation (Weeks 1-2)

**Goal: A working localhost deployment serving a logged-in landing page.**

### Step 0.0 — Resolve blocking questions
- [ ] Q-15: Accept OpenWA ban risk or switch to official API?
- [ ] Q-16: Choose host (Ubuntu 24.04 LTS recommended) and confirm hardware (16 GB RAM, SSD, second disk)
- [ ] Q-20: Confirm SeaweedFS as local S3 and which physical disk holds backups
- [ ] Q-24: Review current OpenWA webhook API reference before building adapter
- [ ] Q-27: Verify SeaweedFS supports presigned URLs + versioning

### Step 0.1 — Host + Coolify (T-002)
- Install Ubuntu 24.04, Docker Engine 24+, full-disk encryption
- Install Coolify on localhost, connect private Git repo via deploy key
- Create resources: Postgres 16, Redis, SeaweedFS (local S3)
- Create `sangad` Docker Compose app with `*.localhost` domains
- Verify: `http://sangad.localhost` returns something; reboot test passes

### Step 0.2 — Backend core (T-003, T-004, T-005)
- FastAPI app skeleton: config, DB session, Alembic, RFC 9457 errors, structured logging
- Auth: login → OTP (Hostinger SMTP) → session (Redis) → password change
- Kernel services: audit log (append-only), file storage service, number sequences, job runner (RQ)

### Step 0.3 — Frontend shell (T-006, T-007)
- React 18 + Vite + Tailwind + shadcn/ui
- App shell (sidebar, top bar), shared components (KpiCard, DataTable, etc.)
- Landing page with 5 module cards
- `openapi-typescript` client generation in build pipeline

### Step 0.4 — CI + tooling (T-001)
- GitHub Actions: ruff, mypy, pytest, eslint, tsc, vitest
- Pre-commit hooks, Conventional Commits enforcement

### Step 0.5 — Backups + hardening (T-008, T-009)
- Coolify scheduled Postgres backup → local S3
- `restic` off-disk copy to second disk (nightly, encrypted)
- Loopback-only binds, host firewall, Coolify 2FA, registration closed
- Encryption key + Coolify `APP_KEY` escrowed offline
- `deploy.sh` script (Coolify API trigger)

### Phase 0 Exit Criteria
Login + OTP works end-to-end at `http://sangad.localhost`. Landing shows 5 empty cards. CI green. Reboot auto-restores all services. Backup restores successfully from off-disk copy only.

---

## Phase 1: Modules (Weeks 3-8)

Build each module standalone with stub adapters. Order matters — build Payslip and Bills first (highest risk/complexity).

### Module 1 — Payslip (Weeks 3-4) | Tasks T-101 to T-109

| Step | What |
|---|---|
| 1.1 | Models + migration (`payslips`, `payslip_lines`, `payslip_deliveries`, `import_jobs`); stub adapters for EmployeeDirectoryPort, CompanyProfilePort |
| 1.2 | `amount_to_words_inr()` + unit tests |
| 1.3 | Manual entry form (API + UI) |
| 1.4 | Import wizard: upload .xlsx/.csv → validate → show errors → confirm |
| 1.5 | Jinja2 template matching Blude TechX LLP payslip; preview endpoint |
| 1.6 | Edit → re-preview → revision lifecycle |
| 1.7 | PDF generation (WeasyPrint, worker) + download |
| 1.8 | Email payslip (single + bulk), delivery tracking, retry |
| 1.9 | Payroll list screen with KPI cards, search, filter, month picker |

**Verify:** V-PAY-01 to V-PAY-05

### Module 2 — Bills + WhatsApp (Weeks 5-7) | Tasks T-201 to T-213

| Step | What |
|---|---|
| 2.1 | Models + migration (`bills`, `bill_items`, `vouchers`, `extraction_jobs`); nullable serial for drafts |
| 2.2 | Upload (image/PDF/Word) + camera capture + deduplication by sha256 |
| 2.3 | `ExtractionPort` — LLM vision adapter (primary) + local OCR (fallback) |
| 2.4 | Review screen → confirm → commit → assign serial (gapless, per-FY) |
| 2.5 | Manual entry + voucher flow (threshold configurable, default ₹2000) |
| 2.6 | Expense dashboard: KPI cards, 6-month trend, category breakdown, filterable table |
| 2.7 | Excel/CSV export |
| **WhatsApp intake:** | |
| 2.8 | `channel_senders`, `inbound_messages` migration; `InboundChannelPort` / `MessagingPort` interfaces |
| 2.9 | OpenWA adapter: internal webhook receiver (HMAC, allow-list, dedupe) |
| 2.10 | Ingest worker: fetch media via OpenWA API → validate → store → draft → acknowledge |
| 2.11 | "Needs review" inbox UI; gateway-status banner + email alert on disconnect |
| 2.12 | Add OpenWA to Compose; pin version; pairing runbook; sender allow-list settings |
| 2.13 | Contract tests with recorded webhook fixtures; Playwright path |

**Verify:** V-BILL-01 to V-BILL-04, V-WA-01 to V-WA-09

### Module 3 — Inventory (Days) | Tasks T-301 to T-303

- Models: `stock_items` + `stock_movements` (movement ledger)
- CRUD API + forms + list with search/filter
- Low-stock flag when quantity ≤ reorder level
- Export

### Module 4 — Employees (Days) | Tasks T-401 to T-404

- Models: `employees` + `employee_documents`; Aadhaar encrypted (AES-GCM), masked in UI
- CRUD API + form + list (soft delete)
- Document upload tab
- Implement `EmployeeDirectoryPort`

### Module 5 — Company (Days) | Tasks T-501 to T-503

- Model: `company_profile` (single row) + `company_documents`
- Profile form + GSTIN validator
- Implement `CompanyProfilePort`

### Phase 1 Exit Criteria
Each module's validation checks pass. Each module is demoable standalone with its own data. R-15 satisfied (unit tests + API tests + Playwright happy-path).

---

## Phase 2: Integration (Week 9) | Tasks T-601 to T-605

| Step | What |
|---|---|
| 2.1 | Swap Payslip stubs for real EmployeeDirectoryPort (Employees) + CompanyProfilePort (Company) |
| 2.2 | Employee picker in payslip form; import resolves by employee ID |
| 2.3 | Letterhead + signatory from Company profile |
| 2.4 | Landing cards show live summary counts (pending bills, employees, etc.) |
| 2.5 | Cross-module audit review; end-to-end Playwright suite |

**Verify:** V-INT-01 to V-INT-03

---

## Phase 3: Hardening & Release (Week 10) | Tasks T-701 to T-708

| Step | What |
|---|---|
| 3.1 | Security pass: dependency audit, security headers, rate limits, OWASP Top 10 review |
| 3.2 | Performance pass: list endpoints < 500ms p95 at 10k rows; 50-payslip PDF batch < 2 min |
| 3.3 | Backup restore drill — restore from off-disk copy only into fresh machine; measure RTO |
| 3.4 | Legal/privacy review of PII handling (DPDP Act) |
| 3.5 | Retention schedule: gateway media purge (24h), record retention per legal advice |
| 3.6 | Supply chain: SBOM, image scan, pinned digests across all images |
| 3.7 | Live WhatsApp UAT with real bills on production number |
| 3.8 | UAT with real payslips and bills → go-live |

### Phase 3 Exit Criteria
All V- ids pass. No critical/high security findings. Backup restores within 4 hours. Owner approves.

---

## Dependency Map (what blocks what)

```
Host + Coolify (T-002)
  ├── Backend core (T-003..005)
  │    ├── All modules (need DB, auth, kernel services)
  │    └── WhatsApp (needs InboundChannelPort from kernel)
  ├── Frontend shell (T-006)
  │    └── All module UIs
  └── CI/tooling (T-001)
       └── Everything

Open questions (Section 9)
  ├── Q-15 (WhatsApp ban) → blocks T-209
  ├── Q-16 (Host OS) → blocks T-002
  ├── Q-20 (Storage) → blocks T-008
  └── Q-24 (OpenWA API ref) → blocks T-209
```

---

## Key Milestones

| Milestone | What done | When |
|---|---|---|
| **M0** | Open questions resolved, host ready | End of week 0 |
| **M1** | Platform: login + landing + CI + backups working | End of week 2 |
| **M2** | Payslip module: upload, preview, PDF, email | End of week 4 |
| **M3** | Bills module + WhatsApp intake working | End of week 7 |
| **M4** | All modules standalone done (Inventory, Employees, Company) | End of week 8 |
| **M5** | Integration complete; all adapters wired | End of week 9 |
| **M6** | Hardening, UAT, go-live | End of week 10 |

---

## What to Build First

**Priority order:**

1. **Host + Coolify (T-002)** — Nothing works without this foundation. Prove it before writing any code.
2. **Auth shell (T-004, T-006)** — Login/OTP + frontend shell gives you a deliverable you can show.
3. **Payslip module (T-101..109)** — Highest business value, biggest complexity (PDF, email, template matching).
4. **Extraction port (T-203)** — Highest technical risk. Test with real bills early.
5. **WhatsApp intake (T-208..213)** — Novel risk (OpenWA ban, webhook contract). Get it working early in Phase 1.

---

## Effort Estimate (rough)

| Phase | Calendar | Person-weeks |
|---|---|---|
| Phase 0 — Platform | 2 weeks | 2 |
| Phase 1 — Modules (Payslip) | 2 weeks | 2 |
| Phase 1 — Modules (Bills + WhatsApp) | 3 weeks | 3 |
| Phase 1 — Modules (Inventory, Emps, Company) | 1 week | 1 |
| Phase 2 — Integration | 1 week | 1 |
| Phase 3 — Hardening + Release | 1 week | 1 |
| **Total** | **10 weeks** | **10 person-weeks** |

Assumes one experienced full-stack developer (Python + React) with Docker familiarity. Add 50% if learning these technologies.

---

## First Actions (Tomorrow)

1. Buy/choose the host machine — Ubuntu 24.04 LTS, 16 GB RAM, SSD 100 GB+, second disk
2. Install Ubuntu + Docker + full-disk encryption
3. Install Coolify, connect your Git repo
4. Create Postgres + Redis + SeaweedFS resources in Coolify
5. Get the `sangad.localhost` proxy working with a hello-world container
6. Run a reboot test — does everything come back?
