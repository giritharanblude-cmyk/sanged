# SANGAD — phase 0A host verification checklist

Every step on this page needs the **real host**: a reboot, a second
device on the LAN, the off-disk backup disk and the Coolify dashboard.
None of them can be run from a build machine, so they are **NOT
VERIFIED** until someone runs them on the host and records the outcome.

Run them in order. Each one has the exact command and the expected
result, and each one ends with a line to copy into
`infra/runbooks/host-hardening-record.md`.

The application behaviour these steps depend on **is** verified by the
build: the restore drill, the LAN scan and the commit message check all
have automated tests that run in CI.

---

## 1. Reboot test — NOT VERIFIED

**Requirement:** V-LOC-01. After a reboot with no manual step, Docker,
Coolify and every production service must be healthy and `/readyz` must
return `200` **within 5 minutes**.

Full procedure: `infra/runbooks/local-host.md` section 2.

```bash
# 1. The stack must be green before the reboot, otherwise a later failure
#    cannot be attributed to the reboot.
cd /opt/sangad
docker compose -f infra/coolify/docker-compose.yml ps
curl -fsS http://127.0.0.1:8088/readyz

# 2. Reboot and note the time.
date --iso-8601=seconds | tee /tmp/reboot-start.txt
sudo reboot

# 3. On the host after it comes back, run the timed loop.
start=$(date +%s)
deadline=$(( start + 300 ))
until curl -fsS http://127.0.0.1:8088/readyz > /tmp/readyz.json 2>/dev/null; do
    now=$(date +%s)
    if [ "$now" -ge "$deadline" ]; then
        echo "FAIL: /readyz did not return 200 within 300s"
        docker compose -f /opt/sangad/infra/coolify/docker-compose.yml ps
        exit 1
    fi
    sleep 5
done
echo "PASS: /readyz returned 200 after $(( $(date +%s) - start ))s"
cat /tmp/readyz.json
```

**Expected:** `PASS`, elapsed time under 300 seconds.

**Record:** the elapsed seconds and the date in the hardening record.

---

## 2. Backup and restore drill — NOT VERIFIED

**Requirement:** the backup must restore from the **off-disk copy only**,
into a scratch environment, and the recovery time must stay under 4 hours.

The restore script itself is proven by the build
(`backend/tests/test_restore_drill.py`): it restores a dump into a
scratch database and fails when a table's row count differs. What is
**not** proven is that the off-disk copy on the second disk is readable
and complete.

```bash
# 1. Take the off-disk backup. It writes into the restic repository on
#    the second disk.
sudo /opt/sangad/infra/scripts/offdisk-backup.sh

# 2. List what is in the repository, and check it for corruption.
export RESTIC_REPO=/mnt/backup-disk/sangad-backups
restic snapshots
restic check

# 3. Restore the newest snapshot into a SCRATCH database only. The script
#    never writes to the production database.
cd /opt/sangad
export SOURCE_DATABASE_URL='postgresql://sangad:<password>@postgres:5432/sangad'
export ADMIN_DATABASE_URL='postgresql://sangad:<password>@postgres:5432/postgres'
infra/scripts/restore.sh --snapshot latest --repo "$RESTIC_REPO"

# 4. Inspect the scratch database by hand before trusting it.
psql "$ADMIN_DATABASE_URL" -c "\l" | grep sangad_restore_check
psql "postgresql://sangad:<password>@postgres:5432/sangad_restore_check" \
    -c "SELECT count(*) FROM users;" \
    -c "SELECT count(*) FROM payslips;" \
    -c "SELECT count(*) FROM audit_log;"
```

**Expected:**

- `restic check` reports no errors.
- `restore.sh` prints `PASS: ... restores cleanly into ...` and exits 0.
- The scratch database exists and its row counts match the source.
- The production database is untouched.

**Record:** the snapshot id, the restore duration, and the row counts in
the hardening record.

**Then repeat it against a freshly provisioned machine** (the host
rebuild steps in `infra/runbooks/local-host.md` section 4) to measure
the real recovery time. The limit is 4 hours (RTO, RK-15).

---

## 3. LAN port scan — NOT VERIFIED

**Requirement:** R-26. Nothing may be reachable from the LAN.

This has to run **from another device** on the same network, not from
the host itself: a scan from the host only proves what the host can see
on its own interfaces.

```bash
# On the other device, with the repository checked out:
cd /opt/sangad
infra/scripts/lan-portscan.sh <host-lan-address>

# Or scan everything the stack uses:
infra/scripts/lan-portscan.sh <host-lan-address> --all

# Or a wider range:
infra/scripts/lan-portscan.sh <host-lan-address> --range 1-1024
```

**Expected:** every port `closed` and the script ends with
`PASS: nothing answered from the LAN.`

If the script is run where `nmap` is installed it uses nmap instead and
prints its report; the pass condition is the same.

**Record:** the LAN address, the date and the result in the hardening
record. Anything that answers is a finding: close it and record it.

---

## 4. Host hardening record — NOT VERIFIED

`infra/runbooks/host-hardening-record.md` is a blank template on purpose.
Fill it in **on the host**, from the machine that actually runs the
stack. Do not fill it in from a build machine and do not invent values.

```bash
# Gather the values the record asks for.
hostnamectl
lsblk
df -h /
uname -a
docker --version
docker compose version
coolify --version 2>/dev/null || echo "read the version from the dashboard"
systemctl is-enabled docker
systemctl is-enabled coolify
ufw status verbose
iptables -L -n | head -30
```

**Expected:** every row of the record has a real value or an explicit
`N/A` with a reason. No row may stay `TODO:` once the host is in
production.

---

## 5. Alert drills — NOT VERIFIED

There is no alerting service wired up in this phase, so the drill is
about proving that a human would notice.

```bash
# 1. Disk usage alert (the build plan asks for an alert at 80 %).
df -h /

# 2. Stop the database and confirm that readiness turns red.
docker compose -f infra/coolify/docker-compose.yml stop postgres
curl -s -w '\nHTTP=%{http_code}\n' http://127.0.0.1:8088/readyz
docker compose -f infra/coolify/docker-compose.yml start postgres

# 3. Confirm it recovers on its own.
until curl -fsS http://127.0.0.1:8088/readyz >/dev/null 2>&1; do sleep 5; done
echo "ready again"
```

**Expected:**

- `/readyz` returns **503** with `"database": "error: ..."` while
  Postgres is stopped, and 200 again once it is back.
- The disk alert threshold is documented in the hardening record and the
  alerting route (log shipper, email, or a manual check) is written
  down.

---

## 6. Rollback test — NOT VERIFIED

**Requirement:** a release must be revertible without touching the
database.

```bash
# 1. Note the current release.
cd /opt/sangad
git describe --tags --always
git log --oneline -1

# 2. Deploy the previous tag through Coolify, then watch it come back.
curl -fsS http://127.0.0.1:8088/readyz

# 3. Roll forward again to the release you want.
```

**Expected:** the stack is healthy again on the previous tag within the
same 5 minute budget as the reboot test, `/readyz` returns 200, and the
database was not migrated backwards by the rollback.

**Record:** the tags involved and the elapsed time in the hardening
record.

**Caution:** the rollback step is the one that can lose data if a
migration was not backwards compatible. Before rolling back, check the
migration that the newer release applied, and take a fresh backup
first.

---

## Summary

| Step | Status | Where to record |
|---|---|---|
| Reboot test (V-LOC-01) | NOT VERIFIED | hardening record |
| Backup and restore drill (RTO 4 h) | NOT VERIFIED | hardening record |
| LAN port scan (R-26) | NOT VERIFIED | hardening record |
| Host hardening record | NOT VERIFIED | `infra/runbooks/host-hardening-record.md` |
| Alert drills | NOT VERIFIED | hardening record |
| Rollback test | NOT VERIFIED | hardening record |
