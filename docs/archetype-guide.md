# Guide des Archétypes

## Qu'est-ce qu'un archétype ?

Un archétype est un ensemble pré-configuré d'agents, de templates et de configurations adapté à un type de projet spécifique. Il fournit un point de départ fonctionnel que vous personnalisez pour votre contexte.

## Archétypes disponibles

### `minimal`

**Cas d'usage** : Tout type de projet — le strict nécessaire pour démarrer.

**Agents inclus :**
| Agent | Icône | Rôle |
|-------|-------|------|
| Atlas (project-navigator) | 🗺️ | Navigation projet, registre des services, cartographie |
| Sentinel (agent-optimizer) | 🔍 | Audit qualité des agents, optimisation prompts, **Self-Improvement Loop** |
| Mnemo (memory-keeper) | 🧠 | Gestion mémoire, contradictions, consolidation |

**+ 1 template vierge** (`custom-agent.tpl.md`) pour créer vos propres agents.

**Quand l'utiliser :**
- Projets non-infrastructure (web apps, APIs, data pipelines)
- Quand vous voulez construire vos agents de zéro
- Pour tester le framework avant d'investir dans un archétype complet

---

### `stack` — Modal Team Engine

**Cas d'usage** : Déployé automatiquement par `--auto` en fonction du stack détecté. Les agents `stack` s'ajoutent à l'archétype de base choisi.

**Agents disponibles (déployés sélectivement) :**
| Agent | Icône | Stack détecté par | Domaine |
|-------|-------|-----------------|--------|
| Gopher | 🐹 | `go.mod` | Go — backend, tests table-driven, performance |
| Pixel | ⚛️ | `package.json` + react/vue/next/vite | TypeScript & React — types, hooks, RTL |
| Serpent | 🐍 | `requirements.txt` / `pyproject.toml` | Python — types, pytest, ruff |
| Container | 🐋 | `Dockerfile` / `docker-compose.yml` | Docker — multi-stage, sécurité, healthchecks |
| Terra | 🌍 | `*.tf` (jusqu'à depth 7) | Terraform — plan obligatoire, modules, tfsec |
| Kube | ⎈ | `k8s/`, `kind: Deployment` | Kubernetes — workloads, troubleshooting, RBAC |
| Playbook | 🎭 | `ansible/`, `playbook*.yml`, `ansible.cfg` | Ansible — idémpotence, vault, lint |

**Comment ça marche (Modal Team Engine) :**
```bash
# L'option --auto fait tout automatiquement :
bash bmad-init.sh --name "Mon App" --user "Guilhem" --auto

# → 1. detect_stack() scan le répertoire courant
# → 2. Identifie les stacks : ex. "go frontend docker"
# → 3. Choisit l'archétype : minimal si app, infra-ops si terraform/k8s/ansible
# → 4. deploy_stack_agents() copie les agents correspondants
# Résultat : équipe exactement adaptée à votre projet
```

**Exemple Anime-Sama-Downloader (Go + React + Docker) :**
```
Stack détecté : go frontend docker
Agent déployés : Gopher 🐹 + Pixel ⚛️ + Container 🐋
```

**Exemple Terraform-HouseServer (Terraform + Ansible + K8s) :**
```
Stack détecté : terraform ansible k8s docker
Archétype auto : infra-ops
Agents stack déployés : Terra 🌍 + Playbook 🎭 + Kube ⎈ + Container 🐋
```

> Les agents `stack` complètent l'archétype (ils ne le remplacent pas). Ils intègrent tous le Completion Contract : `cc-verify.sh --stack X` avant tout "terminé".

---

### `infra-ops`

**Cas d'usage** : Infrastructure, DevOps, homelab, serveurs — l'archétype complet.

**Agents inclus :** (les 3 meta + 7 spécialisés)

| Agent | Icône | Rôle |
|-------|-------|------|
| Atlas | 🗺️ | Navigation & Mémoire projet |
| Sentinel | 🔍 | Qualité & Optimisation agents |
| Mnemo | 🧠 | Mémoire & Qualité connaissances |
| Forge (ops-engineer) | 🔧 | Infrastructure & Provisioning (Terraform, Ansible, Docker) |
| Vault (security-hardener) | 🛡️ | Sécurité & Hardening (SOPS, TLS, firewall) |
| Flow (pipeline-architect) | ⚡ | CI/CD & Automation (GitHub Actions, Taskfile) |
| Hawk (monitoring-specialist) | 📡 | Observabilité (Prometheus, Grafana, alerting) |
| Helm (k8s-navigator) | ☸️ | Kubernetes & Orchestration (K3s, FluxCD) |
| Phoenix (backup-dr-specialist) | 🏰 | Backup & Disaster Recovery |
| Probe (systems-debugger) | 🔬 | Systems Debugging (kernel, perf, strace) |

**Quand l'utiliser :**
- Homelab Proxmox avec LXC/VMs
- Clusters Kubernetes (K3s, K8s)
- Infrastructure as Code (Terraform, Ansible)
- Stacks de monitoring (Prometheus/Grafana/Loki)

---

## Personnaliser un archétype

### Étape 1 : Adapter les identités

Chaque agent a une section `<identity>` avec des `{{placeholders}}`. Remplacez-les par vos valeurs :

```markdown
<!-- AVANT (template) -->
<identity>
Tu es Forge, expert IaC pour le projet décrit dans shared-context.md.
Tu gères {{network_cidr}}, déploiement via {{infra_dir}}.
</identity>

<!-- APRÈS (personnalisé) -->
<identity>
Tu es Forge, expert IaC pour l'infrastructure production.
Tu gères 10.0.0.0/8 avec 3 serveurs bare-metal, déploiement via terraform-prod/.
</identity>
```

### Étape 2 : Adapter les exemples

Les blocs `<example>` contiennent des exemples réalistes. Remplacez-les par des situations de votre projet.

### Étape 3 : Ajouter/retirer des agents

- **Retirer** : Supprimez le fichier `.md` et sa ligne dans `agent-manifest.csv` et `shared-context.md`
- **Ajouter** : Copiez `custom-agent.tpl.md`, remplissez, enregistrez (voir [creating-agents.md](creating-agents.md))

### Étape 4 : Remplir `shared-context.md`

Ce fichier est la source de vérité lue par tous les agents. Décrivez-y :
- Architecture du projet
- Topologie réseau
- Services et où ils tournent
- Conventions d'équipe

## Créer un nouvel archétype

Pour contribuer un archétype au kit :

1. Créer `archetypes/mon-archetype/agents/` avec les agents
2. Créer `archetypes/mon-archetype/shared-context.tpl.md`
3. Documenter dans ce guide
4. Tester avec `bmad-init.sh --archetype mon-archetype`

**Archétypes envisagés :**
- `data-pipeline` — ETL, ML, analytics (dbt, Airflow, Spark)
- `game-dev` — Moteurs de jeu, assets, QA (Unity, Godot)
