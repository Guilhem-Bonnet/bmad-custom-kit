# Context Budget Router — BM-07

> Système de gestion automatique du budget de contexte (tokens) pour les agents BMAD. Inspiré du Context Window Management de mem0/MemGPT.

## Problème

Un agent qui charge tous ses fichiers mémoire + la codebase + l'historique dépasse rapidement la fenêtre de contexte disponible. Sans gestion explicite, l'agent truncate en silence, perd du contexte critique, et hallucine.

## Solution : Priorité de chargement déclarée

Chaque agent déclare un `context_budget` dans son fichier YAML de configuration. Le router choisit les fichiers à charger selon leur priorité et la capacité restante estimée.

## Niveaux de priorité

| Niveau | Nom | Chargement | Contenu typique |
|--------|-----|-----------|-----------------|
| **P0** | ALWAYS | Systématique | Agent persona, règles core, BASE PROTOCOL |
| **P1** | SESSION | À chaque activation | shared-context.md, decisions-log.md, agent-learnings récents |
| **P2** | TASK | Si pertinent pour la tâche | Fichiers liés à la story courante, ADRs du domaine |
| **P3** | LAZY | À la demande explicite | Archives, historiques longs, knowledge-digest |
| **P4** | ON-REQUEST | Sur commande explicite | Fichiers volumineux, dépendances externes |

## Configuration par agent

Ajouter dans le frontmatter de chaque agent :

```yaml
---
name: "go-expert"
context_budget:
  strategy: "priority"
  max_tokens_estimate: 50000
  always_load:
    - "{project-root}/_bmad/_config/custom/agent-base.md"
    - "{project-root}/_bmad/_memory/shared-context.md"
  session_load:
    - "{project-root}/_bmad/_memory/decisions-log.md"
    - "{project-root}/_bmad/_memory/agent-learnings/go-backend.md"
    - "{project-root}/_bmad/_memory/failure-museum.md"            # si > 2 semaines
  task_load:
    - "{current_story_file}"
    - "{related_adrs}"
  lazy_load:
    - "{project-root}/_bmad/_memory/knowledge-digest.md"
    - "{project-root}/_bmad/_memory/archives/"
---
```

## Règles de chargement dans agent-base.md

Les agents base.md héritent déjà de ce protocole via la règle LAZY-LOAD existante. Le Context Budget Router formalise et étend cette règle :

```
CONTEXT BUDGET RULES :
1. Calculer les tokens estimés des fichiers P0+P1 → si > 60% du budget → passer P1 en lazy
2. Repo Map → toujours LAZY (P3) sauf commande [RM] explicite
3. Failure Museum → P1 si projet > 2 semaines, sinon P3
4. Archives → jamais chargées automatiquement (P4)
5. Si contexte sature → résumer les sections les moins récentes via [THINK] → stocker le résumé → décharger l'original
```

## Estimation de tokens

Règle approximative pour guidance des agents :

| Type de fichier | Tokens estimés |
|----------------|---------------|
| `agent-base.md` (complet) | ~3 000 |
| `shared-context.md` (infra moyenne) | ~2 000–5 000 |
| `decisions-log.md` (50 entrées) | ~2 000 |
| Fichier source Go/TS moyen (200 lignes) | ~1 500 |
| `repo-map.md` (projet 100 fichiers) | ~8 000 |
| `failure-museum.md` | ~1 500 |
| Story complète | ~500–1 000 |

## Context Overflow Protocol

Quand un agent détecte un dépassement potentiel :

```
⚠️ CONTEXT BUDGET WARNING
Budget estimé : {used}/{max} tokens
Fichiers chargés : {list}
Action : Je vais résumer les sections > 30 jours dans decisions-log et knowledge-digest
avant de continuer. [THINK] mode activé.
```

Puis l'agent :
1. Résume les sections anciennes en 3-5 bullets
2. Archivage dans `_memory/archives/digest-{date}.md`
3. Remplace la section originale par le résumé
4. Continue avec le budget libéré

## Intégration avec Session Branching

Chaque branche de session a son propre budget indépendant. Le router ne charge **pas** les artefacts des autres branches sauf sur `[cherry-pick]` explicite.

```yaml
# state.json (par branche)
{
  "branch": "feature-auth",
  "context_snapshot": {
    "loaded_files": [...],
    "estimated_tokens_used": 28000,
    "lazy_available": [...]
  }
}
```

## Configuration globale dans `project-context.yaml`

```yaml
context_budget:
  default_max_tokens: 80000      # Claude Sonnet : 200k, GPT-4o : 128k
  warning_threshold: 0.75        # alerte à 75% utilisé
  overflow_strategy: "summarize" # summarize | drop-oldest | ask-user
  repo_map_threshold: 0.50       # charger repo-map seulement si < 50% budget utilisé
```
