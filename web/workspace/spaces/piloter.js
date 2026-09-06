// Espace Piloter — LOT 4.
//
// Remplace `portfolio.html` (cockpit) et `index.html` du cockpit.
// Cible : Flotte (cockpit) et Projet ; tableau sur bureau, cartes sur mobile ;
// KPI en une carte divisée ; « À traiter » toujours visible.
// Inspecteur : projet — kit, hôtes, standard, actions.
//
// Corrections dues par la revue §4.1 : `ci_status` et `commits_total` au
// portefeuille, `antifragile: null` = « pas encore mesurée » (jamais zéro),
// badge démo piloté par `demo`, `unknown` rendu « inconnue » en gris.
//
// API consommées : api.projects(), api.status(), api.health().

export async function mount(root, ctx) {
  const health = await ctx.api.health();
  ctx.docbar.setBreadcrumb([ctx.host.project || 'projet', 'Piloter']);
  ctx.docbar.setZoom(
    ctx.host.kind === 'cockpit'
      ? [{ id: 'flotte', label: 'Flotte' }, { id: 'projet', label: 'Projet' }]
      : [{ id: 'projet', label: 'Projet' }],
    ctx.host.kind === 'cockpit' ? 'flotte' : 'projet',
  );
  ctx.docbar.setViews(
    [{ id: 'table', label: 'Liste' }, { id: 'card', label: 'Carte' }], 'table',
  );
  root.append(ctx.empty(
    'Piloter',
    'Le pilotage de flotte se branche ici (lot 4). Les données réelles du projet '
    + `servi sont déjà là : ${(health.flows || []).length} flow(s), kit `
    + `${health.kit?.installed ? 'installé' : 'absent'}.`,
    'grimoire status',
  ));
  ctx.dock.echo('grimoire status');
}
