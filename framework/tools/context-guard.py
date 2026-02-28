#!/usr/bin/env python3
"""
BMAD Context Budget Guard — BM-55
===================================
Scanne tous les fichiers qu'un agent va charger au démarrage et estime
le budget de contexte consommé avant même la première question utilisateur.

Problème résolu : Un agent BMAD charge silencieusement 8-15 fichiers
(agent.md, agent-base.md, shared-context.md, mémoire, TRACE récent…).
Sur un projet actif, ça peut atteindre 60-80K tokens — la fenêtre d'un
modèle 128K est déjà à moitié utilisée au démarrage.

Ce tool rend ça visible, mesurable, et actionnable.

Usage:
    python3 context-guard.py                        # Tous les agents du projet
    python3 context-guard.py --agent atlas          # Un agent spécifique
    python3 context-guard.py --agent atlas --detail # Détail fichier par fichier
    python3 context-guard.py --threshold 60         # Alerte si > 60% budget
    python3 context-guard.py --model gpt-4o         # Fenêtre cible
    python3 context-guard.py --suggest              # + recommandations Mnemo
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ── Modèles LLM — fenêtres de contexte connues (en tokens) ──────────────────

MODEL_WINDOWS: dict[str, int] = {
    # Anthropic
    "claude-3-5-sonnet": 200_000,
    "claude-3-7-sonnet": 200_000,
    "claude-opus-4":     200_000,
    "claude-sonnet-4":   200_000,
    "claude-haiku":      200_000,
    # OpenAI
    "gpt-4o":            128_000,
    "gpt-4o-mini":       128_000,
    "gpt-4-turbo":       128_000,
    "o1":                200_000,
    "o3":                200_000,
    # Google
    "gemini-1.5-pro":  1_000_000,
    "gemini-2.0-flash":1_000_000,
    # Local
    "codestral":         32_000,
    "llama3":            8_000,
    "mistral":           32_000,
    "qwen2.5":           32_000,
    # GitHub Copilot default
    "copilot":           200_000,
}

DEFAULT_MODEL = "copilot"

# Seuils de santé
THRESHOLD_WARN = 40   # % — Jaune
THRESHOLD_CRIT = 70   # % — Rouge

# ── Estimation tokens ─────────────────────────────────────────────────────────
# Approximation : 1 token ≈ 4 chars (EN) / 3.5 chars (FR)
# On utilise 3.7 comme compromis FR/EN
CHARS_PER_TOKEN = 3.7


def estimate_tokens(text: str) -> int:
    return max(1, int(len(text) / CHARS_PER_TOKEN))


def read_file_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return ""


# ── Profil de chargement d'un agent ──────────────────────────────────────────

@dataclass
class FileLoad:
    """Un fichier chargé par un agent."""
    path: Path
    role: str             # "agent-definition" | "base-protocol" | "memory" | "trace" | "dna" | "project"
    content: str = ""
    tokens: int = 0
    loaded: bool = True

    def compute(self) -> None:
        if self.path.exists():
            self.content = read_file_safe(self.path)
            self.tokens = estimate_tokens(self.content)
        else:
            self.loaded = False
            self.tokens = 0


@dataclass
class AgentBudget:
    """Budget de contexte complet d'un agent."""
    agent_id: str
    agent_path: Path
    model: str
    model_window: int
    loads: list[FileLoad] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return sum(f.tokens for f in self.loads if f.loaded)

    @property
    def pct(self) -> float:
        return (self.total_tokens / self.model_window * 100) if self.model_window else 0

    @property
    def status(self) -> str:
        if self.pct >= THRESHOLD_CRIT:
            return "CRITICAL"
        if self.pct >= THRESHOLD_WARN:
            return "WARNING"
        return "OK"

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.model_window - self.total_tokens)

    def biggest_files(self, n: int = 3) -> list[FileLoad]:
        return sorted([f for f in self.loads if f.loaded], key=lambda x: x.tokens, reverse=True)[:n]


# ── Résolution des fichiers chargés par un agent ─────────────────────────────

def resolve_agent_loads(
    agent_path: Path,
    project_root: Path,
) -> list[FileLoad]:
    """
    Reconstruit la liste des fichiers qu'un agent va charger.
    Basé sur la convention d'activation BMAD (steps 1-2 + contexte projet).
    """
    loads: list[FileLoad] = []

    # 1. L'agent lui-même
    loads.append(FileLoad(path=agent_path, role="agent-definition"))

    # 2. agent-base.md (BASE PROTOCOL — step 2 d'activation)
    base_paths = [
        project_root / "_bmad/_config/custom/agent-base.md",
        project_root / "framework/agent-base.md",
    ]
    for bp in base_paths:
        if bp.exists():
            loads.append(FileLoad(path=bp, role="base-protocol"))
            break

    # 3. shared-context.md (chargé en step 2 via BASE PROTOCOL)
    shared_ctx = project_root / "_bmad/_memory/shared-context.md"
    loads.append(FileLoad(path=shared_ctx, role="memory"))

    # 4. project-context.yaml
    proj_ctx = project_root / "project-context.yaml"
    loads.append(FileLoad(path=proj_ctx, role="project"))

    # 5. Fichiers mémoire agent-spécifiques
    agent_id = agent_path.stem
    memory_candidates = [
        project_root / f"_bmad/_memory/{agent_id}-learnings.md",
        project_root / f"_bmad/_memory/agent-learnings-{agent_id}.md",
    ]
    for mc in memory_candidates:
        if mc.exists():
            loads.append(FileLoad(path=mc, role="memory"))

    # 6. Failure museum (LAZY-LOAD — toujours potentiellement chargé)
    failure_museum = project_root / "_bmad/_memory/failure-museum.md"
    if failure_museum.exists():
        loads.append(FileLoad(path=failure_museum, role="memory"))

    # 7. BMAD_TRACE (dernières N entrées — approximé par les 200 dernières lignes)
    trace_path = project_root / "_bmad-output/BMAD_TRACE.md"
    if trace_path.exists():
        # Simuler le chargement des 200 dernières lignes du TRACE
        try:
            lines = trace_path.read_text(encoding="utf-8", errors="replace").splitlines()
            recent_trace = "\n".join(lines[-200:])
            # Créer un FileLoad synthétique pour le contenu partiel
            fl = FileLoad(path=trace_path, role="trace")
            fl.content = recent_trace
            fl.tokens = estimate_tokens(recent_trace)
            fl.loaded = True
            loads.append(fl)
            # Éviter le recompute
            loads[-1].loaded = True
            return loads
        except OSError:
            pass
    loads.append(FileLoad(path=trace_path, role="trace"))

    return loads


def compute_budget(
    agent_path: Path,
    project_root: Path,
    model: str,
) -> AgentBudget:
    """Calcule le budget complet d'un agent."""
    window = MODEL_WINDOWS.get(model, MODEL_WINDOWS[DEFAULT_MODEL])
    budget = AgentBudget(
        agent_id=agent_path.stem,
        agent_path=agent_path,
        model=model,
        model_window=window,
    )
    loads = resolve_agent_loads(agent_path, project_root)
    for fl in loads:
        if fl.tokens == 0 and not fl.content:
            fl.compute()
    budget.loads = loads
    return budget


# ── Détection des agents ──────────────────────────────────────────────────────

def find_agents(project_root: Path) -> list[Path]:
    """Liste tous les fichiers agents BMAD dans le projet."""
    agents = []
    search_dirs = [
        project_root / "_bmad/_config/custom/agents",
        project_root / "_bmad/bmm/agents",
        project_root / "archetypes",
    ]
    for d in search_dirs:
        if not d.exists():
            continue
        for f in sorted(d.rglob("*.md")):
            # Exclure les templates et proposals
            if any(x in f.name for x in ["tpl.", "proposed.", "template.", "README"]):
                continue
            # Vérifier que c'est un vrai agent (contient activation BMAD)
            try:
                content = f.read_text(encoding="utf-8", errors="replace")[:500]
                if "<activation" in content or 'NEVER break character' in content:
                    agents.append(f)
            except OSError:
                pass
    return agents


# ── Recommandations ───────────────────────────────────────────────────────────

CONSOLIDATION_RULES = {
    "trace": (
        "BMAD_TRACE est volumineux",
        "Mnemo [CH] → consolidation TRACE (garder les 50 dernières entrées)"
    ),
    "memory": (
        "Fichiers mémoire volumineux",
        "Mnemo [CH] → session-save / consolidation des learnings"
    ),
    "agent-definition": (
        "Fichier agent volumineux (> 200 prompts ?)",
        "Revoir le scope — splitter en sous-agents ou réduire les prompts"
    ),
    "base-protocol": (
        "agent-base.md volumineux — partagé par tous les agents",
        "Optimiser agent-base.md — le compresser bénéficie à tous les agents"
    ),
}

def generate_recommendations(budgets: list[AgentBudget]) -> list[str]:
    """Génère des recommandations actionnables basées sur les budgets."""
    recs: list[str] = []

    # Recommandations globales
    worst = sorted(budgets, key=lambda b: b.pct, reverse=True)
    if worst and worst[0].pct >= THRESHOLD_CRIT:
        recs.append(f"🚨 URGENT : {worst[0].agent_id} consomme {worst[0].pct:.0f}% du contexte au démarrage")

    # Fichiers communs les plus gros
    all_loads: dict[str, list[int]] = {}
    for budget in budgets:
        for fl in budget.loads:
            if fl.loaded:
                key = str(fl.path)
                if key not in all_loads:
                    all_loads[key] = []
                all_loads[key].append(fl.tokens)

    # Fichier partagé le plus gros
    shared_files = {k: v for k, v in all_loads.items() if len(v) > 1}
    if shared_files:
        biggest_shared = max(shared_files, key=lambda k: shared_files[k][0])
        tokens = shared_files[biggest_shared][0]
        agents_count = len(shared_files[biggest_shared])
        if tokens > 5000:
            short = Path(biggest_shared).name
            recs.append(
                f"📦 {short} ({tokens:,} tokens) × {agents_count} agents = "
                f"{tokens * agents_count:,} tokens totaux — priorité de réduction"
            )

    # Recommandations par type de fichier volumineux
    seen_rules: set[str] = set()
    for budget in worst[:3]:
        for fl in budget.biggest_files(2):
            if fl.role in CONSOLIDATION_RULES and fl.role not in seen_rules:
                seen_rules.add(fl.role)
                reason, action = CONSOLIDATION_RULES[fl.role]
                recs.append(f"💡 {reason} → {action}")

    return recs[:6]


# ── Formatage ──────────────────────────────────────────────────────────────────

def fmt_tokens(n: int) -> str:
    if n >= 1_000:
        return f"{n / 1000:.1f}K"
    return str(n)


def status_icon(status: str) -> str:
    return {"OK": "✅", "WARNING": "⚠️ ", "CRITICAL": "🔴"}.get(status, "❓")


def bar(pct: float, width: int = 20) -> str:
    filled = int(min(pct / 100, 1.0) * width)
    empty = width - filled
    char = "█" if pct < THRESHOLD_WARN else ("▓" if pct < THRESHOLD_CRIT else "░")
    return f"[{char * filled}{'·' * empty}]"


def role_icon(role: str) -> str:
    return {
        "agent-definition": "🤖",
        "base-protocol":    "⚙️ ",
        "memory":           "🧠",
        "trace":            "📋",
        "dna":              "🧬",
        "project":          "📁",
    }.get(role, "📄")


def print_budget(budget: AgentBudget, detail: bool = False, threshold: int = THRESHOLD_WARN) -> None:
    """Affiche le budget d'un agent."""
    icon = status_icon(budget.status)
    b = bar(budget.pct)
    print(f"  {icon} {budget.agent_id:<30} {b} {budget.pct:5.1f}%  "
          f"({fmt_tokens(budget.total_tokens):>7} / {fmt_tokens(budget.model_window)} tokens)")

    if detail or budget.pct >= threshold:
        for fl in sorted(budget.loads, key=lambda f: f.tokens, reverse=True):
            if not fl.loaded:
                print(f"       {role_icon(fl.role)} {fl.path.name:<40} (absent)")
                continue
            if fl.tokens == 0:
                continue
            pct_of_budget = fl.tokens / budget.model_window * 100
            indent = "  "
            if detail:
                print(f"     {indent}{role_icon(fl.role)} "
                      f"{fl.path.name:<38} {fmt_tokens(fl.tokens):>7} tok  ({pct_of_budget:.1f}%)")


def print_summary_table(budgets: list[AgentBudget]) -> None:
    """Tableau récapitulatif."""
    ok = sum(1 for b in budgets if b.status == "OK")
    warn = sum(1 for b in budgets if b.status == "WARNING")
    crit = sum(1 for b in budgets if b.status == "CRITICAL")

    total_agent_tokens = sum(b.total_tokens for b in budgets)

    print()
    print(f"  ─────────────────────────────────────────────")
    print(f"  Agents analysés : {len(budgets)}")
    print(f"    ✅ OK       : {ok}")
    print(f"    ⚠️  WARNING  : {warn}  (> {THRESHOLD_WARN}% du contexte au démarrage)")
    print(f"    🔴 CRITICAL : {crit}  (> {THRESHOLD_CRIT}% du contexte au démarrage)")
    print(f"  Tokens totaux (sum) : {fmt_tokens(total_agent_tokens)}")
    print()


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="BMAD Context Budget Guard — estime le budget de contexte LLM par agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples :
  python3 context-guard.py
  python3 context-guard.py --agent atlas --detail
  python3 context-guard.py --model gpt-4o --threshold 50
  python3 context-guard.py --suggest
  python3 context-guard.py --json > context-report.json
        """,
    )
    parser.add_argument("--agent", metavar="AGENT_ID",
                        help="Analyser un agent spécifique (ID ou nom de fichier)")
    parser.add_argument("--detail", action="store_true",
                        help="Afficher le détail fichier par fichier")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        choices=sorted(MODEL_WINDOWS.keys()),
                        help=f"Modèle cible (défaut: {DEFAULT_MODEL})")
    parser.add_argument("--threshold", type=int, default=THRESHOLD_WARN,
                        metavar="PCT",
                        help=f"Seuil d'alerte en %% (défaut: {THRESHOLD_WARN})")
    parser.add_argument("--suggest", action="store_true",
                        help="Afficher des recommandations de réduction")
    parser.add_argument("--project-root", metavar="PATH", default=".",
                        help="Racine du projet BMAD (défaut: répertoire courant)")
    parser.add_argument("--json", action="store_true",
                        help="Sortie JSON pour intégration CI")
    parser.add_argument("--list-models", action="store_true",
                        help="Lister les modèles supportés et leur fenêtre de contexte")

    args = parser.parse_args()

    if args.list_models:
        print("\nModèles supportés :\n")
        for m, w in sorted(MODEL_WINDOWS.items(), key=lambda x: x[1], reverse=True):
            print(f"  {m:<25} {w:>10,} tokens ({fmt_tokens(w)})")
        return

    project_root = Path(args.project_root).resolve()

    # Trouver les agents
    if args.agent:
        # Chercher l'agent par ID ou chemin
        agents = find_agents(project_root)
        filtered = [a for a in agents if args.agent.lower() in a.stem.lower()]
        if not filtered:
            # Essai en chemin direct
            direct = Path(args.agent)
            if direct.exists():
                filtered = [direct]
            else:
                print(f"❌ Agent '{args.agent}' introuvable.", file=sys.stderr)
                print(f"   Agents disponibles : {[a.stem for a in agents]}")
                sys.exit(1)
        agent_paths = filtered
    else:
        agent_paths = find_agents(project_root)
        if not agent_paths:
            print("ℹ️  Aucun agent BMAD trouvé dans ce projet.")
            print(f"   Projet root : {project_root}")
            print("   Initialisez avec : bash bmad-init.sh --name ...")
            return

    # Calculer les budgets
    budgets = []
    for ap in agent_paths:
        budget = compute_budget(ap, project_root, args.model)
        budgets.append(budget)

    # Sortie JSON
    if args.json:
        import json
        data = {
            "model": args.model,
            "model_window": MODEL_WINDOWS.get(args.model, MODEL_WINDOWS[DEFAULT_MODEL]),
            "project_root": str(project_root),
            "agents": [
                {
                    "id": b.agent_id,
                    "status": b.status,
                    "total_tokens": b.total_tokens,
                    "pct": round(b.pct, 1),
                    "remaining_tokens": b.remaining_tokens,
                    "files": [
                        {
                            "path": str(f.path.relative_to(project_root)) if f.path.is_relative_to(project_root) else str(f.path),
                            "role": f.role,
                            "tokens": f.tokens,
                            "loaded": f.loaded,
                        }
                        for f in b.loads
                    ],
                }
                for b in budgets
            ],
        }
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return

    # Affichage console
    print()
    print(f"  BMAD Context Budget Guard  ·  modèle: {args.model}  "
          f"·  fenêtre: {fmt_tokens(MODEL_WINDOWS.get(args.model, 0))} tokens")
    print()
    print(f"  {'Agent':<32} {'Budget consommé':<24} {'  %':>6}  {'Tokens':>8}")
    print(f"  {'─' * 75}")

    # Trier par %
    for budget in sorted(budgets, key=lambda b: b.pct, reverse=True):
        print_budget(budget, detail=args.detail, threshold=args.threshold)

    print_summary_table(budgets)

    # Recommandations
    if args.suggest or any(b.status != "OK" for b in budgets):
        recs = generate_recommendations(budgets)
        if recs:
            print("  Recommandations :")
            for r in recs:
                print(f"    {r}")
            print()

    # Code de retour CI
    if any(b.status == "CRITICAL" for b in budgets):
        sys.exit(2)
    if any(b.status == "WARNING" for b in budgets):
        sys.exit(1)


if __name__ == "__main__":
    main()
