// Les infobulles épinglables, et la seule source de définitions.
//
// Spécification §3.2. Une seule source : `framework/glossary.yaml`, servi par
// `/api/workspace/glossary`. Rien dans l'interface ne doit écrire une
// définition en dur : un terme se cite avec `data-term="<id>"`, et
// tests/unit/test_workspace_glossary.py refuse un `data-term` sans entrée.
//
// Mécanique (maquette « Mécaniques de la vue de travail ») :
//   survol 500 ms      → bulle courte, non épinglée
//   Alt                 → fige la bulle ; le pointeur peut y entrer
//   terme dans la bulle → bulle enfant, elle aussi épinglable, 3 niveaux max
//   Échap               → ferme toute la pile
//   Concentration       → nom et raccourci seulement, délai 800 ms

const MAX_DEPTH = 3;

let entries = new Map();
let stack = [];
let hoverTimer = null;
let pendingAnchor = null;

/** Charge le glossaire. Sans lui, les infobulles se taisent — elles n'inventent pas. */
export async function load(api) {
  const payload = await api.glossary();
  entries = new Map((payload.entries || []).map((e) => [e.id, e]));
  return payload;
}

export function get(id) {
  return entries.get(id) || null;
}

export function size() {
  return entries.size;
}

/** Les termes cités par le DOM qui n'ont pas d'entrée. Vide, ou un défaut. */
export function missingTerms(root = document) {
  const cited = new Set(
    [...root.querySelectorAll('[data-term]')].map((el) => el.dataset.term).filter(Boolean),
  );
  return [...cited].filter((id) => !entries.has(id)).sort();
}

function concentration() {
  return document.documentElement.dataset.density === 'concentration';
}

function delay() {
  return concentration() ? 800 : 500;
}

function build(entry, depth, pinned) {
  const tip = document.createElement('div');
  tip.className = 'tip';
  tip.dataset.depth = String(depth);
  tip.dataset.term = entry.id;
  tip.setAttribute('role', 'tooltip');

  const head = document.createElement('div');
  head.className = 'row';
  head.style.justifyContent = 'space-between';
  const name = document.createElement('span');
  name.className = 't';
  name.textContent = entry.nom || entry.id;
  head.append(name);

  const hint = document.createElement('span');
  hint.className = 'lbl';
  hint.textContent = pinned ? 'épinglée' : 'Alt · épingler';
  head.append(hint);
  tip.append(head);

  // Concentration non épinglé : nom et raccourci seulement. Alt rouvre la définition.
  if (!concentration() || pinned) {
    const body = document.createElement('div');
    body.style.marginTop = '6px';
    renderDefinition(body, entry, depth);
    tip.append(body);
  }

  const foot = document.createElement('div');
  foot.className = 'row';
  foot.style.marginTop = '8px';
  foot.style.gap = '10px';
  if (entry.raccourci) {
    const kbd = document.createElement('span');
    kbd.className = 'kbd';
    kbd.textContent = entry.raccourci;
    foot.append(kbd);
  }
  const esc = document.createElement('span');
  esc.className = 'lbl';
  esc.textContent = 'Échap ferme la pile';
  foot.append(esc);
  tip.append(foot);
  return tip;
}

// Les termes liés sont rendus comme boutons : le clavier les atteint, et une
// bulle enfant n'est pas un lien qui navigue.
function renderDefinition(host, entry, depth) {
  host.textContent = entry.definition || '';
  if (depth + 1 >= MAX_DEPTH) return;
  const related = (entry.termes || []).filter((id) => entries.has(id));
  if (!related.length) return;
  const row = document.createElement('div');
  row.className = 'row';
  row.style.marginTop = '8px';
  row.style.flexWrap = 'wrap';
  for (const id of related) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'term';
    button.dataset.term = id;
    button.textContent = entries.get(id).nom;
    button.addEventListener('click', () => open(id, button, depth + 1, true));
    row.append(button);
  }
  host.append(row);
}

function place(tip, anchor) {
  const box = anchor.getBoundingClientRect();
  tip.style.left = Math.max(8, Math.min(box.left, window.innerWidth - 288)) + 'px';
  const below = box.bottom + 8;
  tip.style.top = (below + 160 > window.innerHeight ? Math.max(8, box.top - 168) : below) + 'px';
}

/** Ouvre (ou remplace) la bulle du niveau *depth*. */
export function open(id, anchor, depth = 0, pinned = false) {
  const entry = entries.get(id);
  if (!entry) return null;
  closeFrom(depth);
  const tip = build(entry, depth, pinned);
  document.body.append(tip);
  place(tip, anchor);
  const frame = { id, tip, anchor, depth, pinned };
  stack.push(frame);
  return frame;
}

function closeFrom(depth) {
  while (stack.length && stack[stack.length - 1].depth >= depth) {
    stack.pop().tip.remove();
  }
}

/** Ferme toute la pile — c'est ce que fait Échap. */
export function closeAll() {
  while (stack.length) stack.pop().tip.remove();
  clearTimeout(hoverTimer);
  pendingAnchor = null;
}

function topUnpinned() {
  return stack.length && !stack[stack.length - 1].pinned;
}

/** Branche la mécanique sur un sous-arbre. Idempotent au niveau du document. */
export function attach(root = document) {
  root.addEventListener('pointerover', (event) => {
    const anchor = event.target.closest('[data-term]');
    if (!anchor || !entries.has(anchor.dataset.term)) return;
    if (anchor.closest('.tip')) return; // les termes d'une bulle s'ouvrent au clic
    clearTimeout(hoverTimer);
    pendingAnchor = anchor;
    hoverTimer = setTimeout(() => open(anchor.dataset.term, anchor, 0, false), delay());
  });

  root.addEventListener('pointerout', (event) => {
    const anchor = event.target.closest('[data-term]');
    if (!anchor) return;
    clearTimeout(hoverTimer);
    // Une bulle épinglée survit au départ du pointeur : c'est tout l'intérêt.
    if (topUnpinned() && !event.relatedTarget?.closest?.('.tip')) closeAll();
  });

  // Alt fige la bulle ouverte — ou l'ouvre tout de suite si le survol court encore.
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && stack.length) {
      event.stopPropagation();
      closeAll();
      return;
    }
    if (event.key !== 'Alt') return;
    if (stack.length) {
      const frame = stack[stack.length - 1];
      if (!frame.pinned) {
        const { id, anchor, depth } = frame;
        closeFrom(depth);
        open(id, anchor, depth, true);
      }
      return;
    }
    if (pendingAnchor) {
      clearTimeout(hoverTimer);
      open(pendingAnchor.dataset.term, pendingAnchor, 0, true);
    }
  });
}

export default { load, get, size, open, closeAll, attach, missingTerms };
