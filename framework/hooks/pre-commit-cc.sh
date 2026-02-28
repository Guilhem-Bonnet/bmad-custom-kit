#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# BMAD Completion Contract — Git pre-commit hook
# ═══════════════════════════════════════════════════════════════════════════════
#
# Installé par bmad-init.sh dans .git/hooks/pre-commit
# Vérifie le CC uniquement sur les fichiers stagés. Skip si cc-verify.sh absent.
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
CC_SCRIPT="$PROJECT_ROOT/_bmad/_config/custom/cc-verify.sh"

# Skip si CC non installé (projet sans BMAD)
[[ -f "$CC_SCRIPT" ]] || exit 0

# Extensions à surveiller
WATCHABLE="go|ts|tsx|py|tf|tfvars|sh|Dockerfile"

# Vérifier si des fichiers vérifiables sont stagés
STAGED=$(git diff --cached --name-only 2>/dev/null || true)
if ! echo "$STAGED" | grep -qE "\.(${WATCHABLE})$|^Dockerfile[^/]*$"; then
    exit 0  # Rien à vérifier (md, yaml config, images, etc.) — commit autorisé
fi

echo ""
echo "🔒 BMAD Completion Contract — vérification pre-commit..."
echo "   Fichiers stagés détectés : $(echo "$STAGED" | grep -cE "\.(${WATCHABLE})$|^Dockerfile" || true) fichier(s) vérifiable(s)"
echo ""

# Lancer CC en mode --changed-only pour ne vérifier que le stack impacté
if bash "$CC_SCRIPT" --changed-only; then
    exit 0
else
    echo ""
    echo "🚫 Commit bloqué — CC FAIL détecté."
    echo "   Corrigez les erreurs ci-dessus puis relancez git commit."
    echo "   Pour bypasser (DÉCONSEILLÉ) : git commit --no-verify"
    echo ""
    exit 1
fi
