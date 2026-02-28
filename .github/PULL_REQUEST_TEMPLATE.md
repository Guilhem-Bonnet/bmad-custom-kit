<!-- BMAD Custom Kit — Pull Request Template -->
<!-- Supprimez les sections non-applicables avant de soumettre -->

## Type de changement

<!-- Cochez ce qui correspond -->
- [ ] 🐛 Bug fix (`fix:`)
- [ ] ✨ Nouvelle feature (`feat:`)
- [ ] 📝 Documentation (`docs:`)
- [ ] 🧬 Nouvel archétype / agent DNA
- [ ] 🪝 Hook git
- [ ] ⚙️ CI/CD / tooling
- [ ] ♻️ Refactoring (pas de changement de comportement)

## Changements

<!-- Description concise de ce qui a changé -->

- 
- 

## BM / Story

<!-- Lien vers l'issue ou le BM ID -->
Closes # <!-- ou BM-XX -->

## Checklist

### Obligatoire
- [ ] `bash -n bmad-init.sh` passe (si bmad-init.sh modifié)
- [ ] `bash bmad-init.sh validate --all` passe (si DNA modifié)
- [ ] `bash bmad-init.sh doctor` ne montre pas de nouvelles erreurs

### Si archétype / DNA modifié
- [ ] `acceptance_criteria` renseignés avec `test_command` pour chaque AC `blocking: true`
- [ ] `tools_required` listés avec `command` vérifiable
- [ ] DNA testé avec `bash bmad-init.sh install --archetype <id>`

### Si hook git modifié
- [ ] Hook testé manuellement (installer avec `bash bmad-init.sh hooks --install --hook <name>`)
- [ ] Hook ne bloque jamais le commit sur erreur inattendue (exit 0 garanti pour hooks non-bloquants)
- [ ] Commentaire d'en-tête présent (format standard des autres hooks)

### Si documentation modifiée
- [ ] Liens relatifs vérifiés
- [ ] Code blocks avec langage spécifié (` ```bash `, ` ```yaml `, etc.)
- [ ] Exemples CLI testés manuellement

### Si CI/CD modifié
- [ ] Workflow testé sur une branche feature avant merge
- [ ] Les jobs `needs:` sont correctement chaînés

## Tests

<!-- Comment avez-vous testé ce changement ? -->

```bash
# Commandes exactes utilisées pour tester
```

## Notes pour le reviewer

<!-- Optionnel : context supplémentaire, choix de design, alternatives considérées -->
