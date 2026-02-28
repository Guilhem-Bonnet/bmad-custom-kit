#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# BMAD — Git post-checkout hook
# ══════════════════════════════════════════════════════════════════════════════
#
# Déclenché par : git checkout, git switch
# Paramètres git : $1=prev-HEAD $2=new-HEAD $3=flag (1=branch, 0=file)
#
# Comportement :
#   - Si changement de branche (flag=1) ET session-branch BMAD détectée :
#     → Affiche l'état du checkpoint de la nouvelle branche
#     → Rappelle la commande resume si un checkpoint existe
#     → Vérifie la cohérence du shared-context.md
#
# Installation via : bmad-init.sh hooks --install
# ══════════════════════════════════════════════════════════════════════════════

PREV_HEAD="$1"
NEW_HEAD="$2"
BRANCH_CHECKOUT="$3"  # 1 = changement de branche, 0 = checkout fichier

# Ne s'active que pour les changements de branche
[[ "$BRANCH_CHECKOUT" == "1" ]] || exit 0

GIT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
BMAD_DIR="$GIT_ROOT/_bmad"
MEMORY_DIR="$BMAD_DIR/_memory"
STATE_FILE="$MEMORY_DIR/state.json"
CURRENT_BRANCH="$(git symbolic-ref --short HEAD 2>/dev/null || echo "detached")"

# Skip si pas un projet BMAD
[[ -d "$BMAD_DIR" ]] || exit 0

# Détecter si c'est une session-branch BMAD (format: bmad/<date>/<name>)
IS_BMAD_BRANCH=false
if echo "$CURRENT_BRANCH" | grep -qE '^bmad/[0-9]{8}/'; then
    IS_BMAD_BRANCH=true
fi

echo ""
echo "🔀 BMAD post-checkout → branche : $CURRENT_BRANCH"

# ── Checkpoint status ────────────────────────────────────────────────────────
if [[ -f "$STATE_FILE" ]] && command -v python3 &>/dev/null; then
    CHECKPOINT_INFO=$(python3 - <<'PYEOF'
import json, sys, os
state_file = os.environ.get("BMAD_STATE_FILE", "")
try:
    with open(state_file) as f:
        state = json.load(f)
    checkpoints = state.get("checkpoints", [])
    if checkpoints:
        last = checkpoints[-1]
        cid = last.get("checkpoint_id", "")[:12]
        desc = last.get("description", "")
        ts = last.get("timestamp", "")[:10]
        print(f"   💾 Dernier checkpoint : [{cid}] {desc} ({ts})")
        print(f"   ▶  Reprendre : bash bmad-init.sh resume --checkpoint {last.get('checkpoint_id','')[:12]}")
    else:
        print("   ℹ️  Aucun checkpoint sur cette branche")
except Exception as e:
    pass
PYEOF
)
    BMAD_STATE_FILE="$STATE_FILE" python3 - <<'PYEOF' 2>/dev/null && echo "$CHECKPOINT_INFO" || true
import json, sys, os
state_file = os.environ.get("BMAD_STATE_FILE", "")
try:
    with open(state_file) as f:
        state = json.load(f)
    checkpoints = state.get("checkpoints", [])
    if checkpoints:
        last = checkpoints[-1]
        cid = last.get("checkpoint_id", "")[:12]
        desc = last.get("description", "")
        ts = last.get("timestamp", "")[:10]
        print(f"   💾 Dernier checkpoint : [{cid}] {desc} ({ts})")
        print(f"   ▶  Reprendre : bash bmad-init.sh resume --checkpoint {cid}")
    else:
        print("   ℹ️  Aucun checkpoint sur cette branche")
except Exception:
    pass
PYEOF
fi

# ── Shared-context drift warning ─────────────────────────────────────────────
SHARED_CTX="$GIT_ROOT/_bmad/_memory/shared-context.md"
if [[ -f "$SHARED_CTX" ]]; then
    # Vérifier si shared-context a des modifications non-commises sur cette branche
    if git diff --name-only 2>/dev/null | grep -q "_bmad/_memory/shared-context.md"; then
        echo "   ⚠️  shared-context.md a des modifications locales non-stagées"
    fi
else
    echo "   ⚠️  shared-context.md introuvable — lancez : bash bmad-init.sh install"
fi

# ── Rappel session-branch ────────────────────────────────────────────────────
if [[ "$IS_BMAD_BRANCH" == "true" ]]; then
    echo "   🌿 Session-branch BMAD active — toutes vos sorties vont dans _bmad-output/"
fi

echo ""
exit 0
