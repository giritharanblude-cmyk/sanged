#!/usr/bin/env bash
# Check that a commit message follows the convention the architecture
# requires (R-25): Conventional Commits with a T- task id.
#
# Usage: check-commit-msg.sh <path-to-commit-message-file>
set -uo pipefail

MESSAGE_FILE="${1:-}"
if [ -z "${MESSAGE_FILE}" ] || [ ! -f "${MESSAGE_FILE}" ]; then
    echo "usage: check-commit-msg.sh <commit-message-file>" >&2
    exit 2
fi

# The first line is the subject; a merge or revert commit is allowed to
# be the generated one.
SUBJECT="$(head -n 1 "${MESSAGE_FILE}")"

if [ -z "${SUBJECT}" ]; then
    echo "the commit message is empty" >&2
    exit 1
fi

if ! printf '%s' "${SUBJECT}" | grep -qE '^(feat|fix|docs|chore|refactor|test|perf|build|ci|style|revert)(\([^)]+\))?!?: .+'; then
    cat >&2 <<'MESSAGE'
the commit subject must follow Conventional Commits, for example:
  feat(api): serialise money as strings [T-101]
  fix(deploy): pin the mailpit image [T-002]
MESSAGE
    exit 1
fi

if ! printf '%s' "${SUBJECT}" | grep -qE '\[T-[0-9]+\]'; then
    cat >&2 <<'MESSAGE'
the commit subject must carry the task id of the work, for example:
  feat(api): serialise money as strings [T-101]
MESSAGE
    exit 1
fi

exit 0
