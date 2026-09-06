// Espace Mémoire — LOT 4.
//
// Remplace `memory.html`. Cible : le store et le graphe D'ABORD, les couches et
// les backends ensuite. Inspecteur : entrée.
//
// Correction due par la revue §4.5 : la page ne doit pas expliquer
// l'architecture à la place de montrer la mémoire.
//
// API consommées : api.memoryStatus().

export async function mount(root, ctx) {
  const memory = await ctx.api.memoryStatus();
  ctx.docbar.setBreadcrumb([ctx.host.project || 'projet', 'Mémoire']);
  ctx.docbar.setViews(
    [{ id: 'store', label: 'Store' }, { id: 'graphe', label: 'Graphe' },
     { id: 'couches', label: 'Couches' }],
    'store',
  );
  const entries = memory.entries;
  root.append(ctx.empty(
    'Mémoire',
    entries
      ? `${entries} entrée(s), backend ${memory.resolvedBackend || memory.configuredBackend || 'non résolu'}. `
        + 'Le store et le graphe se branchent ici (lot 4).'
      : "La mémoire de ce projet est vide. Elle se peuplera dès qu'une session y écrira.",
    'grimoire memory status',
  ));
  ctx.dock.echo('grimoire memory status');
}
