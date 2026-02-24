# BMAD Custom Kit — Contributing Guide

## Bienvenue

Tu veux améliorer le kit ? Excellent. Voici comment fonctionne le processus.

---

## Structure du projet

```
bmad-custom-kit/
├── bmad-init.sh              # Script d'installation — teste après tout changement
├── framework/
│   ├── agent-base.md         # Protocole universel — impacte TOUS les agents
│   ├── cc-verify.sh          # Completion Contract verifier
│   ├── sil-collect.sh        # Self-Improvement Loop
│   ├── hooks/
│   │   └── pre-commit-cc.sh  # Hook git CC
│   ├── memory/               # Scripts Python mémoire
│   └── workflows/
│       ├── github-cc-check.yml.tpl  # Template CI déployé dans les projets
│       └── incident-response.md
├── archetypes/
│   ├── meta/agents/          # Agents universels — inclus dans TOUS les archétypes
│   ├── stack/agents/         # Agents par technologie (Modal Team Engine)
│   ├── infra-ops/            # Archétype infrastructure
│   ├── web-app/              # Archétype application web
│   ├── fix-loop/             # Archétype boucle de correction certifiée
│   └── minimal/              # Archétype point de départ
└── docs/
```

---

## Règles fondamentales

### 1. Tout agent doit respecter le format BMAD

Chaque fichier `.md` d'agent doit suivre le pattern :

```xml
<agent id="..." name="..." title="..." icon="...">
  <activation critical="MANDATORY">
    <step n="1">Load persona...</step>
    <step n="2">⚙️ BASE PROTOCOL — Load agent-base.md with: AGENT_TAG=... ...</step>
    <!-- 6-8 steps max -->
    <rules>
      <r>🔒 CC OBLIGATOIRE...</r>
      <r>RAISONNEMENT...</r>
      <!-- 5-8 règles -->
    </rules>
  </activation>
  <persona>...</persona>
  <menu>...</menu>
  <prompts>...</prompts>
</agent>
```

Voir [docs/creating-agents.md](docs/creating-agents.md) pour le guide complet.

### 2. Pas de "terminé" sans CC PASS

Avant tout commit qui touche des fichiers vérifiables (.go, .ts, .py, .sh, .tf...) :

```bash
bash framework/cc-verify.sh
```

Le hook pre-commit s'en charge automatiquement si installé.

### 3. Tests pour les scripts bash

Tout changement à `bmad-init.sh`, `cc-verify.sh` ou `sil-collect.sh` doit passer :

```bash
bash -n bmad-init.sh && echo "✅ syntaxe OK"
shellcheck bmad-init.sh  # si shellcheck disponible
bash bmad-init.sh --help  # smoke test
```

---

## Ajouter un archétype

1. Créer `archetypes/[nom]/` avec :
   - `agents/` — au moins 1 agent `.md`
   - `shared-context.tpl.md` — template contexte projet (optionnel mais recommandé)
   - `README.md` — description, cas d'usage, agents inclus

2. Ajouter la détection dans `auto_select_archetype()` de `bmad-init.sh` si pertinent

3. Documenter dans [docs/archetype-guide.md](docs/archetype-guide.md) avec :
   - Cas d'usage
   - Stack typiquement détecté
   - Liste des agents et leur rôle

4. Mettre à jour le tableau dans [README.md](README.md)

---

## Ajouter un agent stack (Modal Team Engine)

Les agents stack sont dans `archetypes/stack/agents/` et sont déployés automatiquement par `detect_stack()`.

Nommage : `[technologie]-expert.md` (ex: `rust-expert.md`)

Dans `bmad-init.sh`, ajouter dans le `STACK_MAP` :
```bash
["rust"]="rust-expert.md"
```

Et dans `detect_stack()`, ajouter la détection :
```bash
# Rust
[[ -f "$dir/Cargo.toml" ]] && detected+=("rust")
```

---

## Modifier `framework/agent-base.md`

⚠️ **Attention** : ce fichier est chargé par TOUS les agents. Tout changement a un impact global.

Avant de modifier :
1. Identifier quel(s) agent(s) sont impactés
2. Tester sur au moins 2 agents différents
3. Documenter la modification dans le commit message

---

## Format des commits

```
type: description courte (max 72 chars)

- détail 1
- détail 2
```

Types : `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

Exemples :
```
feat: Rust archetype + detect_stack Cargo.toml

- archetypes/stack/agents/rust-expert.md: agent Ferris avec CC --stack rust
- bmad-init.sh: detect_stack() Cargo.toml → rust, STACK_MAP["rust"] ajouté
- docs/archetype-guide.md: section Rust ajoutée
```

---

## Tester localement

```bash
# Smoke test complet
cd /tmp && mkdir test-project && cd test-project && git init
bash /chemin/vers/bmad-custom-kit/bmad-init.sh \
  --name "Test" --user "Test" --auto

# Vérifier la structure générée
ls -la _bmad/_config/custom/agents/
cat _bmad/_memory/shared-context.md

# Vérifier le hook
cat .git/hooks/pre-commit
```

---

## Questions ?

Ouvrir une issue sur GitHub avec le label approprié :
- `bug` — quelque chose ne fonctionne pas
- `enhancement` — proposition d'amélioration
- `new-archetype` — proposition d'un nouvel archétype
- `new-stack-agent` — proposition d'un agent technologie
