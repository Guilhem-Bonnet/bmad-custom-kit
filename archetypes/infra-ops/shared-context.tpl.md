# Contexte Partagé — {{project_name}}

<!-- ARCHETYPE: infra-ops — Template de shared-context pour infrastructure.
     Adaptez les sections à votre environnement. -->

> Ce fichier est chargé par tous les agents au démarrage.
> Il est la source de vérité pour le contexte projet.

## Projet

- **Nom** : {{project_name}}
- **Description** : {{project_description}}
- **Dépôt principal** : {{repo_url}}
- **Stack** : {{stack_description}}

## Infrastructure

<!-- Adaptez cette section à votre environnement -->

| Hôte | IP | Rôle | Services |
|------|----|------|----------|
| {{host_1}} | {{ip_1}} | {{role_1}} | {{services_1}} |
| {{host_2}} | {{ip_2}} | {{role_2}} | {{services_2}} |

**Réseau** : {{network_cidr}}

## Équipe d'Agents Custom

| Agent | Nom | Icône | Domaine |
|-------|-----|-------|---------|
| project-navigator | Atlas | 🗺️ | Navigation & Mémoire projet |
| agent-optimizer | Sentinel | 🔍 | Qualité & Optimisation agents |
| memory-keeper | Mnemo | 🧠 | Mémoire & Qualité connaissances |
| ops-engineer | Forge | 🔧 | Infrastructure & Provisioning |
| security-hardener | Vault | 🛡️ | Sécurité & Hardening |
| pipeline-architect | Flow | ⚡ | CI/CD & Automation |
| monitoring-specialist | Hawk | 📡 | Observabilité & Monitoring |
| k8s-navigator | Helm | ☸️ | Kubernetes & Orchestration |
| backup-dr-specialist | Phoenix | 🏰 | Backup & Disaster Recovery |
| systems-debugger | Probe | 🔬 | Systems Debugging |
| fix-loop-orchestrator | Loop | 🔁 | Correction certifiée & Fix Patterns |

## Conventions

- Langue de communication : {{communication_language}}
- Toutes les décisions sont loggées dans `decisions-log.md`
- Les transferts inter-agents passent par `handoff-log.md`

## Requêtes inter-agents

<!-- Les agents ajoutent ici les requêtes pour d'autres agents -->
<!-- Format: [AGENT_SOURCE→AGENT_CIBLE] description de la requête -->
