// Espace Source — LOT 5. Écran nouveau : rien à remplacer.
//
// Cible : les fichiers par étage (overrides possédés, kit généré, projections
// des hôtes) ; un éditeur à trois onglets — Source, Diff contre le kit, Rendu ;
// « créer un override » quand on édite un fichier du kit. Inspecteur : fichier
// — étage, version, empreinte, override, projeté vers, chargé par.
//
// Le lot 5 possède aussi la Console du dock : `api.run(argv)` n'exécute que les
// sous-commandes `grimoire` de la liste blanche
// (src/grimoire/tools/workspace_exec.py), sans shell, et refuse le reste.
//
// API consommées : api.files(tier), api.file(path), api.fileDiff(path),
// api.createOverride(path), api.writeFile(path, text), api.commands(),
// api.doctor(), api.run(argv).

export async function mount(root, ctx) {
  const tree = await ctx.api.files();
  ctx.docbar.setBreadcrumb([ctx.host.project || 'projet', 'Source']);
  ctx.docbar.setViews(
    [{ id: 'source', label: 'Source' }, { id: 'diff', label: 'Diff contre le kit' },
     { id: 'rendu', label: 'Rendu' }],
    'source',
  );

  // L'arbre par étage est déjà réel : c'est le contrat que le lot 5 habille.
  ctx.explorer.replaceChildren();
  for (const tier of tree.tiers) {
    const head = document.createElement('div');
    head.style.color = 'var(--ink)';
    // Le terme de glossaire vient de l'API (workspace_api.TIERS) : l'interface
    // ne déduit pas un concept d'un identifiant technique.
    if (tier.term) head.dataset.term = tier.term;
    head.textContent = `${tier.label} · ${tier.count}`;
    ctx.explorer.append(head);
  }

  const total = tree.tiers.reduce((sum, t) => sum + t.count, 0);
  root.append(ctx.empty(
    'Source',
    `${total} fichier(s) répartis sur ${tree.tiers.length} étages. `
    + "L'éditeur, le diff contre le kit et la prise d'override se branchent ici (lot 5).",
    'grimoire doctor --check-paths',
  ));
  ctx.dock.echo('grimoire doctor --check-paths');
}
