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

## `bmad-completion.zsh` — Autocomplétion

Fournit l'autocomplétion zsh pour tous les subcommands et options de `bmad-init.sh`.

**Installation :**
```bash
# zsh
echo "source /chemin/vers/bmad-custom-kit/framework/tools/bmad-completion.zsh" >> ~/.zshrc
source ~/.zshrc
```

**Subcommands complétés :** session-branch, install, resume, trace, doctor, validate, changelog, hooks, bench, forge, guard, evolve

---

## Architecture commune

Tous les outils Python suivent le même pattern :

1. **CLI argparse** — options cohérentes, sortie humaine + `--json` pour CI
2. **Stdlib only** — aucune dépendance externe (`import re`, `json`, `pathlib`, `datetime`…)
3. **Exit codes normalisés** — 0=OK, 1=warning, 2=critical (compatible CI/CD)
4. **Wrapper `cmd_XX()` dans `bmad-init.sh`** — dispatch, gestion erreurs, check `python3`
5. **Task VS Code** — groupes `test`/`build`, inputs nommés, `problemMatcher`
