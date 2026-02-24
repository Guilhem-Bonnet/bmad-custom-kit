#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# BMAD Completion Contract Verifier — cc-verify.sh
# ═══════════════════════════════════════════════════════════════════════════════
#
# Détecte automatiquement le(s) stack(s) du projet et lance les vérifications
# correspondantes. Retourne 0 si tout passe, 1 si au moins une vérification échoue.
#
# Usage:
#   bash cc-verify.sh                    # Depuis la racine du projet
#   bash cc-verify.sh --stack go         # Forcer un stack spécifique
#   bash cc-verify.sh --changed-only     # Vérifier seulement les stacks des fichiers modifiés (git diff)
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# ─── Couleurs ─────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

pass() { echo -e "${GREEN}✅ CC PASS${NC} — $*"; }
fail() { echo -e "${RED}🔴 CC FAIL${NC} — $*"; }
info() { echo -e "${CYAN}▶${NC} $*"; }
warn() { echo -e "${YELLOW}⚠️  $*${NC}"; }

# ─── Variables ────────────────────────────────────────────────────────────────
ROOT_DIR="${1:-$(pwd)}"
FORCE_STACK="${CC_STACK:-}"
CHANGED_ONLY=false
OVERALL_PASS=true
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
STACKS_RUN=()

# ─── Parser args ──────────────────────────────────────────────────────────────
for arg in "$@"; do
  case $arg in
    --stack=*) FORCE_STACK="${arg#*=}" ;;
    --stack)   shift; FORCE_STACK="$1" ;;
    --changed-only) CHANGED_ONLY=true ;;
  esac
done

cd "$ROOT_DIR"

echo ""
echo -e "${BOLD}${CYAN}🔒 BMAD Completion Contract Verifier${NC}"
echo -e "${CYAN}────────────────────────────────────────${NC}"
echo -e "  Projet : ${GREEN}$(basename "$ROOT_DIR")${NC}"
echo -e "  Date   : ${GREEN}$TIMESTAMP${NC}"
echo ""

# ─── Détection des fichiers modifiés (si --changed-only) ──────────────────────
changed_files=""
if $CHANGED_ONLY && command -v git &>/dev/null && git rev-parse --git-dir &>/dev/null 2>&1; then
  changed_files=$(git diff --name-only HEAD 2>/dev/null || true)
  changed_files+=$'\n'$(git diff --name-only --cached 2>/dev/null || true)
fi

has_changed() {
  local pattern="$1"
  if $CHANGED_ONLY && [[ -n "$changed_files" ]]; then
    echo "$changed_files" | grep -q "$pattern"
  else
    # Sans --changed-only, toujours true si les fichiers existent dans le projet
    return 0
  fi
}

# ─── Fonctions de vérification par stack ──────────────────────────────────────

verify_go() {
  [[ -n "$FORCE_STACK" && "$FORCE_STACK" != "go" ]] && return 0
  [[ ! -f "go.mod" ]] && return 0
  has_changed "\.go$" || return 0

  echo -e "${BOLD}▶ Stack : Go${NC}"
  STACKS_RUN+=("go")
  local ok=true

  info "go build ./..."
  if go build ./... 2>&1; then
    echo -e "  ${GREEN}→ build OK${NC}"
  else
    echo -e "  ${RED}→ build FAILED${NC}"; ok=false
  fi

  info "go vet ./..."
  if go vet ./... 2>&1; then
    echo -e "  ${GREEN}→ vet OK${NC}"
  else
    echo -e "  ${RED}→ vet FAILED${NC}"; ok=false
  fi

  info "go test ./..."
  local test_output
  if test_output=$(go test ./... 2>&1); then
    local count; count=$(echo "$test_output" | grep -c "^ok" || true)
    echo -e "  ${GREEN}→ tests OK ($count packages)${NC}"
  else
    echo "$test_output" | tail -20
    echo -e "  ${RED}→ tests FAILED${NC}"; ok=false
  fi

  $ok || OVERALL_PASS=false
  echo ""
}

verify_typescript() {
  [[ -n "$FORCE_STACK" && "$FORCE_STACK" != "ts" && "$FORCE_STACK" != "typescript" ]] && return 0
  [[ ! -f "package.json" ]] && return 0
  has_changed "\.(ts|tsx)$" || return 0

  echo -e "${BOLD}▶ Stack : TypeScript / React${NC}"
  STACKS_RUN+=("typescript")
  local ok=true

  # Détecter le package manager
  local pm="npm"
  [[ -f "pnpm-lock.yaml" ]] && pm="pnpm"
  [[ -f "yarn.lock" ]] && pm="yarn"
  [[ -f "bun.lockb" ]] && pm="bun"

  # Type check
  if [[ -f "tsconfig.json" ]]; then
    info "tsc --noEmit"
    if $pm exec tsc --noEmit 2>&1; then
      echo -e "  ${GREEN}→ types OK${NC}"
    else
      echo -e "  ${RED}→ type errors${NC}"; ok=false
    fi
  fi

  # Tests
  local test_cmd=""
  if [[ -f "vitest.config.ts" ]] || [[ -f "vitest.config.js" ]]; then
    test_cmd="$pm exec vitest run"
  elif grep -q '"test"' package.json 2>/dev/null; then
    test_cmd="$pm test -- --run 2>/dev/null || $pm test"
  fi

  if [[ -n "$test_cmd" ]]; then
    info "$test_cmd"
    if eval "$test_cmd" 2>&1; then
      echo -e "  ${GREEN}→ tests OK${NC}"
    else
      echo -e "  ${RED}→ tests FAILED${NC}"; ok=false
    fi
  fi

  $ok || OVERALL_PASS=false
  echo ""
}

verify_terraform() {
  [[ -n "$FORCE_STACK" && "$FORCE_STACK" != "terraform" && "$FORCE_STACK" != "tf" ]] && return 0
  local tf_files; tf_files=$(find . -maxdepth 4 -name "*.tf" -not -path "*/.terraform/*" 2>/dev/null | head -1)
  [[ -z "$tf_files" ]] && return 0
  has_changed "\.tf$" || return 0

  echo -e "${BOLD}▶ Stack : Terraform${NC}"
  STACKS_RUN+=("terraform")
  local ok=true

  # Trouver le répertoire terraform racine
  local tf_dir
  tf_dir=$(find . -maxdepth 3 -name "*.tf" -not -path "*/.terraform/*" -exec dirname {} \; | sort -u | head -1)

  info "terraform validate ($tf_dir)"
  if (cd "$tf_dir" && terraform validate 2>&1); then
    echo -e "  ${GREEN}→ validate OK${NC}"
  else
    echo -e "  ${RED}→ validate FAILED${NC}"; ok=false
  fi

  info "terraform fmt -check (recursive)"
  if terraform fmt -check -recursive . 2>&1; then
    echo -e "  ${GREEN}→ fmt OK${NC}"
  else
    echo -e "  ${YELLOW}→ fmt: fichiers à reformater (run: terraform fmt -recursive .)${NC}"
    # Non-bloquant (style seulement)
  fi

  if command -v tflint &>/dev/null; then
    info "tflint"
    if (cd "$tf_dir" && tflint 2>&1); then
      echo -e "  ${GREEN}→ tflint OK${NC}"
    else
      echo -e "  ${RED}→ tflint FAILED${NC}"; ok=false
    fi
  fi

  $ok || OVERALL_PASS=false
  echo ""
}

verify_ansible() {
  [[ -n "$FORCE_STACK" && "$FORCE_STACK" != "ansible" ]] && return 0
  [[ ! -d "ansible" ]] && ! ls playbook*.yml &>/dev/null 2>&1 && return 0
  has_changed "(ansible|playbook)" || return 0

  echo -e "${BOLD}▶ Stack : Ansible${NC}"
  STACKS_RUN+=("ansible")
  local ok=true

  if command -v ansible-lint &>/dev/null; then
    info "ansible-lint"
    if ansible-lint 2>&1; then
      echo -e "  ${GREEN}→ ansible-lint OK${NC}"
    else
      echo -e "  ${RED}→ ansible-lint FAILED${NC}"; ok=false
    fi
  fi

  if command -v yamllint &>/dev/null; then
    info "yamllint ansible/"
    if yamllint ansible/ 2>&1 || yamllint . 2>&1; then
      echo -e "  ${GREEN}→ yamllint OK${NC}"
    else
      echo -e "  ${RED}→ yamllint FAILED${NC}"; ok=false
    fi
  fi

  $ok || OVERALL_PASS=false
  echo ""
}

verify_python() {
  [[ -n "$FORCE_STACK" && "$FORCE_STACK" != "python" && "$FORCE_STACK" != "py" ]] && return 0
  [[ ! -f "requirements.txt" ]] && [[ ! -f "pyproject.toml" ]] && [[ ! -f "setup.py" ]] && return 0
  has_changed "\.py$" || return 0

  echo -e "${BOLD}▶ Stack : Python${NC}"
  STACKS_RUN+=("python")
  local ok=true

  if command -v pytest &>/dev/null; then
    info "pytest"
    if pytest --tb=short 2>&1; then
      echo -e "  ${GREEN}→ pytest OK${NC}"
    else
      echo -e "  ${RED}→ pytest FAILED${NC}"; ok=false
    fi
  fi

  if command -v ruff &>/dev/null; then
    info "ruff check ."
    if ruff check . 2>&1; then
      echo -e "  ${GREEN}→ ruff OK${NC}"
    else
      echo -e "  ${YELLOW}→ ruff: warnings (voir ci-dessus)${NC}"
    fi
  fi

  if command -v mypy &>/dev/null; then
    info "mypy . (strict off)"
    if mypy . --ignore-missing-imports 2>&1; then
      echo -e "  ${GREEN}→ mypy OK${NC}"
    else
      echo -e "  ${YELLOW}→ mypy: warnings (non-bloquant)${NC}"
    fi
  fi

  $ok || OVERALL_PASS=false
  echo ""
}

verify_docker() {
  [[ -n "$FORCE_STACK" && "$FORCE_STACK" != "docker" ]] && return 0
  [[ ! -f "Dockerfile" ]] && ! ls docker-compose*.yml &>/dev/null 2>&1 && return 0
  has_changed "(Dockerfile|docker-compose)" || return 0

  echo -e "${BOLD}▶ Stack : Docker${NC}"
  STACKS_RUN+=("docker")
  local ok=true

  if [[ -f "docker-compose.yml" ]] || [[ -f "docker-compose.yaml" ]]; then
    info "docker compose config"
    if docker compose config 2>&1 >/dev/null; then
      echo -e "  ${GREEN}→ compose config OK${NC}"
    else
      echo -e "  ${RED}→ compose config FAILED${NC}"; ok=false
    fi
  fi

  if [[ -f "Dockerfile" ]]; then
    info "docker build --check ."
    if docker build --check . 2>&1 || docker build --dry-run . 2>&1; then
      echo -e "  ${GREEN}→ Dockerfile syntax OK${NC}"
    else
      warn "docker build --check non supporté sur cette version, skipping"
    fi
  fi

  $ok || OVERALL_PASS=false
  echo ""
}

verify_kubernetes() {
  [[ -n "$FORCE_STACK" && "$FORCE_STACK" != "k8s" && "$FORCE_STACK" != "kubernetes" ]] && return 0
  [[ ! -d "k8s" ]] && return 0
  has_changed "(k8s/|kind:)" || return 0

  echo -e "${BOLD}▶ Stack : Kubernetes${NC}"
  STACKS_RUN+=("kubernetes")
  local ok=true

  if command -v kubectl &>/dev/null; then
    info "kubectl apply --dry-run=client -f k8s/"
    if kubectl apply --dry-run=client -f k8s/ 2>&1; then
      echo -e "  ${GREEN}→ k8s manifests OK${NC}"
    else
      echo -e "  ${RED}→ k8s manifests FAILED${NC}"; ok=false
    fi
  fi

  if command -v kubeval &>/dev/null; then
    info "kubeval k8s/*.yaml"
    if kubeval k8s/*.yaml 2>&1; then
      echo -e "  ${GREEN}→ kubeval OK${NC}"
    else
      echo -e "  ${RED}→ kubeval FAILED${NC}"; ok=false
    fi
  fi

  $ok || OVERALL_PASS=false
  echo ""
}

verify_shell() {
  [[ -n "$FORCE_STACK" && "$FORCE_STACK" != "shell" && "$FORCE_STACK" != "sh" ]] && return 0
  has_changed "\.sh$" || return 0
  ls ./*.sh &>/dev/null 2>&1 || return 0

  echo -e "${BOLD}▶ Stack : Shell${NC}"
  STACKS_RUN+=("shell")
  local ok=true

  if command -v shellcheck &>/dev/null; then
    info "shellcheck *.sh"
    if shellcheck ./*.sh 2>&1; then
      echo -e "  ${GREEN}→ shellcheck OK${NC}"
    else
      echo -e "  ${YELLOW}→ shellcheck: warnings (voir ci-dessus)${NC}"
    fi
  fi

  $ok || OVERALL_PASS=false
  echo ""
}

# ─── Lancer toutes les vérifications ──────────────────────────────────────────
if [[ -n "$FORCE_STACK" ]]; then
  case "$FORCE_STACK" in
    go)                    verify_go ;;
    ts|typescript|react)   verify_typescript ;;
    terraform|tf)          verify_terraform ;;
    ansible)               verify_ansible ;;
    python|py)             verify_python ;;
    docker)                verify_docker ;;
    k8s|kubernetes)        verify_kubernetes ;;
    shell|sh)              verify_shell ;;
    *) warn "Stack '$FORCE_STACK' non reconnu. Stacks supportés: go, ts, terraform, ansible, python, docker, k8s, shell" ;;
  esac
else
  verify_go
  verify_typescript
  verify_terraform
  verify_ansible
  verify_python
  verify_docker
  verify_kubernetes
  verify_shell
fi

# ─── Résultat final ───────────────────────────────────────────────────────────
echo -e "${CYAN}────────────────────────────────────────${NC}"

if [[ ${#STACKS_RUN[@]} -eq 0 ]]; then
  echo -e "${YELLOW}⚠️  Aucun stack détecté — vérification non requise (doc-only ?)${NC}"
  exit 0
fi

stacks_str=$(printf ", %s" "${STACKS_RUN[@]}"); stacks_str="${stacks_str:2}"

if $OVERALL_PASS; then
  echo ""
  echo -e "${GREEN}${BOLD}✅ CC PASS — [$stacks_str] — $TIMESTAMP${NC}"
  echo ""
  exit 0
else
  echo ""
  echo -e "${RED}${BOLD}🔴 CC FAIL — [$stacks_str] — $TIMESTAMP${NC}"
  echo -e "${RED}  Corriger les erreurs ci-dessus avant de marquer la tâche terminée.${NC}"
  echo ""
  exit 1
fi
