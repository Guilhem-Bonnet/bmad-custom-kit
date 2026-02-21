# Getting Started — BMAD Custom Kit

## Prérequis

- [BMAD Framework](https://github.com/bmadcode/BMAD-METHOD) v6.0+ installé dans votre projet
- Python 3.10+ (pour le système de mémoire)
- Git (pour les hooks pre-commit)

## Installation rapide

```bash
# 1. Cloner le kit
git clone https://github.com/Guilhem-Bonnet/bmad-custom-kit.git
cd bmad-custom-kit

# 2. Initialiser dans votre projet
./bmad-init.sh --name "Mon Projet" --user "Alice" --archetype infra-ops --target /chemin/vers/mon-projet

# 3. Personnaliser
# Éditer project-context.yaml dans votre projet
# Adapter les agents dans _bmad/_config/custom/agents/
```

## Structure créée

Après `bmad-init.sh`, votre projet contiendra :

```
mon-projet/
├── project-context.yaml          ← Configuration centralisée
├── _bmad/
│   ├── _config/
│   │   ├── custom/
│   │   │   ├── agent-base.md     ← Protocole commun
│   │   │   ├── agents/           ← Fichiers agents
│   │   │   ├── prompt-templates/ ← Templates réutilisables
│   │   │   └── workflows/        ← Workflows partagés
│   │   └── agent-manifest.csv    ← Registre des agents
│   └── _memory/
│       ├── config.yaml           ← Config mémoire
│       ├── maintenance.py        ← Health-check & pruning
│       ├── mem0-bridge.py        ← Mémoire sémantique
│       ├── session-save.py       ← Sauvegarde session
│       ├── shared-context.md     ← Contexte partagé
│       ├── decisions-log.md      ← Log décisions
│       ├── memories.json         ← Mémoire JSON
│       ├── activity.jsonl        ← Log activité
│       └── agent-learnings/      ← Apprentissages par agent
```

## Premiers pas

### 1. Éditer `project-context.yaml`

Ce fichier centralise toute la configuration de votre projet. Les scripts Python le lisent pour s'adapter automatiquement :

```yaml
project:
  name: "Mon API Backend"
  type: "api"
  stack: ["Python", "FastAPI", "PostgreSQL"]

user:
  name: "Alice"
  language: "Français"
```

### 2. Personnaliser les agents

Chaque agent dans `_bmad/_config/custom/agents/` contient des `{{placeholders}}` à remplacer par vos valeurs réelles. Les sections à adapter :

- **`<identity>`** — Décrivez votre infrastructure/projet spécifique
- **`<example>`** — Remplacez par des exemples concrets de votre environnement

### 3. Activer la mémoire sémantique (optionnel)

```bash
# Mode minimal (JSON, zéro dépendance)
# → Fonctionne out of the box

# Mode sémantique (recommandé)
pip install -r _bmad/_memory/requirements.txt
python _bmad/_memory/mem0-bridge.py status
```

### 4. Vérifier l'installation

```bash
python _bmad/_memory/maintenance.py health-check --force
```

## Choix de l'archétype

| Archétype | Agents inclus | Cas d'usage |
|-----------|---------------|-------------|
| `minimal` | Atlas, Sentinel, Mnemo + 1 template vierge | Tout projet |
| `infra-ops` | 10 agents spécialisés infra/DevOps | Homelab, serveurs, K8s |

## Hooks pre-commit (optionnel)

Si votre projet utilise `pre-commit`, ajoutez dans `.pre-commit-config.yaml` :

```yaml
- repo: local
  hooks:
    - id: mnemo-consolidate
      name: "🧠 Mnemo — Consolidation mémoire"
      entry: bash -c 'python _bmad/_memory/maintenance.py consolidate-learnings && python _bmad/_memory/maintenance.py context-drift'
      language: system
      always_run: true
      pass_filenames: false
      stages: [pre-commit]
```
