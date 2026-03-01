# framework/tools — Référence des outils CLI

Ce dossier contient les outils Python (stdlib only, Python 3.10+) invocables via `bmad-init.sh`.

---

## Outils disponibles

| Fichier | Commande | Description |
|---------|----------|-------------|
| `agent-bench.py` | `bench` | Mesure les scores de performance des agents |
| `agent-forge.py` | `forge` | Génère des squelettes d'agents depuis le besoin projet |
| `context-guard.py` | `guard` | Analyse le budget de contexte LLM des agents |
| `dna-evolve.py` | `evolve` | Fait évoluer la DNA archétype depuis l'usage réel |
| `dream.py` | `dream` | Consolidation hors-session — insights émergents cross-domaine |
| `adversarial-consensus.py` | `consensus` | Protocole de consensus adversarial pour décisions critiques |
| `antifragile-score.py` | `antifragile` | Score d'anti-fragilité — mesure la résilience adaptative |
| `reasoning-stream.py` | `reasoning` | Flux de raisonnement structuré — hypothèses, doutes, assumptions |
| `cross-migrate.py` | `migrate` | Migration cross-projet d'artefacts BMAD (learnings, rules, DNA, agents) |
| `agent-darwinism.py` | `darwinism` | Sélection naturelle des agents — fitness, évolution, leaderboard |
| `stigmergy.py` | `stigmergy` | Coordination stigmergique — phéromones numériques entre agents |
| `gen-tests.py` | *(direct)* | Génère des templates de tests pour les agents |
| `bmad-completion.zsh` | *(source)* | Autocomplétion zsh pour `bmad-init.sh` |

---

## `agent-bench.py` — Bench

Mesure et suit les scores de performance des agents dans le temps.

```bash
bash bmad-init.sh bench --summary           # tableau de bord global
bash bmad-init.sh bench --report            # rapport détaillé par agent
bash bmad-init.sh bench --improve           # génère bench-context.md pour Sentinel
bash bmad-init.sh bench --since 2026-01-01  # filtrer par date
bash bmad-init.sh bench --agent atlas       # agent spécifique
```

**Sortie :** scores 0-100, tendance semaine, agents en dégradation → `_bmad-output/bench-sessions/`

---

## `agent-forge.py` — Forge

Génère des squelettes d'agents prêts à l'emploi depuis une description en langage naturel ou depuis les lacunes détectées dans BMAD_TRACE.

```bash
bash bmad-init.sh forge --from "expert en migrations DB PostgreSQL"
bash bmad-init.sh forge --from-gap          # lacunes depuis BMAD_TRACE
bash bmad-init.sh forge --from-trace        # analyse complète de la trace
bash bmad-init.sh forge --list              # proposals existants
bash bmad-init.sh forge --install db-migrator
```

**12 domaines reconnus :** database, security, frontend, api, testing, data, devops, monitoring, networking, storage, documentation, performance

**Sortie :** `_bmad-output/forge-proposals/agent-[tag].proposed.md`

---

## `context-guard.py` — Guard

Mesure précisément le budget de contexte LLM consommé par chaque agent *avant la première question utilisateur*. Utile pour détecter les agents trop lourds et les optimiser.

```bash
bash bmad-init.sh guard                          # tous les agents
bash bmad-init.sh guard --agent atlas --detail   # détail fichier par fichier
bash bmad-init.sh guard --model gpt-4o           # fenêtre GPT-4o (128K)
bash bmad-init.sh guard --threshold 50           # seuil alerte personnalisé
bash bmad-init.sh guard --suggest                # recommandations de réduction
bash bmad-init.sh guard --optimize               # analyser les optimisations possibles
bash bmad-init.sh guard --recommend-models       # recommander le meilleur LLM par agent
bash bmad-init.sh guard --list-models            # modèles supportés
bash bmad-init.sh guard --json                   # sortie JSON (CI-compatible)
```

**Seuils par défaut :** < 40% ✅ OK — 40-70% ⚠️ WARNING — > 70% 🔴 CRITICAL

**Exit codes CI :** 0 = OK, 1 = warning, 2 = critical

**Multi-LLM Routing :** `--recommend-models` croise le `model_affinity` de chaque agent (reasoning, context_window, speed, cost) avec les modèles disponibles et produit un tableau de recommandation.

**20+ modèles supportés :** Claude Opus 4 (200K), GPT-4o (128K), Gemini 1.5 Pro (1M), Llama 3 8B (8K)…

**7 fichiers analysés par agent :**
1. L'agent lui-même (`agent.md`)
2. Base protocol (`agent-base.md`)
3. Contexte partagé (`shared-context.md`)
4. Contexte projet (`project-context.yaml`)
5. Learnings de l'agent (`agent-learnings/*.md`)
6. Failure Museum (`failure-museum.md`)
7. BMAD_TRACE récent (200 dernières lignes)

---

## `dna-evolve.py` — Evolve

Analyse l'usage réel du projet (BMAD_TRACE, fichiers de décisions, learnings agents) pour proposer des mutations à `archetype.dna.yaml`. Le gate humain est toujours conservé — `--apply` ne fait jamais une modification silencieuse.

```bash
bash bmad-init.sh evolve                     # proposer évolutions
bash bmad-init.sh evolve --report            # rapport Markdown seul
bash bmad-init.sh evolve --since 2026-01-01  # depuis une date
bash bmad-init.sh evolve --apply             # appliquer après votre review
bash bmad-init.sh evolve --dna path/custom.dna.yaml  # DNA source spécifique
```

**3 sources d'analyse :**
1. `BMAD_TRACE.md` — 35+ patterns outils (docker, kubectl, pytest, jest, trivy…)
2. `decisions-log.md` — patterns de décisions récurrents (security-first, perf, observability…)
3. `agent-learnings/*.md` — frustrations agents → opportunités DNA

**Seuils :** 5+ occurrences pour proposer un outil, 3+ pour proposer un trait comportemental

**Sorties :**
- `_bmad-output/dna-proposals/archetype.dna.patch.{date}.yaml`
- `_bmad-output/dna-proposals/dna-evolution-report.{date}.md`

---

## `dream.py` — Dream Mode

Simule une phase de "rêve" : les agents relisent learnings, decisions, trace, failure museum et shared-context, puis produisent des insights cross-domaine qu'aucun agent n'aurait formulés en session. Mode read-only : aucun fichier source n'est modifié.

```bash
bash bmad-init.sh dream                     # dream complet (toutes les sources)
bash bmad-init.sh dream --since 2026-01-01  # depuis une date
bash bmad-init.sh dream --agent dev         # focus un agent
bash bmad-init.sh dream --validate          # valider les insights (no hallucination)
bash bmad-init.sh dream --dry-run           # preview sans écrire
bash bmad-init.sh dream --json              # sortie JSON
```

**6 sources analysées :** learnings, decisions-log, BMAD_TRACE, failure-museum, shared-context, contradiction-log

**4 dimensions d'analyse :**
1. Connexions croisées entre sources de types différents
2. Patterns récurrents (keywords dans ≥ 2 sources)
3. Tensions et contradictions (marqueurs positifs vs négatifs)
4. Opportunités d'amélioration (TODO, "à améliorer", "not yet"…)

**Sortie :** `_bmad-output/dream-journal.md` (avec auto-archive des précédents)

---

## `adversarial-consensus.py` — Consensus

Protocole BFT simplifié pour les décisions architecturales / techniques majeures. 3 votants (technique, business, risque) + 1 avocat du diable qui tente activement de casser la proposition.

```bash
bash bmad-init.sh consensus --proposal "Utiliser PostgreSQL pour le cache sessions"
bash bmad-init.sh consensus --proposal-file proposal.md
bash bmad-init.sh consensus --proposal "..." --threshold 0.75
bash bmad-init.sh consensus --history       # décisions passées
bash bmad-init.sh consensus --stats         # statistiques agrégées
bash bmad-init.sh consensus --json          # sortie JSON
```

**3 perspectives :** technique (🔧), business (📊), risque (⚠️) + Devil's Advocate (😈)

**Seuil de consensus :** 66% par défaut (2/3 des votants), ajustable via `--threshold`

**Sortie :** rapport Markdown + historique JSON dans `_bmad-output/consensus-history.json`

---

## `antifragile-score.py` — Anti-Fragile Score

Mesure comment le système apprend et s'améliore à partir de ses échecs. Croise Failure Museum, SIL signals, contradictions, learnings et decisions pour un score composite 0-100.

```bash
bash bmad-init.sh antifragile                # score compact
bash bmad-init.sh antifragile --detail       # rapport complet
bash bmad-init.sh antifragile --trend        # tendance historique
bash bmad-init.sh antifragile --since 2026-01-01  # depuis une date
bash bmad-init.sh antifragile --json         # sortie JSON
bash bmad-init.sh antifragile --dry-run      # sans sauvegarder
```

**6 dimensions pondérées :**
- **Récupération** (25%) — failures → leçons → règles instaurées
- **Vélocité d'apprentissage** (20%) — volume et distribution des learnings
- **Résolution contradictions** (15%) — taux de résolution
- **Tendance signaux SIL** (15%) — moins de signaux = mieux
- **Qualité des décisions** (10%) — taux de reversal
- **Non-récurrence patterns** (15%) — diversité vs concentration des failures

**Niveaux :** 🔴 FRAGILE (<30) | 🟡 ROBUST (30-60) | 🟢 ANTIFRAGILE (60-100)

**Sortie :** rapport Markdown + historique JSON dans `_bmad-output/antifragile-history.json`

---

## `reasoning-stream.py` — Reasoning Stream

Flux de raisonnement structuré pour capturer le POURQUOI des décisions. Enregistre hypothèses, doutes, assumptions et alternatives dans un stream JSONL avec analyse et compaction.

```bash
# Ajouter une entrée
bash bmad-init.sh reasoning log --agent dev --type HYPOTHESIS --text "Redis pourrait remplacer memcached" --confidence 0.7
bash bmad-init.sh reasoning log --agent qa --type DOUBT --text "Les tests E2E couvrent-ils ce cas?" --tags perf,e2e

# Interroger
bash bmad-init.sh reasoning query --type DOUBT --status open
bash bmad-init.sh reasoning query --agent dev --limit 10

# Analyser
bash bmad-init.sh reasoning analyze            # rapport complet
bash bmad-init.sh reasoning stats              # stats rapides

# Compacter
bash bmad-init.sh reasoning compact --before 2026-01-01
bash bmad-init.sh reasoning compact --dry-run  # preview

# Résoudre
bash bmad-init.sh reasoning resolve --timestamp 2026-01-15T10:30:00 --status validated
```

**Types d'entrées :** 🔬 HYPOTHESIS | ❓ DOUBT | 🧠 REASONING | 📌 ASSUMPTION | 🔀 ALTERNATIVE

**Statuts :** ⏳ open | ✅ validated | ❌ invalidated | 🚫 abandoned

**Sortie :** stream JSONL dans `_bmad-output/reasoning-stream.jsonl`, compaction dans `reasoning-stream-compacted.md`

---

## `bmad-completion.zsh` — Autocomplétion

Fournit l'autocomplétion zsh pour tous les subcommands et options de `bmad-init.sh`.

**Installation :**
```bash
# zsh
echo "source /chemin/vers/bmad-custom-kit/framework/tools/bmad-completion.zsh" >> ~/.zshrc
source ~/.zshrc
```

**Subcommands complétés :** session-branch, install, resume, trace, doctor, validate, changelog, hooks, bench, forge, guard, evolve, dream, consensus, antifragile, reasoning, migrate, darwinism, stigmergy

---

## `cross-migrate.py` — Cross-Project Migration

Exporte et importe des artefacts BMAD entre projets : learnings, règles du Failure Museum, DNA patches, agents forgés, historique consensus, historique anti-fragile.

```bash
# Exporter un bundle complet
bash bmad-init.sh migrate export
bash bmad-init.sh migrate export --only learnings,rules
bash bmad-init.sh migrate export --since 2026-01-01 --output my-bundle.json

# Inspecter un bundle
bash bmad-init.sh migrate inspect --bundle migration-bundle.json

# Comparer avec le projet
bash bmad-init.sh migrate diff --bundle migration-bundle.json

# Importer
bash bmad-init.sh migrate import --bundle migration-bundle.json
bash bmad-init.sh migrate import --bundle migration-bundle.json --dry-run
```

**Types d'artefacts :** learnings, rules, dna_patches, agents, consensus, antifragile

**Format :** bundle JSON portable (`.bmad-bundle.json`) avec manifeste, déduplication à l'import

**Sortie :** `_bmad-output/migration-bundle.json` (défaut)

---

## `agent-darwinism.py` — Agent Darwinism

Évalue la fitness des agents sur des générations successives et propose des actions évolutives : promotion, amélioration, hybridation, dépréciation.

```bash
# Évaluer la fitness
bash bmad-init.sh darwinism evaluate
bash bmad-init.sh darwinism evaluate --since 2026-01-01 --json

# Classement
bash bmad-init.sh darwinism leaderboard

# Actions évolutives
bash bmad-init.sh darwinism evolve
bash bmad-init.sh darwinism evolve --dry-run

# Historique des générations
bash bmad-init.sh darwinism history

# Lignée d'un agent
bash bmad-init.sh darwinism lineage --agent dev
```

**Dimensions de fitness (pondérées, total 100) :**
- Fiabilité (0.25) — AC pass rate, faible taux de failures
- Productivité (0.20) — commits, décisions
- Apprentissage (0.20) — learnings capitalisés
- Adaptabilité (0.15) — diversité stories
- Résilience (0.10) — récupération après failures
- Influence (0.10) — checkpoints, décisions collectives

**Niveaux :** 🟢 ELITE (≥75) | 🟡 VIABLE (40-74) | 🟠 FRAGILE (20-39) | 🔴 OBSOLETE (<20)

**Actions :** ⬆️ PROMOTE | 🔧 IMPROVE | 🧬 HYBRIDIZE | ⬇️ DEPRECATE | 👁️ OBSERVE

**Sortie :** `_bmad-output/darwinism-history.json`

---

## `stigmergy.py` — Coordination Stigmergique

Système de phéromones numériques : les agents déposent des signaux typés dans l'environnement, d'autres agents les captent et adaptent leur comportement. Coordination indirecte — l'environnement est le médium.

### Types de phéromones

| Type | Icône | Description |
|------|-------|-------------|
| NEED | 🔵 | Besoin (review, expertise, clarification) |
| ALERT | 🔴 | Danger (breaking change, dette technique, sécurité) |
| OPPORTUNITY | 🟢 | Amélioration potentielle |
| PROGRESS | 🟡 | Travail en cours |
| COMPLETE | ✅ | Travail terminé, prêt pour la suite |
| BLOCK | 🚧 | Bloqué, en attente de résolution |

### Mécanique

- **Évaporation :** intensité × 0.5^(age/demi-vie). Demi-vie par défaut : 72h (3 jours)
- **Amplification :** chaque renforcement ajoute +0.2 (cap 1.0)
- **Seuil de détection :** signal invisible sous 5% d'intensité
- **Résolution :** marquage explicite d'un signal comme résolu

### Usage

```bash
# Émettre un signal
bash bmad-init.sh stigmergy emit --type NEED --location "src/auth" --text "review sécurité requise" --agent dev
bash bmad-init.sh stigmergy emit --type ALERT --location "src/db" --text "breaking change" --agent architect --tags "db,urgent"

# Détecter les signaux actifs
bash bmad-init.sh stigmergy sense
bash bmad-init.sh stigmergy sense --type ALERT
bash bmad-init.sh stigmergy sense --location "auth" --json

# Renforcer / Résoudre
bash bmad-init.sh stigmergy amplify --id PH-a1b2c3d4 --agent qa
bash bmad-init.sh stigmergy resolve --id PH-a1b2c3d4 --agent qa

# Cartographie
bash bmad-init.sh stigmergy landscape
bash bmad-init.sh stigmergy trails

# Maintenance
bash bmad-init.sh stigmergy evaporate
bash bmad-init.sh stigmergy evaporate --dry-run
bash bmad-init.sh stigmergy stats
```

### Patterns de coordination détectés

- 🔥 **Hot-zone** — ≥3 signaux actifs dans la même zone
- ❄️ **Cold-zone** — Zone précédemment active, désormais silencieuse
- 🎯 **Convergence** — ≥2 agents différents sur la même zone
- 🚧 **Bottleneck** — ≥2 BLOCK dans la même zone
- 🔄 **Relay** — COMPLETE suivi de NEED/PROGRESS par un agent différent

**Sortie :** `_bmad-output/pheromone-board.json`

---

## Architecture commune

Tous les outils Python suivent le même pattern :

1. **CLI argparse** — options cohérentes, sortie humaine + `--json` pour CI
2. **Stdlib only** — aucune dépendance externe (`import re`, `json`, `pathlib`, `datetime`…)
3. **Exit codes normalisés** — 0=OK, 1=warning, 2=critical (compatible CI/CD)
4. **Wrapper `cmd_XX()` dans `bmad-init.sh`** — dispatch, gestion erreurs, check `python3`
5. **Task VS Code** — groupes `test`/`build`, inputs nommés, `problemMatcher`
