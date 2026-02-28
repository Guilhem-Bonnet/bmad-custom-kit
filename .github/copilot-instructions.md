# GitHub Copilot — Instructions for BMAD Custom Kit

## Project Context

This repository is the **BMAD Custom Kit** — a framework for bootstrapping AI-assisted software projects with specialized agents, archetype-based DNA constraints, and structured memory.

**Key directories:**
- `bmad-init.sh` — main CLI: `session-branch`, `install`, `doctor`, `validate`, `changelog`, `hooks`, `trace`, `resume`, `bench`, `forge`, `guard`, `evolve`
- `archetypes/` — project archetypes (minimal, web-app, infra-ops, fix-loop, stack)
- `framework/` — DNA schema, hooks, tools (gen-tests.py, agent-bench.py, agent-forge.py, context-guard.py, dna-evolve.py, bmad-completion.zsh), agent-rules, context-router, MCP server, BMAD_TRACE
- `_bmad/` — BMAD runtime (agents, workflows, memory)
- `docs/` — human-readable documentation

## Code Style Rules

### Shell (bmad-init.sh, framework/hooks/*.sh)
- Bash only (not POSIX sh) — use `[[ ]]`, `local`, heredocs, arrays
- Always `set -euo pipefail` in standalone scripts (hooks)
- Colors: `RED/GREEN/YELLOW/BLUE/NC` variables already defined in bmad-init.sh
- Functions: `cmd_<subcommand>()` pattern for subcommands
- Error output: `error "message"` function (exits 1), `warn "msg"` (continues), `info "msg"` (neutral)
- Always add `shift` at start of subcommand functions to remove subcommand arg
- Python inline via heredoc uses `PYEOF` as delimiter

### YAML (*.dna.yaml)
- Schema ref: `# yaml-language-server: $schema=../../framework/archetype-dna.schema.yaml`
- Required fields: `$schema: bmad-archetype-dna/v1`, `id`, `name`, `version`, `description`, `archetype_type`
- `acceptance_criteria[].blocking: true` = critique, `false` = soft warning
- `tools_required[].required: true` = install vérifiée par `doctor`

### Python (framework/tools/*.py)
- Type hints on all functions
- Ruff-compatible (no `any`, explicit error types)
- `if __name__ == "__main__"` guard always present
- Prefer `pathlib.Path` over `os.path`

### Markdown (docs/*.md, archetypes/**/*.md)
- Langue : Français (sauf code/commandes)
- Titres : pas de numérotation manuelle
- Liens relatifs depuis le fichier courant

## Agent DNA Constraints

When generating code for an archetype, respect its `acceptance_criteria`:

| Archetype | Key constraints |
|-----------|----------------|
| `stack/go` | table-driven tests, `go vet` clean, no goroutine leak |
| `stack/typescript` | `strict: true` tsconfig, no `any`, typed props |
| `stack/python` | type hints everywhere, `ruff` clean, `pytest` |
| `stack/terraform` | `terraform validate` + `terraform fmt`, `tfsec` |
| `stack/k8s` | resource limits required, readiness/liveness probes |
| `stack/docker` | multi-stage builds, non-root user (`USER 1000`) |
| `stack/ansible` | idempotent tasks, `ansible-lint` clean |
| `infra-ops` | Completion Contract (`cc-verify.sh`) before any "done" |
| `fix-loop` | FER (Fix Evidence Record) YAML for every fix session |
| `minimal` | `cc-verify.sh` passes, shared-context.md filled |

## BMAD_TRACE Convention

Every significant decision or code generation should be traceable. When generating non-trivial code, suggest adding a TRACE entry:
```markdown
[DECISION] <description> | agent:copilot | <rationale>
```

## Git Commit Convention

Conventional Commits format preferred:
- `feat(<scope>): <description>` — new feature
- `fix(<scope>): <description>` — bug fix
- `chore(<scope>): <description>` — maintenance
- `docs(<scope>): <description>` — documentation only
- `refactor(<scope>): <description>` — no behavior change
- `BM-XX: <description>` — also accepted for BMAD backlog items

Scopes: `init`, `hooks`, `dna`, `stack`, `docs`, `vscode`, `ci`, `memory`, `mcp`, `tools`

## Rate Limit Best Practices

- Keep conversation context minimal — start fresh chats after ~20 exchanges
- Reference only immediately needed files (avoid broad `@workspace`)
- Use local tools (`guard`, `bench`, `evolve`) for analysis — they consume zero API quota
- If rate-limited on one model, switch to another (quotas are per-model)

## Important Anti-Patterns to Avoid

- ❌ Never suggest `rm -rf` without guard on path variables
- ❌ Never write DNA files without `$schema` reference
- ❌ Never mark an acceptance criterion `blocking: true` without a `test_command`
- ❌ Never add `--force` to git operations without explicit user confirmation
- ❌ Never hardcode `/home/user/` paths — use `$HOME` or relative paths
- ❌ Never generate Python without type hints in this project
- ❌ Never create a `framework/tools/*.py` without a `cmd_<name>()` wrapper in `bmad-init.sh`
- ❌ Never add a new `bmad-init.sh` subcommand without updating `bmad-completion.zsh`
- ❌ Never modify `guard` exit codes — 0/1/2 are CI-contract (0=OK, 1=warn, 2=critical)
