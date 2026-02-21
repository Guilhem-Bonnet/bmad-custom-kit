#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# BMAD Mnemo — Pre-commit hook pour consolidation mémoire
# ═══════════════════════════════════════════════════════════════════════════════
#
# Ce hook exécute la consolidation des learnings et la vérification de drift
# AVANT chaque commit. Il ne bloque jamais le commit (exit 0 garanti).
#
# Installation :
#   cp framework/hooks/mnemo-consolidate.sh .git/hooks/pre-commit
#   chmod +x .git/hooks/pre-commit
#
# Ou via pre-commit framework (dans .pre-commit-config.yaml) :
#   - repo: local
#     hooks:
#       - id: mnemo-consolidate
#         name: "🧠 Mnemo — Consolidation mémoire"
#         entry: bash scripts/hooks/mnemo-consolidate.sh
#         language: system
#         always_run: true
#         pass_filenames: false
#         stages: [pre-commit]
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# Trouver la racine du workspace (remonter depuis le repo git)
GIT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Le dossier _bmad peut être à la racine du repo ou un niveau au-dessus
if [[ -d "$GIT_ROOT/_bmad/_memory" ]]; then
    MEMORY_DIR="$GIT_ROOT/_bmad/_memory"
elif [[ -d "$GIT_ROOT/../_bmad/_memory" ]]; then
    MEMORY_DIR="$GIT_ROOT/../_bmad/_memory"
else
    # Pas de _bmad trouvé — silencieux
    exit 0
fi

MAINTENANCE="$MEMORY_DIR/maintenance.py"

if [[ ! -f "$MAINTENANCE" ]]; then
    exit 0
fi

# Trouver Python
PYTHON=$(command -v python3 2>/dev/null || command -v python 2>/dev/null || echo "")
if [[ -z "$PYTHON" ]]; then
    exit 0
fi

echo "🧠 Mnemo pre-commit — consolidation mémoire..."

# 1. Consolidation des learnings (merge doublons)
"$PYTHON" "$MAINTENANCE" consolidate-learnings 2>/dev/null || true

# 2. Vérification drift shared-context
"$PYTHON" "$MAINTENANCE" context-drift 2>/dev/null || true

# Ne jamais bloquer le commit
exit 0
