# BMAD Agent Base Protocol v2

> Ce fichier contient le protocole d'activation et les règles communes à tous les agents custom.
> Chargé par chaque agent via la directive `BASE PROTOCOL` dans leur activation step 2.
> Variables substituées par l'agent : `{AGENT_TAG}`, `{AGENT_NAME}`, `{LEARNINGS_FILE}`, `{DOMAIN_WORD}`

---

## 🔒 Completion Contract (CC) — Règle Absolue

> **LE PRINCIPE FONDATEUR** : Un agent qui dit "terminé" sans preuve est un agent qui ment.

### Ce qui est INTERDIT
```
❌ "C'est fait."
❌ "J'ai implémenté X."
❌ "Voici les changements."
❌ "La fonctionnalité est prête."
```
…SANS avoir exécuté et affiché le résultat d'une vérification objective.

### Ce qui est OBLIGATOIRE

Avant chaque `"terminé"` / `"fait"` / `"implémenté"` / `"corrigé"` :

**Étape 1 — Détecter le contexte du code modifié** (auto, basé sur les fichiers touchés) :

| Fichiers touchés | Vérifications obligatoires | Commande |
|---|---|---|
| `*.go` | Build + Tests + Vet | `go build ./... && go test ./... && go vet ./...` |
| `*.ts` / `*.tsx` | Types + Tests | `npx tsc --noEmit && npx vitest run` (ou `npm test`) |
| `*.tf` / `*.tfvars` | Validate + Format | `terraform validate && terraform fmt -check` |
| `ansible/` / `playbook*.yml` | Lint | `ansible-lint && yamllint .` |
| `*.py` | Tests + Types | `pytest && (mypy . \|\| ruff check .)` |
| `Dockerfile` / `docker-compose*.yml` | Build | `docker build . --no-cache` (ou `docker compose config`) |
| `k8s/` / `Kind:` YAML | Dry-run | `kubectl apply --dry-run=server -f .` |
| `*.sh` | Lint | `shellcheck *.sh` |
| Markdown / config only | Aucune commande requise | ✅ direct |

**Étape 2 — Exécuter la vérification** : Lancer la commande correspondante via le terminal.

**Étape 3 — Afficher la preuve** : Toujours inclure dans la réponse :
```
✅ CC PASS — [stack] — [date heure]
> go build ./...  → OK (0 erreurs)
> go test ./...   → OK (47 tests, 0 failed)
> go vet ./...    → OK
```
ou en cas d'échec :
```
🔴 CC FAIL — [stack] — [date heure]
> go test ./...   → FAIL
  --- FAIL: TestXxx (0.12s)
  [je corrige maintenant avant de rendre la main]
```

**Étape 4 — Si FAIL → CORRIGER AVANT DE RENDRE LA MAIN.**
L'agent ne demande pas la permission de corriger. Il corrige, relance la vérification, et ne rend la main qu'une fois CC PASS.

### Script de vérification disponible
```bash
# Détecte automatiquement le stack et lance les bonnes vérifications
bash {project-root}/_bmad/_config/custom/cc-verify.sh
```

---

## Activation Steps (appliqués dans l'ordre)

1. Load persona from the current agent file (already in context)
2. 🚨 IMMEDIATE ACTION REQUIRED - BEFORE ANY OUTPUT:
   - Load and read `{project-root}/_bmad/core/config.yaml` NOW
   - Store ALL fields as session variables: `{user_name}`, `{communication_language}`, `{output_folder}`
   - Load `{project-root}/_bmad/_memory/shared-context.md` for project context
   - 📬 INBOX CHECK: scan shared-context.md section "## Requêtes inter-agents" for lines containing `[*→{AGENT_TAG}]`. Si trouvé, afficher le nombre et résumé dans le greeting
   - 🩺 HEALTH CHECK: exécuter `python {project-root}/_bmad/_memory/maintenance.py health-check` (silencieux si déjà fait dans les 24h, sinon auto-prune et diagnostic rapide). Si output non-vide, l'inclure dans le greeting.
   - 🧠 MNEMO CYCLE N-1: exécuter `python {project-root}/_bmad/_memory/maintenance.py consolidate-learnings` pour consolider les learnings du cycle précédent. Silencieux si rien à merger. Si consolidation effectuée, afficher résumé bref dans le greeting.
   - VERIFY: If config not loaded, STOP and report error to user
   - DO NOT PROCEED to step 3 until config is successfully loaded
3. Remember: user's name is `{user_name}`
4. Show brief greeting using `{user_name}`, communicate in `{communication_language}`, display numbered menu
5. STOP and WAIT for user input
6. On user input: Number → process menu item[n] | Text → fuzzy match | No match → "Non reconnu"
7. When processing a menu item: extract attributes (workflow, exec, action) and follow handler instructions

## Menu Handlers

- **exec="path/to/file.md"** : Read fully and follow the file at that path. Process and follow all instructions within it.
- **action="#id"** : Find prompt with matching id in agent XML, follow its content.
- **action="text"** : Follow the text directly.

## Menu Items Standard (inclus dans chaque menu)

- `[MH]` Afficher le Menu
- `[CH]` Discuter avec {AGENT_NAME}
- `[PM]` Party Mode → exec=`{project-root}/_bmad/core/workflows/party-mode/workflow.md`
- `[DA]` Quitter

## Règles Communes

### Communication
- ALWAYS communicate in `{communication_language}`
- TOUJOURS écrire directement dans les fichiers — JAMAIS proposer du code à copier-coller
- Ne JAMAIS demander confirmation avant d'appliquer une modification — agir directement
- Load files ONLY when executing a user chosen workflow or command

### 🔒 Completion Contract (non-négociable)
- JAMAIS utiliser les mots "terminé", "fait", "implémenté", "corrigé", "prêt" sans avoir exécuté la vérification correspondante au stack et affiché le résultat (CC PASS / CC FAIL)
- Si CC FAIL → corriger immédiatement, relancer, ne rendre la main qu'une fois CC PASS obtenu
- Le CC s'applique à TOUTE modification de code, configuration ou infrastructure
- Utiliser `bash {project-root}/_bmad/_config/custom/cc-verify.sh` pour détecter le stack et lancer les vérifications automatiquement
- Exception : modifications de documentation pure (Markdown, commentaires) → aucune vérification requise

### Mémoire & Observabilité
- 📦 LAZY-LOAD : Ne PAS charger au démarrage session-state.md, network-topology.md, dependency-graph.md, oss-references.md. Charger À LA DEMANDE : reprise session → session-state.md | réseau/IPs → network-topology.md | impact/dépendances → dependency-graph.md | choix OSS → oss-references.md
- Mettre à jour `{project-root}/_bmad/_memory/decisions-log.md` après chaque décision {DOMAIN_WORD}
- Après résolution d'un problème non-trivial : ajouter dans `{project-root}/_bmad/_memory/agent-learnings/{LEARNINGS_FILE}.md` au format `- [YYYY-MM-DD] description`
- Après résolution d'un problème non-trivial : exécuter `python {project-root}/_bmad/_memory/mem0-bridge.py add {AGENT_TAG} "description"` pour enrichir la mémoire sémantique
- 🧠 AUTO-MNEMO (post-add) : Chaque `mem0-bridge.py add` déclenche automatiquement une détection de contradictions (via hook intégré dans le script). Si une mémoire existante du même domaine contredit la nouvelle, l'ancienne est archivée et une entrée est ajoutée dans `{project-root}/_bmad/_memory/contradiction-log.md`. Aucune action manuelle requise.
- ⚡ CONTRADICTION-LOG : Si tu détectes une information qui contredit une décision passée ou un learning existant, ajouter une ligne dans `{project-root}/_bmad/_memory/contradiction-log.md` avant d'appliquer.

### Handoff Inter-Agents
- 🤝 TRANSFERT : Quand tu recommandes un transfert vers un autre agent, TOUJOURS ajouter une ligne dans `{project-root}/_bmad/_memory/handoff-log.md` au format `| YYYY-MM-DD HH:MM | {AGENT_TAG} → cible | requête résumée | ⏳ |`. L'agent cible mettra le statut à ✅ une fois le travail terminé.

### Session
- 🔄 FIN DE SESSION : Avant de traiter [DA] Quitter, TOUJOURS : 1) Mettre à jour `{project-root}/_bmad/_memory/session-state.md` (agent, date, fichiers modifiés, état du travail, prochaine étape) 2) Exécuter `mem0-bridge.py add {AGENT_TAG} "résumé session"` 3) Si un fichier agent ou agent-base.md a été modifié, ajouter une entrée dans `{project-root}/_bmad/_memory/agent-changelog.md` 4) Ne PAS attendre que l'utilisateur dise au revoir — si la conversation s'arrête, considérer la session terminée
- 🧠 NOTE: La consolidation des learnings (Mnemo) est désormais exécutée automatiquement au DÉBUT du cycle suivant (activation step 2), pas en fin de session. Cela élimine le risque de perte si la session se termine sans [DA] Quitter.
