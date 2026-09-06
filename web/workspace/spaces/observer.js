// Espace Observer — LOT 4.
//
// Remplace `observability.html`. Cible : le RUNTIME seulement — six KPI, coût
// par modèle, latence, spans lents, traces par agent ; activité, RTK et bench
// passent en onglets. Inspecteur : trace ou span.
//
// Corrections dues par la revue §4.4 : un projet sans trace obtient UN bloc
// vide qui dit d'où viendra la donnée, jamais un mur de zéros ni une erreur JS.
// Les séries de coût utilisent --s1/--s2/--s3 ; la latence, une seule teinte
// neutre, parce qu'une seule série n'a pas de catégorie à distinguer.
//
// API consommées : api.otel(), api.eventsLog(), api.stigmergy(), api.health().

export async function mount(root, ctx) {
  const spans = await ctx.api.otel().catch(() => ({ spans: [] }));
  ctx.docbar.setBreadcrumb([ctx.host.project || 'projet', 'Observer']);
  ctx.docbar.setViews(
    [{ id: 'runtime', label: 'Runtime' }, { id: 'activite', label: 'Activité' },
     { id: 'rtk', label: 'RTK' }, { id: 'bench', label: 'Bench' }],
    'runtime',
  );
  const count = (spans.spans || []).length;
  root.append(ctx.empty(
    'Observer',
    count
      ? `${count} span(s) au journal. Les six KPI, le coût par modèle et les spans lents se branchent ici (lot 4).`
      : "Aucune trace : ce projet n'a pas encore exécuté de workflow instrumenté. "
        + "La donnée viendra du TraceLedger, sous _grimoire/standard/traces/.",
    'grimoire task trace <id>',
  ));
  ctx.dock.echo('grimoire task trace');
}
