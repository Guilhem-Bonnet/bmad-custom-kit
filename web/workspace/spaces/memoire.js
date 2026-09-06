// Espace Mémoire — LOT 4.
//
// Remplace `memory.html`. Cible : le store et le graphe D'ABORD, les couches
// ensuite, l'explication d'architecture derrière un onglet. Inspecteur :
// entrée.
//
// Correction due par la revue §4.5 : la page ne doit pas expliquer
// l'architecture à la place de montrer la mémoire — deux grandes cartes
// « Vitrine / Cockpit local » remplaçaient la vue du store réel. Ici,
// l'explication existe encore (onglet Architecture) mais n'est plus ce que
// l'espace montre en premier.
//
// Correction due par la revue §4.4, appliquée ici pour le même défaut de
// classe : la dérive store ↔ graphe (`parity`) est un objet vide quand aucun
// graphe n'est câblé — ce module le lit avec des reprises (`?.`), jamais un
// accès direct qui casserait sur l'absence (le `graph_stats` de l'observatoire
// hérité).
//
// API consommées : api.memoryStatus().

const STYLE_ID = 'me-styles';

function injectStyles() {
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement('style');
  style.id = STYLE_ID;
  style.textContent = `
    .me-wrap { padding: var(--sp-4); display: flex; flex-direction: column; gap: var(--sp-5); }
    .me-kpi { display: flex; border: 1px solid var(--line); border-radius: var(--r); background: var(--e1); overflow: hidden; }
    .me-kpi-item { flex: 1; padding: var(--sp-3) var(--sp-4); border-left: 1px solid var(--line); }
    .me-kpi-item:first-child { border-left: 0; }
    .me-kpi-val { font-family: var(--mono); font-size: var(--t-xl); font-weight: 600; color: var(--ink); }
    .me-kpi-lbl { font-size: var(--t-min); color: var(--ink3); margin-top: 2px; }
    .me-graph { display: flex; gap: var(--sp-4); align-items: center; padding: var(--sp-4); border: 1px solid var(--line); border-radius: var(--r); background: var(--e1); }
    .me-graph-node { flex: 1; text-align: center; padding: var(--sp-3); border: 1px solid var(--line); border-radius: var(--r); background: var(--e2); }
    .me-graph-node .val { font-family: var(--mono); font-size: var(--t-l); color: var(--ink); }
    .me-graph-arrow { color: var(--ink3); font-size: var(--t-l); }
    .me-table { width: 100%; border-collapse: collapse; font-size: var(--t-s); }
    .me-table th { text-align: left; font-size: var(--t-min); color: var(--ink3); font-weight: 500; padding: 8px; border-bottom: 1px solid var(--line); }
    .me-table td { padding: 8px; border-bottom: 1px solid var(--line); vertical-align: top; }
    .me-arch p { max-width: 640px; color: var(--ink2); }
  `;
  document.head.append(style);
}

const dot = (cls) => Object.assign(document.createElement('span'), { className: 'dot' + (cls ? ' ' + cls : '') });
function text(tag, className, value) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  node.textContent = value;
  return node;
}
function row(...children) { const d = document.createElement('div'); d.className = 'row'; d.append(...children); return d; }

const STATE_DOT = { ok: 'ok', ready: 'ok', unavailable: 'warn', partial: 'warn', planned: '', disabled: 'bad' };
const STATE_WORD = {
  ok: 'opérationnel', ready: 'prêt', unavailable: 'indisponible',
  partial: 'partiel', planned: 'planifié', disabled: 'désactivé', uninitialized: 'non initialisée',
};

function kpiCard(items) {
  const card = document.createElement('div');
  card.className = 'me-kpi';
  for (const item of items) {
    const cell = document.createElement('div');
    cell.className = 'me-kpi-item';
    cell.append(text('div', 'me-kpi-val mono', item.value), text('div', 'me-kpi-lbl', item.label));
    card.append(cell);
  }
  return card;
}

function renderStore(wrap, ctx, memory) {
  wrap.append(kpiCard([
    { value: memory.entries == null ? '—' : String(memory.entries), label: 'entrées' },
    { value: memory.configuredBackend || '—', label: 'backend configuré' },
    { value: memory.resolvedBackend || '—', label: 'backend résolu' },
    { value: STATE_WORD[memory.state] || memory.state, label: 'état' },
  ]));

  const status = document.createElement('div');
  status.append(row(dot(STATE_DOT[memory.state] || ''), text('span', null, `store ${STATE_WORD[memory.state] || memory.state}`)));
  wrap.append(status);

  if (memory.error) {
    wrap.append(text('p', 'lbl', 'erreur best-effort : ' + memory.error));
  }

  if (memory.detail && Object.keys(memory.detail).length) {
    const table = document.createElement('table');
    table.className = 'me-table';
    const tbody = document.createElement('tbody');
    for (const [key, value] of Object.entries(memory.detail)) {
      const tr = document.createElement('tr');
      tr.append(text('td', 'lbl', key), text('td', 'mono', String(value)));
      tbody.append(tr);
    }
    table.append(tbody);
    wrap.append(table);
  }
}

function renderGraph(wrap, ctx, memory) {
  const parity = memory.parity || {};
  const h3 = text('h3', null, 'Graphe');
  h3.dataset.term = 'graphe';
  wrap.append(h3);

  if (!Object.keys(parity).length) {
    wrap.append(ctx.empty(
      'Graphe',
      "Aucun graphe de mémoire n'est câblé sur ce projet — la dérive store ↔ graphe "
      + 'ne se mesure qu\'avec un backend graphe configuré (Neo4j).',
      'grimoire memory status',
    ));
    return;
  }
  if (parity.error) {
    wrap.append(text('p', 'lbl', 'sonde du graphe en échec : ' + parity.error));
    return;
  }

  const graph = document.createElement('div');
  graph.className = 'me-graph';
  const node = (label, value) => {
    const box = document.createElement('div');
    box.className = 'me-graph-node';
    box.append(text('div', 'val mono', value == null ? '—' : String(value)), text('div', 'lbl', label));
    return box;
  };
  graph.append(node('store', parity.storeEntries));
  graph.append(text('div', 'me-graph-arrow', '↔'));
  graph.append(node('graphe', parity.graphMemories));
  graph.append(text('div', 'me-graph-arrow', '↔'));
  graph.append(node('vecteurs', parity.graphVectorObjects));
  wrap.append(graph);
  wrap.append(row(dot(parity.ok ? 'ok' : 'warn'), text('span', null, parity.ok ? 'store et graphe alignés' : `dérive : ${parity.drift}`)));
}

function renderLayers(wrap, ctx, memory) {
  const layers = memory.layers || [];
  if (!layers.length) {
    wrap.append(ctx.empty('Couches', 'Aucune couche déclarée — la config mémoire du projet est absente ou illisible.', 'grimoire memory status'));
    return;
  }
  const table = document.createElement('table');
  table.className = 'me-table';
  const thead = document.createElement('thead');
  const headRow = document.createElement('tr');
  for (const label of ['Couche', 'État', 'Backend', 'Objet', 'Écarts']) headRow.append(text('th', null, label));
  thead.append(headRow);
  table.append(thead);
  const tbody = document.createElement('tbody');
  for (const layer of layers) {
    const tr = document.createElement('tr');
    tr.append(text('td', null, layer.label || layer.id));
    const stateCell = document.createElement('td');
    stateCell.append(row(dot(STATE_DOT[layer.state] || ''), text('span', null, STATE_WORD[layer.state] || layer.state)));
    tr.append(stateCell);
    tr.append(text('td', 'lbl', layer.backend || '—'));
    tr.append(text('td', null, layer.purpose || ''));
    tr.append(text('td', 'lbl', (layer.gaps || []).join(', ') || '—'));
    tbody.append(tr);
  }
  table.append(tbody);
  wrap.append(table);
}

function renderArchitecture(wrap, ctx, memory) {
  wrap.className += ' me-arch';
  wrap.append(text('h3', null, `Profil : ${memory.layerProfile || 'non résolu'}`));
  wrap.append(text('p', null,
    "Le Memory OS du kit organise sept couches — court terme, épisodique, sémantique, "
    + 'procédurale, code graph, tâches et projet — chacune servie par un backend '
    + "qui peut être local ou distant. Cette page ne montre l'explication qu'ici : "
    + 'le store et le graphe restent la vue par défaut.',
  ));
  for (const layer of memory.layers || []) {
    const block = document.createElement('div');
    block.style.marginTop = '10px';
    block.append(text('div', null, layer.label || layer.id), text('div', 'lbl', layer.purpose || ''));
    wrap.append(block);
  }
}

export async function mount(root, ctx) {
  injectStyles();
  ctx.docbar.setBreadcrumb([ctx.host.project || 'projet', 'Mémoire']);

  const memory = await ctx.api.memoryStatus().catch(() => null);

  if (!memory || memory.state === 'uninitialized') {
    ctx.docbar.setViews([], null);
    root.append(ctx.empty(
      'Mémoire',
      "Ce projet n'a pas de mémoire configurée — ni `project-context.yaml`, ni backend "
      + 'résolu. Elle se peuplera dès qu\'une session y écrira, après `grimoire init`.',
      'grimoire memory status',
    ));
    ctx.dock.echo('grimoire memory status');
    ctx.inspector.replaceChildren(text('p', 'lbl', 'Aucune entrée à inspecter.'));
    return;
  }

  let view = 'store';
  const draw = () => {
    root.replaceChildren();
    const wrap = document.createElement('div');
    wrap.className = 'me-wrap';
    if (view === 'store') renderStore(wrap, ctx, memory);
    else if (view === 'graphe') renderGraph(wrap, ctx, memory);
    else if (view === 'couches') renderLayers(wrap, ctx, memory);
    else if (view === 'architecture') renderArchitecture(wrap, ctx, memory);
    root.append(wrap);
  };

  ctx.docbar.setViews(
    [{ id: 'store', label: 'Store' }, { id: 'graphe', label: 'Graphe' },
     { id: 'couches', label: 'Couches' }, { id: 'architecture', label: 'Architecture' }],
    view,
    (id) => { view = id; draw(); },
  );

  draw();
  // Aucune route ne sert le détail d'une entrée individuelle du store — seul
  // son statut agrégé (`/api/memory/status`) existe côté vue de travail. Le
  // dire honnêtement plutôt que fabriquer une liste d'entrées inspectables.
  ctx.inspector.replaceChildren(text('p', 'lbl', "L'inspecteur d'entrée individuelle n'a pas encore de route côté API — seul le statut agrégé du store est servi ici."));
  ctx.dock.echo('grimoire memory status');
}
