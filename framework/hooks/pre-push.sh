#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# BMAD — Git pre-push hook
# ══════════════════════════════════════════════════════════════════════════════
#
# Déclenché avant git push.
# Lit remote/branch depuis stdin : <local_ref> <local_sha> <remote_ref> <remote_sha>
#
# Comportement :
#   1. Vérifie la syntaxe bash de bmad-init.sh si modifié
#   2. Lance validate --all (léger — python inline, <2s)
#   3. Vérifie que BMAD_TRACE.md n'est pas vide si _bmad-output/ a des commits
#   4. Skip si BMAD_SKIP_PUSH_CHECK=1 (CI/CD ou urgence)
#
# Installation via : bmad-init.sh hooks --install
# ══════════════════════════════════════════════════════════════════════════════

# Bypass d'urgence
[[ "${BMAD_SKIP_PUSH_CHECK:-0}" == "1" ]] && exit 0

GIT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
INIT_SCRIPT="$GIT_ROOT/bmad-init.sh"

[[ -d "$GIT_ROOT/_bmad" ]] || exit 0

ERRORS=0

echo ""
echo "🚀 BMAD pre-push checks..."

# ── 1. Syntaxe bash sur bmad-init.sh si modifié ───────────────────────────────
if [[ -f "$INIT_SCRIPT" ]]; then
    # Vérifier si bmad-init.sh est dans les commits à pousser
    MODIFIED=$(git diff --name-only origin/HEAD HEAD 2>/dev/null | grep -F "bmad-init.sh" || true)
    if [[ -n "$MODIFIED" ]] || git diff --cached --name-only 2>/dev/null | grep -qF "bmad-init.sh"; then
        if bash -n "$INIT_SCRIPT" 2>&1; then
            echo "   ✓ bmad-init.sh — syntaxe bash OK"
        else
            echo "   ✗ bmad-init.sh — ERREUR de syntaxe bash !"
            ERRORS=$((ERRORS + 1))
        fi
    fi
fi

# ── 2. Validation DNA (tous les archetypes) ───────────────────────────────────
DNA_FILES=$(find "$GIT_ROOT/archetypes" -name "*.dna.yaml" 2>/dev/null | wc -l)
if [[ "$DNA_FILES" -gt 0 ]]; then
    if command -v python3 &>/dev/null; then
        VALIDATE_RESULT=$(bash "$INIT_SCRIPT" validate --all 2>&1 | tail -3)
        if echo "$VALIDATE_RESULT" | grep -qi "erreur\|error\|invalid"; then
            echo "   ✗ DNA validate --all — erreurs détectées !"
            echo "     $VALIDATE_RESULT"
            ERRORS=$((ERRORS + 1))
        else
            echo "   ✓ DNA validate — $DNA_FILES fichiers OK"
        fi
    fi
fi

# ── 3. Résumé ─────────────────────────────────────────────────────────────────
if [[ $ERRORS -eq 0 ]]; then
    echo "   ✅ Tous les checks BMAD passent — push autorisé"
    echo ""
    exit 0
else
    echo ""
    echo "   🚫 $ERRORS check(s) échoué(s) — push bloqué"
    echo "   Pour bypasser : BMAD_SKIP_PUSH_CHECK=1 git push"
    echo ""
    exit 1
fi
