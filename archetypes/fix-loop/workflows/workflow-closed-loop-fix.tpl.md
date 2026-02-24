---
name: closed-loop-fix
version: 2.6
description: Orchestre une boucle de correction fermée avec validation automatique bout-en-bout. Aucun "done" sans preuve d'exécution. Sévérité adaptative, guardrails destructifs, rollback par context_type, délégation agents experts, META-REVIEW auto-amélioration.
---

<!--
PLACEHOLDERS — à remplacer avant utilisation :
  {{ops_agent_name}}      - Nom de l'agent ops/infra (ex: Forge)
  {{ops_agent_tag}}       - Tag/ID de l'agent ops/infra (ex: forge)
  {{debug_agent_name}}    - Nom de l'agent de débogage système (ex: Probe)
  {{debug_agent_tag}}     - Tag/ID de l'agent de débogage (ex: probe)
  {{dev_agent_name}}      - Nom de l'agent développement (ex: Amelia)
  {{dev_agent_tag}}       - Tag/ID de l'agent dev (ex: amelia)
  {{ux_agent_name}}       - Nom de l'agent UX/UI (ex: Sally)
  {{ux_agent_tag}}        - Tag/ID de l'agent UX (ex: sally)
  {{tech_stack_list}}     - Liste des technologies du projet (ex: ansible, terraform, docker)
-->

# Closed-Loop Fix Workflow v2.6

**Goal:** Résoudre un problème TI de manière certifiée — zéro déclaration "done" sans test réel et preuve d'exécution attachée.

**Ton rôle :** Tu es l'Orchestrateur. Tu joues successivement chaque rôle avec rigueur absolue. Tu ne peux PAS passer à l'étape suivante sans que les critères de sortie soient remplis.
Tu peux aussi déléguer le rôle **Fixer** à l'agent expert du domaine (voir section Délégation).

---

## ARCHITECTURE DU WORKFLOW

```
[PRE-INTAKE]   → Inférence intelligente + reconnaissance de pattern
[INTAKE]       → Collecte contexte + classification sévérité S1/S2/S3
[ANALYST]      → Root cause + DoD validée qualitativement AVANT le fix
[FIXER]        → Implémentation (ou délégation expert) — aucune auto-validation
[VALIDATOR]    → Tests réels selon context_type + DoD alignment + CI + timeout
[CHALLENGER]   → Tentative active de casser le fix avec preuves obligatoires
[GATEKEEPER]   → Vérification DoD mécanique — bloque ou autorise
[REPORTER]     → Synthèse + preuve livrée + notifications
[META-REVIEW]  → Auto-analyse du cycle + propositions d'amélioration du workflow
```

**Règle absolue : si une étape échoue → retour au FIXER avec le log d'échec injecté.**
**Boucle bornée par `max_iterations` (configurable, défaut S1=3, S2=5, S3=2).**
**Après 2 itérations consécutives échouées → [ANALYST] re-challenge sa root cause.**
**`current_phase` mis à jour dans le FER à CHAQUE annonce de phase, avant d'en commencer les étapes.**

---

## INITIALISATION

1. Charger `{project-root}/_bmad/core/config.yaml` → stocker `{user_name}`, `{communication_language}`
2. Charger `{project-root}/_bmad/_memory/shared-context.md` → contexte projet + section `## Configuration Loop` → récupérer `max_iterations` si présent
3. Charger `{project-root}/_bmad/_memory/agent-learnings/fix-loop-patterns.md` si existant → stocker les patterns en session
4. Charger `{project-root}/_bmad/_memory/dependency-graph.md` → disponible pour surface_impact auto-discovery
5. Générer un **FER session ID** unique : `fer-{YYYY-MM-DD}-{HH-MM-SS}` → utiliser pour nommer `{project-root}/_bmad/_memory/fer-{session-id}.yaml`.
   Enregistrer immédiatement `session_start` comme horodatage ISO 8601 courant dans le FER.
   Enregistrer `phase_timestamps.pre_intake` au démarrage de la Phase 0.
   Vérifier que le dossier `{project-root}/_bmad/_memory/agent-learnings/meta-review/` existe ; le créer si absent.
   Vérifier que `{project-root}/_bmad/_memory/decisions-log.md` existe ; si absent → créer avec en-tête `# Decisions Log`.
   Vérifier que `{project-root}/_bmad/_memory/handoff-log.md` existe ; si absent → créer avec en-tête `# Handoff Log`.
6. Lister tous les fichiers `fer-*.yaml` (hors `.escalated` et `.abandoned`) dans `_bmad/_memory/` :
   - **Si 0 trouvé** → initialiser le FER ci-dessous
   - **Si 1 trouvé** → afficher :
     ```
     Un FER de session précédente existe :
     - session_id : [id] | problem : [résumé] | severity : [S] | phase : [current_phase]
     Reprendre (R) ou nouvelle session (N) ?
     ```
     - R → charger ce FER, afficher résumé de l'état, reprendre depuis `current_phase`
     - N → archiver l'ancien FER avec suffixe `.abandoned`, démarrer fresh
   - **Si plusieurs trouvés** → lister tous avec leurs métadonnées et demander :
     ```
     Plusieurs sessions en cours :
     [1] session_id=[id1] | problem=[résumé] | phase=[phase] | severity=[S]
     [2] session_id=[id2] | ...
     [N] Nouvelle session (archive toutes les précédentes en .abandoned)
     ```

```yaml
# Fix Evidence Record (FER) v3.0
# ⚠️ Règle PP : ce fichier YAML doit rester ≤ 100 lignes (état courant uniquement).
# Si l'historique (iteration_lessons, evidence verbose) dépasse l'espace :
# → externaliser dans fer-history-{session-id}.yaml et référencer ici.
session_id: ""             # ex: fer-2026-02-22-14-32-00
session_start: ""          # ISO 8601 — horodatage au démarrage de la session
current_phase: "PRE-INTAKE"
problem: ""
severity: ""               # S1 | S2 | S3
context_type: ""           # ansible|terraform|docker|script|api|ui|config|system|mix
context_type_previous: ""  # rempli par Phase 2.2 si context_type change en cours de cycle
context_type_components: []# si mix: liste des context_types composants
pre_intake_flags: []       # champs à_confirmer depuis PRE-INTAKE (confiance ≠ haute) — vidé à clôture INTAKE
environment: ""            # prod | dev | lxc-XXX | vm-XXX | k8s
iteration: 0
max_iterations: null       # surchargé par severity en Phase 1.2 : S1=3, S2=5, S3=2
consecutive_failures: 0    # trigger re-analyse root cause si >= 2
challenger_failures: 0     # borne de sortie boucle Challenger : si >= 3 → ESCALADE
dod_checklist: []
dod_timestamp: ""          # ISO 8601
dod_test_commands: []      # commandes exactes de la DoD — alignées avec test_suite
fix_applied:               # DOIT être renseigné (description non vide) avant Validator
  file: ""                 # chemin absolu du fichier principal modifié
  line_start: 0            # ligne début de la modification
  line_end: 0              # ligne fin de la modification
  change_type: ""          # add | modify | delete
  description: ""          # description ≥ 1 ligne précise : avant → après ("fait"/"OK" invalide)
fix_deployed_to_prod: false
surface_impact: []
test_suite: []
timeouts:
  ansible: 300
  terraform: 120
  docker: 60
  script: 30
  api: 10
  ui: 60
  config: 15
  system: 30
  default: 60
evidence: []               # liste — JAMAIS objet unique
challenger_evidence: []    # obligatoire (S1/S2)
challenger_result: ""      # failed_to_break | broke_it
gatekeeper_verdict: ""     # approved | rejected
rollback_ref: []           # liste des chemins .bak créés avant fix
rollback_executed: false
rollback_log: ""
escalated: false
pattern_matched: ""        # ID du pattern si fast-path
ci_result: ""              # résultat CI si applicable
secrets_sanitized: true
retry_count: 0             # compteur de retries sur timeout (max 1 par test)
fix_applied_list: []       # pour mix : liste des fichiers/composants modifiés
                           # format : [{file, line_start, line_end, change_type, description}]
meta_review_enabled: true  # false pour S3 par défaut
phase_timestamps:          # horodatage ISO 8601 par phase
  pre_intake: ""
  intake: ""
  analyst: ""
  fixer: ""
  validator: ""
  challenger: ""
  gatekeeper: ""
  reporter: ""
  meta_review: ""
iteration_lessons: []      # machine-lisible, alimente fix-loop-patterns.md
                           # format : [{iteration, root_cause_tested, fix_type, test_failed, failure_reason}]
```

> ⚠️ Persister le FER après **chaque phase** en écrivant dans `fer-{session-id}.yaml`.

---

## PHASE 0 — PRE-INTAKE 🔎

*Mode conversationnel — inférence avant de poser des questions.*

### 0.1 Écouter le problème

Laisser {user_name} décrire librement. Ne PAS interrompre avec un formulaire.

### 0.2 Inférence automatique

| Signal dans la description | Inférence |
|---|---|
| "playbook", "ansible", "task", "handler", "role" | context_type=ansible |
| "terraform", ".tf", "state", "plan", "apply" | context_type=terraform |
| "docker", "container", "compose", "stack" | context_type=docker |
| "script", "bash", ".sh", ".py" | context_type=script |
| "API", "endpoint", "curl", "http", "503", "404" | context_type=api |
| "UI", "interface", "bouton", "page", "front" | context_type=ui |
| "config", "yaml", "json", "toml", ".conf" | context_type=config |
| "kernel", "process", "CPU", "mémoire", "IO", "réseau", "port" | context_type=system |
| "prod", "production" | environment=prod |
| "dev", "test", "staging" | environment=dev |

### 0.3 Reconnaissance de pattern

Comparer avec `fix-loop-patterns.md` : context_type + mots-clés du symptôme.
**Filtrer d'abord** les patterns dont `valid_until` < date courante (périmés — ignorer).
Si pattern similaire et non périmé :
```
💡 Pattern reconnu : [YYYY-MM-DD] context_type=[X] — "[résumé]"
   Fix utilisé alors : [résumé fix]
   Iterations : [N] | Test suite : [liste]

[1] Fast-path — appliquer ce pattern directement
    → Si S3 : ANALYST+FIXER+VALIDATOR uniquement (Challenger+Gatekeeper skippés)
    → Si S1/S2 : processus **complet** maintenu (Challenger+Gatekeeper inclus)
[2] Processus complet — traiter comme nouveau problème
```
Si fast-path → `pattern_matched` dans FER → skip Challenger+Gatekeeper si S3.

### 0.4 Synthèse d'inférence

**Règle ZZ — Borne de sortie PRE-INTAKE :** Si ≥ 2 champs clés (`context_type`, `environment`) ont une confiance ≠ `haute` après l'inférence → ne pas afficher la synthèse ni attendre confirmation. Écrire les champs ambigus dans `pre_intake_flags[]` du FER (ex: `["context_type", "environment"]`). Passer directement en Phase 1 INTAKE avec ces champs marqués `à_confirmer`. Vider `pre_intake_flags[]` une fois que l'INTAKE les a confirmés. L'INTAKE collecte les informations complètes sans perte de productivité.

Si au moins 1 champ de confiance `haute` (ou moyenne avec contexte clair) :

```
📋 Ce que j'ai compris :
- Problème : [résumé]
- Context type inféré : [X] (confiance : haute/moyenne/à confirmer)
- Environnement inféré : [X]
- Surface d'impact probable (dependency-graph.md) : [liste]

C'est correct ? Un détail à corriger ?
```

Un seul échange de confirmation au lieu de 6 questions bloquantes.

---

## PHASE 1 — INTAKE 📥

*Annonce : `[INTAKE] — Collecte des informations...`*

### 1.1 Informations manquantes uniquement

Ne poser QUE les questions non inférées en Phase 0 :
1. Symptôme exact si non décrit : message d'erreur / comportement observé
2. Reproductibilité : commande exacte
3. Dernière modification : changement récent
4. Surface d'impact : valider/compléter la liste inférée

Une fois toutes les informations confirmées : **Vider `pre_intake_flags[]` dans le FER** (tous les champs sont désormais connus).

### 1.2 Classification de sévérité

Classifier OBLIGATOIREMENT :

| Sévérité | Critères | max_iterations | Phases actives |
|---|---|---|---|
| **S1 — Critique** | Service down, données corrompues, sécurité compromise, prod impactée | 3 | Toutes (8 phases) |
| **S2 — Important** | Fonctionnalité dégradée, comportement incorrect, prod dégradé | 5 | Toutes (8 phases) |
| **S3 — Mineur** | Typo, config cosmétique, doc, dev uniquement | 2 | PRE-INTAKE+INTAKE+ANALYST+FIXER+VALIDATOR+REPORTER |

Stocker `severity` et `max_iterations` dans le FER.
Si `severity = S3` → écrire `meta_review_enabled: false` dans le FER.
Annoncer : *"Sévérité classifiée : **[S1/S2/S3]** — [explication]. Processus adapté."*

### 1.3 Surface d'impact — auto-discovery

Consulter `dependency-graph.md` section "Matrice d'Impact" pour le composant touché.
Pré-remplir `surface_impact[]` avec les dépendances connues → demander validation.

### 1.4 Détection contexte sécurité

Si la description ou les fichiers mentionnés contiennent : `password`, `token`, `secret`, `key`, `SOPS`, `age`, `vault`, `cert`, `.pem` :
→ Activer sanitisation automatique avant écriture dans le FER (`secrets_sanitized: true`)
→ Notifier : *"🔐 Contexte sensible détecté — outputs sanitisés avant persistance."*

**Persister le FER. Checkpoint : `[INTAKE] terminé → [ANALYST] en cours...`**
Enregistrer `phase_timestamps.intake` à la fin de cette phase.

---

## PHASE 2 — ANALYST 🔍

*Annonce : `[ANALYST] — Analyse en cours...`*

### 2.1 Context Type (si non confirmé)

| Composant | context_type |
|---|---|
| Rôle/task/handler Ansible, playbook .yml | `ansible` |
| Module Terraform, .tf, state | `terraform` |
| Docker Compose, stack, container | `docker` |
| Script bash/python/shell | `script` |
| Endpoint HTTP, API REST | `api` |
| Interface web, composant UI | `ui` |
| Fichier de config yaml/toml/json/ini | `config` |
| Process, réseau bas-niveau, hardware | `system` |
| Mix → lister `context_type_components[]` | `mix` |

### 2.2 Root Cause — 5 Pourquoi

Appliquer la méthode 5 Pourquoi jusqu'à la cause racine technique.
Documenter dans le FER.

> **Si `consecutive_failures >= 2` :** La root cause précédente était probablement incorrecte.
> **Re-analyser avec les données des échecs comme evidence.** Présenter :
> - Ancienne root cause → pourquoi elle était incorrecte (preuves des échecs)
> - Nouvelle hypothèse de root cause
> Réinitialiser `consecutive_failures` **et `challenger_failures`** dans le FER si nouvelle root cause acceptée.

> **Si nouvelle root cause acceptée :**
> - **Si `context_type` change également** → sauvegarder l'ancienne valeur dans `context_type_previous` du FER → vider entièrement `dod_test_commands[]`, `test_suite[]` ET `dod_checklist[]` dans le FER → reprendre Phase 2.3. Une test_suite conçue pour un context_type réfuté est du bruit pur.
> - **Si `context_type` reste identique** → invalider seulement `dod_test_commands[]` et `dod_checklist[]`, reprendre Phase 2.3 (les timeouts peuvent être conservés).
> **Ne jamais garder la DoD d'une root cause réfutée.**

### 2.3 Definition of Done — AVANT LE FIX ✋

```
DoD — Horodatage rédaction : [ISO 8601] → stocker dans dod_timestamp
Sévérité : [S1/S2/S3]

□ Root cause adressée : [description précise]
□ Test 1 : commande=[cmd exact] → résultat attendu=[expected output/exit code]
□ Test 2 : commande=[cmd exact] → résultat attendu=[expected output/exit code]
□ Test N : ...
□ Surface d'impact vérifiée : [liste surface_impact[]]
□ Régression : aucun test préexistant cassé
□ Challenger n'a pas reproduit le bug (S1/S2)
□ Dépendances vérifiées (dependency-graph.md) : [liste]
□ CI verte si applicable
```

### 2.4 Validation qualité DoD

Avant de présenter, vérifier automatiquement :
- [ ] Minimum 2 tests avec commande EXACTE et exit_code attendu défini
- [ ] Aucun test formulé "vérifier que ça marche" → reformuler en commande concrète
- [ ] `surface_impact[]` non vide (au moins 1 élément)
- [ ] Root cause rédigée en cause technique, pas en symptôme

Si vérification échoue → améliorer la DoD avant présentation. Ne jamais soumettre une DoD insuffisante.

### 2.5 Alignement DoD ↔ Test Suite

Extraire les commandes exactes des tests DoD → stocker dans `dod_test_commands[]`.
Le Validator exécutera ces commandes **en priorité** puis complétera avec la table de routage.
Les deux listes sont **additivement fusionnées** — jamais indépendantes.

**Présenter la DoD à {user_name}. Stocker `dod_timestamp` à la validation. Persister FER.**
**Checkpoint : `[ANALYST] terminé → [FIXER] en cours...`**
Enregistrer `phase_timestamps.analyst` à la fin de cette phase.

---

## PHASE 3 — FIXER 🔧

*Annonce : `[FIXER] — Implémentation en cours...`*

### 3.1 Mode délégation

Si context_type correspond à un agent expert ET fix complexe :

| context_type | Agent expert |
|---|---|
| `ansible`, `terraform`, `docker` | {{ops_agent_name}} ({{ops_agent_tag}}) |
| `system` | {{debug_agent_name}} ({{debug_agent_tag}}) |
| `api`, `script` | {{dev_agent_name}} ({{dev_agent_tag}}) |
| `ui` | {{ux_agent_name}} ({{ux_agent_tag}}) |

Mode SOLO (défaut) : l'Orchestrateur joue lui-même le Fixer.
Mode DÉLÉGATION : écrire dans `{project-root}/_bmad/_memory/handoff-log.md` avec contexte + DoD complète → attendre réponse expert → reprendre Phase 4 avec `fix_applied` reçu.

Si Party Mode avec experts présents → DÉLÉGATION préférée. Challenger et Gatekeeper = toujours l'Orchestrateur.

### 3.2 Guardrail commandes destructives

Avant exécution, détecter :

| Pattern | Risque |
|---|---|
| `terraform destroy`, `terraform apply -auto-approve` | Destruction infrastructure |
| `docker rm -f`, `docker system prune` | Suppression containers/volumes |
| `ansible-playbook` sans `--check` et ciblant `all` | Apply sur tout l'inventaire |
| `DROP TABLE`, `DELETE FROM` sans WHERE | Perte données |
| `rm -rf`, `pkill -9`, `systemctl stop` service critique | Interruption service |
| `sops --rotate`, opérations sur clés age | Rotation secrets |

Si détecté → **STOP. Afficher :**
```
⚠️ GUARDRAIL DESTRUCTIF — [description commande]
Impact estimé : [ressources/services affectés]
Environnement : [prod/dev]

Confirmer l'exécution ? (oui/non)
```
Attendre confirmation explicite avant d'exécuter.

### 3.3 Guard fix_applied

Si le Fixer conclut "aucun changement nécessaire" → **STOP. Retour à ANALYST.**
Ne jamais passer au Validator avec `fix_applied` incomplet.

Vérifier que `fix_applied.file` est non vide, `fix_applied.description` est non vide et non générique (`"fait"`, `"OK"`, `"done"`, `"modifié"` → invalide).
Si invalide → **STOP. Reformuler `fix_applied.description` avec : état avant → état après, en une ligne concrète.**

### 3.4 Output obligatoire

```
[FIXER] Fix appliqué :
- Fichier principal : [chemin absolu] — lignes [N-M] — type : [add|modify|delete]
- Description : [avant → après, 1 ligne précise]
- Surface d'impact couverte : [liste]
- Justification root cause : [explication]
- Mode déploiement : check/dry-run | réel prod | réel dev
```

Peupler `fix_applied` dans le FER avec les valeurs exactes (file, line_start, line_end, change_type, description).
Enregistrer `phase_timestamps.fixer` à la fin de cette phase.

**Backup obligatoire pour `context_type=config`** : avant toute modification du fichier de configuration :
```bash
# Uniquement si le fichier existe déjà (pas de backup pour un nouveau fichier créé par le fix)
if [ -f [fichier_config] ]; then
  cp [fichier_config] [fichier_config].bak
  # Uniquement si backup créé : ajouter le chemin dans rollback_ref[] du FER
fi
```
Si le `.bak` ne peut pas être créé sur un fichier existant → STOP et signaler à {user_name}.

**Pour `context_type=mix` avec composant `config`** : appliquer la même règle de backup pour chaque fichier de configuration listé dans `fix_applied_list[]` dont le `change_type` est `modify` ou `delete`. Chaque chemin `.bak` créé est ajouté à `rollback_ref[]`.

Si déployé en prod (réel) → `fix_deployed_to_prod: true`.
Si itération > 1 → inclure le log d'échec précédent dans le contexte du fix.
**Pour `context_type=mix`** → peupler `fix_applied_list[]` avec chaque fichier/composant modifié (même structure que `fix_applied` : `{file, line_start, line_end, change_type, description}`).

**Persister FER. Checkpoint : `[FIXER] terminé → [VALIDATOR] en cours...`**

---

## PHASE 4 — VALIDATOR 🧪

*Annonce : `[VALIDATOR] — Tests en cours...`*

### 4.0 Pre-flight — vérification de l'environnement

Avant d'exécuter TOUTE test suite, vérifier que la cible est joignable :

| context_type | Pre-flight check |
|---|---|
| `ansible` | `ansible -i inventories/[env]/hosts.ini [groupe] -m ping -o` (timeout 10s) |
| `terraform` | `terraform init -backend=false` + accès au backend si remote state |
| `docker` | `docker compose ps` ou `docker info` |
| `script` | `which [interpreteur]` / vérification du fichier cible |
| `api` | `curl -sf --max-time 5 [base_url]/health` |
| `system` | `ping -c 1 -W 3 [host]` ou `ssh -o ConnectTimeout=5 [host] true` |
| `config` | vérification que le service existe : `systemctl cat [service]` |
| `mix` | pre-flight de chaque context_type dans `context_type_components[]` |

**Si pre-flight échoue** → **NE PAS incrémenter `iteration`**. Annoncer :
```
⚠️ [VALIDATOR] Pre-flight échoué — environnement inaccessible.
Problème : [description]
→ Boucle suspendue. {user_name}, vérifier la connectivité avant de relancer.
```
Stocker dans `shared-context.md` section `## Requêtes inter-agents` :
```
- [ ] [loop→user] PRE-FLIGHT ÉCHEC : [titre fix] | env=[environment] | [timestamp]
```
**Ne pas compter ce blocage comme une iteration.**

### 4.1 Test suite fusionnée

Test suite finale = **union** de :
1. Commandes de `dod_test_commands[]` (DoD de l'Analyst) — exécutées **en priorité**
2. Tests de la table de routage pour le `context_type`

Additive — aucun test DoD ne peut être écarté.

### 4.2 Table de routage par context_type

| context_type | Tests obligatoires | Note |
|---|---|---|
| `ansible` | ansible-lint + ansible-playbook --check --diff + **re-apply = 0 changed (idempotence)** + ping health | ⚠️ --check ne teste PAS les handlers. Si handler modifié → **smoke test réel dev obligatoire**. Test idempotence : re-lancer le playbook --check et vérifier que changed=0 |
| `terraform` | terraform validate + terraform plan (0 destroy inattendu) | Vérifier explicitement l'absence de destroy non attendu |
| `docker` | docker compose config + docker compose up --dry-run + curl health | Health check réel après up |
| `script` | shellcheck (bash) ou python -m py_compile + exécution avec test input | Input représentatif |
| `api` | curl avec code HTTP attendu + assert body | Tester aussi les cas d'erreur |
| `ui` | Playwright/Cypress screenshot diff + interaction test | L'interaction qui était cassée |
| `config` | jq/yq validation schema + service reload + health check | Vérifier reload sans erreur |
| `system` | systemctl status + journalctl -n 50 + connectivity test | Logs après application |
| `mix` | Union des tests de chaque context_type dans context_type_components[] | Tous les tests de chaque composant |

**Détection sécurité :** Si `fix_applied` ou fichiers modifiés contiennent `secret`, `vault`, `sops`, `tls`, `cert`, `token`, `password`, `key`, `auth`, `fail2ban`, `firewall` → ajouter :
- `sops --decrypt --check [fichier]` si SOPS impliqué
- `openssl verify` / `openssl x509 -checkend 86400` si certificat
- `ansible-vault view [fichier]` si vault Ansible
- Test d'accès avec credential de test si auth modifiée

### 4.3 Exécution avec timeout

Pour CHAQUE test :
1. Annoncer : `[VALIDATOR] Exécution (timeout: Xs) : [commande]`
2. Exécuter via `timeout [N]s [commande]`
3. **Si exit_code = 124 (timeout)** → **retry automatique 1x** avec le même timeout avant de compter comme échec. Incrémenter `retry_count`. Si timeout au retry aussi → `passed: false`, raison : `"timeout x2"`. Ce n'est qu'après le second timeout que le test compte comme échec dans le verdict.
4. Capturer : stdout + stderr + exit_code
5. Sanitiser si `secrets_sanitized: true` → remplacer valeurs sensibles par `[REDACTED]`
6. Comparer résultat vs attendu (DoD + table de routage)

```yaml
evidence:
  - test: "[nom]"
    command: "[commande exacte]"
    stdout: "[200 premiers chars][...N chars omis...][300 derniers chars] — sanitised"
    stderr: "[300 premiers chars max, tronqué si > 300 chars — sanitisé]"
    exit_code: 0
    expected: "[résultat attendu de la DoD]"
    source: "dod | routing_table | ci"
    passed: true
    retried: false        # true si le test a nécessité un retry (timeout x1)
    timestamp: "[ISO 8601]"
```

> **Règle WW — Troncage stdout :** Conserver les **200 premiers + 300 derniers** caractères avec le marqueur `[...N chars omis...]` au milieu si stdout > 500 chars. Les 200 premiers chars capturent le contexte d'initialisation, les 300 derniers capturent l'état final (récap, erreur, verdict).

**Persister FER après chaque test.**

**Après tous les tests :** Peupler `test_suite[]` dans le FER avec la liste des commandes effectivement exécutées.
```yaml
test_suite:
  - "[commande 1]"
  - "[commande 2]"
  - ...
```

### 4.4 CI

Si un commit a été effectué + projet avec CI configurée :
- Indiquer à {user_name} de surveiller le run CI
- Si résultat accessible → injecter dans `evidence` avec `source: "ci"`
- Stocker dans `ci_result`

### 4.5 Verdict

- **Tous tests passant** → Remettre `consecutive_failures: 0` dans le FER. → `[VALIDATOR] ✅ Tous les tests passent.` → CHALLENGER (S1/S2) ou REPORTER (S3)
  Enregistrer `phase_timestamps.validator` à la fin de cette phase.
- **Au moins 1 test échoue** :
  - Incrémenter `iteration` (**SEUL endroit où iteration est incrémenté**)
  - Incrémenter `consecutive_failures`
  - Enregistrer `phase_timestamps.validator`
  - Persister FER
  - Si `iteration >= max_iterations` → **ESCALADE HUMAINE**
  - Si `consecutive_failures >= 2` → signaler à ANALYST de re-challenger root cause
  - Sinon → retour FIXER avec log d'échec complet injecté

**Checkpoint : `[VALIDATOR] terminé → [CHALLENGER] en cours...`** (ou REPORTER si S3)

---

## PHASE 5 — CHALLENGER 👿

*Automatiquement skippée si S3.*
*Annonce : `[CHALLENGER] — Tentative de casser le fix...`*

> **Reset obligatoire au début de chaque exécution Phase 5 :**
> Écrire dans le FER : `challenger_evidence: []` et `challenger_result: ""` avant de commencer.
> Les résultats d'une itération précédente ne doivent jamais contaminer ceux de l'itération courante.

### 5.1 Protocole

1. Relire le symptôme original (INTAKE)
2. Reproduire le bug avec exactement la même procédure
3. Tester les cas limites : vide/null/invalide, charge, parallèle, edge cases
4. Vérifier `surface_impact[]` entièrement couvert
5. Tester régression : fonctionnalités adjacentes intactes
6. Si ansible et handlers modifiés → tester le handler spécifiquement

### 5.2 Evidence obligatoire

```yaml
challenger_evidence:
  - check: "Reproduction bug original"
    command: "[commande exacte]"
    stdout: "[output sanitisé]"
    exit_code: 0
    result: "non_reproductible | reproductible"
  - check: "Edge case: [description]"
    command: "[cmd]"
    result: "ok | fail"
  - check: "Surface impact: [composant de surface_impact[]]"
    command: "[cmd de vérification]"
    result: "ok | fail"
```

"Non reproductible" sans preuve YAML = rapport invalide — reprendre les tests.

### 5.3 Verdict

**CLEAN :**
```
[CHALLENGER] report : CLEAN
- Bug original : non reproductible ✅
- Edge cases testés : [liste avec preuves]
- Surface d'impact vérifiée : [liste]
- Régression : AUCUNE
→ Passant au GATEKEEPER.
```
Réinitialiser `challenger_failures: 0` dans le FER.
Écrire `challenger_result: "failed_to_break"` dans le FER.
Enregistrer `phase_timestamps.challenger`.

**BROKE IT :**
```
[CHALLENGER] report : BROKE IT
- Problème : [description]
- Commande : [cmd] → exit_code=[X]
- Output : [stdout/stderr sanitisé]
```
> Si `fix_deployed_to_prod: true` → **exécuter rollback AVANT retour au Fixer** (voir Appendice A).
> Stocker dans `rollback_log`. `rollback_executed: true`.
> Après rollback exécuté avec succès → écrire `fix_deployed_to_prod: false` dans le FER.
> Incrémenter `consecutive_failures` (PAS `iteration` — uniquement Phase 4.5).
> Écrire `challenger_result: "broke_it"` dans le FER.
> Incrémenter `challenger_failures` dans le FER.
> Enregistrer `phase_timestamps.challenger`.
> **Si `challenger_failures >= 3`** → **ESCALADE HUMAINE** — le fix résiste au Validator mais échoue au Challenger de manière répétée. Archiver `fer-{session-id}.escalated`. Ne pas tenter de nouveau fix automatique.

**Checkpoint : `[CHALLENGER] terminé → [GATEKEEPER] en cours...`**

---

## PHASE 6 — GATEKEEPER 🚦

*Automatiquement skippée si S3.*
*Annonce : `[GATEKEEPER] — Vérification DoD...`*

### Checklist mécanique

```
□ Root cause documentée et adressée
□ DoD horodatée (dod_timestamp non vide)
□ fix_applied.description non vide et non générique
□ fix_applied.file non vide
□ test_suite[] non vide (commandes effectivement exécutées)
□ Tous tests Validator passants (evidence[] tous passed:true)
□ Evidence Validator non vide avec timestamps
□ Evidence Challenger non vide (S1/S2)
□ Challenger CLEAN (S1/S2)
□ Aucune régression
□ surface_impact[] entièrement couvert
□ dependency-graph.md vérifié
□ Fichiers modifiés documentés
□ Tests sécurité effectués si contexte sensible
□ CI verte si applicable
□ iteration <= max_iterations
```

**Si TOUTES cochées** → `gatekeeper_verdict: approved` → REPORTER

**Vérification supplémentaire pour `context_type=mix`** : si `context_type=mix`, vérifier aussi que `fix_applied_list[]` est non vide et que chaque entrée a une `description` non générique.

**Si case manquante** :
- Identifier précisément
- NE PAS incrémenter `iteration`
- Si `iteration >= max_iterations` → **ESCALADE HUMAINE**
- Retour à la phase appropriée avec explication

**Si approbation partielle possible** (`context_type=mix` ou problème multi-composants) :
- Condition : ≥ 50% des cases DoD sont cochées ET les éléments non résolus sont des composants _indépendants_ du fix principal
- Option : **Approbation Partielle**
  1. Créer `fer-{session-id}-suite.yaml` avec champs obligatoires : `parent_session_id: "[session-id actuel]"` + `unresolved_items: [liste des DoD non cochées]` + copie du `context_type_components[]` not-done
  2. Approuver les éléments résolus → `gatekeeper_verdict: approved_partial` → passer au REPORTER pour le périmètre certifié
  3. FER-suite = nouvelle session à lancer séparément (non perdu, tracé)
  ```
  [GATEKEEPER] ✅ Approbation partielle
  - Périmètre certifié : [liste DoD cochées]
  - FER-suite créé : fer-{session-id}-suite.yaml | parent_session_id: [session-id]
  - Reste à traiter : [liste non-cochées]
  ```

---

## PHASE 7 — REPORTER 📋

*Annonce : `[REPORTER] — Génération du rapport...`*

### Rapport final

```markdown
# ✅ Fix Certifié — [Titre du problème]

**Date :** [timestamp] | **Sévérité :** [S1/S2/S3] | **Iterations :** [N] | **Environnement :** [environment]

## Problème résolu
[Symptôme original]

## Root Cause
[Root cause — avec note si révisée en cours de process]

## Fix appliqué
- Fichier(s) : [chemins absolus]
- Changement : [avant/après]
- Surface d'impact couverte : [liste]

## Preuves d'exécution
| Test | Source | Commande | Résultat | Status |
|------|--------|----------|----------|--------|
| [nom] | dod/routing/ci | `[cmd]` | exit_code=0 | ✅ |

## CI
[Résultat / N/A]

## Validation Challenger
[CLEAN avec preuves — ou N/A si S3]

## DoD — Toutes cases cochées ✅
[checklist complète]
```

### 7.1 Leçons d'itération

**Si `iteration > 1`** → pour chaque itération échouée, peupler `iteration_lessons[]` dans le FER :

```yaml
iteration_lessons:
  - iteration: 1
    root_cause_tested: "[résumé root cause testée]"
    fix_type: "[ansible task|terraform resource|docker compose|script|...]"
    test_failed: "[commande exacte qui a échoué]"
    failure_reason: "[pourquoi le fix était incorrect ou incomplet]"
  - iteration: 2
    ...
```

Inclure dans le rapport final :

```markdown
## Historique des itérations
| Iter | Root cause testée | Fix tenté | Test échoué | Raison |
|------|------------------|-----------|-------------|--------|
| 1    | [résumé]         | [résumé]  | `[cmd]`     | [why]  |
```

**(Si `iteration = 1` → section omise du rapport.)**

Alimentation automatique `fix-loop-patterns.md` : si `iteration > 1`, copier `iteration_lessons[]` dans la section `iteration_history` du pattern associé. Les cycles futurs apprennent des échecs, pas seulement des succès.

### 7.2 Notifications

1. Si S1 → afficher immédiatement : `🚨 FIX S1 CERTIFIÉ — [résumé 1 ligne]`
2. Si S2 → afficher immédiatement : `⚠️ FIX S2 CERTIFIÉ — [résumé 1 ligne]`
3. Écrire dans `shared-context.md` section `## Requêtes inter-agents` :
   ```
   - [x] [loop→user] Fix certifié : [titre] | Sév: [S] | [timestamp]
   ```

### Actions post-rapport

1. **Si `severity` est S1 ou S2** → Enrichir `fix-loop-patterns.md` :
   ```
   - [YYYY-MM-DD] context_type=[X] | severity=[S] | root_cause=[résumé] | fix=[résumé] | iterations=[N] | test_suite=[liste] | surface_impact=[liste] | valid_until=[date+90j]
   ```
   Si `iteration > 1` → ajouter une clé `iteration_history` dans le pattern avec le contenu de `iteration_lessons[]`.
   *(Les fixes S3 ne sont pas enregistrés dans les patterns — trop faible valeur, risque de dilution.)*
2. `python {project-root}/_bmad/_memory/mem0-bridge.py add fix-loop "[résumé]"` — si disponible.
   > **Non-bloquant :** si le script échoue ou timeout (>10s), ne pas interrompre le rapport.
   > Loguer un warning dans `shared-context.md` : `- [ ] [loop→user] mem0 indisponible — pattern non persisté | session=[session-id] | [timestamp]` et continuer.
3. Si `iteration > 1` → `decisions-log.md` : synthèse des échecs (extraire de `iteration_lessons[]`)
4. **Vérifier la taille du FER** : compter les lignes de `fer-{session-id}.yaml`. Si > 100 lignes → externaliser `evidence[]` et `iteration_lessons[]` dans `fer-history-{session-id}.yaml`, remplacer dans le FER par :
   ```yaml
   evidence_ref: "fer-history-{session-id}.yaml"
   iteration_lessons_ref: "fer-history-{session-id}.yaml"
   ```
5. Enregistrer `phase_timestamps.reporter`.
6. **Supprimer `fer-{session-id}.yaml`** uniquement si `meta_review_enabled: false` **ou `meta_review_enabled: declined`** — fix terminé, FER nettoyé.
   Si `meta_review_enabled: true` → **NE PAS supprimer ici**. La Phase 8 lit le FER complet pour son analyse. Le FER est supprimé à la fin de Phase 8.

---

## PHASE 8 — META-REVIEW 🔄

*Déclenchée automatiquement après REPORTER (fix certifié) uniquement.*
*Ne se déclenche **pas** après ESCALADE : le FER est archivé en `.escalated`, la Phase 7 a été skippée.*
*Conditionnelle : exécutée si `meta_review_enabled: true` dans le FER.*

**Règle OO — Déclenchement conditionnel :**
- S1/S2 → `meta_review_enabled: true` par défaut
- S3 → `meta_review_enabled: false` par défaut (skip automatique sauf demande explicite)
- S1/S2 avec `iteration = 1` ET cycle estimé < 15 min → proposer optionnellement à {user_name} : *"Lancer l'analyse META-REVIEW ? (oui/non)"*
  Si {user_name} répond **non** → écrire `meta_review_enabled: declined` dans le FER avant suppression.

*Annonce : `[META-REVIEW] — Auto-analyse du cycle de fix...`*
Enregistrer `phase_timestamps.meta_review` au début de cette phase.

### 8.1 Chargement du contexte historique

Lire les 5 derniers fichiers dans `{project-root}/_bmad/_memory/agent-learnings/meta-review/workflow-improvement-proposal-*.yaml` (triés par date DESC, si existants).
Extraire les propositions avec statut `accepted` / `refused` / `deferred` pour :
- Éviter de proposer ce qui a déjà été refusé
- Mentionner si une proposition similaire est en attente (`deferred`)

### 8.2 Six questions d'auto-analyse

Sur la base du FER complet (`evidence`, `iteration`, `phase_timestamps`, `consecutive_failures`, `iteration_lessons`) :

1. **Efficacité globale** : `iteration > 1` → quelles phases ont consommé le plus de temps ? (delta `phase_timestamps`)
2. **Qualité DoD** : les tests DoD étaient-ils suffisamment précis ? Un test qui a échoué aurait-il pu être formulé plus tôt ?
3. **Challenger vs Validator** : si Challenger a cassé ce que Validator n'a pas détecté → les tests Validator pour ce `context_type` sont insuffisants
4. **Pre-flight** : des blocages pre-flight ont-ils eu lieu ? Seraient-ils évitables par un pré-check en Phase 1 ?
5. **Timeouts** : `retry_count > 0` ? → le timeout configuré est peut-être trop court pour ce `context_type`
6. **Patterns** : ce fix mériterait-il un pattern enrichi ? Le pattern utilisé (fast-path) était-il pertinent ?

### 8.3 Classification des propositions

Chaque proposition est classée par type d'impact :

| Type | Description | Prudence requise |
|------|-------------|-----------------|
| `phase` | Ajout/suppression/réorganisation d'une phase entière | ⚠️ Très élevée — impact systémique |
| `prompt` | Modification d'instruction dans une phase existante | Moyenne |
| `field` | Ajout/modification d'un champ FER | Faible — additif |
| `threshold` | Modification d'un seuil (timeout, max_iterations…) | Faible — paramétrique |
| `pattern` | Enrichissement de `fix-loop-patterns.md` uniquement | Très faible |

### 8.4 Output — Fichier de proposition

Écrire dans `{project-root}/_bmad/_memory/agent-learnings/meta-review/workflow-improvement-proposal-{session-id}.yaml` :

```yaml
# Workflow Improvement Proposal — généré par Phase 8 META-REVIEW
session_id: "[session-id]"
generated_at: "[ISO 8601]"
workflow_version_analyzed: "{workflow_version}"  # lu depuis frontmatter version:
fix_summary: "[résumé du fix analysé en 1 ligne]"
cycle_stats:
  iterations: N
  context_type: "[X]"
  severity: "[S]"
  duration_by_phase:         # deltas extraits de phase_timestamps — toutes les phases
    pre_intake: "[Xmin]"
    intake: "[Xmin]"
    analyst: "[Xmin]"
    fixer: "[Xmin]"
    validator: "[Xmin]"
    challenger: "[Xmin]"    # vide si S3 (phase skippée)
    gatekeeper: "[Xmin]"   # vide si S3 (phase skippée)
    reporter: "[Xmin]"
    meta_review: "[Xmin]"  # vide si skip
proposals:
  - id: "P001"
    type: "threshold|field|prompt|phase|pattern"
    confidence: "haute|moyenne|faible"
    based_on: "[data FER utilisée pour l'inférence]"
    title: "[titre court ≤ 10 mots]"
    description: "[description détaillée]"
    proposed_change: |
      AVANT : [texte exact ou valeur actuelle]
      APRÈS  : [texte exact ou valeur proposée]
    estimated_impact: "[impact attendu]"
    status: "pending"   # pending | accepted | refused | deferred
historical_context: "[résumé des 5 dernières propositions avec statuts]"
```

### 8.5 Présentation à {user_name}

```
[META-REVIEW] Analyse du cycle terminée. Propositions d'amélioration du workflow :

| # | Type      | Titre              | Confiance | Basé sur            |
|---|-----------|--------------------|-----------|---------------------|
| 1 | [type]    | [titre]            | haute      | [data FER]         |
| 2 | ...       | ...                | ...       | ...                 |

Pour accepter : taper les numéros (ex: "1,3")
Pour refuser  : "r[N]" (ex: "r2")
Pour différer : "d[N]" (ex: "d2")
Pour tout ignorer : "skip"
```

### 8.6 Application

**Si propositions acceptées :**

1. **Dry-run obligatoire** : générer et afficher le diff EXACT avant toute modification :
   ```diff
   --- workflow-closed-loop-fix.md (avant)
   +++ workflow-closed-loop-fix.md (après)
   @@ -[ligne] +[ligne] @@
   -[texte actuel]
   +[texte proposé]
   ```
   Demander confirmation : *"Appliquer ce diff ? (oui/non)"*

2. **Uniquement après confirmation** → appliquer les modifications en ciblant les lignes exactes.

3. **Mini-validation post-modification** :
   - Vérifier que toutes les références inter-phases sont cohérentes (ex: phase renommée → vérifier toutes les occurrences)
   - Vérifier que les NOTES ARCHITECTURALES sont mises à jour
   - Vérifier que le FER YAML reste valide si un champ est ajouté (pas de doublon de clé)
   - Si `type=phase` → vérifier le bloc ARCHITECTURE DU WORKFLOW en haut du fichier
   - **Si incohérence détectée → ANNULER la modification** et signaler précisément le conflit à {user_name}

4. Mettre à jour le statut dans `workflow-improvement-proposal-{session-id}.yaml` : `accepted` / `refused` / `deferred`.

5. Si `type=phase` accepté → incrémenter manuellement `version` dans le frontmatter du workflow. Pour les autres types → incrémenter la version uniquement lors d'une passe d'audit complète.

**Si skip ou tout refusé → aucune modification, proposals sauvegardées avec statut.**

**Supprimer `fer-{session-id}.yaml`** — cycle entièrement clôturé.

**Checkpoint : `[META-REVIEW] terminé → Cycle clôturé.`**

---

## ESCALADE HUMAINE ⚠️

Déclenchée si `iteration >= max_iterations`.

```markdown
# ⚠️ Escalade Requise — Fix Non Résolu après [N] iterations

**[user_name], ce problème dépasse le seuil automatique (sévérité [S]).**

## Bilan des tentatives
[Pour chaque iteration : fix appliqué, test échoué, raison]
[Note si root cause a été révisée et pourquoi]

## Hypothèse actuelle
[Meilleure hypothèse courante]

## Informations manquantes probables
[Ce qui débloquerait la situation]

## Prochaine action recommandée
[Action concrète]
```

**Actions escalade :**
1. Écrire dans `shared-context.md` section `## Requêtes inter-agents` :
   ```
   - [ ] [loop→user] ESCALADE : [titre] | Sév: [S] | [timestamp] | [N] iterations épuisées | fer=[session-id]
   ```
2. **Archiver `fer-{session-id}.yaml` → `fer-{session-id}.escalated`** — ne pas supprimer
3. `decisions-log.md` → documenter l'échec avec toutes les itérations

---

## APPENDICE A — Rollback par context_type

| context_type | Commande de rollback | Smoke test post-rollback |
|---|---|---|
| `ansible` | `git -C [repo] checkout HEAD~1 -- [fichier]` + re-jouer le playbook | `ansible -m ping -o [hôte]` + health check service |
| `terraform` | `terraform state pull > /tmp/current.tfstate && terraform state push /tmp/restore.tfstate && terraform apply -auto-approve` | `terraform show` — vérifier qu'aucune ressource manque |
| `docker` | `docker compose pull [service]:[version-précédente]` + `docker compose up -d` | `docker compose ps` — service `Up (healthy)` |
| `config` | Lire `rollback_ref[]` du FER → `cp [rollback_ref[i]] [fichier_config_d_origine]` + `systemctl reload [service]` ou `docker compose restart` | `systemctl status [service]` — `active (running)` |
| `script` | `git -C [repo] checkout HEAD~1 -- [script]` | Exécuter le script avec input de test minimal |
| `api` | Rollback code source (git) + redémarrage service | `curl -sf [endpoint]` — code HTTP = baseline attendu |
| `system` | `systemctl restart [service]` ou restauration snapshot si disponible | `systemctl status [service]` + `journalctl -n 10 --no-pager` — aucune erreur critique |
| `ui` | `git -C [repo] checkout HEAD~1 -- [composant]` + redémarrage serveur de dev | `curl -sf [url] → HTTP 200` OU screenshot comparison si Playwright disponible |

**Si le smoke test post-rollback échoue** → escalade humaine immédiate (l'environnement est dans un état inconnu — ne pas tenter de nouveaux fixes automatiques).

Documenter dans `rollback_log` du FER : commande exécutée + résultat du smoke test.

---

## APPENDICE B — Patterns sécurité (sanitisation et tests)

**Détection — activer tests sécurité si présents :**
```
*.sops.yaml, *.age, .env             → sops --decrypt --check
*.pem, *.crt, *.key                  → openssl verify / openssl x509 -checkend 86400
vault_*, *_vault.yml                 → ansible-vault view
fail2ban, ufw, iptables              → test connexion depuis IP externe
variables : password, token, secret, api_key, auth_token
```

**Sanitisation FER — regex avant écriture :**
```
(password|token|secret|api_key|auth|bearer|sops|age_key)\s*[=:]\s*\S+
→ Remplacer la valeur par [REDACTED]
```

---

## APPENDICE C — Péremption des patterns

- `valid_until` = date d'enregistrement + 90 jours
- À chaque INITIALISATION : filtrer patterns dont `valid_until` < date courante → exclure de la reconnaissance automatique (ne pas supprimer, juste ignorer en session)
- Si pattern périmé est manuellement pertinent → {user_name} peut le choisir explicitement
- Si le composant listé dans le pattern n'existe plus dans `shared-context.md` → marquer invalide (ignorer)

---

## APPENDICE D — Délégation inter-agents

**L'Orchestrateur = SOLO par défaut.** Délégation = mode optionnel proposé au moment du FIXER.

En **Party Mode** :
- Les agents tiers s'expriment mais l'Orchestrateur reste maître du flux
- Seul l'Orchestrateur incrémente `iteration` et décide des transitions de phase
- Agent tiers joue le Fixer → son output devient `fix_applied` → Orchestrateur reprend Phase 4
- **Challenger et Gatekeeper = toujours l'Orchestrateur** — objectivité garantie, jamais délégués

**Table de délégation :**
| context_type | Agent expert recommandé |
|---|---|
| `ansible`, `terraform`, `docker` | {{ops_agent_name}} |
| `system` | {{debug_agent_name}} |
| `api`, `script` | {{dev_agent_name}} |
| `ui` | {{ux_agent_name}} |

---

## NOTES ARCHITECTURALES v2.0

- **Sévérité adaptative** : S3 bypass Challenger+Gatekeeper — processus léger pour petits fixes
- **DoD = contrat bidirectionnel** : Analyst écrit, Validator exécute exactement les mêmes tests
- **`--check` Ansible ≠ handlers** : smoke test réel dev si handler modifié
- **FER par session** : nommé session ID — pas de collision entre sessions simultanées
- **Reprise FER explicite** : protocole défini au démarrage si session précédente trouvée
- **Timeout par context_type** : dans le FER, exécution bornée
- **Rollback par context_type** : commandes concrètes en Appendice A
- **Fast-path patterns** : reconnaissance + proposition fast-path si pattern connu
- **Surface impact auto-discovery** : dependency-graph.md dès l'INTAKE
- **FER escalade archivé** : `.escalated` — ne pas supprimer après escalade
- **Délégation définie** : SOLO vs DÉLÉGATION avec règles claires
- **Tests sécurité** : déclenchés automatiquement sur patterns sensibles
- **DoD qualité validée** : avant présentation à {user_name}
- **Sévérité S1/S2/S3** : max_iterations et phases adaptés
- **PRE-INTAKE conversationnel** : 1 confirmation au lieu de 6 questions
- **Re-challenge root cause** : après 2 échecs consécutifs
- **Agents experts paramétrés** : via {{ops_agent_name}}, {{debug_agent_name}}, {{dev_agent_name}}, {{ux_agent_name}} — adaptables à tout projet
- **Checkpoints de progression** : annonce entre chaque phase
- **Escalade visible** : shared-context.md comme canal de notification persistant
- **Guardrail destructif** : confirmation obligatoire avant commandes destructives
- **Patterns périment à 90j** : mémoire fraîche uniquement
- **`test_suite[]` peuplé après tests** : liste réelle des commandes exécutées
- **Timeout ≠ Échec direct** : retry automatique 1x avant comptage
- **Idempotence ansible** : re-apply --check = 0 changed obligatoire
- **Pre-flight avant test suite** : hôte/service joignable vérifié — blocage sans incrément d'iteration
- **Smoke test post-rollback** : valider que l'env est stable après rollback, escalade si smoke fail
- **Reset challenger entre itérations** : `challenger_evidence: []` et `challenger_result: ""` au début Phase 5
- **`current_phase` mis à jour** : à chaque annonce de phase avant d'en commencer les étapes
- **S3 exclu des patterns** : seuls S1/S2 enrichissent `fix-loop-patterns.md`
- **`fix_applied_list[]` pour mix** : liste structurée des fichiers modifiés pour context_type=mix
- **Fix partiel Gatekeeper** : approbation partielle + FER-suite avec `parent_session_id` obligatoire
- **Leçons d'itération machine-lisibles** : `iteration_lessons[]` → alimente `fix-loop-patterns.md` automatiquement
- **DoD invalide si root cause change** : vider `test_suite[]` + `dod_test_commands[]` si root cause révisée
- **`phase_timestamps{}` par phase** : horodatage début/fin à chaque phase — input direct META-REVIEW
- **`fix_applied` structuré** : {file, line_start, line_end, change_type, description}
- **Phase 8 META-REVIEW** : auto-analyse post-REPORTER, 6 questions, output YAML, dry-run exact
- **Classification propositions par type** : phase > prompt > field > threshold > pattern
- **Historique proposals persisté** : lecture des 5 derniers `meta-review/*.yaml`
- **Déclenchement conditionnel META-REVIEW** : S1/S2 par défaut, S3 skip automatique
- **FER <= 100 lignes** : dépassement → externaliser historique verbose
- **Dossier `meta-review/`** : créé à l'INITIALISATION si absent
- **`meta_review_enabled: false` pour S3** : Phase 1.2 écrit explicitement la valeur
- **Backup `.bak` obligatoire avant fix config** : Phase 3.4 crée `[fichier].bak` et stocke dans `rollback_ref`
- **`context_type_previous` dans FER** : rempli par Phase 2.2 quand context_type change
- **INITIALISATION multi-FER** : liste tous les `fer-*.yaml` non clôturés et propose le choix
- **Troncage stdout 200+300** : 200 premiers + 300 derniers chars — le récap est en fin d'output
- **`mem0-bridge.py` non-bloquant** : échec mémorisé dans shared-context.md sans interrompre
- **Borne de sortie boucle Challenger** : `challenger_failures` >= 3 → ESCALADE
- **Suppression FER conditionnelle** : Phase 7 supprime si false/declined ; Phase 8 supprime à sa fin
- **Backup `.bak` conditionnel** : `[ -f fichier ]` avant `cp` — pas d'erreur si nouveau fichier
- **Notification S2 certifié** : `⚠️ FIX S2 CERTIFIÉ` annonce explicite, parité avec S1
- **Fast-path S1/S2 phases complètes** : Challenger+Gatekeeper maintenus sur fast-path S1/S2
- **`challenger_result` rempli dans les deux branches** : `failed_to_break` dans CLEAN, `broke_it` dans BROKE IT
- **Gatekeeper vérifie `fix_applied_list[]` pour mix** : check supplémentaire prévient approbation générique
- **`max_iterations: null` dans FER template** : force re-classification si reprise avant Phase 1.2
- **`fix_deployed_to_prod: false` après rollback** : prévient double rollback à l'itération suivante
- **Règle PP déclenchée en Phase 7** : vérification taille FER > 100 lignes, externalisation automatique
