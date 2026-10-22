#!/usr/bin/env bash
# Scan a host from the LAN and report which TCP ports answer.
#
# The stack is meant to be loopback-only (R-26). This script is meant to
# be run from another device on the same network, pointing at the host's
# LAN address: if a port answers from the LAN, the host is exposed.
#
# It uses bash's /dev/tcp, so it needs no scanning tool installed. If
# nmap is present it is used instead, because it can also report the
# service behind a closed port and does the probing faster.
#
# Usage:
#   lan-portscan.sh <host> [port ...]
#   lan-portscan.sh <host> --all            # scan the common ports
#   lan-portscan.sh <host> --range 1-1024   # scan a port range
#
# Ports default to the ones SANGAD uses, plus the ones that should never
# be reachable from the LAN.
set -uo pipefail

HOST=""
PORTS=()
RANGE=""
USE_NMAP=0

COMMON_PORTS=(
    22      # ssh
    80      # http
    443     # https
    3000    # node
    5000    # flask
    5432    # postgres
    6379    # redis
    8000    # coolify dashboard
    8025    # mailpit
    8088    # sangad api
    8333    # seaweedfs s3
    9333    # seaweedfs status
    27017   # mongodb
)

usage() {
    sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
    exit "${1:-0}"
}

while [ $# -gt 0 ]; do
    case "$1" in
        --all) PORTS=("${COMMON_PORTS[@]}"); shift ;;
        --range) RANGE="${2:-}"; shift 2 ;;
        -h|--help) usage 0 ;;
        -*) echo "unknown option: $1" >&2; usage 1 ;;
        *) if [ -z "${HOST}" ]; then HOST="$1"; else PORTS+=("$1"); fi; shift ;;
    esac
done

[ -n "${HOST}" ] || usage 1

if [ -n "${RANGE}" ]; then
    start="${RANGE%-*}"
    end="${RANGE#*-}"
    if [ "${start}" -gt "${end}" ]; then
        echo "invalid range: ${RANGE}" >&2
        exit 2
    fi
    port="${start}"
    while [ "${port}" -le "${end}" ]; do
        PORTS+=("${port}")
        port=$((port + 1))
    done
fi

if [ "${#PORTS[@]}" -eq 0 ]; then
    PORTS=("${COMMON_PORTS[@]}")
fi

echo "Scanning ${HOST} for ${#PORTS[@]} port(s) from $(hostname -I 2>/dev/null | awk '{print $1}')"

# --- nmap when it is available ------------------------------------------------
if command -v nmap >/dev/null 2>&1; then
    USE_NMAP=1
fi

if [ "${USE_NMAP}" -eq 1 ]; then
    port_spec="$(IFS=,; echo "${PORTS[*]}")"
    echo "Using nmap."
    nmap -Pn -sT -p "${port_spec}" "${HOST}"
    nmap_status=$?
    echo
    echo "Any port listed as open is a finding: the stack must be loopback-only."
    exit "${nmap_status}"
fi

# --- bash /dev/tcp fallback ---------------------------------------------------
echo "Using bash /dev/tcp (no nmap found)."
echo

open_ports=()
closed_ports=()

for port in "${PORTS[@]}"; do
    if timeout 2 bash -c "exec 3<>/dev/tcp/${HOST}/${port}" 2>/dev/null; then
        open_ports+=("${port}")
        printf '  OPEN    %s\n' "${port}"
    else
        closed_ports+=("${port}")
        printf '  closed  %s\n' "${port}"
    fi
done

echo
echo "open:   ${#open_ports[@]}"
echo "closed: ${#closed_ports[@]}"

if [ "${#open_ports[@]}" -gt 0 ]; then
    echo
    echo "FAIL: the following ports answered from the LAN:"
    for port in "${open_ports[@]}"; do
        echo "  ${port}"
    done
    echo "The stack must bind to 127.0.0.1 only (R-26). Record the finding in"
    echo "infra/runbooks/host-hardening-record.md and close the port."
    exit 1
fi

echo
echo "PASS: nothing answered from the LAN."
exit 0
