# BMAD Custom Kit

> Toolkit pour créer et gérer un écosystème d'agents IA spécialisés par projet — personas, mémoire sémantique, workflows et qualité automatisée.

## Qu'est-ce que c'est ?

BMAD Custom Kit est un **starter kit** pour déployer une équipe d'agents IA spécialisés dans n'importe quel projet. Chaque agent a une persona, un domaine d'expertise, et accède à une mémoire partagée persistante.

**Ce que vous obtenez :**
- 🤖 **Agents spécialisés** — personas avec domaine, style de communication et principes
- 🧠 **Mémoire persistante** — recherche sémantique (Qdrant) + fallback JSON, consolidation automatique
- 📋 **Protocole d'activation** — chaque agent suit un workflow standardisé (health-check, inbox, consolidation)
- 🔄 **Qualité automatisée** — détection contradictions, consolidation learnings, drift check
- 📦 **Archétypes** — starter kits thématiques (infra-ops, minimal, ou créez les vôtres)

## Quick Start

```bash
# 1. Cloner le kit
git clone https://github.com/Guilhem-Bonnet/bmad-custom-kit.git

# 2. Initialiser dans votre projet
cd votre-projet/
bash /chemin/vers/bmad-custom-kit/bmad-init.sh \
  --name "Mon Projet" \
  --user "Votre Nom" \
  --lang "Français" \
  --archetype infra-ops

# 3. Configurer le contexte projet
# Éditer le fichier project-context.yaml généré

# 4. Activer un agent dans VS Code
# Utiliser les modes agents configurés dans .vscode/settings.json
```

## Structure du Kit

```
bmad-custom-kit/
├── bmad-init.sh                    # Script d'initialisation
├── project-context.tpl.yaml        # Template contexte projet
│
├── framework/                      # GENERIC — ne jamais modifier par projet
│   ├── agent-base.md               # Protocole d'activation universel
│   ├── memory/
│   │   ├── maintenance.py          # Health-check, consolidation, drift
│   │   ├── mem0-bridge.py          # Mémoire sémantique (Qdrant + JSON)
│   │   ├── session-save.py         # Persistance session
│   │   └── requirements.txt        # Dépendances Python
│   ├── prompt-templates/           # Templates de prompts réutilisables
│   └── workflows/
│       └── incident-response.md    # Workflow incident/post-mortem
│
├── archetypes/                     # Starter kits thématiques
│   ├── meta/                       # Agents universels (toujours inclus)
│   │   └── agents/                 # Atlas, Sentinel, Mnemo
│   ├── infra-ops/                  # Infrastructure & DevOps
│   │   ├── agents/                 # Forge, Vault, Flow, Hawk, Helm, Phoenix, Probe
│   │   └── shared-context.tpl.md   # Template contexte infra
│   └── minimal/                    # Agent vierge + meta
│       └── agents/
│           └── custom-agent.tpl.md # Template agent personnalisable
│
├── docs/                           # Documentation
└── examples/                       # Projet de référence
    └── terraform-houseserver/
```

## Archétypes disponibles

| Archétype | Agents inclus | Pour qui |
|-----------|---------------|----------|
| **minimal** | Atlas + Sentinel + Mnemo + 1 agent vierge | Tout projet — point de départ |
| **infra-ops** | + Forge, Vault, Flow, Hawk, Helm, Phoenix, Probe | Projets infrastructure/DevOps |

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
- Détection de contradictions à chaque ajout mémoire
- Consolidation des learnings au démarrage de session
- Vérification de cohérence (context drift) en pre-commit

## Prérequis

- Python 3.10+
- Git
- [BMAD Framework](https://github.com/bmadcode/BMAD-METHOD) v6.0+ installé
- (Optionnel) Qdrant pour la recherche sémantique avancée

## Licence

MIT — utilisez, forkez, adaptez librement.
