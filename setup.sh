# setup.sh — source-safe virtualenv setup (bash/zsh)
# Usage:  source ./setup.sh  [PYTHON=python3] [REQ=requirements.txt]

# Detect if we're sourced
_is_sourced=0
# bash
if [ -n "${BASH_SOURCE:-}" ] && [ "${BASH_SOURCE[0]}" != "$0" ]; then _is_sourced=1; fi
# zsh
if [ -n "${ZSH_EVAL_CONTEXT:-}" ] && [[ "$ZSH_EVAL_CONTEXT" == *:file ]]; then _is_sourced=1; fi

# If *executed*, bail and tell user to source
if [ $_is_sourced -eq 0 ]; then
  echo "❌ Run me with:  source ./setup.sh"
  exit 1
fi

# Do NOT use `set -e` in a sourced script; emulate it safely
set -u -o pipefail

# error handler that won't kill your shell
_die() {
  echo "ERROR: $*" >&2
  return 1
}
_try() { "$@" || _die "command failed: $*"; }

PY_BIN="${PYTHON:-python3}"
REQ_FILE="${REQ:-requirements.txt}"

# pick python
if ! command -v "$PY_BIN" >/dev/null 2>&1; then
  _die "python not found: $PY_BIN"; return
fi

# create venv if needed
if [ ! -d ".venv" ]; then
  echo "==> Creating .venv with: $PY_BIN -m venv .venv"
  _try "$PY_BIN" -m venv .venv || return
else
  echo "==> Reusing existing .venv"
fi

# activate (bash/zsh)
# shellcheck disable=SC1091
if [ -f ".venv/bin/activate" ]; then
  . .venv/bin/activate || { _die "activate failed"; return; }
else
  _die "missing .venv/bin/activate"; return
fi

echo "==> Upgrading pip tooling"
_try python -m pip install -U pip setuptools wheel || return

if [ -f "$REQ_FILE" ]; then
  echo "==> Installing from $REQ_FILE"
  if ! python -m pip install -r "$REQ_FILE"; then
    echo "==> Retry with helpers and no isolation"
    python -m pip install -U cython build hatchling || true
    _try python -m pip install --no-build-isolation --no-cache-dir -r "$REQ_FILE" || return
  fi
else
  echo "==> No $REQ_FILE; skipping installs"
fi

echo "✅ Activated in this shell. To deactivate:  deactivate"