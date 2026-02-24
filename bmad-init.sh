#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# BMAD Custom Kit — Initialisation d'un nouveau projet
# ═══════════════════════════════════════════════════════════════════════════════
#
# Usage:
#   bmad-init.sh --name "Mon Projet" --user "Guilhem" --lang "Français" --archetype infra-ops
#   bmad-init.sh --help
#
# Ce script installe le framework BMAD Custom dans le répertoire courant.
# Il est conçu pour être exécuté depuis la racine du projet cible.
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# ─── Variables ────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_DIR="$(pwd)"
PROJECT_NAME=""
USER_NAME=""
LANGUAGE="Français"
ARCHETYPE="minimal"
AUTO_DETECT=false

# ─── Couleurs ────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ─── Fonctions utilitaires ───────────────────────────────────────────────────
info()  { echo -e "${BLUE}ℹ️  $*${NC}"; }
ok()    { echo -e "${GREEN}✅ $*${NC}"; }
warn()  { echo -e "${YELLOW}⚠️  $*${NC}"; }
error() { echo -e "${RED}❌ $*${NC}" >&2; exit 1; }

usage() {
    cat <<EOF
${CYAN}BMAD Custom Kit — Initialisation${NC}

Usage:
  $(basename "$0") --name "Nom du Projet" --user "Votre Nom" [options]

Options:
  --name NAME         Nom du projet (requis)
  --user USER         Votre nom (requis)
  --lang LANGUAGE     Langue de communication (défaut: Français)
  --archetype TYPE    Archétype à utiliser: minimal, infra-ops (défaut: minimal)
  --target DIR        Répertoire cible (défaut: répertoire courant)
  --auto              Détecter automatiquement le stack et choisir l'archétype optimal
  --help              Afficher cette aide

Archétypes:
  minimal     Meta-agents (Atlas, Sentinel, Mnemo) + 1 agent vierge
  infra-ops   Agents Infrastructure & DevOps complets (10 agents)

Exemples:
  $(basename "$0") --name "Mon API" --user "Alice" --archetype minimal
  $(basename "$0") --name "Infra Prod" --user "Bob" --archetype infra-ops --lang "English"
EOF
    exit 0
}

# ─── Parsing arguments ──────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --name)     PROJECT_NAME="$2"; shift 2 ;;
        --user)     USER_NAME="$2"; shift 2 ;;
        --lang)     LANGUAGE="$2"; shift 2 ;;
        --archetype) ARCHETYPE="$2"; shift 2 ;;
        --target)   TARGET_DIR="$2"; shift 2 ;;
        --auto)     AUTO_DETECT=true; shift ;;
        --help)     usage ;;
        *)          error "Option inconnue: $1. Utilisez --help." ;;
    esac
done

# ─── Détection automatique du stack ─────────────────────────────────────────
detect_stack() {
    local dir="${1:-$(pwd)}"
    local detected=()

    # Go
    [[ -f "$dir/go.mod" ]] && detected+=("go")

    # Terraform (racine ou sous-dossiers profonds, hors .terraform/)
    if find "$dir" -maxdepth 7 -name '*.tf' \
         -not -path '*/.terraform/*' \
         -not -path '*/node_modules/*' \
         -print -quit 2>/dev/null | grep -q .; then
        detected+=("terraform")
    fi

    # Frontend (React/Vue/Next/Vite) — chercher package.json jusqu'à depth 3
    if find "$dir" -maxdepth 3 -name 'package.json' \
         -not -path '*/node_modules/*' \
         -exec grep -qE '"(react|vue|next|vite)"' {} \; \
         -print -quit 2>/dev/null | grep -q .; then
        detected+=("frontend")
    # Node sans framework frontend
    elif [[ -f "$dir/package.json" ]] && \
         ! grep -qE '"(react|vue|next|vite)"' "$dir/package.json" 2>/dev/null; then
        detected+=("node")
    fi

    # Ansible
    if [[ -d "$dir/ansible" ]] || \
       find "$dir" -maxdepth 3 -name 'playbook*.yml' -print -quit 2>/dev/null | grep -q . || \
       find "$dir" -maxdepth 3 -name 'site.yml' -print -quit 2>/dev/null | grep -q . || \
       find "$dir" -maxdepth 3 -name 'ansible.cfg' -print -quit 2>/dev/null | grep -q .; then
        detected+=("ansible")
    fi

    # Kubernetes (manifests avec kind: Deployment/StatefulSet/Service)
    if [[ -d "$dir/k8s" ]] || [[ -d "$dir/kubernetes" ]] || \
       find "$dir" -maxdepth 4 -name '*.yaml' \
         -not -path '*/node_modules/*' \
         -not -path '*/.terraform/*' \
         -exec grep -qlE '^kind: (Deployment|StatefulSet|DaemonSet|Service|Ingress)' {} \; \
         -print -quit 2>/dev/null | grep -q .; then
        detected+=("k8s")
    fi

    # Python
    if [[ -f "$dir/requirements.txt" ]] || [[ -f "$dir/pyproject.toml" ]] || \
       find "$dir" -maxdepth 2 -name 'requirements*.txt' -print -quit 2>/dev/null | grep -q .; then
        detected+=("python")
    fi

    # Docker
    if [[ -f "$dir/Dockerfile" ]] || \
       find "$dir" -maxdepth 3 -name 'docker-compose*.yml' -print -quit 2>/dev/null | grep -q . || \
       find "$dir" -maxdepth 3 -name 'Dockerfile*' -print -quit 2>/dev/null | grep -q .; then
        detected+=("docker")
    fi

    echo "${detected[*]:-unknown}"
}

auto_select_archetype() {
    local stacks="$1"
    # infra-ops si terraform ou k8s ou ansible
    if echo "$stacks" | grep -qE '(terraform|k8s|ansible)'; then
        echo "infra-ops"
    else
        echo "minimal"
    fi
}

# ─── Déploiement des agents stack (Modal Team Engine) ───────────────────────
# Copie les agents spécialisés correspondant aux stacks détectés dans le
# répertoire _bmad/_config/custom/agents/ du projet cible.
deploy_stack_agents() {
    local stacks="$1"
    local target_agents_dir="$2"
    local stack_agents_dir="$SCRIPT_DIR/archetypes/stack/agents"
    local deployed=()

    [[ ! -d "$stack_agents_dir" ]] && { warn "archetypes/stack/agents/ non trouvé — agents stack ignorés"; return 0; }

    declare -A STACK_MAP=(
        ["go"]="go-expert.md"
        ["frontend"]="typescript-expert.md"
        ["node"]="typescript-expert.md"
        ["python"]="python-expert.md"
        ["docker"]="docker-expert.md"
        ["terraform"]="terraform-expert.md"
        ["k8s"]="k8s-expert.md"
        ["ansible"]="ansible-expert.md"
    )

    for stack in $stacks; do
        agent_file="${STACK_MAP[$stack]:-}"
        [[ -z "$agent_file" ]] && continue
        src="$stack_agents_dir/$agent_file"
        dst="$target_agents_dir/$agent_file"
        if [[ -f "$src" ]] && [[ ! -f "$dst" ]]; then
            cp "$src" "$dst"
            deployed+=("$agent_file")
        fi
    done

    if [[ ${#deployed[@]} -gt 0 ]]; then
        ok "Agents stack déployés : ${deployed[*]}"
    else
        info "Aucun agent stack supplémentaire (déjà présents ou stacks non reconnus)"
    fi
}

# ─── Validation ──────────────────────────────────────────────────────────────
[[ -z "$PROJECT_NAME" ]] && error "--name est requis"
[[ -z "$USER_NAME" ]]    && error "--user est requis"
[[ ! -d "$SCRIPT_DIR/framework" ]] && error "Le kit BMAD n'est pas trouvé dans $SCRIPT_DIR"

# Auto-détection du stack si --auto
if $AUTO_DETECT; then
    info "Analyse automatique du stack..."
    DETECTED_STACKS=$(detect_stack "$TARGET_DIR")
    AUTO_ARCHETYPE=$(auto_select_archetype "$DETECTED_STACKS")
    [[ "$ARCHETYPE" == "minimal" ]] && ARCHETYPE="$AUTO_ARCHETYPE"
    ok "Stack détecté : ${DETECTED_STACKS:-aucun} → archétype : $ARCHETYPE"
fi

ARCHETYPE_DIR="$SCRIPT_DIR/archetypes/$ARCHETYPE"
[[ ! -d "$ARCHETYPE_DIR" ]] && error "Archétype '$ARCHETYPE' non trouvé. Disponibles: $(ls "$SCRIPT_DIR/archetypes/")"

# ─── Vérification cible ─────────────────────────────────────────────────────
BMAD_DIR="$TARGET_DIR/_bmad"
if [[ -d "$BMAD_DIR/_config/custom" ]]; then
    warn "Un dossier _bmad/custom existe déjà dans $TARGET_DIR"
    read -p "Continuer et écraser ? (y/N) " -n 1 -r
    echo
    [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
fi

# ═══════════════════════════════════════════════════════════════════════════════
# INSTALLATION
# ═══════════════════════════════════════════════════════════════════════════════

echo ""
echo -e "${CYAN}🤖 BMAD Custom Kit — Initialisation${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "  Projet:     ${GREEN}$PROJECT_NAME${NC}"
echo -e "  Utilisateur: ${GREEN}$USER_NAME${NC}"
echo -e "  Langue:     ${GREEN}$LANGUAGE${NC}"
echo -e "  Archétype:  ${GREEN}$ARCHETYPE${NC}"
echo -e "  Cible:      ${GREEN}$TARGET_DIR${NC}"
echo ""

# ─── 1. Créer la structure de base ──────────────────────────────────────────
info "Création de la structure _bmad..."

mkdir -p "$BMAD_DIR/_config/custom/agents"
mkdir -p "$BMAD_DIR/_config/custom/prompt-templates"
mkdir -p "$BMAD_DIR/_config/custom/workflows"
mkdir -p "$BMAD_DIR/_memory/agent-learnings"
mkdir -p "$BMAD_DIR/_memory/session-summaries"
mkdir -p "$BMAD_DIR/_memory/archives"

# ─── 2. Copier le framework ────────────────────────────────────────────────
info "Installation du framework..."

# Agent base protocol
cp "$SCRIPT_DIR/framework/agent-base.md" "$BMAD_DIR/_config/custom/agent-base.md"

# Completion Contract verifier
cp "$SCRIPT_DIR/framework/cc-verify.sh" "$BMAD_DIR/_config/custom/cc-verify.sh"
chmod +x "$BMAD_DIR/_config/custom/cc-verify.sh"

# Self-Improvement Loop collector
cp "$SCRIPT_DIR/framework/sil-collect.sh" "$BMAD_DIR/_config/custom/sil-collect.sh"
chmod +x "$BMAD_DIR/_config/custom/sil-collect.sh"

# Scripts mémoire
cp "$SCRIPT_DIR/framework/memory/maintenance.py" "$BMAD_DIR/_memory/maintenance.py"
cp "$SCRIPT_DIR/framework/memory/mem0-bridge.py" "$BMAD_DIR/_memory/mem0-bridge.py"
cp "$SCRIPT_DIR/framework/memory/session-save.py" "$BMAD_DIR/_memory/session-save.py"
cp "$SCRIPT_DIR/framework/memory/requirements.txt" "$BMAD_DIR/_memory/requirements.txt"

# Prompt templates
cp -r "$SCRIPT_DIR/framework/prompt-templates/"* "$BMAD_DIR/_config/custom/prompt-templates/" 2>/dev/null || true

# Workflows
cp -r "$SCRIPT_DIR/framework/workflows/"* "$BMAD_DIR/_config/custom/workflows/" 2>/dev/null || true

ok "Framework installé"

# ─── 3. Copier les agents meta (toujours inclus) ────────────────────────────
info "Installation des agents meta (Atlas, Sentinel, Mnemo)..."

cp "$SCRIPT_DIR/archetypes/meta/agents/"*.md "$BMAD_DIR/_config/custom/agents/"
ok "Agents meta installés"

# ─── 4. Copier les agents de l'archétype ────────────────────────────────────
if [[ "$ARCHETYPE" != "meta" ]]; then
    info "Installation de l'archétype '$ARCHETYPE'..."
    cp "$ARCHETYPE_DIR/agents/"*.md "$BMAD_DIR/_config/custom/agents/" 2>/dev/null || true

    # Copier le template shared-context si disponible
    if [[ -f "$ARCHETYPE_DIR/shared-context.tpl.md" ]]; then
        cp "$ARCHETYPE_DIR/shared-context.tpl.md" "$BMAD_DIR/_memory/shared-context.md"
    fi

    ok "Archétype '$ARCHETYPE' installé"
fi

# ─── 4b. Déployer les agents stack via Modal Team Engine (MTE) ───────────────
if $AUTO_DETECT && [[ -n "${DETECTED_STACKS:-}" ]]; then
    info "Modal Team Engine — déploiement des agents stack..."
    deploy_stack_agents "$DETECTED_STACKS" "$BMAD_DIR/_config/custom/agents"
fi

# ─── 5. Générer project-context.yaml ────────────────────────────────────────
info "Génération de project-context.yaml..."

PROJECT_CONTEXT="$TARGET_DIR/project-context.yaml"
if [[ ! -f "$PROJECT_CONTEXT" ]]; then
    sed -e "s/\"Mon Projet\"/\"$PROJECT_NAME\"/" \
        -e "s/\"Votre Nom\"/\"$USER_NAME\"/" \
        -e "s/\"Français\"/\"$LANGUAGE\"/" \
        -e "s/\"minimal\"/\"$ARCHETYPE\"/" \
        "$SCRIPT_DIR/project-context.tpl.yaml" > "$PROJECT_CONTEXT"
    ok "project-context.yaml créé"
else
    warn "project-context.yaml existe déjà, pas écrasé"
fi

# ─── 6. Générer les configs BMAD ────────────────────────────────────────────
info "Génération des fichiers de configuration..."

# Config mémoire
cat > "$BMAD_DIR/_memory/config.yaml" <<YAML
user_name: "$USER_NAME"
communication_language: "$LANGUAGE"
document_output_language: "$LANGUAGE"
output_folder: "{project-root}/_bmad-output"
YAML

# Shared context par défaut (si pas fourni par l'archétype)
if [[ ! -f "$BMAD_DIR/_memory/shared-context.md" ]]; then
    cat > "$BMAD_DIR/_memory/shared-context.md" <<MD
# Contexte Partagé — $PROJECT_NAME

> Ce fichier est chargé par tous les agents au démarrage.
> Il contient les informations essentielles du projet.

## Projet

- **Nom** : $PROJECT_NAME
- **Type** : À compléter
- **Stack** : À compléter

## Équipe d'Agents Custom

| Agent | Nom | Icône | Domaine |
|-------|-----|-------|---------|
$(ls "$BMAD_DIR/_config/custom/agents/"*.md 2>/dev/null | while read f; do
    name=$(basename "$f" .md)
    echo "| $name | — | — | À compléter |"
done)

## Conventions

- À compléter selon les besoins du projet
MD
fi

# Fichiers mémoire vides
touch "$BMAD_DIR/_memory/decisions-log.md"
touch "$BMAD_DIR/_memory/handoff-log.md"
touch "$BMAD_DIR/_memory/agent-changelog.md"
echo '[]' > "$BMAD_DIR/_memory/memories.json"
touch "$BMAD_DIR/_memory/activity.jsonl"

# Contradiction log
sed "s/{{project_name}}/$PROJECT_NAME/g" \
    "$SCRIPT_DIR/framework/memory/contradiction-log.tpl.md" \
    > "$BMAD_DIR/_memory/contradiction-log.md"

# Session state
cat > "$BMAD_DIR/_memory/session-state.md" <<MD
# État de la dernière session

> Mis à jour automatiquement par les agents en fin de session.

| Champ | Valeur |
|-------|--------|
| Agent | — |
| Date | — |
| Fichiers modifiés | — |
| État du travail | — |
| Prochaine étape | — |
MD

# Créer les fichiers learnings pour chaque agent
for agent_file in "$BMAD_DIR/_config/custom/agents/"*.md; do
    agent_name=$(basename "$agent_file" .md)
    learnings_file="$BMAD_DIR/_memory/agent-learnings/${agent_name}.md"
    if [[ ! -f "$learnings_file" ]]; then
        echo "# Learnings — $agent_name" > "$learnings_file"
        echo "" >> "$learnings_file"
        echo "> Apprentissages accumulés par cet agent." >> "$learnings_file"
    fi
done

ok "Configuration générée"

# ─── 7. Générer le manifest ─────────────────────────────────────────────────
info "Génération du manifest d'agents..."

MANIFEST="$BMAD_DIR/_config/agent-manifest.csv"
echo 'name,displayName,title,icon,role,module,path' > "$MANIFEST"
for agent_file in "$BMAD_DIR/_config/custom/agents/"*.md; do
    agent_name=$(basename "$agent_file" .md)
    echo "\"$agent_name\",\"$agent_name\",\"\",\"\",\"\",\"custom\",\"_bmad/_config/custom/agents/$agent_name.md\"" >> "$MANIFEST"
done

ok "Manifest généré (à compléter avec les détails des agents)"

# ─── 8. Installer les dépendances Python (optionnel) ────────────────────────
if command -v pip3 &>/dev/null; then
    info "Installation des dépendances Python..."
    pip3 install -q -r "$BMAD_DIR/_memory/requirements.txt" 2>/dev/null && \
        ok "Dépendances Python installées" || \
        warn "Installation des dépendances échouée (non bloquant)"
else
    warn "pip3 non trouvé — installez les dépendances manuellement : pip install -r _bmad/_memory/requirements.txt"
fi

# ─── 9. Résumé ──────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🎉 BMAD Custom Kit installé avec succès !${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo "  Prochaines étapes :"
echo "  1. Éditer ${CYAN}project-context.yaml${NC} avec vos infos projet"
echo "  2. Compléter ${CYAN}_bmad/_memory/shared-context.md${NC}"
echo "  3. Personnaliser les agents dans ${CYAN}_bmad/_config/custom/agents/${NC}"
echo "  4. Installer BMAD Framework si pas déjà fait :"
echo "     ${CYAN}npx bmad-install${NC}"
echo ""
echo "  Pour vérifier l'installation :"
echo "     ${CYAN}python3 _bmad/_memory/maintenance.py health-check${NC}"
  echo ""
  echo "  Completion Contract — vérifier votre code :"
  echo "     ${CYAN}bash _bmad/_config/custom/cc-verify.sh${NC}"
  echo ""

  if $AUTO_DETECT && [[ -n "${DETECTED_STACKS:-}" ]]; then
    echo -e "  ${CYAN}Stack(s) détecté(s) : ${GREEN}$DETECTED_STACKS${NC}"
    echo ""
  fi