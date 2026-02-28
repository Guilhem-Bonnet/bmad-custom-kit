#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# BMAD — Git post-commit hook
# ══════════════════════════════════════════════════════════════════════════════
#
# Déclenché APRÈS chaque commit réussi.
# Ne reçoit pas de paramètres.
#
# Comportement :
#   1. Append une entrée [GIT-COMMIT] dans BMAD_TRACE.md avec :
#      - Hash court du commit
#      - Message du commit
#      - Fichiers modifiés (liste)
#      - Agent actif (depuis state.json)
#      - Branche courante
#   2. Ne bloque jamais (exit 0 garanti)
#
# Installation via : bmad-init.sh hooks --install
# ══════════════════════════════════════════════════════════════════════════════

set -uo pipefail  # pas -e : hook post-commit ne doit jamais bloquer

GIT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
BMAD_DIR="$GIT_ROOT/_bmad"

[[ -d "$BMAD_DIR" ]] || exit 0

TRACE_FILE="$GIT_ROOT/_bmad-output/BMAD_TRACE.md"
STATE_FILE="$BMAD_DIR/_memory/state.json"

# Informations du commit
COMMIT_HASH="$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")"
COMMIT_MSG="$(git log -1 --pretty=%s 2>/dev/null || echo "")"
BRANCH="$(git symbolic-ref --short HEAD 2>/dev/null || echo "detached")"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
DATE="$(date -u +"%Y-%m-%d")"

# Fichiers modifiés dans le commit
CHANGED_FILES="$(git diff-tree --no-commit-id -r --name-only HEAD 2>/dev/null | head -20 | tr '\n' ', ' | sed 's/,$//')"

# Agent actif
ACTIVE_AGENT=""
if [[ -f "$STATE_FILE" ]] && command -v python3 &>/dev/null; then
    ACTIVE_AGENT=$(python3 - <<PYEOF 2>/dev/null || true
import json
try:
    with open("$STATE_FILE") as f:
        state = json.load(f)
    print(state.get("active_agent", ""))
except Exception:
    pass
PYEOF
)
fi

# Construire l'entrée TRACE
AGENT_TAG="${ACTIVE_AGENT:-system}"
TRACE_ENTRY="
## $(date -u +"%Y-%m-%d %H:%M") | git-commit | $AGENT_TAG

[GIT-COMMIT] hash:$COMMIT_HASH branch:$BRANCH
**Message :** $COMMIT_MSG
**Fichiers :** $CHANGED_FILES
"

# Créer le répertoire si nécessaire
mkdir -p "$(dirname "$TRACE_FILE")"

# Initialiser le fichier s'il n'existe pas
if [[ ! -f "$TRACE_FILE" ]]; then
    echo "# BMAD_TRACE — Audit Trail" > "$TRACE_FILE"
    echo "" >> "$TRACE_FILE"
    echo "> Généré automatiquement — ne pas éditer manuellement" >> "$TRACE_FILE"
    echo "" >> "$TRACE_FILE"
fi

# Append l'entrée
echo "$TRACE_ENTRY" >> "$TRACE_FILE"

exit 0
