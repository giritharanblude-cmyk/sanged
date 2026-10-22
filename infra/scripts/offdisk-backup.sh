# SANGAD — Off-disk backup script
# Run nightly via cron/systemd timer
set -euo pipefail
SRC_DIR="/var/lib/docker/volumes"
DEST_DIR="/mnt/backup-disk/sangad-backups"
restic -r "${DEST_DIR}" backup "${SRC_DIR}"
restic -r "${DEST_DIR}" check
