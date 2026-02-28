# BMAD Custom Kit

> Toolkit pour créer et gérer un écosystème d'agents IA spécialisés par projet — teams Enterprise, personas, mémoire sémantique, workflows et qualité automatisée.

## Qu'est-ce que c'est ?

BMAD Custom Kit est un **starter kit** pour déployer une ou plusieurs équipes d'agents IA spécialisés dans n'importe quel projet.  
Chaque agent a une persona forte, un domaine d'expertise précis, et s'inscrit dans une **team avec workflow de livraison complet** — comme dans une vraie entreprise.

**Ce que vous obtenez :**
- 🏢 **Team of Teams** — Team Vision, Team Build, Team Ops avec Delivery Contracts inter-teams
- 🤖 **Agents spécialisés** — personas avec domaine, style de communication et principes
- 🧠 **Mémoire persistante** — recherche sémantique (Qdrant) + fallback JSON, consolidation automatique
- 📋 **Protocole d'activation** — chaque agent suit un workflow standardisé (health-check, inbox, consolidation)
- 🔒 **Completion Contract (CC)** — `cc-verify.sh` détecte le stack et vérifie (build, tests, lint) avant tout "terminé"
- 🔀 **Plan/Act Mode** — switch explicite entre planification pure et exécution autonome
- 🧠 **Extended Thinking** — délibération profonde [THINK] pour les décisions critiques
- 🔄 **Modal Team Engine** — `--auto` détecte le stack et déploie les bons agents
- 🌿 **Session Branching** — branches isolées pour explorer plusieurs approches en parallèle
- 🪃 **Boomerang Orchestration** — orchestrateur (SM) qui délègue + récupère les résultats
- 📜 **Delivery Contracts** — artefacts contractuels inter-teams (aucun handoff sans contrat signé)
- 🏛️ **Failure Museum** — mémoire collective des erreurs pour ne pas les répéter
- 🔌 **MCP Server** — expose BMAD comme server MCP local (cross-IDE : Cursor, Cline, Claude Desktop)
- 🎯 **Prompt Skills Library** — prompts réutilisables par team dans `.github/prompts/{team}/`
- ⚡ **Qualité automatisée** — détection contradictions, consolidation learnings, drift check
- 🔁 **Self-Improvement Loop** — `sil-collect.sh` analyse les patterns d'échec et Sentinel améliore le framework
- 🧭 **Context Budget Guard** — mesure précise du budget LLM consommé par chaque agent avant la première question
- 🧬 **DNA Evolution Engine** — fait évoluer `archetype.dna.yaml` depuis l'usage réel du projet (BMAD_TRACE)
- 🔨 **Agent Forge** — génère des squelettes d'agents depuis une description textuelle ou les lacunes détectées
- 📊 **Agent Bench** — mesure les scores de performance des agents et produit un plan d'amélioration
- 🌙 **Dream Mode** — consolidation hors-session : croise mémoire, trace, decisions et failure museum pour produire des insights émergents
- 🏛️ **Adversarial Consensus** — protocole BFT simplifié pour les décisions critiques : 3 votants + 1 avocat du diable

## Quick Start

```bash
# 1. Cloner le kit
git clone https://github.com/Guilhem-Bonnet/bmad-custom-kit.git

# 2. Initialiser dans votre projet (manuel)
cd votre-projet/
bash /chemin/vers/bmad-custom-kit/bmad-init.sh \
  --name "Mon Projet" \
  --user "Votre Nom" \
  --lang "Français" \
  --archetype infra-ops

# 2. OU initialiser en mode auto (Modal Team Engine)
# détecte le stack automatiquement → déploie les bons agents
bash /chemin/vers/bmad-custom-kit/bmad-init.sh \
  --name "Mon Projet" \
  --user "Votre Nom" \
  --auto

# 3. Vérifier votre code (Completion Contract)
bash _bmad/_config/custom/cc-verify.sh

# 4. Créer une branche de session pour explorer une approche (optionnel)
bash /chemin/vers/bmad-custom-kit/bmad-init.sh session-branch --name "explore-graphql"

# 5. Analyser les patterns d'échec après quelques semaines (optionnel)
bash _bmad/_config/custom/sil-collect.sh
# puis activer Sentinel → [FA] Self-Improvement Loop
```

## 🏢 Modèle Team of Teams

BMAD Custom Kit v3 introduit le modèle **Team of Teams** : chaque team est une unité de livraison autonome avec ses agents, son workflow, et son Delivery Contract.

```
┌─────────────────────────────────────────────────────────────┐
│  🔭 TEAM VISION              🔨 TEAM BUILD                  │
│  PM · Analyst · UX    ──►   Dev · Arch · QA · SM           │
│  Discovery → PRD → UX   PRD  Architecture → Stories → Code  │
│                      Contract                               │
└──────────────────────────────────────┬──────────────────────┘
                                       │ Delivery Contract
                                       ▼
                            ┌─────────────────────┐
                            │  ⚙️ TEAM OPS          │
                            │  Infra · CI/CD · Sec  │
                            │  IaC → Pipeline → Run │
                            └─────────────────────┘
```

**Règle fondamentale** : Aucune team ne commence sans un **Delivery Contract** signé de la team précédente.  
Template : `framework/delivery-contract.tpl.md`  
Manifests : `framework/teams/team-vision.yaml`, `team-build.yaml`, `team-ops.yaml`  
Schema : `framework/team-manifest.schema.yaml`

## 🌿 Session Branching

Explorez plusieurs approches en parallèle — comme des branches Git, mais pour vos sessions d'agents.

```bash
# Créer une branche pour explorer une option
bash bmad-init.sh session-branch --name "explore-graphql"

# Lister les branches actives
bash bmad-init.sh session-branch --list

# Comparer les artefacts produits dans deux branches
bash bmad-init.sh session-branch --diff main explore-graphql

# Merger une branche vers main
bash bmad-init.sh session-branch --merge explore-graphql

# Cherry-pick un artefact spécifique
bash bmad-init.sh session-branch --cherry-pick explore-graphql \
  "_bmad-output/.runs/explore-graphql/arch.md" \
  "_bmad-output/planning-artifacts/architecture-final.md"
```

Structure : `_bmad-output/.runs/{branch-name}/{run-id}/`  
Guide complet : `framework/sessions/README.md`

## 🔀 Plan/Act Mode & Extended Thinking

Chaque agent supporte deux modes et un mode de délibération :

| Trigger | Mode | Comportement |
|---------|------|-------------|
| `[PLAN]` ou "planifie" | Planification | Structure + attend validation avant toute modification |
| `[ACT]` ou rien | Exécution (défaut) | Exécute directement jusqu'à CC PASS sans interruption |
| `[THINK]` ou "réfléchis profondément" | Délibération | ≥ 3 options, simulation des échecs, ADR obligatoire |

## 🪃 Boomerang Orchestration

Un agent orchestrateur (SM) décompose, délègue à des sous-agents en parallèle, et agrège les résultats.

```yaml
# Exemple dans un workflow YAML
- step: "analyse-codebase"
  type: orchestrate
  spawn:
    - agent: dev
      task: "Analyse sécurité dans src/"
      output_key: security_findings
    - agent: qa
      task: "Coverage analysis dans src/"
      output_key: coverage_findings
  merge:
    strategy: summarize
    save_to: "_bmad-output/team-build/analysis-report.md"
```

Documentation : `framework/workflows/boomerang-orchestration.md`  
Protocol : `framework/workflows/subagent-orchestration.md`

## 🎯 Prompt Skills Library

Prompts réutilisables par team, invocables via slash commands dans Copilot Chat :

```
.github/prompts/
├── team-vision/
│   ├── competitive-intelligence.prompt.md   # Analyse concurrentielle sprint
│   ├── user-interview.prompt.md             # Interview utilisateur structuré
│   └── mvp-scoping.prompt.md               # Priorisation MoSCoW
├── team-build/
│   ├── tdd-cycle.prompt.md                  # Cycle TDD red-green-refactor
│   ├── adversarial-code-review.prompt.md    # Revue de code adversariale
│   └── architecture-decision-record.prompt.md  # ADR avec [THINK]
└── team-ops/
    ├── incident-runbook.prompt.md           # Runbook opérationnel step-by-step
    └── security-audit.prompt.md            # Audit sécurité OWASP + infra
```

## 🔌 MCP Server BMAD

BMAD expose un serveur MCP (Model Context Protocol) local — compatible avec tout IDE MCP.

```bash
# Configurer dans Claude Desktop / Cursor / Cline
{
  "mcpServers": {
    "bmad": {
      "command": "node",
      "args": ["/chemin/vers/bmad-custom-kit/framework/mcp/server.js"],
      "env": { "BMAD_PROJECT_ROOT": "/votre-projet" }
    }
  }
}
```

**Tools disponibles** : `get_project_context`, `get_agent_memory`, `run_completion_contract`,  
`get_workflow_status`, `list_sessions`, `get_failure_museum`, `spawn_subagent_task`

Spécification complète : `framework/mcp/bmad-mcp-server.md`

## Structure du Kit

```
bmad-custom-kit/
├── bmad-init.sh                    # Script d'init + session-branch subcommand
├── project-context.tpl.yaml        # Template contexte projet
│
├── framework/                      # GENERIC — ne jamais modifier par projet
│   ├── agent-base.md               # Protocole activation + CC + Plan/Act + [THINK]
│   ├── cc-verify.sh                # Completion Contract verifier (multi-stack)
│   ├── sil-collect.sh              # Self-Improvement Loop : collecteur de signaux
│   ├── team-manifest.schema.yaml   # Schema standard de définition d'une team
│   ├── delivery-contract.tpl.md    # Template contrat inter-teams
│   ├── teams/                      # Teams prêtes à l'emploi
│   │   ├── team-vision.yaml        # Team Vision — Product & Strategy
│   │   ├── team-build.yaml         # Team Build — Engineering & Quality
│   │   └── team-ops.yaml           # Team Ops — Infrastructure & Reliability
│   ├── sessions/
│   │   └── README.md               # Guide Session Branching
│   ├── mcp/
│   │   └── bmad-mcp-server.md      # Spec MCP Server BMAD local
│   ├── memory/
│   │   ├── maintenance.py
│   │   ├── mem0-bridge.py
│   │   ├── session-save.py
│   │   ├── failure-museum.tpl.md   # Template Failure Museum
│   │   └── contradiction-log.tpl.md
│   └── workflows/
│       ├── boomerang-orchestration.md   # Boomerang pattern SM→Dev→QA→SM
│       ├── subagent-orchestration.md    # Protocol spawn sous-agents
│       ├── state-checkpoint.md          # State persistence & resume
│       ├── workflow-status.tpl.md       # Template status workflow
│       └── incident-response.md
│
├── archetypes/                     # Starter kits thématiques
│   ├── meta/       # Atlas 🗺️, Sentinel 🔍, Mnemo 🧠
│   ├── stack/      # Gopher🐹 Go, Pixel⚛️ TS, Serpent🐍 Py, Container🐋, Terra🌍, Kube⎈
│   ├── infra-ops/  # Forge, Vault, Flow, Hawk, Helm, Phoenix, Probe
│   └── minimal/    # Agent vierge + meta
│
└── .github/
    └── prompts/
        ├── team-vision/   # competitive-intelligence, user-interview, mvp-scoping
        ├── team-build/    # tdd-cycle, adversarial-code-review, adr
        └── team-ops/      # incident-runbook, security-audit
```

## Archétypes disponibles

| Archétype | Agents inclus | Pour qui |
|-----------|---------------|----------|
| **minimal** | Atlas + Sentinel + Mnemo + 1 agent vierge | Tout projet — point de départ |
| **infra-ops** | + Forge, Vault, Flow, Hawk, Helm, Phoenix, Probe | Projets infrastructure/DevOps |
| **web-app** | Atlas + Sentinel + Mnemo (+ agents stack auto) | Applications web — SPA + API + DB |
| **stack** (auto) | Gopher, Pixel, Serpent, Container, Terra, Kube, Playbook | Déployés selon stack détecté |

## Créer un nouvel agent

Voir [docs/creating-agents.md](docs/creating-agents.md) pour le guide complet.

1. Copier `archetypes/minimal/agents/custom-agent.tpl.md`
2. Remplir la persona, les prompts, les règles
3. Ajouter dans `agent-manifest.csv`
4. Créer son fichier learnings dans `agent-learnings/`
5. Si applicable, créer son dossier dans `.github/prompts/{team-name}/`

## ⚡ Outils de Performance & Évolution

### Commandes de gestion du kit

```bash
# Version actuelle
bash bmad-init.sh --version

# Mise à jour depuis le dépôt upstream
bash bmad-init.sh upgrade              # met à jour framework/ et archetypes/
bash bmad-init.sh upgrade --dry-run    # preview sans modification
bash bmad-init.sh upgrade --force      # écrase même les fichiers modifiés localement
```

### Outils CLI avancés

Six outils CLI pour maintenir le kit en bonne santé sur la durée :

```bash
# Bench — mesurer les scores de performance des agents
bash bmad-init.sh bench --summary           # tableau de bord global
bash bmad-init.sh bench --report            # détail par agent + tendance
bash bmad-init.sh bench --improve           # génère bench-context.md pour Sentinel

# Forge — générer des squelettes d'agents
bash bmad-init.sh forge --from "migrations DB PostgreSQL"
bash bmad-init.sh forge --from-gap          # depuis les lacunes détectées
bash bmad-init.sh forge --install db-migrator

# Guard — budget de contexte LLM
bash bmad-init.sh guard                     # tous les agents (exit 1=warn, 2=crit)
bash bmad-init.sh guard --agent atlas --detail --model gpt-4o
bash bmad-init.sh guard --suggest           # + recommandations de réduction
bash bmad-init.sh guard --json              # sortie JSON (CI-compatible)

# Evolve — DNA vivante
bash bmad-init.sh evolve                    # proposer évolutions depuis BMAD_TRACE
bash bmad-init.sh evolve --report           # rapport Markdown seul
bash bmad-init.sh evolve --since 2026-01-01 # période spécifique
bash bmad-init.sh evolve --apply            # appliquer le dernier patch (après review)

# Dream — consolidation hors-session et insights émergents
bash bmad-init.sh dream                     # dream complet (toutes les sources)
bash bmad-init.sh dream --since 2026-01-01  # depuis une date
bash bmad-init.sh dream --agent dev         # focus un agent
bash bmad-init.sh dream --validate          # valider les insights (no hallucination)
bash bmad-init.sh dream --dry-run           # preview sans écrire

# Consensus — protocole de consensus adversarial pour décisions critiques
bash bmad-init.sh consensus --proposal "Utiliser PostgreSQL pour le cache sessions"
bash bmad-init.sh consensus --proposal-file proposal.md --threshold 0.75
bash bmad-init.sh consensus --history       # voir les décisions passées
bash bmad-init.sh consensus --stats         # statistiques de consensus
```

Voir [framework/tools/README.md](framework/tools/README.md) pour la référence complète.

## Système de mémoire

Le kit inclut un système de mémoire à 4 niveaux :

1. **Mémoire sémantique** (`mem0-bridge.py`) — recherche vectorielle via Qdrant ou fallback JSON
2. **Learnings par agent** (`agent-learnings/`) — apprentissages structurés par domaine
3. **Contexte partagé** (`shared-context.md`) — source de vérité cross-agents
4. **Failure Museum** (`failure-museum.md`) — erreurs passées pour ne pas les répéter

**Qualité automatisée :**
- Détection de contradictions à chaque ajout mémoire → `contradiction-log.md`
- Consolidation des learnings au démarrage de session
- State checkpoints à chaque step de workflow → resume automatique si interruption

**Self-Improvement Loop :**
```bash
bash _bmad/_config/custom/sil-collect.sh
# → produit _bmad-output/sil-report-latest.md
# → activer Sentinel [FA] pour proposer des améliorations concrètes
```

## Comparaison avec les alternatives

| Feature | CrewAI | AutoGen | LangGraph | Aider | Cline | **BMAD v3** |
|---------|--------|---------|-----------|-------|-------|-------------|
| Local/IDE-native | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Team of Teams | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Completion Contract | ❌ | ❌ | ❌ | ~ | ~ | ✅ |
| Delivery Contracts | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Session Branching | ❌ | ❌ | ~ | ❌ | ❌ | ✅ |
| State Checkpoint/Resume | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| Subagent Orchestration | ~ | ✅ | ✅ | ❌ | ✅ | ✅ |
| MCP Server | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Self-improvement | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Plan/Act Mode | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Extended Thinking [THINK] | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Failure Museum | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

## 🧪 Tests

Le kit inclut une suite de tests complète (388+ tests) en deux catégories :

**Tests unitaires Python** (10 fichiers, 388 tests) :
```bash
# Lancer tous les tests
python3 -m unittest discover -s tests -v

# Un fichier spécifique
python3 -m unittest tests.test_context_guard_advanced -v
```

| Fichier | Outil testé | Tests |
|---------|-------------|-------|
| `test_python_tools.py` | Tous les outils (base) | 48 |
| `test_context_guard_advanced.py` | Context Guard avancé | 42 |
| `test_maintenance_advanced.py` | Maintenance mémoire | 29 |
| `test_agent_forge.py` | Agent Forge | 36 |
| `test_agent_bench.py` | Agent Bench | 19 |
| `test_dna_evolve.py` | DNA Evolve | 25 |
| `test_session_save.py` | Session Save | 11 |
| `test_gen_tests.py` | Gen Tests (scaffolding) | 31 |
| `test_dream.py` | Dream Mode | 68 |
| `test_adversarial_consensus.py` | Adversarial Consensus | 76 |

**Smoke tests Bash** (78 assertions) :
```bash
bash tests/smoke-test.sh
```

**CI** : les tests Python s'exécutent automatiquement dans le job `python-tests` du workflow CI.

## Prérequis

- Python 3.10+
- Git
- [BMAD Framework](https://github.com/bmadcode/BMAD-METHOD) v6.0+ installé
- (Optionnel) Node.js 18+ pour le MCP Server
- (Optionnel) Qdrant pour la recherche sémantique avancée

## Licence

MIT — utilisez, forkez, adaptez librement.

