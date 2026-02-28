# Workflow Status — {{workflow_name}}

> **BM-02** — Fichier mis à jour automatiquement après chaque step de workflow.
> Lisible à tout moment pour connaître l'état exact de l'exécution.
>
> Emplacement : `_bmad-output/.runs/{{run_id}}/workflow-status.md`
> Format machine-readable ET human-readable.

---

## 🎯 Workflow en Cours

| Champ | Valeur |
|---|---|
| **Workflow** | `{{workflow_name}}` |
| **Run ID** | `{{run_id}}` |
| **Démarré le** | `{{start_datetime}}` |
| **Dernière MAJ** | `{{last_update_datetime}}` |
| **Agent actif** | `{{active_agent}}` |
| **Step courant** | `{{current_step}} / {{total_steps}}` |
| **Statut global** | `{{status}}` |
| **Session branch** | `{{session_branch}}` |

---

## 📊 Progression des Steps

```
{{progress_bar}}
```

| Step | Nom | Statut | Agent | Durée | Output |
|---|---|---|---|---|---|
{{steps_table}}

---

## 📦 Variables de Session

> Variables accumulées au fil des steps — disponibles pour les steps suivants.

```yaml
{{session_variables}}
```

---

## 📁 Artefacts Produits

> Fichiers créés ou modifiés depuis le début de ce run.

{{artefacts_list}}

---

## ❗ Problèmes Rencontrés

> Erreurs, avertissements, et décisions de déviation.

{{issues_list}}

---

## 🔄 Reprendre ce Workflow

Si interrompu, reprendre avec :

```
État sauvegardé dans : _bmad-output/.runs/{{run_id}}/state.json
Step de reprise      : {{resume_step}}
Variables disponibles: voir state.json → session_variables
```

*Pour reprendre : activer l'agent {{active_agent}} et indiquer "reprendre run {{run_id}} au step {{resume_step}}"*

---

*Template BMAD Custom Kit — BM-02 Workflow Status | framework/workflows/workflow-status.tpl.md*
