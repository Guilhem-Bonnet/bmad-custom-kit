# Agent Rules — Override DNA par dossier (BM-25)

> Inspiré de `.cursorrules` / `.github/copilot-instructions.md` — des règles contextuelles
> qui s'appliquent automatiquement quand un agent travaille dans un dossier ou module donné.
>
> **Principe** : chaque dossier peut contenir un `.agent-rules` qui surcharge localement les
> traits DNA de l'archétype. Pas besoin de modifier le DNA global.

---

## Format d'un fichier `.agent-rules`

Créer un fichier `.agent-rules` dans n'importe quel dossier :

```yaml
# .agent-rules — Override local des règles BMAD
# Scope : ce dossier et tous ses sous-dossiers
# Héritage : s'ajoute (ou surcharge) les règles DNA de l'archétype actif

scope: "src/payments/"         # chemin relatif depuis la racine projet (informatif)
priority: 1                    # 1=critique, 2=important, 3=conseil (défaut: 2)

# ── Règles additionnelles ───────────────────────────────────────────────────
rules:
  - id: "payments-pci"
    description: "Toute modification du module payments requiert validation Sentinel"
    enforcement: "hard"        # hard | soft
    triggers_on: ["*.ts", "*.py", "*.go"]

  - id: "no-logging-secrets"
    description: "JAMAIS logger card_number, cvv, account_iban dans ce dossier"
    enforcement: "hard"
    triggers_on: ["**/*"]

  - id: "test-coverage-100"
    description: "Couverture de tests 100% obligatoire dans payments/"
    enforcement: "soft"
    triggers_on: ["*.ts", "*.py"]

# ── Agents affectés ─────────────────────────────────────────────────────────
agents_affected: ["*"]         # ou ["dev", "qa"] pour cibler des agents spécifiques

# ── Contexte additionnel à charger automatiquement ──────────────────────────
# Le Context Router (BM-07) charges ces fichiers quand l'agent opera dans ce scope
auto_load:
  - "docs/payments-architecture.md"   # relatif à la racine projet
  - "docs/pci-dss-checklist.md"

# ── Messages de rappel (affichés à l'agent à l'activation) ──────────────────
reminders:
  - "⚠️  Module PCI-DSS : toute modif requiert double review (dev + qa)"
  - "📋  ADR-042 : utiliser Stripe SDK, pas appels API directs"
```

---

## Résolution des règles (priorité d'application)

```
Ordre de résolution (du + spécifique au + général) :
  1. .agent-rules dans le dossier courant
  2. .agent-rules dans les dossiers parents (jusqu'à la racine)
  3. archetype DNA (archetype.dna.yaml)
  4. agent-base.md (règles universelles)
```

En cas de conflit entre un `.agent-rules` enfant et un `.agent-rules` parent :
→ **L'enfant gagne** sur les règles avec le même `id`.
→ Les règles sans conflit sont **cumulées**.

---

## Intégration dans le Context Budget Router (BM-07)

Le `context-router.md` charge automatiquement les `.agent-rules` en priorité **P0** :

```
AGENT RULES RESOLUTION PROTOCOL :
1. À chaque activation, l'agent liste les .agent-rules du chemin courant
2. Merge des règles : enfant surcharge parent, les deux s'ajoutent aux DNA
3. Si enforcement: "hard" détecté → afficher WARN PROMINENTE avant toute action
4. Les auto_load files passent en priorité P1 (SESSION) pour ce scope
5. Les reminders sont affichés au démarrage de session
```

---

## Exemples d'usage

### Sécurité renforcée sur un module critique

```bash
# src/auth/.agent-rules
rules:
  - id: "no-token-logging"
    description: "Aucun JWT/token dans les logs"
    enforcement: "hard"
  - id: "hash-passwords-always"
    description: "Utiliser bcrypt/argon2, jamais MD5/SHA1"
    enforcement: "hard"
auto_load:
  - "docs/security-guidelines.md"
```

### Style de code spécifique à un dossier

```bash
# frontend/components/.agent-rules
rules:
  - id: "no-inline-styles"
    description: "Utiliser Tailwind uniquement, pas de style inline"
    enforcement: "soft"
  - id: "accessibility-mandatory"
    description: "Chaque composant doit avoir aria-label ou aria-labelledby"
    enforcement: "soft"
agents_affected: ["dev", "ux-designer"]
```

### Override DNA pour un sous-projet legacy

```bash
# legacy/v1/.agent-rules
# Désactiver TDD obligatoire sur le legacy (code difficile à tester)
rules:
  - id: "tdd-mandatory"
    description: "TDD recommandé mais non bloquant sur legacy/v1"
    enforcement: "soft"   # surcharge le "hard" du DNA web-app
reminders:
  - "🏔️  Code legacy — éviter les refactors massifs, cibler les correctifs chirurgicaux"
auto_load:
  - "legacy/v1/ARCHITECTURE.md"
  - "legacy/v1/KNOWN-ISSUES.md"
```

---

## Création rapide

```bash
# Dans n'importe quel dossier
cat > .agent-rules << 'EOF'
scope: "chemin/du/dossier"
priority: 2
rules:
  - id: "ma-regle"
    description: "Description de la règle"
    enforcement: "soft"
agents_affected: ["*"]
EOF
```

---

## Référence croisée

- Context Router : [framework/context-router.md](../context-router.md) — chargement P0 des `.agent-rules`
- Archetype DNA : [framework/archetype-dna.schema.yaml](../archetype-dna.schema.yaml) — règles globales
- Agent Base : [framework/agent-base.md](../agent-base.md) — règles universelles

---

*BM-25 Agent Rules par dossier | framework/agent-rules.md*
