# SANGAD — host hardening record (T-009)

This is a **blank template**. Fill it in on the host and keep it with the
repository. Every value is deliberately left as `TODO:` — nothing here
may be invented, because the record has to describe the machine that
actually runs the stack.

Copy the section for each host you operate.

---

## Host

| Item | Value |
|---|---|
| Hostname | TODO: |
| Physical or virtual machine | TODO: |
| LAN address | TODO: |
| Operating system and version | TODO: |
| Kernel version | TODO: |
| CPU | TODO: |
| RAM | TODO: |
| System disk | TODO: |
| Backup disk and mount point | TODO: |
| Host rebuild date | TODO: |

## Disk encryption (R-21, C-13)

| Item | Value |
|---|---|
| Full-disk encryption in use | TODO: |
| Key escrow location | TODO: |
| Key escrow date | TODO: |

## Network (R-26, V-DEP-02)

| Item | Value |
|---|---|
| Host firewall enabled | TODO: |
| Firewall default inbound policy | TODO: |
| Ports published on the LAN | TODO: |
| LAN port scan date and result | TODO: |
| Router port forwarding disabled | TODO: |
| Loopback-only binds confirmed | TODO: |

## Docker

| Item | Value |
|---|---|
| Docker Engine version | TODO: |
| Docker starts at boot | TODO: |
| Docker log driver and rotation | TODO: |
| Images pinned to explicit tags | TODO: |

## Coolify (R-21)

| Item | Value |
|---|---|
| Coolify version | TODO: |
| Dashboard bound to loopback | TODO: |
| Dashboard password set | TODO: |
| Two-factor authentication enabled | TODO: |
| Registration disabled | TODO: |
| Update cadence | TODO: |

## Secrets (R-21)

| Item | Value |
|---|---|
| Encryption key escrowed offline | TODO: |
| Coolify `APP_KEY` escrowed offline | TODO: |
| Secret rotation date | TODO: |
| Password manager used | TODO: |

## Backups (T-008, T-011)

| Item | Value |
|---|---|
| Off-disk backup schedule | TODO: |
| Off-disk backup location | TODO: |
| Last successful backup | TODO: |
| Last restore drill and its result | TODO: |
| Measured recovery time | TODO: |

## Availability (T-011, V-LOC-01, V-LOC-03)

| Item | Value |
|---|---|
| Sleep and hibernate disabled | TODO: |
| UPS installed and configured | TODO: |
| Last reboot test result and elapsed time | TODO: |
| Last power-loss test result | TODO: |

## Monitoring (T-008)

| Item | Value |
|---|---|
| Log destination | TODO: |
| Disk usage alert threshold | TODO: |
| Alert channel | TODO: |
| Last alert drill | TODO: |

## Findings and follow-ups

| Date | Finding | Action | Owner | Closed |
|---|---|---|---|---|
| TODO: | TODO: | TODO: | TODO: | TODO: |
