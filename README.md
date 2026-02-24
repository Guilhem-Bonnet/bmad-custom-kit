# BMAD Custom Kit

> Toolkit pour créer et gérer un écosystème d'agents IA spécialisés par projet — personas, mémoire sémantique, workflows et qualité automatisée.

## Qu'est-ce que c'est ?

BMAD Custom Kit est un **starter kit** pour déployer une équipe d'agents IA spécialisés dans n'importe quel projet. Chaque agent a une persona, un domaine d'expertise, et accède à une mémoire partagée persistante.

**Ce que vous obtenez :**
- 🤖 **Agents spécialisés** — personas avec domaine, style de communication et principes
- 🧠 **Mémoire persistante** — recherche sémantique (Qdrant) + fallback JSON, consolidation automatique
- 📋 **Protocole d'activation** — chaque agent suit un workflow standardisé (health-check, inbox, consolidation)
- � **Completion Contract (CC)** — `cc-verify.sh` détecte le stack et exécute les vérifications appropriées (build, tests, lint) avant tout "terminé"
- 🔄 **Modal Team Engine** — `--auto` détecte le stack du projet et déploie automatiquement les agents spécialisés (Go, TypeScript, Python, Docker, Terraform, K8s, Ansible)
- ⚡ **Qualité automatisée** — détection contradictions, consolidation learnings, drift check
- 🔁 **Self-Improvement Loop** — `sil-collect.sh` analyse les patterns d'échec et Sentinel propose des améliorations concrètes au framework

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

# 4. Analyser les patterns d'échec après quelques semaines (optionnel)
bash _bmad/_config/custom/sil-collect.sh
# puis activer Sentinel → [FA] Self-Improvement Loop
```

## Structure du Kit

```
bmad-custom-kit/
├── bmad-init.sh                    # Script d'initialisation (+ --auto)
├── project-context.tpl.yaml        # Template contexte projet
│
├── framework/                      # GENERIC — ne jamais modifier par projet
│   ├── agent-base.md               # Protocole d'activation universcel (avec CC)
│   ├── cc-verify.sh                # Completion Contract verifier (multi-stack)
│   ├── sil-collect.sh              # Self-Improvement Loop : collecteur de signaux
│   ├── memory/
│   │   ├── maintenance.py
│   │   ├── mem0-bridge.py
│   │   ├── session-save.py
│   │   ├── contradiction-log.tpl.md # Template log contradictions inter-agents
│   │   └── requirements.txt
│   ├── prompt-templates/
│   └── workflows/
│       └── incident-response.md
│
├── archetypes/                     # Starter kits thématiques
│   ├── meta/                       # Agents universels (toujours inclus)
│   │   └── agents/                 # Atlas 🗺️, Sentinel 🔍, Mnemo 🧠
│   ├── stack/                      # Modal Team Engine — agents par technologie
│   │   └── agents/                 # Gopher🐹 Go, Pixel⚛️ TS, Serpent🐍 Py,
│   │                               # Container🐋 Docker, Terra🌍 TF, Kube⎈ K8s,
│   │                               # Playbook🎭 Ansible
│   ├── infra-ops/                  # Infrastructure & DevOps complet
│   │   ├── agents/                 # Forge, Vault, Flow, Hawk, Helm, Phoenix, Probe
│   │   └── shared-context.tpl.md
│   └── minimal/                    # Agent vierge + meta
│       └── agents/
│           └── custom-agent.tpl.md
│
├── docs/
└── examples/
    └── terraform-houseserver/
```

## Archétypes disponibles

| Archétype | Agents inclus | Pour qui |
|-----------|---------------|----------|
| **minimal** | Atlas + Sentinel + Mnemo + 1 agent vierge | Tout projet — point de départ |
| **infra-ops** | + Forge, Vault, Flow, Hawk, Helm, Phoenix, Probe | Projets infrastructure/DevOps |
| **stack** (auto) | Gopher, Pixel, Serpent, Container, Terra, Kube, Playbook | Déployés selon le stack détecté par `--auto` |

> Les agents `stack` sont sélectifs : seuls ceux correspondant au stack détecté sont déployés.
> Exemple : projet Go + React + Docker → Gopher + Pixel + Container.

## Créer un nouvel agent

Voir [docs/creating-agents.md](docs/creating-agents.md) pour le guide complet.

En résumé :
1. Copier `archetypes/minimal/agents/custom-agent.tpl.md`
2. Remplir la persona, les prompts, les règles
3. Ajouter l'agent dans `agent-manifest.csv`
4. Créer son fichier learnings dans `agent-learnings/`

## Système de mémoire

Le kit inclut un système de mémoire à 3 niveaux :

1. **Mémoire sémantique** (`mem0-bridge.py`) — recherche vectorielle via Qdrant local ou fallback JSON
2. **Learnings par agent** (`agent-learnings/`) — apprentissages structurés par domaine
3. **Contexte partagé** (`shared-context.md`) — source de vérité chargée par tous les agents

**Qualité automatisée :**
- Détection de contradictions à chaque ajout mémoire → `contradiction-log.md`
- Consolidation des learnings au démarrage de session
- Vérification de cohérence (context drift) en pre-commit

**Self-Improvement Loop :**
```bash
# Collecter les signaux d'échec des 90 derniers jours
bash _bmad/_config/custom/sil-collect.sh
# → produit _bmad-output/sil-report-latest.md
# → activer Sentinel [FA] pour analyser et proposer des améliorations
```

## Prérequis

- Python 3.10+
- Git
- [BMAD Framework](https://github.com/bmadcode/BMAD-METHOD) v6.0+ installé
- (Optionnel) Qdrant pour la recherche sémantique avancée

## Licence

MIT — utilisez, forkez, adaptez librement.
