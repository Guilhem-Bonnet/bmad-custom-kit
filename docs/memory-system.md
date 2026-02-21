# Système de Mémoire — Guide complet

## Architecture

Le système de mémoire BMAD Custom Kit repose sur 3 couches complémentaires :

```
┌─────────────────────────────────────────┐
│          Mémoire Sémantique             │ ← Qdrant + sentence-transformers
│   (recherche par similarité, dispatch)  │    Score cosinus, embeddings locaux
├─────────────────────────────────────────┤
│          Mémoire Structurée             │ ← Fichiers Markdown
│   (learnings, décisions, contexte)      │    Lisible, versionnable, auditable
├─────────────────────────────────────────┤
│          Mémoire Éphémère               │ ← session-state.md, activity.jsonl
│   (état session, logs d'activité)       │    Continuité inter-sessions
└─────────────────────────────────────────┘
```

## Composants

### 1. `mem0-bridge.py` — Mémoire sémantique

**2 modes de fonctionnement :**

| Mode | Dépendances | Recherche | Performance |
|------|-------------|-----------|-------------|
| `local` | Aucune | Mots-clés fuzzy | Basique |
| `semantic` | sentence-transformers + qdrant-client | Embeddings cosine | Excellente |

**Commandes :**

```bash
# Ajouter une mémoire
python mem0-bridge.py add forge "Le module X nécessite le provider Y"

# Rechercher
python mem0-bridge.py search "comment configurer le provider"

# Dispatch sémantique — quel agent pour cette question ?
python mem0-bridge.py dispatch "les métriques Prometheus ne remontent pas"

# Statut complet
python mem0-bridge.py status

# Métriques cercle vertueux
python mem0-bridge.py stats
```

**Detection de contradictions (Mnemo hook) :**

Chaque `add` déclenche automatiquement une recherche de mémoires contradictoires (score > 0.8 = quasi-doublon). Si trouvé, l'ancienne mémoire est marquée `superseded` et un warning est affiché.

### 2. `maintenance.py` — Santé et pruning

**Commandes :**

```bash
# Health-check rapide (rate-limité 1x/24h)
python maintenance.py health-check [--force]

# Audit complet (Mnemo)
python maintenance.py memory-audit

# Consolidation learnings (élimine doublons >85% similarité)
python maintenance.py consolidate-learnings

# Détecter le drift shared-context vs manifest
python maintenance.py context-drift

# Pruning complet
python maintenance.py prune-all

# Archiver mémoires > 30 jours
python maintenance.py archive 30
```

**Health-check automatique :**

Le health-check est exécuté automatiquement à chaque activation d'agent (via `agent-base.md` step 2). Il est rate-limité à 1x/24h et effectue :

1. Compactage doublons mémoire (auto-fix)
2. Vérification taille learnings (>100 lignes = warning)
3. Archivage décisions > 6 mois
4. Compactage activity.jsonl > 90 jours
5. Vérification hit rate recherche (<50% = warning)
6. Détection drift shared-context

### 3. `session-save.py` — Continuité inter-sessions

```bash
python session-save.py forge \
  --work "Déployé le monitoring complet" \
  --files "docker-compose.yml,prometheus.yml" \
  --next "Vérifier les targets Prometheus" \
  --duration "2h"
```

Écrit `session-state.md` (état courant, écrasé à chaque session) et archive dans `session-summaries/` (historique complet).

## Fichiers mémoire

| Fichier | Rôle | Qui écrit | Qui lit |
|---------|------|-----------|---------|
| `shared-context.md` | Contexte projet partagé | User, Atlas | Tous les agents |
| `decisions-log.md` | Log chronologique des décisions | Tous les agents | Atlas, Sentinel |
| `handoff-log.md` | Transferts inter-agents | Tous les agents | Tous les agents |
| `session-state.md` | État de la dernière session | session-save.py | Agent suivant |
| `agent-changelog.md` | Modifications aux fichiers agents | Agents modifiant | Sentinel |
| `memories.json` | Mémoire JSON (fallback) | mem0-bridge.py | mem0-bridge.py |
| `activity.jsonl` | Log d'activité détaillé | mem0-bridge.py | maintenance.py |
| `agent-learnings/*.md` | Apprentissages par agent | Chaque agent | Mnemo |

## Cercle vertueux

Le système de mémoire forme un **cercle vertueux** :

```
Agent utilise mémoire → meilleur contexte → meilleure action
     ↑                                           ↓
   Mnemo consolide ←── Agent enregistre learning ←┘
```

**Métriques clés** (via `mem0-bridge.py stats`) :
- **Hit rate** : % de recherches avec score ≥ 0.3 → mesure la pertinence
- **Score moyen** : qualité globale des résultats sémantiques
- **Répartition agents** : couverture des domaines

## Configuration via `project-context.yaml`

Les scripts Python chargent automatiquement `project-context.yaml` pour :
- `USER_ID` et `APP_ID` (mem0-bridge.py)
- Pattern d'infrastructure (maintenance.py — détection contradictions)
- Nom du projet (session-save.py)
- Profils d'agents (mem0-bridge.py — dispatch sémantique)

```yaml
# Ajouter des agents au dispatch sémantique
agents:
  custom_agents:
    - name: "mon-agent"
      icon: "🤖"
      domain: "Mon Domaine"
      keywords: "keyword1 keyword2 keyword3"
```

## Automatisations

### Au démarrage d'une session agent
1. `health-check` → auto-prune si nécessaire
2. `consolidate-learnings` → merge doublons du cycle précédent
3. `inbox check` → requêtes inter-agents en attente

### À chaque `mem0-bridge.py add`
1. Contradiction detection → supersede si doublon >0.8
2. Health-check background → rate-limité 1x/24h

### Pre-commit (si configuré)
1. `consolidate-learnings` → nettoyage avant commit
2. `context-drift` → vérification cohérence
