# Subagent Orchestration Protocol

> **BM-19** — Architecture native pour spawner des sous-agents en parallèle depuis un workflow BMAD.
>
> Inspiré de Claude's tool_use, MetaGPT SOP, et Roo-Code Boomerang Tasks.
>
> **Principe** : Un agent orchestrateur décompose une tâche complexe en sous-tâches atomiques,
> les délègue à des agents spécialisés (en parallèle quand possible), puis agrège les résultats.

---

## Syntaxe dans les Workflows YAML

### Step type `orchestrate`

```yaml
- step: "analyse-codebase"
  type: orchestrate
  description: "Analyse parallèle sécurité + coverage depuis deux agents spécialisés"
  spawn:
    - agent: "dev"
      task: "Analyse le répertoire src/ pour les problèmes de sécurité (OWASP Top 10). Retourne une liste structurée : [{file, line, severity, description}]"
      context:
        - "_bmad/_memory/shared-context.md"
        - "_bmad-output/implementation-artifacts/architecture-*.md"
      output_key: "security_findings"

    - agent: "qa"
      task: "Analyse la couverture de tests dans src/. Identifie les fichiers sans tests et les branches non couvertes. Retourne : [{file, coverage_pct, missing_tests}]"
      context:
        - "_bmad/_memory/shared-context.md"
      output_key: "coverage_findings"

  merge:
    strategy: "summarize"           # summarize | concat | first-wins | vote
    merged_output_key: "analysis_report"
    save_to: "_bmad-output/implementation-artifacts/analysis-report-{date}.md"
```

---

## Stratégies de Merge

| Stratégie | Description | Cas d'usage |
|---|---|---|
| `summarize` | L'orchestrateur synthétise tous les findings en un rapport cohérent | Analyses multiples — résumé exécutif |
| `concat` | Concaténation brute des outputs, section par section | Documentation, listes exhaustives |
| `first-wins` | Premier sous-agent à terminer décide, les autres valident ou overrident | Decisions rapides avec validation |
| `vote` | Chaque agent vote pour la meilleure option — majorité gagne | Choix techniques controversés |
| `structured` | Chaque output va dans une section prédéfinie du résultat final | Rapports multi-sections |

---

## Fallback pour LLMs sans support sous-agents natif

Si le LLM ne supporte pas le spawn réel de sous-agents :

```yaml
  fallback:
    mode: "sequential"             # Exécute les tâches séquentiellement, même agent
    note: "Sequential fallback — parallel execution not available in this runtime"
```

L'orchestrateur exécute les tâches une par une dans le même contexte, en simulant le changement de persona entre chaque tâche.

---

## Patterns Recommandés

### Pattern 1 — Analyse Parallèle

```yaml
# Contexte : review d'un gros codebase — lancer Dev + QA + Architect en parallèle
type: orchestrate
spawn:
  - agent: dev
    task: "Review code quality dans src/ — retourne top 5 problèmes avec file:line"
    output_key: code_quality
  - agent: qa
    task: "Liste les tests manquants dans src/ — retourne [{file, reason}]"
    output_key: missing_tests
  - agent: architect
    task: "Identifie les violations de l'architecture dans src/ — retourne [{file, violation, fix}]"
    output_key: arch_violations
merge:
  strategy: summarize
  save_to: "_bmad-output/implementation-artifacts/full-review-{date}.md"
```

### Pattern 2 — Validation Croisée

```yaml
# Contexte : valider une décision depuis plusieurs angles
type: orchestrate
question: "Doit-on migrer de REST vers GraphQL pour l'API ?"
spawn:
  - agent: architect
    task: "Analyse technique : avantages/inconvénients migration REST→GraphQL pour {project}. Décision recommandée avec justification."
    output_key: tech_analysis
  - agent: pm
    task: "Impact produit : la migration REST→GraphQL affecte-t-elle les features Q2 ? Délai estimé vs valeur."
    output_key: product_impact
merge:
  strategy: vote
  save_to: "_bmad-output/planning-artifacts/adr-rest-vs-graphql.md"
```

### Pattern 3 — Boomerang Tasks (hiérarchique)

```yaml
# Contexte : SM décompose, Dev implémente chaque story, QA valide, SM réagrège
type: orchestrate
mode: sequential-hierarchical      # chaque sous-tâche peut spawner ses propres sous-tâches
spawn:
  - agent: sm
    task: "Décompose la feature 'authentification' en 3 stories atomiques avec ACs. Retourne YAML stories[]."
    output_key: stories

# → SM retourne les stories → pour chaque story, Dev est spawné
  - agent: dev
    task: "Implémente la story {stories[0]}. CC PASS obligatoire. Retourne : {files_changed, tests_added, cc_result}"
    output_key: story_1_impl
    depends_on: stories

  - agent: qa
    task: "Valide story_1 : vérifie les ACs, coverage, edge cases. Retourne : {acs_covered[], gaps[]}"
    output_key: story_1_qa
    depends_on: story_1_impl

merge:
  strategy: structured
  template: "framework/workflows/boomerang-report.tpl.md"
```

---

## Règles Obligatoires

1. **Chaque sous-agent reçoit un contexte minimal** — uniquement les fichiers nécessaires à SA tâche
2. **Chaque sous-agent retourne du JSON ou Markdown structuré** — jamais du prose non-parseable
3. **L'orchestrateur ne modifie JAMAIS les fichiers pendant le spawn** — il attend les résultats
4. **Si un sous-agent échoue**, l'orchestrateur le signale, n'annule pas les autres, et agrège ce qui a réussi
5. **Le merge produit toujours un artefact persisté** — jamais un résultat éphémère

---

*BM-19 Subagent Orchestration Protocol | framework/workflows/subagent-orchestration.md*
