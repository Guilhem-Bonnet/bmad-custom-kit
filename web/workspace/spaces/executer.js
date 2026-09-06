// Espace Exécuter — LOT 4.
//
// Remplace `kanban.html`. Cible : tâches en Board 4 ou 8 colonnes, Liste,
// Timeline ; la porte de chaque colonne en une ligne sous son titre ; carte de
// tâche à trois niveaux. Inspecteur : tâche — critères, preuves, prochaine
// porte avec bouton, timeline.
//
// Corrections dues par la revue §4.3 : huit états annoncés, huit montrés (ou
// dire où sont les quatre repliés) ; la transition suivante est l'information
// la plus grande, pas la plus petite ; colonnes vides en pointillé.
//
// API consommées : api.tasks(), api.task(id), api.taskTrace(id),
// api.taskAction(id, 'claim'|'move'|'block'|'close', body).
// Le refus d'un gate revient en 200 avec `blocked: true` et la preuve
// manquante nommée — c'est une réponse à afficher, pas une erreur à avaler.

export async function mount(root, ctx) {
  const board = await ctx.api.tasks();
  ctx.docbar.setBreadcrumb([ctx.host.project || 'projet', 'Exécuter']);
  ctx.docbar.setViews(
    [{ id: 'board4', label: 'Board 4' }, { id: 'board8', label: 'Board 8' },
     { id: 'liste', label: 'Liste' }, { id: 'timeline', label: 'Timeline' }],
    'board4',
  );
  if (!board.ledger) {
    root.append(ctx.empty('Exécuter', board.note || "Ce projet n'a pas encore de Mission Ledger.", 'grimoire task add'));
  } else {
    root.append(ctx.empty(
      'Exécuter',
      `${board.count} tâche(s) au ledger, ${board.columns.length} colonnes de board. `
      + 'Le board gouverné, les portes et la carte de tâche se branchent ici (lot 4).',
      'grimoire task board',
    ));
  }
  ctx.dock.echo('grimoire task board');
}
