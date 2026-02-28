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
FORCE=false
MEMORY_BACKEND="auto"

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
  $(basename "$0") session-branch --name "branch-name" [--list|--diff|--merge|--archive|--cherry-pick]
  $(basename "$0") install --archetype TYPE [--force] [--list] [--inspect TYPE]

Options init:
  --name NAME         Nom du projet (requis)
  --user USER         Votre nom (requis)
  --lang LANGUAGE     Langue de communication (défaut: Français)
  --archetype TYPE    Archétype à utiliser: minimal, infra-ops, fix-loop (défaut: minimal)
  --target DIR        Répertoire cible (défaut: répertoire courant)
  --auto              Détecter automatiquement le stack et choisir l'archétype optimal
  --memory BACKEND    Backend mémoire: auto, local, qdrant-local, qdrant-server, ollama,
                        qdrant-docker (génère docker-compose.memory.yml)
  --force             Écraser une installation existante sans demander confirmation
  --help              Afficher cette aide

Options session-branch:
  session-branch --name NAME    Créer une nouvelle branche de session
  session-branch --list         Lister toutes les branches actives
  session-branch --diff B1 B2   Comparer les artefacts de deux branches
  session-branch --merge NAME   Merger une branche vers main
  session-branch --archive NAME Archiver une branche terminée
  session-branch --cherry-pick BRANCH SRC DST  Copier un artefact spécifique vers main

Options install:
  install --archetype TYPE  Installer un archétype dans un projet BMAD existant
  install --list            Lister tous les archétypes disponibles avec leur DNA
  install --inspect TYPE    Inspecter un archétype (agents, traits, contraintes) sans installer
  install --force           Forcer la réinstallation (overwrite fichiers existants)

Archétypes:
  minimal     Meta-agents (Atlas, Sentinel, Mnemo) + 1 agent vierge
  infra-ops   Agents Infrastructure & DevOps complets (10 agents)
  web-app     Agents Full-Stack (Stack, Pixel) + agents stack auto
  fix-loop    Orchestrateur boucle de correction certifiée + workflow 9 phases

Exemples:
  $(basename "$0") --name "Mon API" --user "Alice" --archetype minimal
  $(basename "$0") --name "Infra Prod" --user "Bob" --archetype infra-ops --lang "English"
  $(basename "$0") --name "Mon App" --user "Guilhem" --auto --memory ollama
  $(basename "$0") session-branch --name "explore-graphql"
  $(basename "$0") session-branch --list
  $(basename "$0") session-branch --diff main explore-graphql
  $(basename "$0") install --list
  $(basename "$0") install --archetype infra-ops
  $(basename "$0") install --archetype stack/go --force
  $(basename "$0") install --inspect fix-loop
EOF
    exit 0
}

# ─── Session Branching (BM-16) ───────────────────────────────────────────────
# Gestion des branches de session BMAD
# Usage: bmad-init.sh session-branch [--name|--list|--diff|--merge|--archive|--cherry-pick]
cmd_session_branch() {
    local RUNS_DIR="${TARGET_DIR}/_bmad-output/.runs"
    local action=""
    local branch_name=""
    local branch_b=""
    local src_file=""
    local dst_file=""
    local NOW
    NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    local DATE_SHORT
    DATE_SHORT="$(date +%Y-%m-%d)"

    # Parser les sous-arguments
    shift  # retirer "session-branch"
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --name)       action="create"; branch_name="$2"; shift 2 ;;
            --list)       action="list"; shift ;;
            --diff)       action="diff"; branch_name="$2"; branch_b="${3:-main}"; shift 3 ;;
            --merge)      action="merge"; branch_name="$2"; shift 2 ;;
            --archive)    action="archive"; branch_name="$2"; shift 2 ;;
            --cherry-pick) action="cherry-pick"; branch_name="$2"; src_file="$3"; dst_file="$4"; shift 4 ;;
            *) error "Option inconnue pour session-branch: $1. Utilisez --help." ;;
        esac
    done

    case "$action" in
        create)
            [[ -z "$branch_name" ]] && error "Nom de branche requis : --name nom-branche"
            local branch_dir="${RUNS_DIR}/${branch_name}"
            if [[ -d "$branch_dir" ]] && ! $FORCE; then
                error "La branche '${branch_name}' existe déjà. Utilisez --force pour écraser."
            fi
            mkdir -p "$branch_dir"
            cat > "${branch_dir}/branch.json" << EOF
{
  "branch": "${branch_name}",
  "created_at": "${NOW}",
  "created_by": "bmad-init",
  "purpose": "Session branch created by bmad-init.sh",
  "parent_branch": "main",
  "status": "active"
}
EOF
            ok "Branche de session créée : ${branch_name}"
            info "Outputs isolés dans : ${branch_dir}/"
            info "Référencer dans project-context.yaml : session_branch: ${branch_name}"
            ;;

        list)
            if [[ ! -d "$RUNS_DIR" ]]; then
                info "Aucun run trouvé dans ${RUNS_DIR}/ — pas encore de sessions"
                exit 0
            fi
            echo -e "${CYAN}Branches de session BMAD :${NC}"
            echo ""
            local found=false
            for dir in "${RUNS_DIR}"/*/; do
                [[ -d "$dir" ]] || continue
                local bname
                bname="$(basename "$dir")"
                [[ "$bname" == "archive" ]] && continue
                local bstatus="active"
                local bdate="—"
                if [[ -f "${dir}/branch.json" ]]; then
                    bstatus="$(grep '"status"' "${dir}/branch.json" | sed 's/.*: *"\(.*\)".*/\1/')"
                    bdate="$(grep '"created_at"' "${dir}/branch.json" | sed 's/.*: *"\(.*\)".*/\1/' | cut -c1-10)"
                fi
                local run_count
                run_count="$(find "$dir" -maxdepth 1 -name "state.json" | wc -l | tr -d ' ')"
                echo -e "  ${GREEN}●${NC} ${CYAN}${bname}${NC} — statut: ${bstatus} | créée: ${bdate} | runs: ${run_count}"
                found=true
            done
            $found || info "Aucune branche trouvée"
            ;;

        diff)
            [[ -z "$branch_name" ]] && error "Deux branches requises : --diff branch1 branch2"
            local dir_a="${RUNS_DIR}/${branch_name}"
            local dir_b="${RUNS_DIR}/${branch_b}"
            [[ ! -d "$dir_a" ]] && error "Branche '$branch_name' non trouvée"
            [[ ! -d "$dir_b" ]] && error "Branche '$branch_b' non trouvée"
            echo -e "${CYAN}Diff : ${branch_name} vs ${branch_b}${NC}"
            echo ""
            echo "=== Artefacts dans ${branch_name} (pas dans ${branch_b}) ==="
            comm -23 <(find "$dir_a" -type f | sed "s|${dir_a}/||" | sort) \
                     <(find "$dir_b" -type f | sed "s|${dir_b}/||" | sort) || true
            echo ""
            echo "=== Artefacts dans ${branch_b} (pas dans ${branch_name}) ==="
            comm -13 <(find "$dir_a" -type f | sed "s|${dir_a}/||" | sort) \
                     <(find "$dir_b" -type f | sed "s|${dir_b}/||" | sort) || true
            ;;

        merge)
            [[ -z "$branch_name" ]] && error "Nom de branche requis pour le merge"
            local src_dir="${RUNS_DIR}/${branch_name}"
            local dst_dir="${RUNS_DIR}/main"
            [[ ! -d "$src_dir" ]] && error "Branche '$branch_name' non trouvée"
            mkdir -p "$dst_dir"
            info "Merge de '${branch_name}' → main..."
            cp -r "${src_dir}/." "${dst_dir}/"
            # Mettre à jour le statut
            [[ -f "${src_dir}/branch.json" ]] && \
                sed -i 's/"status": "active"/"status": "merged"/' "${src_dir}/branch.json"
            ok "Branche '${branch_name}' mergée dans main"
            warn "Vérifiez les conflits manuellement dans ${dst_dir}/"
            ;;

        archive)
            [[ -z "$branch_name" ]] && error "Nom de branche requis pour l'archivage"
            local arch_src="${RUNS_DIR}/${branch_name}"
            local arch_dst="${RUNS_DIR}/archive/${branch_name}-$(date +%Y%m%d)"
            [[ ! -d "$arch_src" ]] && error "Branche '$branch_name' non trouvée"
            mkdir -p "${RUNS_DIR}/archive"
            mv "$arch_src" "$arch_dst"
            ok "Branche '${branch_name}' archivée dans archive/$(basename "$arch_dst")"
            ;;

        cherry-pick)
            [[ -z "$branch_name" || -z "$src_file" || -z "$dst_file" ]] && \
                error "Usage: session-branch --cherry-pick branch source-file destination-file"
            [[ ! -f "$src_file" ]] && error "Fichier source non trouvé: $src_file"
            mkdir -p "$(dirname "$dst_file")"
            cp "$src_file" "$dst_file"
            ok "Cherry-pick : $src_file → $dst_file"
            ;;

        "")
            error "Action requise. Exemples: --name, --list, --diff, --merge, --archive"
            ;;
    esac
    exit 0
}

# ─── Archetype Registry Install (BM-21) ──────────────────────────────────────────────────
# Usage: bmad-init.sh install [--archetype|--list|--inspect]
cmd_install() {
    shift  # retirer "install"
    local action="install"
    local archetype_id=""
    local target_bmad=""
    local INSTALL_FORCE=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --archetype)  action="install"; archetype_id="$2"; shift 2 ;;
            --list)       action="list"; shift ;;
            --inspect)    action="inspect"; archetype_id="$2"; shift 2 ;;
            --force)      INSTALL_FORCE=true; shift ;;
            *) error "Option inconnue pour install: $1. Utilisez --help." ;;
        esac
    done

    # Localiser le projet BMAD le plus proche
    target_bmad="$(pwd)/_bmad"
    if [[ ! -d "$target_bmad/_config/custom" ]]; then
        error "Aucun projet BMAD trouvé dans $(pwd). Lancez d'abord bmad-init.sh --name ... --user ..."
    fi

    case "$action" in
        list)
            echo -e "${CYAN}Archétypes BMAD disponibles :${NC}"
            echo ""
            # Parcourir les répertoires d'archétypes
            local arch_base="$SCRIPT_DIR/archetypes"
            for dir in "$arch_base"/*/; do
                [[ -d "$dir" ]] || continue
                local aid
                aid="$(basename "$dir")"
                local dna="${dir}archetype.dna.yaml"
                if [[ -f "$dna" ]]; then
                    local aname
                    aname="$(grep '^name:' "$dna" | head -1 | sed 's/name: *//;s/"//g')"
                    local adesc
                    adesc="$(grep '^description:' "$dna" | head -1 | sed 's/description: *//;s/"//g' | cut -c1-80)"
                    echo -e "  ${GREEN}●${NC} ${CYAN}${aid}${NC} — ${aname}"
                    echo -e "      ${adesc}"
                else
                    echo -e "  ${YELLOW}◦${NC} ${aid} (pas de DNA déclarée)"
                fi
                # Stack sub-archetypes
                if [[ -d "${dir}agents/" ]]; then
                    for subdir in "${dir}agents/"*.md; do
                        [[ -f "$subdir" ]] || continue
                        local sname
                        sname="$(basename "$subdir" .md | sed 's/-expert$//')"
                        echo -e "    ${BLUE}└ stack/${sname}${NC}"
                    done
                fi
            done
            echo ""
            info "Pour installer : $(basename "$0") install --archetype <id>"
            ;;

        inspect)
            [[ -z "$archetype_id" ]] && error "ID d'archétype requis : --inspect <id>"
            # Gestion stack/{lang}
            if [[ "$archetype_id" == stack/* ]]; then
                local lang="${archetype_id#stack/}"
                local sa="$SCRIPT_DIR/archetypes/stack/agents/${lang}-expert.md"
                [[ ! -f "$sa" ]] && error "Agent stack '$lang' non trouvé. Valides : $(ls "$SCRIPT_DIR/archetypes/stack/agents/" | sed 's/-expert\.md//' | tr '\n' ' ')"
                echo -e "${CYAN}Agent stack : ${archetype_id}${NC}"
                cat "$sa"
                exit 0
            fi
            local arch_dir="$SCRIPT_DIR/archetypes/${archetype_id}"
            [[ ! -d "$arch_dir" ]] && error "Archétype '$archetype_id' non trouvé dans archetypes/"
            local dna="${arch_dir}/archetype.dna.yaml"
            echo -e "${CYAN}Inspection de l'archétype : ${archetype_id}${NC}"
            echo ""
            if [[ -f "$dna" ]]; then
                cat "$dna"
            else
                warn "Pas de fichier archetype.dna.yaml pour $archetype_id"
                echo "Agents disponibles :"
                ls "${arch_dir}/agents/" 2>/dev/null | sed 's/^/  • /'
            fi
            ;;

        install)
            [[ -z "$archetype_id" ]] && error "ID d'archétype requis : --archetype <id>"

            # ── Gestion sous-archétypes stack : stack/go → archetypes/stack/agents/go-expert.md ──
            if [[ "$archetype_id" == stack/* ]]; then
                local lang="${archetype_id#stack/}"
                local sa="$SCRIPT_DIR/archetypes/stack/agents/${lang}-expert.md"
                # Fallback : chercher par glob si le nom exact n'existe pas
                if [[ ! -f "$sa" ]]; then
                    local candidate
                    candidate="$(find "$SCRIPT_DIR/archetypes/stack/agents/" -name "${lang}*.md" | head -1)"
                    [[ -n "$candidate" ]] && sa="$candidate"
                fi
                [[ ! -f "$sa" ]] && error "Agent stack '$lang' non trouvé. Valides : $(ls "$SCRIPT_DIR/archetypes/stack/agents/" | sed 's/-expert\.md//' | tr '\n' ' ')"
                local fname
                fname="$(basename "$sa")"
                local agents_dst="$target_bmad/_config/custom/agents"
                if [[ -f "${agents_dst}/${fname}" ]] && ! $INSTALL_FORCE; then
                    warn "${fname} existe déjà (utilisez --force pour écraser)"
                else
                    cp "$sa" "${agents_dst}/"
                    ok "Agent stack installé : ${fname}"
                fi
                local installed_log="$target_bmad/_config/installed-archetypes.yaml"
                [[ ! -f "$installed_log" ]] && { echo "# Auto-généré par bmad-init.sh" > "$installed_log"; echo "installed:" >> "$installed_log"; }
                cat >> "$installed_log" << STACKEOF
  - id: ${archetype_id}
    installed_at: "$(date +%Y-%m-%d)"
    force: ${INSTALL_FORCE}
STACKEOF
                ok "Stack '${archetype_id}' installé avec succès"
                info "Activer l'agent dans Copilot : ouvrir ${agents_dst}/${fname}"
                exit 0
            fi

            local arch_dir="$SCRIPT_DIR/archetypes/${archetype_id}"
            [[ ! -d "$arch_dir" ]] && error "Archétype '$archetype_id' non trouvé dans archetypes/"

            local agents_dst="$target_bmad/_config/custom/agents"
            local workflows_dst="$target_bmad/_config/custom/workflows"

            info "Installation de l'archétype '${archetype_id}'..."

            # Copier les agents
            if [[ -d "${arch_dir}/agents/" ]]; then
                local count=0
                for agent_file in "${arch_dir}/agents/"*.md; do
                    [[ -f "$agent_file" ]] || continue
                    local fname
                    fname="$(basename "$agent_file")"
                    if [[ -f "${agents_dst}/${fname}" ]] && ! $INSTALL_FORCE; then
                        warn "  ${fname} existe déjà (utilisez --force pour écraser)"
                    else
                        cp "$agent_file" "${agents_dst}/"
                        ok "  Agent installé : ${fname}"
                        (( count++ )) || true
                    fi
                done
                [[ $count -eq 0 ]] || ok "${count} agent(s) installé(s)"
            fi

            # Copier les workflows
            if [[ -d "${arch_dir}/workflows/" ]]; then
                mkdir -p "$workflows_dst"
                cp -r "${arch_dir}/workflows/"* "${workflows_dst}/" 2>/dev/null || true
                ok "  Workflows installés"
            fi

            # Fusionner le shared-context si existant
            if [[ -f "${arch_dir}/shared-context.tpl.md" ]]; then
                local sc_dst="$target_bmad/_memory/shared-context.md"
                if [[ ! -f "$sc_dst" ]]; then
                    cp "${arch_dir}/shared-context.tpl.md" "$sc_dst"
                    ok "  shared-context.md créé"
                else
                    echo "" >> "$sc_dst"
                    echo "<!-- Ajout archétype ${archetype_id} : $(date +%Y-%m-%d) -->" >> "$sc_dst"
                    cat "${arch_dir}/shared-context.tpl.md" >> "$sc_dst"
                    ok "  shared-context.md enrichi avec le contexte ${archetype_id}"
                fi
            fi

            # Enregistrer dans installed-archetypes.yaml
            local installed_log="$target_bmad/_config/installed-archetypes.yaml"
            if [[ ! -f "$installed_log" ]]; then
                echo "# Auto-généré par bmad-init.sh" > "$installed_log"
                echo "installed:" >> "$installed_log"
            fi
            cat >> "$installed_log" << YAMLEOF
  - id: ${archetype_id}
    installed_at: "$(date +%Y-%m-%d)"
    force: ${INSTALL_FORCE}
YAMLEOF
            ok "Archétype '${archetype_id}' installé avec succès"
            info "Agents disponibles dans : ${agents_dst}/"
            ;;
    esac
    exit 0
}

# ─── Dispatch des sous-commandes ──────────────────────────────────────────────────
if [[ "${1:-}" == "session-branch" ]]; then
    cmd_session_branch "$@"
fi
if [[ "${1:-}" == "install" ]]; then
    cmd_install "$@"
fi

# ─── Parsing arguments ──────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --name)     PROJECT_NAME="$2"; shift 2 ;;
        --user)     USER_NAME="$2"; shift 2 ;;
        --lang)     LANGUAGE="$2"; shift 2 ;;
        --archetype) ARCHETYPE="$2"; shift 2 ;;
        --target)   TARGET_DIR="$2"; shift 2 ;;
        --auto)     AUTO_DETECT=true; shift ;;
        --memory)   MEMORY_BACKEND="$2"; shift 2 ;;
        --force)    FORCE=true; shift ;;
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
    # web-app si frontend + (go|node|python)
    elif echo "$stacks" | grep -qE 'frontend' && echo "$stacks" | grep -qE '(go|node|python)'; then
        echo "web-app"
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

# Auto-détection du backend mémoire si "auto"
if [[ "$MEMORY_BACKEND" == "auto" ]]; then
    info "Détection du backend mémoire..."
    MEMORY_BACKEND=$(detect_memory_backend)
    ok "Backend mémoire détecté : $MEMORY_BACKEND"
fi

ARCHETYPE_DIR="$SCRIPT_DIR/archetypes/$ARCHETYPE"
[[ ! -d "$ARCHETYPE_DIR" ]] && error "Archétype '$ARCHETYPE' non trouvé. Disponibles: $(ls "$SCRIPT_DIR/archetypes/")"

# ─── Vérification cible ─────────────────────────────────────────────────────
BMAD_DIR="$TARGET_DIR/_bmad"
if [[ -d "$BMAD_DIR/_config/custom" ]]; then
    if $FORCE; then
        warn "--force : écrasement de l'installation existante dans $TARGET_DIR"
    else
        warn "Un dossier _bmad/custom existe déjà dans $TARGET_DIR"
        read -p "Continuer et écraser ? (y/N) " -n 1 -r
        echo
        [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
    fi
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
echo -e "  Mémoire:    ${GREEN}$MEMORY_BACKEND${NC}"
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

# Backend memory — copier les backends/
mkdir -p "$BMAD_DIR/_memory/backends"
cp -r "$SCRIPT_DIR/framework/memory/backends/"* "$BMAD_DIR/_memory/backends/"

# Choisir le bon requirements selon le backend
case "$MEMORY_BACKEND" in
    ollama)          REQS_SRC="$SCRIPT_DIR/framework/memory/requirements/requirements-ollama.txt" ;;
    qdrant-*|semantic) REQS_SRC="$SCRIPT_DIR/framework/memory/requirements/requirements-qdrant.txt" ;;
    *)               REQS_SRC="$SCRIPT_DIR/framework/memory/requirements/requirements-minimal.txt" ;;
esac
cp "${REQS_SRC:-$SCRIPT_DIR/framework/memory/requirements/requirements-minimal.txt}" "$BMAD_DIR/_memory/requirements.txt"

# Copier aussi le requirements original complet (référence)
cp "$SCRIPT_DIR/framework/memory/requirements.txt" "$BMAD_DIR/_memory/requirements-full.txt"

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
# ─── 4c. Déployer les agents features selon le backend mémoire ────────────────────
deploy_feature_agents "$MEMORY_BACKEND" "$BMAD_DIR/_config/custom/agents"
# ─── 5. Générer project-context.yaml ────────────────────────────────────────
info "Génération de project-context.yaml..."

PROJECT_CONTEXT="$TARGET_DIR/project-context.yaml"
if [[ ! -f "$PROJECT_CONTEXT" ]]; then
    sed -e "s/\"Mon Projet\"/\"$PROJECT_NAME\"/" \
        -e "s/\"Votre Nom\"/\"$USER_NAME\"/" \
        -e "s/\"Français\"/\"$LANGUAGE\"/" \
        -e "s/\"minimal\"/\"$ARCHETYPE\"/" \
        -e "s/backend: \"auto\"/backend: \"$MEMORY_BACKEND\"/" \
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

# ─── Failure Museum (BM-03) ─────────────────────────────────────────────────
if [[ ! -f "$BMAD_DIR/_memory/failure-museum.md" ]]; then
    sed -e "s/{{project_name}}/$PROJECT_NAME/g" \
        -e "s/{{init_date}}/$(date +%Y-%m-%d)/g" \
        "$SCRIPT_DIR/framework/memory/failure-museum.tpl.md" \
        > "$BMAD_DIR/_memory/failure-museum.md"
fi

# ─── Session Branching — structure .runs/ (BM-16) ──────────────────────────
info "Initialisation de la structure de sessions..."
RUNS_DIR="$TARGET_DIR/_bmad-output/.runs"
mkdir -p "$RUNS_DIR/main"
cat > "$RUNS_DIR/main/branch.json" << JSONEOF
{
  "branch": "main",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "created_by": "bmad-init",
  "purpose": "Branche de session principale",
  "parent_branch": null,
  "status": "active"
}
JSONEOF

# ─── Team Context Directories (BM-17) ───────────────────────────────────────
mkdir -p "$TARGET_DIR/_bmad-output/team-vision"
mkdir -p "$TARGET_DIR/_bmad-output/team-build/stories"
mkdir -p "$TARGET_DIR/_bmad-output/team-build/test-reports"
mkdir -p "$TARGET_DIR/_bmad-output/team-ops"
mkdir -p "$TARGET_DIR/_bmad-output/contracts"
ok "Structure de sessions et teams créée"

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

# ─── 8. Installer le git pre-commit hook (CC) ──────────────────────────────
GIT_DIR="$(git -C "$TARGET_DIR" rev-parse --git-dir 2>/dev/null || true)"
if [[ -n "$GIT_DIR" ]]; then
    HOOK_SRC="$SCRIPT_DIR/framework/hooks/pre-commit-cc.sh"
    HOOK_DST="$GIT_DIR/hooks/pre-commit"
    if [[ -f "$HOOK_SRC" ]]; then
        if [[ -f "$HOOK_DST" ]] && grep -q 'BMAD Completion Contract' "$HOOK_DST" 2>/dev/null; then
            ok "Pre-commit hook CC déjà installé"
        elif [[ -f "$HOOK_DST" ]] && ! $FORCE; then
            warn "Un pre-commit hook non-BMAD existe déjà — utilisez --force pour le chaîner"
        elif [[ -f "$HOOK_DST" ]]; then
            # Chaîner avec le hook existant
            cp "$HOOK_DST" "${HOOK_DST}.pre-bmad"
            printf '#!/usr/bin/env bash\nbash "$(git rev-parse --git-dir)/hooks/pre-commit.pre-bmad" || exit 1\nbash "%s" || exit 1\n' "$HOOK_SRC" > "$HOOK_DST"
            chmod +x "$HOOK_DST"
            ok "Pre-commit hook chaîné (existant + CC)"
        else
            cp "$HOOK_SRC" "$HOOK_DST"
            chmod +x "$HOOK_DST"
            ok "Pre-commit hook CC installé"
        fi
    fi
else
    info "Pas de dépôt git détecté — hook pre-commit non installé"
fi

# ─── 9. Générer docker-compose.memory.yml si backend = qdrant-docker ─────────────────
if [[ "$MEMORY_BACKEND" == "qdrant-docker" ]]; then
    DOCKER_MEM="$TARGET_DIR/docker-compose.memory.yml"
    if [[ ! -f "$DOCKER_MEM" || "$FORCE" == "true" ]]; then
        cp "$SCRIPT_DIR/framework/memory/docker-compose.memory.tpl.yml" "$DOCKER_MEM"
        ok "docker-compose.memory.yml généré — lancer : docker compose -f docker-compose.memory.yml up -d"
    fi
fi

# ─── 10. Installer les dépendances Python (optionnel) ────────────────────────────────
if command -v pip3 &>/dev/null; then
    info "Installation des dépendances Python (backend: $MEMORY_BACKEND)..."
    pip3 install -q -r "$BMAD_DIR/_memory/requirements.txt" 2>/dev/null && \
        ok "Dépendances Python installées" || \
        warn "Installation des dépendances échouée (non bloquant)"
else
    warn "pip3 non trouvé — installez les dépendances manuellement : pip install -r _bmad/_memory/requirements.txt"
fi

# ─── 11. Initialiser les collections Qdrant structurées (BM-22) ─────────────
if command -v python3 &>/dev/null && [[ -f "$BMAD_DIR/_memory/mem0-bridge.py" ]]; then
    info "Initialisation des collections Qdrant structurées..."
    python3 "$BMAD_DIR/_memory/mem0-bridge.py" init-collections 2>/dev/null && true
fi

# ─── 12. Résumé ──────────────────────────────────────────────────────────────
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