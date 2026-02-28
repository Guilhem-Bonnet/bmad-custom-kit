# Agent2Agent Protocol — Handoff Structuré Cross-Outils (BM-32)

> **BM-32** — Stub d'implémentation du protocole Agent2Agent (A2A) de Google (mars 2025).
>
> **Objectif** : Permettre à un agent BMAD de déléguer une tâche à un agent dans un autre
> outil (Cursor, Claude Desktop, VS Code Copilot, OpenAI Assistants) avec un contexte
> structuré et récupérer la réponse de façon standardisée.
>
> **Référence** : [Google Agent2Agent Protocol](https://google.github.io/A2A/) — standard ouvert
> pour la communication inter-agents cross-plateformes.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Agent BMAD (émetteur)                          │
│  ex: sm/Bob dans VS Code Copilot                │
└──────────────────┬──────────────────────────────┘
                   │  A2A Task Request (JSON)
                   ▼
┌─────────────────────────────────────────────────┐
│  BMAD A2A Dispatcher                           │
│  framework/tools/a2a-dispatcher.py             │
│                                                  │
│  Routes vers :                                   │
│  ├── bmad-local      (autre agent BMAD local)   │
│  ├── cursor-agent    (via Cursor API)            │
│  ├── claude-desktop  (via Claude Projects)       │
│  ├── openai-agent    (via OpenAI Assistants API) │
│  └── mcp-agent       (via MCP sampling)          │
└──────────────────┬──────────────────────────────┘
                   │  A2A Task Response (JSON)
                   ▼
┌─────────────────────────────────────────────────┐
│  Agent BMAD (récepteur) — résultat intégré      │
└─────────────────────────────────────────────────┘
```

---

## Format A2A Task Request (BMAD Profile)

```json
{
  "a2a_version": "1.0",
  "task_id": "bmad-task-20260227-143022-abc123",
  "sender": {
    "agent_id": "sm/Bob",
    "tool": "github-copilot",
    "project": "my-saas-app",
    "session_branch": "feature-auth"
  },
  "recipient": {
    "agent_id": "architect/Winston",
    "tool": "bmad-local",
    "capabilities_required": ["architecture-review", "adr-creation"]
  },
  "task": {
    "type": "review",
    "priority": "high",
    "title": "Valider l'architecture Auth JWT avant implémentation",
    "description": "L'agent dev a proposé JWT stateless avec Redis blacklist. Valider la cohérence avec l'ADR existant et les contraintes scalabilité.",
    "context": {
      "story": "US-042",
      "sprint": "sprint-7",
      "files_to_review": ["docs/adr-042-auth.md", "src/auth/jwt.ts"],
      "constraints": "Must support 10k concurrent users, PCI-DSS compliant",
      "prior_decisions": "ADR-040: microservices, ADR-041: PostgreSQL for persistence"
    },
    "acceptance_criteria": [
      "Valider ou invalider l'approche JWT stateless",
      "Si invalide : proposer alternative avec justification",
      "Créer ADR-042 avec la décision finale",
      "Estimer la complexité d'implémentation (S/M/L)"
    ],
    "deadline_ms": null
  },
  "handoff_context": {
    "previous_output": "L'agent dev a déjà rédigé un plan d'implémentation en draft/US-042-impl-plan.md",
    "shared_memory": {
      "qdrant_endpoint": "http://localhost:6333",
      "collection_prefix": "my-saas-app",
      "relevant_types": ["decisions", "shared-context"]
    }
  },
  "response_format": {
    "type": "structured",
    "schema": {
      "decision": "approve | reject | approve-with-conditions",
      "rationale": "string",
      "adr_path": "string | null",
      "complexity": "S | M | L | XL",
      "conditions": ["string"]
    }
  }
}
```

---

## Format A2A Task Response (BMAD Profile)

```json
{
  "a2a_version": "1.0",
  "task_id": "bmad-task-20260227-143022-abc123",
  "responder": {
    "agent_id": "architect/Winston",
    "tool": "bmad-local",
    "completed_at": "2026-02-27T14:45:22Z"
  },
  "status": "completed",
  "result": {
    "decision": "approve-with-conditions",
    "rationale": "JWT stateless OK pour ≤10k users. Redis blacklist ajoute complexité ops — préférer expiry court (15min) + refresh token rotation.",
    "adr_path": "docs/adr-042-auth-jwt.md",
    "complexity": "M",
    "conditions": [
      "Expiry access token : 15min max",
      "Refresh token rotation obligatoire",
      "Blacklist Redis optionnelle — activer seulement si revocation immédiate requise"
    ]
  },
  "artefacts": [
    {
      "type": "adr",
      "path": "docs/adr-042-auth-jwt.md",
      "created": true
    }
  ],
  "memory_written": [
    {
      "type": "decisions",
      "content": "ADR-042 : JWT stateless + refresh token rotation. Blacklist optionnelle."
    }
  ],
  "trace_id": "bmad-task-20260227-143022-abc123"
}
```

---

## Stub Python (`framework/tools/a2a-dispatcher.py`)

```python
#!/usr/bin/env python3
"""
a2a-dispatcher.py — BMAD Agent2Agent Protocol Dispatcher (BM-32)
Route les A2A Task Requests vers l'agent/outil destinataire.

Statut : STUB — implémentation complète nécessite HTTP + auth
Routes implémentées :
  ✅ bmad-local   (sous-process Python)
  🔵 mcp-agent    (via MCP sampling — BM-31)
  🔵 cursor-agent (nécessite Cursor API — non disponible publiquement)
  🔵 openai-agent (nécessite OpenAI Assistants API key)
"""
import json, sys, subprocess

def dispatch(task_request: dict) -> dict:
    recipient_tool = task_request.get("recipient", {}).get("tool", "bmad-local")
    
    if recipient_tool == "bmad-local":
        return dispatch_local(task_request)
    elif recipient_tool == "mcp-agent":
        return dispatch_via_mcp(task_request)
    else:
        return {
            "status": "error",
            "error": f"Tool '{recipient_tool}' non encore supporté. Supportés: bmad-local, mcp-agent"
        }

def dispatch_local(task: dict) -> dict:
    """Délégation vers un agent BMAD local via contexte structuré."""
    recipient = task["recipient"]["agent_id"]
    context = json.dumps(task["task"]["context"], indent=2)
    # En pratique : formater le prompt et l'envoyer au LLM avec le persona de l'agent
    print(f"→ Dispatching to local agent: {recipient}")
    return {"status": "dispatched", "method": "local", "agent": recipient}

def dispatch_via_mcp(task: dict) -> dict:
    """Délégation via MCP sampling (BM-31) — appel LLM imbriqué."""
    # Nécessite MCP v2 + sampling capability
    return {"status": "stub", "error": "MCP sampling non encore implémenté localement"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 a2a-dispatcher.py task-request.json")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        request = json.load(f)
    response = dispatch(request)
    print(json.dumps(response, indent=2, ensure_ascii=False))
```

---

## Protocole pour les agents BMAD

Quand un agent souhaite déléguer à un autre outil :

```markdown
## A2A HANDOFF PROTOCOL (BM-32)

Quand je dois déléguer une tâche à un agent dans un autre outil :

1. Construire un A2A Task Request JSON avec :
   - task.description : objectif précis
   - task.context : fichiers, ADRs, contraintes pertinentes
   - task.acceptance_criteria : liste des livrables attendus
   - handoff_context.shared_memory : endpoint Qdrant si disponible
   - response_format.schema : structure de la réponse attendue

2. Envoyer via : python3 framework/tools/a2a-dispatcher.py task.json

3. Parser la réponse :
   - artefacts[] → vérifier que les fichiers ont été créés
   - memory_written[] → confirmer que decisions/learnings ont été mémorisés
   - result → utiliser le résultat structuré pour continuer le workflow

4. Logger dans BMAD_TRACE.md :
   [HANDOFF→{recipient.agent_id}@{recipient.tool}] "{task.title}"
```

---

## Compatibilité Cross-Outils (Roadmap)

| Outil | Statut | Mécanisme |
|-------|--------|-----------|
| BMAD local | ✅ Stub | Sous-process + contexte structuré |
| VS Code Copilot MCP | 🔵 Prévu BM-31 | MCP sampling |
| Cursor | 🔵 Roadmap | Cursor API (non public) |
| Claude Desktop | 🔵 Roadmap | Claude Projects API |
| OpenAI Assistants | 🔵 Roadmap | Assistants API v2 |
| AutoGen | 🔵 Roadmap | AutoGen GroupChat protocol |

---

## Référence croisée

- MCP v2 Sampling : [framework/mcp/bmad-mcp-server.md](mcp/bmad-mcp-server.md)
- Subagent Orchestration : [framework/workflows/subagent-orchestration.md](workflows/subagent-orchestration.md)
- Boomerang : [framework/workflows/boomerang-orchestration.md](workflows/boomerang-orchestration.md)
- BMAD Trace : [framework/bmad-trace.md](bmad-trace.md)

---

*BM-32 Agent2Agent Protocol Stub | framework/agent2agent.md*
