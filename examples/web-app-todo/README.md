# Exemple — Application Web (SPA + API Go + PostgreSQL)

Démonstration de l'archétype `web-app` sur un projet concret : une application de gestion de tâches avec frontend React, API Go, et base PostgreSQL.

---

## Stack détecté automatiquement

```bash
bash /chemin/vers/bmad-custom-kit/bmad-init.sh \
  --name "TodoApp" --user "Alice" --auto
```

```
ℹ️  Analyse automatique du stack...
✅ Stack détecté : go frontend docker → archétype : web-app
✅ Framework installé
✅ Agents meta installés (Atlas, Sentinel, Mnemo)
✅ Archétype 'web-app' installé
✅ Agents stack déployés : go-expert.md typescript-expert.md docker-expert.md
✅ Pre-commit hook CC installé
```

Agents déployés automatiquement :
- **Stack ⚡** (fullstack-dev) — feature end-to-end
- **Pixel 🎨** (frontend-specialist) — composants React, accessibilité
- **Gopher 🐹** (go-expert) — API Go, gestion des erreurs, tests
- **Container 🐋** (docker-expert) — build, compose, optimisation image
- **Atlas 🗺️** / **Sentinel 🔍** / **Mnemo 🧠** — agents meta universels

---

## Structure du projet type

```
todo-app/
├── project-context.yaml
├── _bmad/
│   ├── _config/
│   │   └── custom/
│   │       ├── agent-base.md
│   │       ├── cc-verify.sh
│   │       ├── sil-collect.sh
│   │       └── agents/
│   │           ├── fullstack-dev.md   ← Stack ⚡
│   │           ├── frontend-specialist.md  ← Pixel 🎨
│   │           ├── go-expert.md       ← Gopher 🐹
│   │           ├── docker-expert.md   ← Container 🐋
│   │           ├── project-navigator.md  ← Atlas 🗺️
│   │           ├── agent-optimizer.md    ← Sentinel 🔍
│   │           └── memory-keeper.md      ← Mnemo 🧠
│   └── _memory/
│       ├── shared-context.md  ← Rempli depuis shared-context.tpl.md
│       └── agent-learnings/
├── frontend/               ← React + Vite + TypeScript
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── pages/
│   └── package.json
├── backend/                ← Go + chi + SQLite/PostgreSQL
│   ├── cmd/
│   ├── internal/
│   │   ├── domain/
│   │   ├── ports/
│   │   └── adapters/
│   ├── migrations/
│   └── go.mod
└── docker-compose.yml
```

---

## Exemple d'utilisation des agents

### Feature end-to-end avec Stack ⚡

> "Ajoute la possibilité de filtrer les tâches par tag"

Stack raisonne :
1. DB migration : `migrations/005_add_tags.sql`
2. Backend : `GET /api/tasks?tag=...` + handler + test
3. shared-context.md → API section mise à jour
4. Frontend : `src/components/TagFilter.tsx` + `src/hooks/useTags.ts`
5. `cc-verify.sh --changed-only` → `✅ CC PASS — [go, typescript]`

### Accessibilité avec Pixel 🎨

> "Audit WCAG 2.1 AA sur le formulaire de création de tâche"

```
[A11y] TaskForm.tsx — 3 violations WCAG 2.1 AA détectées :

1. 🔴 Input sans label associé (ligne 23)
   → <input id="title"> sans <label htmlFor="title">
   Fix : ajouter <label htmlFor="title">Titre de la tâche</label>

2. 🟠 Bouton submit sans texte accessible (ligne 45)
   → <button><Icon /></button> — aria-label manquant
   Fix : <button aria-label="Créer la tâche"><Icon /></button>

3. 🟡 Contraste insuffisant sur le placeholder (ratio 3.2:1 < 4.5:1)
   Fix : changer couleur #999 → #767676
```

### Correction certifiée avec fix-loop 🔁

> "L'API retourne 500 quand le titre dépasse 255 caractères"

Loop [INTAKE] → S2 — backend bug, pas d'impact prod actuel
Loop [ANALYST] → DoD : `PATCH /tasks/:id` avec titre > 255 doit retourner 400 + message d'erreur
Loop [FIXER] → délégué à Gopher
Gopher → validation ajoutée + test de régression
Loop [VALIDATOR] → tests passent
Loop [CHALLENGER] → tente le cas limite (255, 256, 10000 chars)
Loop [GATEKEEPER] → DoD validée mécaniquement
Loop [REPORTER] → `✅ Fix validé — 2 itérations — pattern sauvegardé`

---

## Completion Contract en action

```bash
# Après avoir modifié des fichiers Go et TypeScript
git add .
git commit -m "feat: filtre par tag"

🔒 BMAD Completion Contract — vérification pre-commit...
   Fichiers stagés détectés : 8 fichier(s) vérifiable(s)

🔍 Détection du stack...
   → go (go.mod détecté)
   → typescript (package.json avec react détecté)

⚙️  [go] Vérification...
   → go build ./...        ✅
   → go test ./...         ✅ (23 tests, 0 failed)
   → go vet ./...          ✅

⚙️  [typescript] Vérification...
   → npx tsc --noEmit      ✅
   → npx vitest run        ✅ (11 tests passed)

✅ CC PASS — [go, typescript] — 2026-02-23 14:32:01
[main abc1234] feat: filtre par tag
```

---

## shared-context.md rempli

Après installation, compléter `_bmad/_memory/shared-context.md` :

```yaml
# Stack Technique
| Couche     | Technologie     | Version |
|------------|-----------------|---------|
| Frontend   | React + Vite    | 18 / 5  |
| Backend    | Go + chi/v5     | 1.22    |
| DB         | PostgreSQL      | 16      |
| Container  | Docker + Compose| 27      |

# API
Base URL : http://localhost:8080/api/v1
Routes :
  GET    /tasks          → liste paginée
  POST   /tasks          → créer
  PATCH  /tasks/:id      → modifier
  DELETE /tasks/:id      → supprimer
  GET    /tasks?tag=...  → filtrer par tag
```
