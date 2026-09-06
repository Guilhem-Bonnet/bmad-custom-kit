// Le seul endroit qui parle à l'API locale.
//
// Deux hôtes, une coque : `grimoire serve` sert un projet, `grimoire cockpit
// serve` en sert N et attend `?project=<slug>` sur chaque lecture. Ce module
// porte cette différence pour que les six modules d'espace ne l'aient jamais à
// connaître : ils appellent `api.tasks()`, et la cible est déjà bonne.
//
// Aucun module d'espace ne doit appeler `fetch` directement. Une route qui
// manque s'ajoute ici, et son contrat est celui de
// `src/grimoire/tools/workspace_routes.py`.

const WS = '/api/workspace/';

/** État de l'hôte, résolu une fois à l'amorçage. */
export const host = {
  /** 'atelier' | 'cockpit' — décidé par la réponse de /api/status. */
  kind: 'atelier',
  /** Slug du projet ciblé côté cockpit ; null en atelier. */
  project: null,
  /** Vrai quand l'hôte refuse les écritures (cockpit). */
  readOnly: false,
  status: null,
};

class ApiError extends Error {
  constructor(message, code, payload) {
    super(message);
    this.code = code;
    this.payload = payload;
  }
}
export { ApiError };

function withProject(path) {
  if (!host.project) return path;
  return path + (path.includes('?') ? '&' : '?') + 'project=' + encodeURIComponent(host.project);
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(withProject(path), {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
  } catch (cause) {
    throw new ApiError('API locale injoignable', 0, { cause: String(cause) });
  }
  const text = await response.text();
  let payload = null;
  if (text) {
    try { payload = JSON.parse(text); } catch { payload = { raw: text }; }
  }
  if (!response.ok) {
    const message = (payload && (payload.error || payload.message)) || `HTTP ${response.status}`;
    throw new ApiError(message, response.status, payload);
  }
  return payload;
}

function get(path, params) {
  const query = params ? '?' + new URLSearchParams(params).toString() : '';
  return request(path + query);
}

function post(path, body) {
  if (host.readOnly) {
    return Promise.reject(new ApiError('hôte en lecture seule', 403, { readOnly: true }));
  }
  return request(path, { method: 'POST', body: JSON.stringify(body || {}) });
}

/** Amorçage : résout l'hôte et le projet ciblé. À appeler une fois. */
export async function boot() {
  const params = new URLSearchParams(location.search);
  const wanted = params.get('project');
  if (wanted) host.project = wanted;
  const status = await get('/api/status');
  host.status = status;
  host.kind = status.host === 'cockpit' ? 'cockpit' : 'atelier';
  host.readOnly = status.readOnly === true;
  if (host.kind === 'cockpit') host.project = host.project || status.project || status.slug;
  else host.project = null;
  return status;
}

// ── Lectures partagées par les deux hôtes ───────────────────────────────────

export const api = {
  status: () => get('/api/status'),
  health: () => get('/api/health'),
  projects: () => get('/api/projects'),
  memoryStatus: () => get('/api/memory/status'),
  blueprints: () => get('/api/blueprints'),
  primitives: () => get('/api/primitives'),
  features: () => get('/api/features'),
  stigmergy: () => get('/api/stigmergy'),
  eventsLog: () => get('/api/events/log'),
  otel: () => get('/api/otel'),

  // ── Vue de travail ────────────────────────────────────────────────────────
  glossary: () => get(WS + 'glossary'),
  tasks: (params) => get(WS + 'tasks', params),
  task: (id) => get(WS + 'tasks/' + encodeURIComponent(id)),
  taskTrace: (id) => get(WS + 'tasks/' + encodeURIComponent(id) + '/trace'),
  files: (tier) => get(WS + 'files', tier ? { tier } : undefined),
  file: (path) => get(WS + 'file', { path }),
  fileDiff: (path) => get(WS + 'file/diff', { path }),
  fileUsage: (path) => get(WS + 'file/usage', { path }),
  fileHistory: (path) => get(WS + 'file/history', { path }),
  commands: () => get(WS + 'commands'),
  doctor: () => get(WS + 'doctor'),

  // ── Écritures : atelier seulement, refusées côté cockpit ──────────────────
  taskAction: (id, action, body) =>
    post(WS + 'tasks/' + encodeURIComponent(id) + '/' + action, body),
  createOverride: (path) => post(WS + 'file/override', { path }),
  writeFile: (path, text) => post(WS + 'file/write', { path, text }),
  run: (argv) => post(WS + 'command', { argv }),
};

export default api;
