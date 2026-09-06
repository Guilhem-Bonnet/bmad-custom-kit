// Espace Concevoir — LOT 3.
//
// Remplace `blueprints.html`, `patterns.html`, `extensions.html`
// (bibliothèque en panneau). Cible : zoom Projet → Workflow → Nœud ;
// vues Carte (graphe), Board, Liste ; palette de nœuds ; validation,
// simulation, compilation. Inspecteur : nœud ou workflow — propriétés,
// validation, coût, preuves.
//
// La toile est la seule à porter la grille de points (`#canvas[data-grid=on]`).
// L'éditeur hérité `bp2-core.js` n'est PAS importé : ce lot le réécrit contre
// les routes existantes plutôt que d'embarquer ses 100 Ko.
//
// API consommées : api.blueprints(), api.primitives(),
// /api/blueprints/<id> (GET/PUT), /validate, /simulate, /compile.

export async function mount(root, ctx) {
  const blueprints = await ctx.api.blueprints();
  ctx.docbar.setBreadcrumb([ctx.host.project || 'projet', 'Concevoir']);
  ctx.docbar.setZoom(
    [{ id: 'projet', label: 'Projet' }, { id: 'workflow', label: 'Workflow' }, { id: 'noeud', label: 'Nœud' }],
    'projet',
  );
  ctx.docbar.setViews(
    [{ id: 'carte', label: 'Carte' }, { id: 'board', label: 'Board' }, { id: 'liste', label: 'Liste' }],
    'carte',
  );
  root.append(ctx.empty(
    'Concevoir',
    blueprints.length
      ? `${blueprints.length} blueprint(s) dans ce projet. La toile, l'éditeur de graphe et l'inspecteur de nœud se branchent ici (lot 3).`
      : "Ce projet n'a pas encore de blueprint. La toile se peuplera dès qu'il en aura un.",
    'grimoire blueprint list',
  ));
  ctx.dock.echo('grimoire blueprint list');
}
