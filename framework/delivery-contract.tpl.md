---
# ═══════════════════════════════════════════════════════════════════════════════
# BMAD Custom Kit — Delivery Contract Inter-Teams
# BM-18 : Contrat de handoff entre deux teams
# ═══════════════════════════════════════════════════════════════════════════════
#
# Usage : copier ce template, remplir les champs, committer dans :
#   _bmad-output/contracts/{from_team}-to-{to_team}-{date}.md
#
# RÈGLE : Aucune team ne commence sans un Delivery Contract signé et complet.
# ═══════════════════════════════════════════════════════════════════════════════

contract_id: "{{from_team}}-to-{{to_team}}-{{date}}"
version: "1.0"
status: "pending-acceptance"  # pending-acceptance | accepted | rejected | renegotiating

from_team: "{{from_team}}"     # ex: "team-vision"
to_team: "{{to_team}}"         # ex: "team-build"
date: "{{date}}"               # YYYY-MM-DD
signed_by: "{{agent_name}}"    # agent qui signe (ex: "John — PM")
---

# 📜 Delivery Contract — {{from_team}} → {{to_team}}

> **Ce contrat certifie** que {{from_team}} a livré tous les artefacts requis par {{to_team}}
> pour démarrer sa phase de travail.
> **Une seule règle** : Si un artefact requis est manquant ou incomplet, {{to_team}} refuse
> le contrat et le retourne à {{from_team}} avec les questions ouvertes.

---

## 📦 Artefacts Livrés

### ✅ Requis (bloquants)

- [ ] **{{artefact_1}}**
  - 📁 Chemin : `{{path_1}}`
  - ✔️ Critère d'acceptation : {{acceptance_1}}

- [ ] **{{artefact_2}}**
  - 📁 Chemin : `{{path_2}}`
  - ✔️ Critère d'acceptation : {{acceptance_2}}

- [ ] **{{artefact_3}}**
  - 📁 Chemin : `{{path_3}}`
  - ✔️ Critère d'acceptation : {{acceptance_3}}

### 🔵 Optionnels (enrichissants)

- [ ] **{{artefact_opt_1}}**
  - 📁 Chemin : `{{path_opt_1}}`
  - 💡 Valeur ajoutée : {{value_opt_1}}

---

## ❓ Questions Ouvertes

> Lister ici toutes les ambiguïtés, hypothèses, et points à clarifier.
> {{to_team}} NE PEUT PAS commencer si une question critique est sans réponse.

| # | Question | Criticité | Responsable | Statut |
|---|---|---|---|---|
| 1 | {{question_1}} | 🔴 Critique / 🟡 Important / 🟢 Nice-to-have | {{owner_1}} | ⏳ En attente |

---

## 🔒 Critères de Complétion de {{from_team}}

> Checklist auto-évaluée par {{from_team}} avant de signer.

- [ ] Tous les artefacts requis sont présents et à leur chemin prévu
- [ ] Pas de placeholder non rempli dans les documents
- [ ] Les questions critiques identifiées ont une réponse
- [ ] Un récapitulatif des décisions clés est inclus (voir section ci-dessous)

---

## 📋 Résumé des Décisions Clés

> Les décisions que {{to_team}} DOIT connaître pour travailler efficacement.

| Décision | Justification | Impact sur {{to_team}} |
|---|---|---|
| {{decision_1}} | {{justification_1}} | {{impact_1}} |
| {{decision_2}} | {{justification_2}} | {{impact_2}} |

---

## 🔑 Contexte Critique

> Informations que {{to_team}} doit absolument avoir avant de commencer.

**Ce qui a été exploré et rejeté :**
- {{rejected_option_1}} — raison : {{reason_1}}

**Contraintes non-négociables héritées :**
- {{constraint_1}}

**Risques identifiés :**
- 🔴 **{{risk_1}}** — Probabilité : {{prob_1}} — Mitigation : {{mitigation_1}}

---

## ✍️ Signature

### {{from_team}} certifie :
```
Tous les artefacts requis sont livrés et complets.
Les questions critiques ont une réponse.
{{to_team}} peut commencer son travail.

Signé par : {{signed_by}}
Date       : {{date}}
```

---

## 📬 Acceptation par {{to_team}}

> À remplir par {{to_team}} après lecture du contrat.

```
☐ ACCEPTÉ — Nous commençons la phase {{next_phase}}
☐ REJETÉ — Questions bloquantes (voir ci-dessus)
☐ RENEGOCIATING — Demande de clarification ponctuelle

Accepté/Refusé par : ___________________
Date              : ___________________
Questions ouvertes: ___________________
```

---

*Template BMAD Custom Kit — BM-18 Delivery Contract | framework/delivery-contract.tpl.md*
