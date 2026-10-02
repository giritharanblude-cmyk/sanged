# SANGAD operational runbooks

## Deploy
1. Merge changes to main, tag with vX.Y.Z
2. Open Coolify dashboard or run: `infra/scripts/deploy.sh production main`
3. Monitor health via /healthz and /readyz endpoints

## Rollback
1. Re-deploy previous Git tag via Coolify UI
2. If migration damaged data, restore from backup (see restore runbook)

## Restore from backup
1. Provision fresh Ubuntu 24.04 machine
2. Install Docker Engine 24+ and Coolify
3. Clone the Git repo via deploy key
4. Restore Postgres from latest S3 backup: `restic restore latest --target /tmp/restore`
5. Copy restored database to the new Postgres resource
6. Set environment variables from the secrets vault
7. Redeploy from Coolify

## WhatsApp re-pair
1. Open OpenWA dashboard (loopback-bound port on localhost)
2. Scan QR code or use pairing code with the dedicated number
3. Verify webhook delivery by sending a test message
4. Update sender allow-list if needed

## Encryption key escrow
- Store a copy of `SANGAD_FIELD_ENCRYPTION_KEY` in a physical safe
- Store Coolify APP_KEY in a separate secure location
- Recovery: Re-enter the key in Coolify env, restart the API service

## Breach response
1. Isolate the host from network
2. Rotate all secrets in Coolify
3. Revoke and re-issue WhatsApp gateway API key
4. Audit all audit_log entries for unauthorized access
5. Restore from pre-breach backup if data integrity is compromised