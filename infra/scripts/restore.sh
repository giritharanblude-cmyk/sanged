#!/usr/bin/env bash
# Restore a SANGAD Postgres backup into a SCRATCH database and verify it.
#
# This script never writes to the production database. It restores a dump
# into a throwaway database, compares the row counts of every table with
# the source, and exits non-zero when they differ. That is the check the
# backup drill has to pass: a backup that cannot be restored is not a
# backup.
#
# The dump can come from two places:
#
#   * a plain file, produced by the off-disk copy or by pg_dump
#   * a restic snapshot in the off-disk repository, which is what the
#     nightly backup script writes
#
# Usage:
#   restore.sh --dump <file> [--scratch-db <name>] [--source-url <url>] [--admin-url <url>]
#   restore.sh --snapshot <id> [--repo <restic-repo>] [same options]
#
# The database URLs default to the standard environment variables:
#   SOURCE_DATABASE_URL  the database the backup was taken from
#   ADMIN_DATABASE_URL   a connection that may create databases
set -euo pipefail

DUMP_FILE=""
SNAPSHOT_ID=""
RESTIC_REPO="${RESTIC_REPO:-/mnt/backup-disk/sangad-backups}"
SCRATCH_DB="${SCRATCH_DB:-sangad_restore_check}"
SOURCE_URL="${SOURCE_DATABASE_URL:-}"
ADMIN_URL="${ADMIN_DATABASE_URL:-}"
WORK_DIR=""

log() { printf '%s %s\n' "[restore]" "$*"; }
fail() { printf '%s %s\n' "[restore] ERROR:" "$*" >&2; exit 1; }

usage() {
    sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'
    exit "${1:-0}"
}

cleanup() {
    if [ -n "${WORK_DIR}" ] && [ -d "${WORK_DIR}" ]; then
        rm -rf "${WORK_DIR}"
    fi
}
trap cleanup EXIT

while [ $# -gt 0 ]; do
    case "$1" in
        --dump) DUMP_FILE="${2:-}"; shift 2 ;;
        --snapshot) SNAPSHOT_ID="${2:-}"; shift 2 ;;
        --repo) RESTIC_REPO="${2:-}"; shift 2 ;;
        --scratch-db) SCRATCH_DB="${2:-}"; shift 2 ;;
        --source-url) SOURCE_URL="${2:-}"; shift 2 ;;
        --admin-url) ADMIN_URL="${2:-}"; shift 2 ;;
        -h|--help) usage 0 ;;
        *) fail "unknown argument: $1" ;;
    esac
done

[ -n "${SOURCE_URL}" ] || fail "SOURCE_DATABASE_URL is not set; pass --source-url"
[ -n "${ADMIN_URL}" ] || fail "ADMIN_DATABASE_URL is not set; pass --admin-url"

for tool in psql pg_restore; do
    command -v "${tool}" >/dev/null 2>&1 || fail "${tool} is not on the PATH"
done

WORK_DIR="$(mktemp -d)"

# --- 1. get the dump ---------------------------------------------------------
if [ -n "${SNAPSHOT_ID}" ]; then
    command -v restic >/dev/null 2>&1 || fail "restic is not on the PATH"
    log "restoring snapshot ${SNAPSHOT_ID} from ${RESTIC_REPO}"
    restic -r "${RESTIC_REPO}" restore "${SNAPSHOT_ID}" --target "${WORK_DIR}" >/dev/null
    # The repository holds one dump per database; take the newest one.
    DUMP_FILE="$(find "${WORK_DIR}" -type f \( -name '*.dump' -o -name '*.sql' \) -printf '%T@ %p\n' \
        | sort -nr | head -n 1 | cut -d' ' -f2-)"
    [ -n "${DUMP_FILE}" ] || fail "snapshot ${SNAPSHOT_ID} holds no dump file"
fi

[ -n "${DUMP_FILE}" ] || fail "pass --dump <file> or --snapshot <id>"
[ -f "${DUMP_FILE}" ] || fail "dump file not found: ${DUMP_FILE}"
log "using dump ${DUMP_FILE} ($(wc -c < "${DUMP_FILE}") bytes)"

# --- 2. create the scratch database ------------------------------------------
scratch_url() {
    # Replace the database name in a connection URL.
    printf '%s' "${1}" | sed -E "s#/[^/?]+(\?[^/]*)?\$#/${SCRATCH_DB}\1#"
}

SCRATCH_URL="$(scratch_url "${ADMIN_URL}")"
log "dropping any previous scratch database ${SCRATCH_DB}"
psql "${ADMIN_URL}" -v ON_ERROR_STOP=1 -q \
    -c "DROP DATABASE IF EXISTS ${SCRATCH_DB} WITH (FORCE);" >/dev/null
psql "${ADMIN_URL}" -v ON_ERROR_STOP=1 -q \
    -c "CREATE DATABASE ${SCRATCH_DB};" >/dev/null
log "scratch database ${SCRATCH_DB} created"

# --- 3. restore --------------------------------------------------------------
log "restoring into ${SCRATCH_DB}"
case "${DUMP_FILE}" in
    *.sql)
        psql "${SCRATCH_URL}" -v ON_ERROR_STOP=1 -q -f "${DUMP_FILE}" >/dev/null
        ;;
    *)
        pg_restore --no-owner --no-privileges --dbname "${SCRATCH_URL}" "${DUMP_FILE}" >/dev/null
        ;;
esac
log "restore finished"

# --- 4. compare the row counts ----------------------------------------------
tables_of() {
    psql "$1" -At -v ON_ERROR_STOP=1 -c "
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name;"
}

count_of() {
    # $1 = database url, $2 = table name
    psql "$1" -At -v ON_ERROR_STOP=1 -c "SELECT count(*) FROM public.\"$2\";"
}

SOURCE_TABLES="$(tables_of "${SOURCE_URL}")"
SCRATCH_TABLES="$(tables_of "${SCRATCH_URL}")"

if [ -z "${SOURCE_TABLES}" ]; then
    fail "the source database has no tables"
fi
if [ "${SOURCE_TABLES}" != "${SCRATCH_TABLES}" ]; then
    log "table lists differ"
    printf 'source: %s\nscratch: %s\n' "${SOURCE_TABLES}" "${SCRATCH_TABLES}" >&2
    fail "the restored database does not have the same tables"
fi

mismatches=0
compared=0
while IFS= read -r table; do
    [ -n "${table}" ] || continue
    source_count="$(count_of "${SOURCE_URL}" "${table}")"
    scratch_count="$(count_of "${SCRATCH_URL}" "${table}")"
    compared=$((compared + 1))
    if [ "${source_count}" != "${scratch_count}" ]; then
        printf '  MISMATCH %-24s source=%s scratch=%s\n' "${table}" "${source_count}" "${scratch_count}" >&2
        mismatches=$((mismatches + 1))
    fi
done <<< "${SOURCE_TABLES}"

if [ "${mismatches}" -ne 0 ]; then
    fail "${mismatches} of ${compared} tables have a different row count"
fi

log "all ${compared} tables match the source row counts"
log "PASS: ${DUMP_FILE} restores cleanly into ${SCRATCH_DB}"
exit 0
