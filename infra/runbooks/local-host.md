# SANGAD — local host runbook (T-011)

Covers the host that runs the whole stack: auto-start after a reboot,
the sleep and power-loss behaviour, the UPS note, and how to rebuild the
host from nothing.

The host is assumed to be **Ubuntu 24.04 LTS**, 16 GB RAM, an SSD for the
stack and a **second disk** for the off-disk backup copy (architecture
§9.1, Q-16 and Q-20). The initial setup is in `infra/local/host-setup.md`.

Related documents:

- `infra/runbooks/operations.md` — deploy, rollback, restore, breach response
- `infra/runbooks/host-hardening-record.md` — the record of what was hardened
- `infra/scripts/restore.sh` — restore a backup into a scratch database
- `infra/scripts/offdisk-backup.sh` — the nightly off-disk copy
- `infra/scripts/lan-portscan.sh` — check what the host exposes on the LAN

---

## 1. What "healthy" means

| Check | Command | Expected |
|---|---|---|
| The stack is up | `docker compose -f infra/coolify/docker-compose.yml ps` | every service `running`, the api and worker `healthy` |
| The API answers | `curl -fsS http://127.0.0.1:8088/healthz` | `{"status":"ok"}` |
| The API is ready | `curl -fsS http://127.0.0.1:8088/readyz` | `{"status":"ok","checks":{"database":"ok","redis":"ok","storage":"ok"}}` |
| Coolify is up | `curl -fsS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000` | `200` |

`/readyz` is the one that matters: it probes Postgres, Redis and the
object store, so it is not green until the stack can actually serve.

---

## 2. Reboot test (V-LOC-01)

**Rule:** after a reboot, with nobody touching the machine, Docker,
Coolify and every production service must be healthy and `/readyz` must
return `200` **within 5 minutes**.

### 2.1 Before the reboot

```bash
# Make sure the stack is green now, so a failure later is not blamed on
# a stack that was already broken.
cd /opt/sangad
docker compose -f infra/coolify/docker-compose.yml ps
curl -fsS http://127.0.0.1:8088/readyz
```

### 2.2 Run the timed reboot

The timer starts the moment the machine comes back up.

```bash
# Record the moment the host goes down.
date --iso-8601=seconds | tee /tmp/reboot-start.txt

# Reboot now.
sudo reboot
```

When the host is back, run this on it. It prints the elapsed seconds and
the readiness result, and it fails if the stack was not ready within 5
minutes:

```bash
start=$(date --iso-8601=seconds)
deadline=$(( $(date +%s) + 300 ))

until curl -fsS http://127.0.0.1:8088/readyz > /tmp/readyz.json 2>/dev/null; do
    now=$(date +%s)
    if [ "$now" -ge "$deadline" ]; then
        echo "FAIL: /readyz did not return 200 within 300s"
        cat /tmp/readyz.json 2>/dev/null
        docker compose -f /opt/sangad/infra/coolify/docker-compose.yml ps
        exit 1
    fi
    sleep 5
done

end=$(date --iso-8601=seconds)
echo "PASS: /readyz returned 200 after $(( $(date +%s) - ${deadline} + 300 ))s"
cat /tmp/readyz.json
```

Copy the output into the record section of
`infra/runbooks/host-hardening-record.md`.

**Expected result:** `PASS`, with an elapsed time comfortably under 300
seconds. Postgres crash recovery after an unclean stop is the slow part;
if the first boot takes longer than the second, that is normal.

### 2.3 If the reboot test fails

| Symptom | Cause | Fix |
|---|---|---|
| `docker` is not running | Docker is not enabled | `sudo systemctl enable --now docker` |
| Coolify is not running | Coolify is not enabled | `sudo systemctl enable --now coolify` |
| Postgres is `starting` forever | The data volume was not mounted | `lsblk`, `mount /mnt/backup-disk`, check `/etc/fstab` |
| The api container is unhealthy but Postgres is fine | The api waited for the schema | `docker compose logs api` and look for the Alembic output |
| The stack came up but `/readyz` is 503 | A dependency is still starting | `curl -fsS http://127.0.0.1:8088/readyz` names the failing check |

---

## 3. Power loss and sleep (V-LOC-03)

A power cut is the worst case: the filesystem was not closed cleanly.

### 3.1 Sleep must be off

A sleeping host stops serving. Disable it and make sure it stays off:

```bash
sudo systemctl mask sleep.target suspend.target hibernate.target
sudo systemctl disable sleep.target suspend.target hibernate.target
```

Laptop models also need the lid closed setting:

```bash
sudo install -m 0644 /dev/null /etc/systemd/system/sleep.target
grep -R . /etc/systemd/system/sleep.target.d/ 2>/dev/null
```

### 3.2 Power-loss test

```bash
# Take the stack down the way a power cut would: no clean shutdown.
sudo systemctl stop docker
sudo systemctl start docker
```

Then run the readiness loop from §2.2 and confirm the stack recovers on
its own. Postgres replays its write-ahead log on the first start after an
unclean stop, so the first start is slower than a clean one.

### 3.3 Disk pressure

The build plan asks for a disk alert at 80 % full. Check it and record
the numbers in the hardening record:

```bash
df -h /
docker system df
```

### 3.4 UPS note

The host runs the only copy of the production data. A UPS is not optional
for a machine that is expected to survive a power cut with its database
intact:

- A **line-interactive UPS with USB or network signalling** lets the host
  shut itself down cleanly on mains loss, which turns a power cut into an
  orderly stop.
- Configure it with `apcupsd` (USB) or `nut` (network), and set the host
  to stop when the UPS battery is low:

  ```bash
  sudo systemctl enable apcupsd
  # /etc/apcupsd/apcupsd.conf: UPSNAME, HOSTADDR, MONITOR
  ```

- Test the shutdown path with `apcaccess status` and the host's own
  `onbattery` event, not by pulling the plug during work.
- If there is no UPS, raise the risk in the hardening record: an unclean
  stop is survivable (Postgres recovers) but the window for data loss is
  real.

---

## 4. Host rebuild steps

If the machine has to be built again from nothing, in this order:

1. Install Ubuntu 24.04 LTS, enable full-disk encryption, set the
   hostname and the static address.
2. Mount the second disk at `/mnt/backup-disk` and add it to `/etc/fstab`.
3. Install Docker Engine and Coolify (`infra/local/host-setup.md`).
4. Disable sleep (§3.1) and enable Docker and Coolify at boot (§2.3).
5. Clone the repository with the deploy key and check out the tag you
   want to run.
6. Restore Postgres from the off-disk copy **into a scratch database
   first** and check the row counts, then restore it for real:

   ```bash
   infra/scripts/restore.sh --snapshot latest --repo /mnt/backup-disk/sangad-backups
   ```

   The restore script only ever writes to a scratch database. Move the
   restored data into the production database only after it reports PASS.
7. Restore the object store bucket from the same off-disk copy.
8. Re-enter the secrets in Coolify from the vault, including the
   encryption key and Coolify's own `APP_KEY` (R-21).
9. Run the reboot test (§2) and the backup drill
   (`infra/scripts/offdisk-backup.sh` followed by `infra/scripts/restore.sh`).
10. Fill in `infra/runbooks/host-hardening-record.md`.

---

## 5. LAN exposure

The stack is meant to be loopback-only (R-26). From another device on
the same network, confirm that nothing is listening:

```bash
# On the other device, with the host's LAN address:
infra/scripts/lan-portscan.sh <host-lan-address>
```

The scan must report every port as closed. Anything open is a finding:
record it in the hardening record and close it.
