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

# 2a. Initialiser en mode automatique (recommandé)
# Détecte le stack et déploie les agents adaptés automatiquement
cd votre-projet/
bash /chemin/vers/bmad-custom-kit/bmad-init.sh \
  --name "Mon Projet" \
  --user "Alice" \
  --auto

# 2b. OU initialiser manuellement avec un archétype spécifique
bash /chemin/vers/bmad-custom-kit/bmad-init.sh \
  --name "Mon Projet" \
  --user "Alice" \
  --archetype infra-ops

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
│   │   │   ├── agent-base.md     ← Protocole commun (avec Completion Contract)
│   │   │   ├── cc-verify.sh      ← Vérificateur multi-stack (go/ts/docker/tf/k8s/...)
│   │   │   ├── sil-collect.sh    ← Collecteur Self-Improvement Loop
│   │   │   ├── agents/           ← Fichiers agents déployés
│   │   │   ├── prompt-templates/
│   │   │   └── workflows/
│   │   └── agent-manifest.csv
│   └── _memory/
│       ├── config.yaml
│       ├── maintenance.py
│       ├── mem0-bridge.py
│       ├── session-save.py
│       ├── shared-context.md     ← Contexte partagé
│       ├── decisions-log.md
│       ├── contradiction-log.md  ← Contradictions inter-agents
│       ├── memories.json
│       ├── activity.jsonl
│       └── agent-learnings/
└── _bmad-output/
    └── sil-report-latest.md      ← Rapport Self-Improvement Loop (généré)
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
| `--auto` | Détecté par stack | Laissez le Modal Team Engine décider |

### Agents stack (déployés par `--auto` selon ce qui est détecté)

| Stack détecté | Agent déployé | Persona |
|---------------|--------------|--------|
| `go.mod` | Gopher | 🐹 Expert Go |
| `package.json` + react/vue | Pixel | ⚛️ Expert TypeScript/React |
| `requirements.txt` | Serpent | 🐍 Expert Python |
| `Dockerfile` | Container | 🐋 Expert Docker |
| `*.tf` | Terra | 🌍 Expert Terraform |
| `k8s/` ou `kind: Deployment` | Kube | ⎈ Expert K8s |
| `ansible/` ou `playbook*.yml` | Playbook | 🎭 Expert Ansible |

## Completion Contract

Tous les agents intègrent le Completion Contract : ils ne peuvent pas dire "terminé" sans passer
`cc-verify.sh`.

```bash
# Vérifier votre code manuellement
bash _bmad/_config/custom/cc-verify.sh

# Vérifier un stack spécifique seulement
bash _bmad/_config/custom/cc-verify.sh --stack go
bash _bmad/_config/custom/cc-verify.sh --stack k8s
```

Sortie : `✅ CC PASS — [go, typescript, docker] — 2026-02-23 21:28`

## Self-Improvement Loop (optionnel)

Après quelques semaines d'utilisation, analysez vos patterns d'échec :

```bash
# Collecter les signaux
bash _bmad/_config/custom/sil-collect.sh
# → génère : _bmad-output/sil-report-latest.md

# Analyser avec Sentinel
# Ouvrir Sentinel dans VS Code → [FA] Self-Improvement Loop
# Sentinel propose des règles à ajouter au framework
```

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
