# Troubleshooting — BMAD Custom Kit

Solutions aux problèmes les plus fréquents.

---

## 1. La mémoire sémantique ne fonctionne pas

**Symptôme** : `⚠️ Mémoire sémantique indisponible` ou recherche peu pertinente

**Diagnostic** :
```bash
python3 _bmad/_memory/mem0-bridge.py status
```

**Causes et fixes** :

| Cause | Message | Fix |
|-------|---------|-----|
| `qdrant-client` non installé | `Qdrant lib: ❌` | `pip install qdrant-client` |
| `sentence-transformers` manquant | `Embeddings: ❌` | `pip install sentence-transformers` |
| Erreur init Qdrant | `init échoué` | Supprimer `_bmad/_memory/qdrant_data/` et relancer |
| Toutes dépendances manquantes | Mode fallback JSON | `pip install -r _bmad/_memory/requirements.txt` |

**Note importante** : le fallback JSON est **fonctionnel**. Les agents travaillent normalement — seule la qualité de la recherche sémantique est réduite (mots-clés vs embeddings). Tu peux travailler sans Qdrant.

```bash
# Réinstaller toutes les dépendances
pip install -r _bmad/_memory/requirements.txt

# Vérifier le résultat
python3 _bmad/_memory/mem0-bridge.py status
```

---

## 2. cc-verify.sh ne trouve pas le bon stack

**Symptôme** : `⚠️ Aucun stack reconnu` sur un projet Go/TypeScript/etc.

**Diagnostic** :
```bash
bash _bmad/_config/custom/cc-verify.sh  # sans --stack
```

**Causes** :

| Symptôme | Cause probable | Fix |
|----------|----------------|-----|
| Go non détecté | `go.mod` absent ou hors de portée | Ajouter `go.mod` à la racine |
| TypeScript non détecté | `package.json` sans `tsc` dans devDependencies | `npm install -D typescript` |
| Terraform non détecté | Fichiers `.tf` > 7 niveaux de profondeur | `--stack terraform` en option |

**Forcer un stack** :
```bash
bash _bmad/_config/custom/cc-verify.sh --stack go
bash _bmad/_config/custom/cc-verify.sh --stack typescript
bash _bmad/_config/custom/cc-verify.sh --stack go,docker
```

---

## 3. Le pre-commit hook bloque le commit

**Symptôme** : `🚫 Commit bloqué — CC FAIL détecté`

**C'est normal** — c'est le Completion Contract qui fonctionne correctement.

**Workflow** :
```bash
# 1. Voir les erreurs
git commit  # → affiche le CC FAIL

# 2. Corriger les erreurs
# (go build, npx tsc, pytest, etc. selon le stack)

# 3. Re-tenter
git commit

# Bypass d'urgence (DÉCONSEILLÉ — à éviter en équipe)
git commit --no-verify
```

**Si le hook est trop agressif** (faux positifs) :
```bash
# Vérifier ce que le hook détecte
bash .git/hooks/pre-commit

# Désactiver temporairement (ne pas laisser en place)
chmod -x .git/hooks/pre-commit
# ... corriger ...
chmod +x .git/hooks/pre-commit
```

---

## 4. bmad-init.sh écrase mon installation existante

**Symptôme** : Prompt `Continuer et écraser ? (y/N)` à chaque lancement

**Fix** :
```bash
# Option 1 — Confirmer manuellement
bash bmad-init.sh --name "..." --user "..." # répondre 'y' au prompt

# Option 2 — Mode force (pas de prompt)
bash bmad-init.sh --name "..." --user "..." --force

# Option 3 — Cibler un dossier différent
bash bmad-init.sh --name "..." --user "..." --target /chemin/vers/projet
```

---

## 5. sil-collect.sh ne génère rien

**Symptôme** : `Aucune source de données disponible` / rapport vide

**Explication** : C'est **attendu** sur un projet neuf. Le SIL a besoin d'historique accumulé.

```
Sources attendues (toutes vides sur un projet neuf) :
- _bmad/_memory/decisions-log.md
- _bmad/_memory/contradiction-log.md
- _bmad/_memory/agent-learnings/*.md
- _bmad/_memory/activity.jsonl
```

**Quand utiliser le SIL** : après 2-3 semaines d'utilisation normale, quand les agents ont accumulé des learnings et que tu as noté des décisions.

**Forcer la génération** (pour tester) :
```bash
bash _bmad/_config/custom/sil-collect.sh --force-empty
```

---

## 6. Les agents ne se souviennent pas du contexte entre sessions

**Symptôme** : L'agent ne connaît pas le projet au démarrage

**Cause** : `shared-context.md` non rempli ou `agent-learnings/` vides

**Fix** :
```bash
# 1. Compléter shared-context.md
nano _bmad/_memory/shared-context.md
# Remplir : stack, architecture, API, conventions, équipe

# 2. Vérifier les learnings
ls _bmad/_memory/agent-learnings/
# Des fichiers .md doivent exister pour chaque agent

# 3. Tester la mémoire
python3 _bmad/_memory/mem0-bridge.py search "nom du projet"
```

---

## 7. auto_select_archetype détecte le mauvais archétype

**Symptôme** : `--auto` sélectionne `minimal` au lieu de `web-app` ou `infra-ops`

**Diagnostic** :
```bash
# Simuler la détection depuis la racine du projet
source <(sed -n '/^detect_stack/,/^}/p' /chemin/vers/bmad-init.sh)
source <(sed -n '/^auto_select_archetype/,/^}/p' /chemin/vers/bmad-init.sh)
stacks=$(detect_stack "$(pwd)")
echo "Stacks : $stacks"
echo "Archétype : $(auto_select_archetype "$stacks")"
```

**Logique de détection** :
- `infra-ops` si terraform, k8s, ou ansible détecté
- `web-app` si frontend (react/vue/next/vite) **ET** (go, node, ou python) détectés
- `minimal` sinon

**Fix** : spécifier l'archétype manuellement :
```bash
bash bmad-init.sh --name "..." --user "..." --archetype web-app
```

---

## 8. Erreur `Permission denied` sur les scripts

```bash
chmod +x _bmad/_config/custom/cc-verify.sh
chmod +x _bmad/_config/custom/sil-collect.sh
chmod +x .git/hooks/pre-commit
```

---

## 9. `python3 maintenance.py health-check` échoue

```bash
# Vérifier Python
python3 --version  # 3.10+ requis

# Vérifier le path
cd _bmad/_memory/ && python3 maintenance.py health-check

# Vérifier les dépendances
pip3 install -r requirements.txt
```

---

## Obtenir de l'aide

Si le problème persiste :

1. `python3 _bmad/_memory/mem0-bridge.py status` — état complet de la mémoire
2. `bash _bmad/_config/custom/cc-verify.sh` — état du CC
3. Ouvrir une issue sur GitHub avec la sortie de ces deux commandes
