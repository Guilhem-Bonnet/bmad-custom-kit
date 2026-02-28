# Créer un agent — Guide

## Voie rapide — Agent Forge (BM-52)

`agent-forge.py` génère un scaffold rempli intelligemment depuis un besoin textuel ou des gaps détectés automatiquement.

```bash
# Depuis une description textuelle
bash bmad-init.sh forge --from "je veux un agent pour les migrations de base de données"

# Depuis les requêtes inter-agents non résolues (shared-context.md)
bash bmad-init.sh forge --from-gap

# Depuis les failures BMAD_TRACE sans agent propriétaire
bash bmad-init.sh forge --from-trace

# Lister les proposals en attente de review
bash bmad-init.sh forge --list

# Installer après review du [TODO]
bash bmad-init.sh forge --install db-migrator
```

**Pipeline :**
```
forge --from "..."
  → _bmad-output/forge-proposals/agent-[tag].proposed.md
  → [ Réviser les [TODO] : identité, prompts métier ]
  → forge --install [tag]
  → Sentinel [AA] audit qualité
```

> **Note :** Le scaffold couvre la structure, les outils, l'icône et les protocoles inter-agents.  
> Les prompts métier (sections `[TODO]`) nécessitent votre connaissance du domaine.

> **Conseil budget :** Après avoir installé un nouvel agent, vérifiez qu'il ne sature pas la fenêtre de contexte :
> ```bash
> bash bmad-init.sh guard --agent [id-de-votre-agent] --detail --suggest
> ```
> Seuil recommandé : < 40% de la fenêtre du modèle cible.

---

## Anatomie d'un agent BMAD Custom

Un agent est un fichier Markdown structuré avec des balises XML qui définissent sa personnalité, ses capacités et ses actions.

```
mon-agent.md
├── Persona (identité, principes, règles)
├── Activation (comment démarrer)
├── Menu (actions numérotées)
└── Prompts (instructions détaillées par action)
```

## Créer un agent de zéro

### 1. Copier le template

```bash
cp _bmad/_config/custom/agents/custom-agent.tpl.md \
   _bmad/_config/custom/agents/mon-nouvel-agent.md
```

### 2. Remplir les variables

| Variable | Description | Exemple |
|----------|-------------|---------|
| `{{agent_name}}` | Nom affiché | "Gardien" |
| `{{agent_icon}}` | Emoji | "🛡️" |
| `{{agent_tag}}` | Tag court (minuscule) | "gardien" |
| `{{agent_role}}` | Rôle en une phrase | "Sécurité applicative" |
| `{{domain}}` | Domaine d'expertise | "sécurité, authentification, RBAC" |
| `{{learnings_file}}` | Nom du fichier learnings | "security-app" |
| `{{domain_word}}` | Mot-clé pour decisions-log | "sécurité" |

### 2b. Configurer model_affinity (optionnel)

Déclarez les besoins LLM de votre agent dans le frontmatter YAML :

```yaml
---
name: "mon-agent"
description: "Mon Agent — Alias"
model_affinity:
  reasoning: high       # low | medium | high | extreme
  context_window: medium  # small (≤32K) | medium (≤128K) | large (≤200K) | massive (>1M)
  speed: fast           # fast | medium | slow-ok
  cost: medium          # cheap | medium | any
---
```

| Axe | Quand utiliser `extreme`/`massive` | Quand utiliser `low`/`small`/`cheap` |
|---|---|---|
| **reasoning** | Debug deep, audit sécurité, architecture | CRUD, mémoire, monitoring |
| **context_window** | Scan codebase entier, refactoring large | Tâches ciblées, corrections ponctuelles |
| **speed** | Boucles rapides fix→test, CI | Décisions stratégiques, audits |
| **cost** | Tâches critiques, sécurité | Tâches répétitives, consolidation |

Vérifiez la recommandation : `bash bmad-init.sh guard --recommend-models`

### 3. Écrire l'identité

La section `<identity>` est la plus importante. Elle doit :
- Décrire l'expertise spécifique au projet
- Mentionner les outils/technologies maîtrisés
- Référencer `shared-context.md` pour le contexte d'infra

```markdown
<identity>
Tu es Gardien, expert en sécurité applicative pour le projet {{project_name}}.
Tu maîtrises OAuth2/OIDC, RBAC, rate-limiting, WAF, et les headers de sécurité.
Consulte shared-context.md pour l'architecture complète.
</identity>
```

### 4. Définir les prompts

Chaque action du menu pointe vers un `<prompt>`. Structure recommandée :

```markdown
<prompt id="audit-auth" title="Audit Authentification">
### Audit du système d'authentification

**Étapes :**
1. Scanner les endpoints d'authentification
2. Vérifier la configuration JWT/OAuth2
3. Tester les flux de login/logout
4. Vérifier les rate-limits

**Output :**
- Rapport dans decisions-log.md
- Actions correctives si trouvées

<example>
Vérifier que le endpoint /api/auth/login :
- Accepte uniquement POST
- Rate-limité à 5 tentatives/min
- Retourne 401 avec body générique (pas de leak d'info)
</example>
</prompt>
```

### 5. Enregistrer l'agent

Ajouter dans `_bmad/_config/agent-manifest.csv` :

```csv
"mon-nouvel-agent","Gardien","Sécurité Applicative","🛡️","security-app","custom","_bmad/_config/custom/agents/mon-nouvel-agent.md"
```

Ajouter dans `_bmad/_memory/shared-context.md` (table équipe) :

```markdown
| mon-nouvel-agent | Gardien | 🛡️ | Sécurité applicative |
```

Créer le fichier learnings :

```bash
echo "# Learnings — Gardien" > _bmad/_memory/agent-learnings/security-app.md
```

## Clause "Use when"

Chaque agent devrait inclure en en-tête une clause commentée `USE WHEN` qui guide le dispatch et aide l'utilisateur à choisir l'agent approprié.

```markdown
<!--
USE WHEN:
- [Situation ou besoin 1]
- [Situation ou besoin 2]
- [Situation ou besoin 3]
DON'T USE WHEN:
- [Cas hors-périmètre]
-->
```

**Exemples :**

```markdown
<!--
USE WHEN:
- Besoin de diagnostiquer un problème technique récurrent
- Besoin de preuves d'exécution avant de claimer "done"
- Fix qui a échoué plusieurs fois sans explication claire
DON'T USE WHEN:
- Exploration exploratoire (pas de bug précis à corriger)
- Questions de design ou d'architecture (voir Atlas ou Sentinel)
-->
```

Cette clause est extraite automatiquement par `mem0-bridge.py dispatch` pour le routage contextuel.

---

## Bonnes pratiques

### Scope strict
Chaque agent doit avoir un périmètre clair. Si deux agents se chevauchent, c'est un signe qu'il faut fusionner ou clarifier les frontières.

### Exemples concrets
Les `<example>` dans les prompts sont essentiels. Un agent sans exemples produit des résultats génériques. Incluez des commandes, chemins et valeurs spécifiques à votre projet.

### Keywords pour le dispatch
Si vous utilisez `mem0-bridge.py dispatch`, ajoutez votre agent dans `project-context.yaml` :

```yaml
agents:
  custom_agents:
    - name: "gardien"
      icon: "🛡️"
      domain: "Sécurité applicative"
      keywords: "oauth jwt rbac auth login permission security headers csp cors"
```

### Test de l'agent

```bash
# Vérifier la cohérence
python _bmad/_memory/maintenance.py context-drift

# Tester le dispatch
python _bmad/_memory/mem0-bridge.py dispatch "vérifier la sécurité des endpoints API"
```
