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
    "codex":             192_000,
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

# ── Capacités LLM par modèle ─────────────────────────────────────────────────
# Chaque modèle est classé sur 4 axes (matching model_affinity des agents)
# reasoning: low | medium | high | extreme
# context_window: small (≤32K) | medium (≤128K) | large (≤200K) | massive (>200K)
# speed: fast | medium | slow-ok
# cost/tier: economy | standard | premium

REASONING_RANK = {"low": 1, "medium": 2, "high": 3, "extreme": 4}
WINDOW_RANK = {"small": 1, "medium": 2, "large": 3, "massive": 4}
SPEED_RANK = {"fast": 3, "medium": 2, "slow-ok": 1}
TIER_RANK = {"economy": 1, "standard": 2, "premium": 3}
# Reverse maps for naming (rank → label)
TIER_FROM_RANK = {1: "economy", 2: "standard", 3: "premium"}

@dataclass
class ModelProfile:
    """Profil de capacités d'un modèle LLM."""
    id: str
    reasoning: str        # low | medium | high | extreme
    context_window: str   # small | medium | large | massive
    speed: str            # fast | medium | slow-ok
    tier: str             # economy | standard | premium
    window_tokens: int = 0

MODEL_PROFILES: dict[str, ModelProfile] = {
    # Anthropic
    "claude-opus-4":     ModelProfile("claude-opus-4",     "extreme", "large",   "slow-ok", "premium",  200_000),
    "claude-sonnet-4":   ModelProfile("claude-sonnet-4",   "high",    "large",   "fast",    "standard", 200_000),
    "claude-haiku":      ModelProfile("claude-haiku",      "medium",  "large",   "fast",    "economy",  200_000),
    "claude-3-7-sonnet": ModelProfile("claude-3-7-sonnet", "high",    "large",   "fast",    "standard", 200_000),
    "claude-3-5-sonnet": ModelProfile("claude-3-5-sonnet", "high",    "large",   "fast",    "standard", 200_000),
    # OpenAI
    "o3":                ModelProfile("o3",                "extreme", "large",   "slow-ok", "premium",  200_000),
    "o1":                ModelProfile("o1",                "extreme", "large",   "slow-ok", "premium",  200_000),
    "gpt-4o":            ModelProfile("gpt-4o",            "high",    "medium",  "fast",    "standard", 128_000),
    "gpt-4o-mini":       ModelProfile("gpt-4o-mini",       "medium",  "medium",  "fast",    "economy",  128_000),
    "gpt-4-turbo":       ModelProfile("gpt-4-turbo",       "high",    "medium",  "medium",  "standard", 128_000),
    "codex":             ModelProfile("codex",             "high",    "large",   "medium",  "standard", 192_000),
    # Google
    "gemini-1.5-pro":    ModelProfile("gemini-1.5-pro",    "high",    "massive", "medium",  "standard", 1_000_000),
    "gemini-2.0-flash":  ModelProfile("gemini-2.0-flash",  "medium",  "massive", "fast",    "economy",  1_000_000),
    # Local
    "codestral":         ModelProfile("codestral",         "medium",  "small",   "fast",    "economy",  32_000),
    "llama3":            ModelProfile("llama3",            "low",     "small",   "fast",    "economy",   8_000),
    "mistral":           ModelProfile("mistral",           "medium",  "small",   "fast",    "economy",  32_000),
    "qwen2.5":           ModelProfile("qwen2.5",           "medium",  "small",   "fast",    "economy",  32_000),
    "copilot":           ModelProfile("copilot",           "high",    "large",   "fast",    "standard", 200_000),
}

# Modèles NON recommandés pour agents BMAD (protocole trop complexe pour economy tier)
# Ces modèles restent dans le catalogue pour --list-models mais sont pénalisés dans --recommend-models
ECONOMY_PENALTY_MODELS = {"claude-haiku", "gpt-4o-mini", "gemini-2.0-flash", "llama3", "codestral", "mistral", "qwen2.5"}

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


# ── Optimize ──────────────────────────────────────────────────────────────────

# Seuils de détection
OPTIMIZE_COMMENT_RATIO = 0.30  # Si > 30% du fichier est commentaires → flag
OPTIMIZE_MIN_TOKENS = 500      # Ignorer les petits fichiers

@dataclass
class OptimizeHint:
    """Une suggestion d'optimisation pour un fichier."""
    path: Path
    category: str        # "comments" | "verbose-yaml" | "extractable" | "duplicate"
    description: str
    current_tokens: int
    estimated_savings: int

    @property
    def pct_savings(self) -> float:
        return (self.estimated_savings / self.current_tokens * 100) if self.current_tokens else 0


def _count_comment_lines(content: str, ext: str) -> tuple[int, int]:
    """Retourne (lignes_commentaires, lignes_totales)."""
    lines = content.splitlines()
    total = len(lines)
    comments = 0
    in_block = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if ext in (".yaml", ".yml"):
            if stripped.startswith("#"):
                comments += 1
        elif ext == ".md":
            # Blocs de code ``` comptés comme contenu
            if stripped.startswith("```"):
                in_block = not in_block
            # En-dehors des blocs, les blockquotes longs sont verbeux
        elif ext == ".py":
            if stripped.startswith("#"):
                comments += 1
            elif stripped.startswith('"""') or stripped.startswith("'''"):
                in_block = not in_block
            elif in_block:
                comments += 1
    return comments, total


def _find_extractable_sections(content: str) -> list[tuple[str, int]]:
    """Détecte les sections Markdown extractibles (tables, exemples longs)."""
    sections: list[tuple[str, int]] = []
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        # Détection de tables (> 10 lignes)
        if "|" in line and "---" in line:
            table_start = max(0, i - 1)
            table_lines = 0
            while i < len(lines) and "|" in lines[i]:
                table_lines += 1
                i += 1
            if table_lines > 10:
                table_text = "\n".join(lines[table_start:i])
                sections.append((f"Table ({table_lines} lignes)", estimate_tokens(table_text)))
            continue
        # Détection de blocs de code (> 15 lignes)
        if line.strip().startswith("```"):
            block_start = i
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                i += 1
            block_lines = i - block_start
            if block_lines > 15:
                block_text = "\n".join(lines[block_start:i + 1])
                sections.append((f"Bloc de code ({block_lines} lignes)", estimate_tokens(block_text)))
        i += 1
    return sections


def analyze_file_for_optimize(path: Path, role: str) -> list[OptimizeHint]:
    """Analyse un fichier et retourne les suggestions d'optimisation."""
    hints: list[OptimizeHint] = []
    content = read_file_safe(path)
    if not content:
        return hints

    tokens = estimate_tokens(content)
    if tokens < OPTIMIZE_MIN_TOKENS:
        return hints

    ext = path.suffix.lower()

    # 1. Ratio de commentaires élevé (YAML, Python)
    if ext in (".yaml", ".yml", ".py"):
        comment_lines, total_lines = _count_comment_lines(content, ext)
        if total_lines > 0:
            ratio = comment_lines / total_lines
            if ratio > OPTIMIZE_COMMENT_RATIO:
                savings = int(tokens * ratio * 0.7)  # On peut supprimer ~70% des commentaires
                hints.append(OptimizeHint(
                    path=path,
                    category="comments",
                    description=f"{comment_lines}/{total_lines} lignes de commentaires ({ratio:.0%}) "
                                f"— compresser en one-liners ou renvoyer vers docs/",
                    current_tokens=tokens,
                    estimated_savings=savings,
                ))

    # 2. Sections extractibles (tables, blocs de code longs) dans .md
    if ext == ".md":
        extractable = _find_extractable_sections(content)
        for name, section_tokens in extractable:
            if section_tokens > 200:
                hints.append(OptimizeHint(
                    path=path,
                    category="extractable",
                    description=f"{name} extractible vers un fichier on-demand "
                                f"(~{section_tokens} tokens récupérables)",
                    current_tokens=tokens,
                    estimated_savings=int(section_tokens * 0.85),
                ))

    # 3. Fichiers partagés très lourds (base-protocol, project)
    if role in ("base-protocol", "project") and tokens > 2000:
        hints.append(OptimizeHint(
            path=path,
            category="shared-heavy",
            description=f"Fichier partagé ({role}) chargé par TOUS les agents — "
                        f"chaque token économisé ici est multiplié × N agents",
            current_tokens=tokens,
            estimated_savings=0,  # informatif
        ))

    return hints


def do_optimize(
    project_root: Path,
    model: str,
    agent_id: Optional[str] = None,
) -> None:
    """Analyse les fichiers framework et agents pour trouver des optimisations de tokens."""
    window = MODEL_WINDOWS.get(model, MODEL_WINDOWS[DEFAULT_MODEL])

    # Collecter tous les fichiers chargés
    agents = find_agents(project_root)
    if agent_id:
        agents = [a for a in agents if agent_id.lower() in a.stem.lower()]
        if not agents:
            print(f"❌ Agent '{agent_id}' introuvable.", file=sys.stderr)
            sys.exit(1)

    # Collecter les fichiers uniques toutes charges confondues
    seen_files: dict[str, tuple[Path, str, int]] = {}  # path_str → (path, role, tokens)
    agent_count = len(agents)

    for ap in agents:
        loads = resolve_agent_loads(ap, project_root)
        for fl in loads:
            fl.compute()
            key = str(fl.path)
            if fl.loaded and fl.tokens > 0 and key not in seen_files:
                seen_files[key] = (fl.path, fl.role, fl.tokens)

    # Analyser chaque fichier pour des optimisations
    all_hints: list[OptimizeHint] = []
    for path, role, tokens in seen_files.values():
        all_hints.extend(analyze_file_for_optimize(path, role))

    # Aussi analyser copilot-instructions.md (envoyé à CHAQUE requête, pas analysé par resolve_agent_loads)
    copilot_instr = project_root / ".github" / "copilot-instructions.md"
    if copilot_instr.exists():
        content = read_file_safe(copilot_instr)
        tokens_ci = estimate_tokens(content)
        if tokens_ci > OPTIMIZE_MIN_TOKENS:
            all_hints.append(OptimizeHint(
                path=copilot_instr,
                category="always-loaded",
                description=f"Envoyé avec CHAQUE requête Copilot ({tokens_ci} tokens) — "
                            f"chaque token économisé ici a le plus grand impact",
                current_tokens=tokens_ci,
                estimated_savings=0,
            ))

    # Affichage
    print()
    print(f"  BMAD Context Optimizer  ·  modèle: {model}  ·  fenêtre: {fmt_tokens(window)} tokens")
    print(f"  {agent_count} agents analysés  ·  {len(seen_files)} fichiers uniques")
    print()

    if not all_hints:
        print("  ✅ Aucune optimisation évidente détectée — le framework est déjà compact.")
        return

    # Trier par savings estimé décroissant (informatifs en dernier)
    all_hints.sort(key=lambda h: h.estimated_savings, reverse=True)

    total_savings = 0
    print(f"  {'Fichier':<40} {'Catégorie':<14} {'Actuel':>8} {'Gain':>8} {'%':>6}")
    print(f"  {'─' * 80}")

    for hint in all_hints:
        short_name = hint.path.name
        gain_str = f"-{fmt_tokens(hint.estimated_savings)}" if hint.estimated_savings > 0 else "info"
        pct_str = f"-{hint.pct_savings:.0f}%" if hint.estimated_savings > 0 else ""
        print(f"  {short_name:<40} {hint.category:<14} {fmt_tokens(hint.current_tokens):>8} {gain_str:>8} {pct_str:>6}")
        print(f"    💡 {hint.description}")
        total_savings += hint.estimated_savings

    print()
    if total_savings > 0:
        per_agent = total_savings
        total_fleet = total_savings * agent_count
        print(f"  ─────────────────────────────────────────────")
        print(f"  Gain estimé par agent  : ~{fmt_tokens(per_agent)} tokens")
        print(f"  Gain total (× {agent_count} agents) : ~{fmt_tokens(total_fleet)} tokens")
        print(f"  Équivalent fenêtre     : {per_agent / window * 100:.1f}% du budget {model}")
        print()
    print("  💡 Pour appliquer : optimiser manuellement les fichiers listés ci-dessus.")
    print("      Stratégies : compresser les commentaires, extraire les sections on-demand,")
    print("      renvoyer vers docs/ pour les détails verbeux.")
    print()


# ── Model Recommendation ─────────────────────────────────────────────────────

@dataclass
class ModelAffinity:
    """Affinité de modèle déclarée par un agent."""
    reasoning: str = "medium"
    context_window: str = "medium"
    speed: str = "medium"
    cost: str = "medium"


def parse_model_affinity(agent_path: Path) -> Optional[ModelAffinity]:
    """Parse le frontmatter YAML d'un agent et extrait model_affinity."""
    content = read_file_safe(agent_path)
    if not content:
        return None
    # Chercher le bloc frontmatter YAML entre ---
    lines = content.splitlines()
    in_fm = False
    fm_lines: list[str] = []
    for line in lines:
        if line.strip() == "---":
            if in_fm:
                break  # fin du frontmatter
            in_fm = True
            continue
        if in_fm:
            fm_lines.append(line)
    if not fm_lines:
        return None
    # Parser simple (pas de dépendance PyYAML)
    affinity: dict[str, str] = {}
    in_affinity = False
    for line in fm_lines:
        stripped = line.strip()
        if stripped.startswith("model_affinity:"):
            in_affinity = True
            continue
        if in_affinity:
            if not line.startswith("  ") and not line.startswith("\t"):
                break  # sortie du bloc indenté
            if ":" in stripped:
                key, val = stripped.split(":", 1)
                affinity[key.strip()] = val.strip().strip('"').strip("'")
    if not affinity:
        return None
    return ModelAffinity(
        reasoning=affinity.get("reasoning", "medium"),
        context_window=affinity.get("context_window", "medium"),
        speed=affinity.get("speed", "medium"),
        cost=affinity.get("cost", "medium"),
    )


def _cost_to_tier(cost: str) -> str:
    """Convertit le champ cost de model_affinity en tier."""
    return {"cheap": "economy", "medium": "standard", "any": "premium"}.get(cost, "standard")


def score_model_for_agent(
    profile: ModelProfile, affinity: ModelAffinity, agent_tokens: int
) -> float:
    """Score un modèle par rapport aux besoins d'un agent (0-100)."""
    score = 0.0

    # Reasoning match (40 points max)
    needed = REASONING_RANK.get(affinity.reasoning, 2)
    has = REASONING_RANK.get(profile.reasoning, 2)
    if has >= needed:
        score += 40
    elif has == needed - 1:
        score += 20  # acceptable, un cran en dessous
    # Surqualifié = fonctionnel mais gaspillage → léger malus plus tard via cost

    # Context window fit (25 points max)
    needed_w = WINDOW_RANK.get(affinity.context_window, 2)
    has_w = WINDOW_RANK.get(profile.context_window, 2)
    if has_w >= needed_w:
        score += 25
        # Bonus si l'agent tient réellement dans la fenêtre
        if profile.window_tokens > 0 and agent_tokens > 0:
            usage_pct = agent_tokens / profile.window_tokens * 100
            if usage_pct < THRESHOLD_WARN:
                score += 5  # confortable
    else:
        # Fenêtre trop petite
        if profile.window_tokens > 0 and agent_tokens > 0:
            if agent_tokens / profile.window_tokens * 100 > THRESHOLD_CRIT:
                score -= 20  # inutilisable

    # Speed match (20 points max)
    needed_s = SPEED_RANK.get(affinity.speed, 2)
    has_s = SPEED_RANK.get(profile.speed, 2)
    if has_s >= needed_s:
        score += 20
    elif has_s == needed_s - 1:
        score += 10

    # Cost efficiency (15 points max) — plus le tier est bas et suffisant, mieux c'est
    needed_tier = TIER_RANK.get(_cost_to_tier(affinity.cost), 2)
    has_tier = TIER_RANK.get(profile.tier, 2)
    if has_tier <= needed_tier:
        score += 15  # dans le budget
    elif has_tier == needed_tier + 1:
        score += 5   # un cran au-dessus = acceptable
    # Si le modèle est surqualifié en reasoning ET coûteux → malus
    reasoning_surplus = REASONING_RANK.get(profile.reasoning, 2) - REASONING_RANK.get(affinity.reasoning, 2)
    if reasoning_surplus >= 2 and has_tier >= 3:
        score -= 10  # gaspillage flagrant

    # Pénalité modèles economy — le protocole agent-base.md BMAD est trop complexe
    # pour les modèles economy (Haiku, GPT-4o-mini, etc.) → forte pénalité
    if profile.id in ECONOMY_PENALTY_MODELS:
        score -= 30  # déconseillé pour tout agent BMAD

    return max(0, min(100, score))


def load_available_models(project_root: Path) -> Optional[list[dict[str, str]]]:
    """Charge la section models.available depuis project-context.yaml."""
    ctx_path = project_root / "project-context.yaml"
    if not ctx_path.exists():
        return None
    content = read_file_safe(ctx_path)
    # Parser léger YAML pour la section models.available
    models: list[dict[str, str]] = []
    in_models = False
    in_available = False
    current: dict[str, str] = {}
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("models:"):
            in_models = True
            continue
        if in_models and stripped.startswith("available:"):
            in_available = True
            continue
        if in_available:
            if not line.startswith(" ") and not line.startswith("\t") and stripped:
                break  # sortie du bloc
            if stripped.startswith("- id:"):
                if current:
                    models.append(current)
                current = {"id": stripped.split(":", 1)[1].strip().strip('"')}
            elif ":" in stripped and current:
                key, val = stripped.split(":", 1)
                current[key.strip()] = val.strip().strip('"').strip("#").strip()
        if in_models and not in_available and stripped.startswith("routing_strategy:"):
            pass  # on pourrait l'utiliser plus tard
    if current:
        models.append(current)
    return models if models else None


def do_recommend_models(
    project_root: Path,
    agent_id: Optional[str] = None,
) -> None:
    """Recommande le meilleur modèle LLM pour chaque agent basé sur model_affinity."""
    agents = find_agents(project_root)
    if agent_id:
        agents = [a for a in agents if agent_id.lower() in a.stem.lower()]
        if not agents:
            print(f"❌ Agent '{agent_id}' introuvable.", file=sys.stderr)
            sys.exit(1)

    # Charger la config des modèles disponibles (optionnel)
    user_models = load_available_models(project_root)
    if user_models:
        available_ids = {m["id"] for m in user_models}
        # Filtrer MODEL_PROFILES aux modèles disponibles
        profiles_to_use = {k: v for k, v in MODEL_PROFILES.items() if k in available_ids}
        if not profiles_to_use:
            profiles_to_use = MODEL_PROFILES  # fallback
    else:
        profiles_to_use = MODEL_PROFILES

    # Collecter les recommandations
    @dataclass
    class Recommendation:
        agent_id: str
        affinity: ModelAffinity
        best_model: str
        best_score: float
        alt_model: str
        alt_score: float
        agent_tokens: int
        reason: str

    recs: list[Recommendation] = []

    for ap in agents:
        affinity = parse_model_affinity(ap)
        if not affinity:
            continue

        # Calculer les tokens de l'agent avec le modèle par défaut
        budget = compute_budget(ap, project_root, DEFAULT_MODEL)
        agent_tokens = budget.total_tokens

        # Scorer chaque modèle
        scores: list[tuple[str, float]] = []
        for mid, profile in profiles_to_use.items():
            s = score_model_for_agent(profile, affinity, agent_tokens)
            scores.append((mid, s))

        scores.sort(key=lambda x: x[1], reverse=True)

        if len(scores) >= 2:
            best_id, best_score = scores[0]
            alt_id, alt_score = scores[1]
        elif scores:
            best_id, best_score = scores[0]
            alt_id, alt_score = best_id, best_score
        else:
            continue

        # Construire la raison
        parts = []
        if affinity.reasoning in ("extreme", "high"):
            parts.append(f"reasoning={affinity.reasoning}")
        if affinity.context_window in ("large", "massive"):
            parts.append(f"window={affinity.context_window}")
        if affinity.speed == "fast":
            parts.append("speed=fast")
        if affinity.cost == "cheap":
            parts.append("cost=cheap")
        reason = ", ".join(parts) if parts else "balanced"

        recs.append(Recommendation(
            agent_id=ap.stem,
            affinity=affinity,
            best_model=best_id,
            best_score=best_score,
            alt_model=alt_id,
            alt_score=alt_score,
            agent_tokens=agent_tokens,
            reason=reason,
        ))

    # Affichage
    print()
    source = "project-context.yaml" if user_models else "tous les modèles connus"
    print(f"  BMAD Model Recommender  ·  source: {source}")
    print(f"  {len(recs)} agents avec model_affinity / {len(agents)} agents total")
    print()

    if not recs:
        print("  ℹ️  Aucun agent avec model_affinity trouvé.")
        print("      Ajoutez model_affinity dans le frontmatter YAML de vos agents.")
        print("      Voir docs/creating-agents.md pour le format.")
        return

    print(f"  {'Agent':<28} {'Recommandé':<20} {'Score':>6} {'Alternatif':<20} {'Score':>6} {'Raison'}")
    print(f"  {'─' * 110}")

    # Trier par score décroissant du best
    recs.sort(key=lambda r: r.best_score, reverse=True)

    tier_savings = {"economy": 0, "standard": 0, "premium": 0}
    for rec in recs:
        best_profile = MODEL_PROFILES.get(rec.best_model)
        tier_icon = {"economy": "💚", "standard": "💛", "premium": "❤️ "}.get(
            best_profile.tier if best_profile else "standard", "💛")
        print(f"  {rec.agent_id:<28} {tier_icon} {rec.best_model:<17} {rec.best_score:>5.0f}/100"
              f"   {rec.alt_model:<20} {rec.alt_score:>5.0f}/100  {rec.reason}")
        if best_profile:
            tier_savings[best_profile.tier] = tier_savings.get(best_profile.tier, 0) + 1

    # Résumé
    print()
    print(f"  ─────────────────────────────────────────────")
    total = len(recs)
    for tier_name, icon in [("economy", "💚"), ("standard", "💛"), ("premium", "❤️ ")]:
        count = tier_savings.get(tier_name, 0)
        if count:
            pct = count / total * 100
            print(f"    {icon} {tier_name:<10} : {count} agents ({pct:.0f}%)")
    print()
    economy_pct = tier_savings.get("economy", 0) / total * 100 if total else 0
    if economy_pct >= 30:
        print(f"  💡 {economy_pct:.0f}% des agents peuvent tourner sur des modèles economy")
        print(f"      → réduction significative des rate limits et coûts API")
    print()

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
  python3 context-guard.py --optimize
  python3 context-guard.py --recommend-models
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
    parser.add_argument("--optimize", action="store_true",
                        help="Analyser les fichiers framework pour des optimisations de tokens")
    parser.add_argument("--recommend-models", action="store_true",
                        help="Recommander le meilleur modèle LLM pour chaque agent")

    args = parser.parse_args()

    if args.list_models:
        print("\nModèles supportés :\n")
        for m, w in sorted(MODEL_WINDOWS.items(), key=lambda x: x[1], reverse=True):
            print(f"  {m:<25} {w:>10,} tokens ({fmt_tokens(w)})")
        return

    project_root = Path(args.project_root).resolve()

    # Mode optimize
    if args.optimize:
        do_optimize(project_root, args.model, agent_id=args.agent)
        return

    # Mode recommend-models
    if args.recommend_models:
        do_recommend_models(project_root, agent_id=args.agent)
        return

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
