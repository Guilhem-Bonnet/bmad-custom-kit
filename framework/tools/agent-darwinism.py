#!/usr/bin/env python3
"""
agent-darwinism.py — Sélection naturelle des agents BMAD.
==========================================================

Évalue la fitness des agents sur des générations successives et propose des
actions évolutives : promotion, amélioration, hybridation, dépréciation.

Dimensions de fitness (pondérées, total 100) :
  - reliability  (0.25) : AC pass rate, faible taux de failures
  - productivity (0.20) : commits, décisions
  - learning     (0.20) : learnings capitalisés, capitalisation active
  - adaptability (0.15) : diversité des stories touchées
  - resilience   (0.10) : récupération après failures, absence de patterns récurrents
  - influence    (0.10) : checkpoints créés, contributions aux décisions collectives

Niveaux d'évolution :
  - ELITE    (≥75) 🟢 — patterns à répliquer
  - VIABLE   (40-74) 🟡 — maintien, amélioration suggérée
  - FRAGILE  (20-39) 🟠 — amélioration requise
  - OBSOLETE (<20) 🔴 — deprecation recommandée

Usage :
  python3 agent-darwinism.py --project-root . evaluate
  python3 agent-darwinism.py --project-root . evaluate --since 2026-01-01
  python3 agent-darwinism.py --project-root . leaderboard
  python3 agent-darwinism.py --project-root . evolve
  python3 agent-darwinism.py --project-root . evolve --dry-run
  python3 agent-darwinism.py --project-root . history
  python3 agent-darwinism.py --project-root . lineage --agent dev

Stdlib only — aucune dépendance externe.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ── Constantes ────────────────────────────────────────────────────────────────

DARWINISM_VERSION = "1.0.0"

FITNESS_WEIGHTS = {
    "reliability":  0.25,
    "productivity": 0.20,
    "learning":     0.20,
    "adaptability": 0.15,
    "resilience":   0.10,
    "influence":    0.10,
}

LEVEL_ELITE      = "ELITE"
LEVEL_VIABLE     = "VIABLE"
LEVEL_FRAGILE    = "FRAGILE"
LEVEL_OBSOLETE   = "OBSOLETE"

LEVEL_THRESHOLDS = {
    LEVEL_ELITE:    75,
    LEVEL_VIABLE:   40,
    LEVEL_FRAGILE:  20,
    LEVEL_OBSOLETE: 0,
}

LEVEL_ICONS = {
    LEVEL_ELITE:    "🟢",
    LEVEL_VIABLE:   "🟡",
    LEVEL_FRAGILE:  "🟠",
    LEVEL_OBSOLETE: "🔴",
}

ACTION_PROMOTE    = "PROMOTE"
ACTION_IMPROVE    = "IMPROVE"
ACTION_HYBRIDIZE  = "HYBRIDIZE"
ACTION_DEPRECATE  = "DEPRECATE"
ACTION_OBSERVE    = "OBSERVE"

ACTION_ICONS = {
    ACTION_PROMOTE:   "⬆️",
    ACTION_IMPROVE:   "🔧",
    ACTION_HYBRIDIZE: "🧬",
    ACTION_DEPRECATE: "⬇️",
    ACTION_OBSERVE:   "👁️",
}


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class RawAgentStats:
    """Statistiques brutes d'un agent depuis BMAD_TRACE."""
    agent_id: str
    stories_touched: int = 0
    decisions_count: int = 0
    failures_count: int = 0
    failure_patterns: list[str] = field(default_factory=list)
    ac_pass_count: int = 0
    ac_fail_count: int = 0
    checkpoints_created: int = 0
    commits_attributed: int = 0
    learnings_count: int = 0
    last_activity: str = ""

    @property
    def ac_total(self) -> int:
        return self.ac_pass_count + self.ac_fail_count

    @property
    def ac_pass_rate(self) -> float:
        return (self.ac_pass_count / self.ac_total * 100) if self.ac_total > 0 else 0.0


@dataclass
class FitnessDimensions:
    """Scores par dimension de fitness (0-100 chacun)."""
    reliability: float = 0.0
    productivity: float = 0.0
    learning: float = 0.0
    adaptability: float = 0.0
    resilience: float = 0.0
    influence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "reliability": round(self.reliability, 1),
            "productivity": round(self.productivity, 1),
            "learning": round(self.learning, 1),
            "adaptability": round(self.adaptability, 1),
            "resilience": round(self.resilience, 1),
            "influence": round(self.influence, 1),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "FitnessDimensions":
        return cls(**{k: d.get(k, 0.0) for k in
                      ("reliability", "productivity", "learning",
                       "adaptability", "resilience", "influence")})


@dataclass
class FitnessScore:
    """Score de fitness composite d'un agent."""
    agent_id: str
    dimensions: FitnessDimensions = field(default_factory=FitnessDimensions)
    composite: float = 0.0
    level: str = LEVEL_OBSOLETE
    generation: int = 0
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "dimensions": self.dimensions.to_dict(),
            "composite": round(self.composite, 1),
            "level": self.level,
            "generation": self.generation,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "FitnessScore":
        return cls(
            agent_id=d.get("agent_id", ""),
            dimensions=FitnessDimensions.from_dict(d.get("dimensions", {})),
            composite=d.get("composite", 0.0),
            level=d.get("level", LEVEL_OBSOLETE),
            generation=d.get("generation", 0),
            timestamp=d.get("timestamp", ""),
        )


@dataclass
class EvolutionAction:
    """Action évolutive recommandée pour un agent."""
    agent_id: str
    action: str
    reason: str
    detail: str = ""
    source_agents: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "action": self.action,
            "reason": self.reason,
            "detail": self.detail,
            "source_agents": self.source_agents,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EvolutionAction":
        return cls(
            agent_id=d.get("agent_id", ""),
            action=d.get("action", ""),
            reason=d.get("reason", ""),
            detail=d.get("detail", ""),
            source_agents=d.get("source_agents", []),
        )


@dataclass
class GenerationRecord:
    """Enregistrement d'une génération d'évaluation."""
    generation: int
    timestamp: str
    scores: list[dict] = field(default_factory=list)
    actions: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "generation": self.generation,
            "timestamp": self.timestamp,
            "scores": self.scores,
            "actions": self.actions,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GenerationRecord":
        return cls(
            generation=d.get("generation", 0),
            timestamp=d.get("timestamp", ""),
            scores=d.get("scores", []),
            actions=d.get("actions", []),
            summary=d.get("summary", {}),
        )


# ── Parsing BMAD_TRACE (allégé — réutilise les patterns de bench) ─────────

HEADER_RE = re.compile(
    r"^##\s+(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2})?)\s*\|\s*([^\|]+)\s*\|\s*(.+)$"
)

TYPE_PATTERNS = {
    "GIT-COMMIT":  re.compile(r"\[GIT-COMMIT\]"),
    "DECISION":    re.compile(r"\[DECISION\]"),
    "REMEMBER":    re.compile(r"\[REMEMBER:([^\]]+)\]"),
    "FAILURE":     re.compile(r"\[FAILURE\]|\[ÉCHEC\]|\bFAIL\b"),
    "AC-PASS":     re.compile(r"\[AC-PASS\]|\bAC.*PASS\b|\bpasse\b.*\bAC\b"),
    "AC-FAIL":     re.compile(r"\[AC-FAIL\]|\bAC.*FAIL\b|\béchec\b.*\bAC\b"),
    "CHECKPOINT":  re.compile(r"\[CHECKPOINT\]|checkpoint_id"),
}

FAILURE_CATEGORIZER = {
    "test-failure": re.compile(r"test.*fail|pytest.*error|go test.*FAIL|jest.*fail", re.IGNORECASE),
    "lint-error":   re.compile(r"lint|ruff|shellcheck|yamllint|golangci", re.IGNORECASE),
    "recurring":    re.compile(r"again|encore|récurrent|même erreur", re.IGNORECASE),
}


def parse_trace_stats(trace_path: Path,
                      since: Optional[str] = None) -> dict[str, RawAgentStats]:
    """Parse BMAD_TRACE.md et retourne des stats par agent."""
    agents: dict[str, RawAgentStats] = {}

    if not trace_path.exists():
        return agents

    since_dt = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
        except ValueError:
            pass

    current_header: dict = {}
    content_lines: list[str] = []

    def flush():
        if not current_header:
            return
        content = "\n".join(content_lines).strip()
        if not content:
            return

        ts = current_header.get("ts", "")
        ag = current_header.get("agent", "system").strip().lower()
        story = current_header.get("story", "").strip()

        if since_dt and ts:
            try:
                entry_dt = datetime.fromisoformat(ts.replace(" ", "T"))
                if entry_dt < since_dt:
                    return
            except ValueError:
                pass

        if ag not in agents:
            agents[ag] = RawAgentStats(agent_id=ag)
        m = agents[ag]

        if story:
            m.stories_touched += 1  # Count mentions, deduplicate later
        m.last_activity = ts

        # Detect entry type
        entry_type = "GENERIC"
        for etype, pat in TYPE_PATTERNS.items():
            if pat.search(content):
                entry_type = etype
                break

        if entry_type == "GIT-COMMIT":
            m.commits_attributed += 1
        elif entry_type == "DECISION":
            m.decisions_count += 1
        elif entry_type == "FAILURE":
            m.failures_count += 1
            for cat, pat in FAILURE_CATEGORIZER.items():
                if pat.search(content):
                    m.failure_patterns.append(cat)
                    break
        elif entry_type == "AC-PASS":
            m.ac_pass_count += 1
        elif entry_type == "AC-FAIL":
            m.ac_fail_count += 1
        elif entry_type == "CHECKPOINT":
            m.checkpoints_created += 1
        elif entry_type == "REMEMBER":
            m.learnings_count += 1

    try:
        with trace_path.open(encoding="utf-8", errors="replace") as f:
            for raw_line in f:
                line = raw_line.rstrip()
                m = HEADER_RE.match(line)
                if m:
                    flush()
                    current_header = {
                        "ts": m.group(1), "agent": m.group(2),
                        "story": m.group(3)}
                    content_lines = []
                elif current_header:
                    content_lines.append(line)
        flush()
    except OSError:
        pass

    return agents


def count_agent_learnings(project_root: Path) -> dict[str, int]:
    """Compte les learnings par agent dans agent-learnings/."""
    learnings_dir = project_root / "_bmad" / "_memory" / "agent-learnings"
    counts: dict[str, int] = {}
    if not learnings_dir.exists():
        return counts
    for f in learnings_dir.glob("*.md"):
        agent = f.stem
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
            count = sum(1 for l in lines
                        if l.strip() and (l.startswith("- ") or l.startswith("* ")))
            counts[agent] = count
        except OSError:
            pass
    return counts


# ── Fitness Computation ───────────────────────────────────────────────────────

def compute_dimension_reliability(stats: RawAgentStats) -> float:
    """Reliability : AC pass rate pondéré, pénalité pour failures."""
    score = 0.0
    if stats.ac_total > 0:
        score += stats.ac_pass_rate * 0.6  # 0-60 points from AC pass rate
    else:
        score += 30.0  # Default baseline if no AC data

    # Failure penalty: -5 per failure, max -40
    failure_penalty = min(stats.failures_count * 5, 40)
    score = max(score - failure_penalty, 0.0)

    return min(score / 0.6 if stats.ac_total > 0 else score * 2, 100.0)


def compute_dimension_productivity(stats: RawAgentStats) -> float:
    """Productivity : commits et décisions pondérés."""
    score = 0.0
    score += min(stats.commits_attributed * 10, 50)
    score += min(stats.decisions_count * 8, 50)
    return min(score, 100.0)


def compute_dimension_learning(stats: RawAgentStats,
                                external_learnings: int = 0) -> float:
    """Learning : capitalisation des connaissances."""
    total = stats.learnings_count + external_learnings
    return min(total * 10, 100.0)


def compute_dimension_adaptability(stats: RawAgentStats) -> float:
    """Adaptability : diversité des stories touchées."""
    return min(stats.stories_touched * 15, 100.0)


def compute_dimension_resilience(stats: RawAgentStats) -> float:
    """Resilience : faible récurrence de failures, récupération."""
    if stats.failures_count == 0:
        return 80.0  # Good baseline, no failures

    recurring = stats.failure_patterns.count("recurring")
    recurring_ratio = recurring / stats.failures_count if stats.failures_count > 0 else 0

    # Start at 60, penalize for recurring patterns
    score = 60.0 - (recurring_ratio * 40.0)

    # Extra penalty for many failures
    if stats.failures_count > 5:
        score -= min((stats.failures_count - 5) * 5, 30)

    return max(min(score, 100.0), 0.0)


def compute_dimension_influence(stats: RawAgentStats) -> float:
    """Influence : checkpoints, décisions = contribution visible."""
    score = 0.0
    score += min(stats.checkpoints_created * 15, 50)
    score += min(stats.decisions_count * 10, 50)
    return min(score, 100.0)


def compute_fitness(stats: RawAgentStats,
                    external_learnings: int = 0,
                    generation: int = 0) -> FitnessScore:
    """Calcule le score de fitness composite d'un agent."""
    dims = FitnessDimensions(
        reliability=compute_dimension_reliability(stats),
        productivity=compute_dimension_productivity(stats),
        learning=compute_dimension_learning(stats, external_learnings),
        adaptability=compute_dimension_adaptability(stats),
        resilience=compute_dimension_resilience(stats),
        influence=compute_dimension_influence(stats),
    )

    composite = (
        dims.reliability  * FITNESS_WEIGHTS["reliability"] +
        dims.productivity * FITNESS_WEIGHTS["productivity"] +
        dims.learning     * FITNESS_WEIGHTS["learning"] +
        dims.adaptability * FITNESS_WEIGHTS["adaptability"] +
        dims.resilience   * FITNESS_WEIGHTS["resilience"] +
        dims.influence    * FITNESS_WEIGHTS["influence"]
    )

    # Determine level
    level = LEVEL_OBSOLETE
    for lv in (LEVEL_ELITE, LEVEL_VIABLE, LEVEL_FRAGILE, LEVEL_OBSOLETE):
        if composite >= LEVEL_THRESHOLDS[lv]:
            level = lv
            break

    return FitnessScore(
        agent_id=stats.agent_id,
        dimensions=dims,
        composite=round(composite, 1),
        level=level,
        generation=generation,
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
    )


# ── Evolution Actions ─────────────────────────────────────────────────────────

def propose_actions(scores: list[FitnessScore],
                    previous_scores: Optional[list[FitnessScore]] = None
                    ) -> list[EvolutionAction]:
    """Propose des actions évolutives basées sur les scores de fitness."""
    actions: list[EvolutionAction] = []

    # Build previous score map for trend detection
    prev_map: dict[str, float] = {}
    if previous_scores:
        for ps in previous_scores:
            prev_map[ps.agent_id] = ps.composite

    # Identify elite agents for potential hybridization sources
    elite_agents = [s for s in scores if s.level == LEVEL_ELITE]
    elite_ids = [s.agent_id for s in elite_agents]

    for score in scores:
        prev_composite = prev_map.get(score.agent_id)
        trend = ""
        if prev_composite is not None:
            delta = score.composite - prev_composite
            if delta > 10:
                trend = f" (↑ +{delta:.0f} vs génération précédente)"
            elif delta < -10:
                trend = f" (↓ {delta:.0f} vs génération précédente)"

        if score.level == LEVEL_ELITE:
            actions.append(EvolutionAction(
                agent_id=score.agent_id,
                action=ACTION_PROMOTE,
                reason=f"Score fitness {score.composite:.0f}% — "
                       f"agent exemplaire{trend}",
                detail="Patterns de cet agent à répliquer dans "
                       "les agents fragiles.",
            ))

        elif score.level == LEVEL_VIABLE:
            # Check weakest dimension for targeted improvement
            dims = score.dimensions.to_dict()
            weakest = min(dims, key=lambda k: dims[k])
            actions.append(EvolutionAction(
                agent_id=score.agent_id,
                action=ACTION_OBSERVE,
                reason=f"Score {score.composite:.0f}% viable, "
                       f"dimension faible : {weakest} ({dims[weakest]:.0f}){trend}",
                detail=f"Améliorer la dimension '{weakest}' pour "
                       f"passer au niveau ELITE.",
            ))

        elif score.level == LEVEL_FRAGILE:
            dims = score.dimensions.to_dict()
            weakest = min(dims, key=lambda k: dims[k])

            if elite_agents:
                # Suggest hybridization with elite agent
                best_elite = max(elite_agents,
                                 key=lambda e: e.dimensions.to_dict().get(weakest, 0))
                actions.append(EvolutionAction(
                    agent_id=score.agent_id,
                    action=ACTION_HYBRIDIZE,
                    reason=f"Score {score.composite:.0f}% fragile, "
                           f"dimension critique : {weakest} ({dims[weakest]:.0f}){trend}",
                    detail=f"Hybrider avec {best_elite.agent_id} (expert en {weakest}).",
                    source_agents=[best_elite.agent_id],
                ))
            else:
                actions.append(EvolutionAction(
                    agent_id=score.agent_id,
                    action=ACTION_IMPROVE,
                    reason=f"Score {score.composite:.0f}% fragile, "
                           f"dimension critique : {weakest} ({dims[weakest]:.0f}){trend}",
                    detail="Renforcer les protocoles et rules de cet agent.",
                ))

        elif score.level == LEVEL_OBSOLETE:
            # Check if declining
            if prev_composite is not None and prev_composite >= 20:
                actions.append(EvolutionAction(
                    agent_id=score.agent_id,
                    action=ACTION_DEPRECATE,
                    reason=f"Score {score.composite:.0f}% obsolète — "
                           f"en déclin depuis la dernière génération{trend}",
                    detail="Envisager la fusion avec un agent viable ou la suppression.",
                ))
            else:
                actions.append(EvolutionAction(
                    agent_id=score.agent_id,
                    action=ACTION_DEPRECATE,
                    reason=f"Score {score.composite:.0f}% obsolète — "
                           f"inactif ou inefficace",
                    detail="Agent candidat à la dépréciation. "
                           "Vérifier s'il a une niche pertinente avant retrait.",
                ))

    return actions


# ── Persistence ───────────────────────────────────────────────────────────────

HISTORY_FILE = "darwinism-history.json"


def _history_path(project_root: Path) -> Path:
    return project_root / "_bmad-output" / HISTORY_FILE


def load_history(project_root: Path) -> list[GenerationRecord]:
    """Charge l'historique des générations."""
    path = _history_path(project_root)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [GenerationRecord.from_dict(d) for d in data]
    except (json.JSONDecodeError, OSError):
        return []


def save_history(project_root: Path,
                 history: list[GenerationRecord]) -> None:
    """Sauvegarde l'historique."""
    path = _history_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [g.to_dict() for g in history]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                    encoding="utf-8")


def get_previous_scores(history: list[GenerationRecord]
                        ) -> Optional[list[FitnessScore]]:
    """Retourne les scores de la dernière génération."""
    if not history:
        return None
    last = history[-1]
    return [FitnessScore.from_dict(s) for s in last.scores]


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_evaluate(project_root: Path, trace_path: Path,
                 since: Optional[str] = None,
                 save: bool = True) -> list[FitnessScore]:
    """Évalue la fitness de tous les agents et enregistre la génération."""
    stats = parse_trace_stats(trace_path, since=since)
    ext_learnings = count_agent_learnings(project_root)

    history = load_history(project_root)
    gen_num = (history[-1].generation + 1) if history else 1

    scores = []
    for agent_id, agent_stats in sorted(stats.items()):
        ext = ext_learnings.get(agent_id, 0)
        fitness = compute_fitness(agent_stats, external_learnings=ext,
                                   generation=gen_num)
        scores.append(fitness)

    if save:
        previous = get_previous_scores(history)
        actions = propose_actions(scores, previous)

        # Summary
        level_counts = defaultdict(int)
        for s in scores:
            level_counts[s.level] += 1

        avg_fitness = (sum(s.composite for s in scores) / len(scores)) \
            if scores else 0.0

        record = GenerationRecord(
            generation=gen_num,
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
            scores=[s.to_dict() for s in scores],
            actions=[a.to_dict() for a in actions],
            summary={
                "agents_evaluated": len(scores),
                "avg_fitness": round(avg_fitness, 1),
                "elite": level_counts.get(LEVEL_ELITE, 0),
                "viable": level_counts.get(LEVEL_VIABLE, 0),
                "fragile": level_counts.get(LEVEL_FRAGILE, 0),
                "obsolete": level_counts.get(LEVEL_OBSOLETE, 0),
            },
        )
        history.append(record)
        save_history(project_root, history)

    return scores


def cmd_evolve(project_root: Path, trace_path: Path,
               since: Optional[str] = None,
               dry_run: bool = False) -> list[EvolutionAction]:
    """Évalue et propose des actions évolutives."""
    # First evaluate
    stats = parse_trace_stats(trace_path, since=since)
    ext_learnings = count_agent_learnings(project_root)

    history = load_history(project_root)
    gen_num = (history[-1].generation + 1) if history else 1

    scores = []
    for agent_id, agent_stats in sorted(stats.items()):
        ext = ext_learnings.get(agent_id, 0)
        fitness = compute_fitness(agent_stats, external_learnings=ext,
                                   generation=gen_num)
        scores.append(fitness)

    previous = get_previous_scores(history)
    actions = propose_actions(scores, previous)

    if not dry_run:
        level_counts = defaultdict(int)
        for s in scores:
            level_counts[s.level] += 1
        avg_fitness = (sum(s.composite for s in scores) / len(scores)) \
            if scores else 0.0

        record = GenerationRecord(
            generation=gen_num,
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
            scores=[s.to_dict() for s in scores],
            actions=[a.to_dict() for a in actions],
            summary={
                "agents_evaluated": len(scores),
                "avg_fitness": round(avg_fitness, 1),
                "elite": level_counts.get(LEVEL_ELITE, 0),
                "viable": level_counts.get(LEVEL_VIABLE, 0),
                "fragile": level_counts.get(LEVEL_FRAGILE, 0),
                "obsolete": level_counts.get(LEVEL_OBSOLETE, 0),
            },
        )
        history.append(record)
        save_history(project_root, history)

    return actions


# ── Rendering ─────────────────────────────────────────────────────────────────

def render_leaderboard(scores: list[FitnessScore]) -> str:
    """Affiche le classement des agents."""
    sorted_scores = sorted(scores, key=lambda s: s.composite, reverse=True)
    lines = [
        "# 🏆 Leaderboard Darwiniste",
        "",
        f"| Rang | Agent | Fitness | Niveau | Fiabilité | Productivité | Apprentissage | Adaptabilité | Résilience | Influence |",
        f"|------|-------|---------|--------|-----------|--------------|---------------|--------------|------------|-----------|",
    ]

    for i, s in enumerate(sorted_scores, 1):
        d = s.dimensions
        icon = LEVEL_ICONS.get(s.level, "")
        lines.append(
            f"| {i} | {s.agent_id} | {s.composite:.0f} | {icon} {s.level} | "
            f"{d.reliability:.0f} | {d.productivity:.0f} | {d.learning:.0f} | "
            f"{d.adaptability:.0f} | {d.resilience:.0f} | {d.influence:.0f} |"
        )

    if scores:
        avg = sum(s.composite for s in scores) / len(scores)
        lines.extend(["", f"**Fitness moyenne** : {avg:.1f}/100"])

    return "\n".join(lines)


def render_evaluate(scores: list[FitnessScore],
                    generation: int) -> str:
    """Affiche le rapport d'évaluation."""
    lines = [
        f"# 🧬 Évaluation Darwiniste — Génération {generation}",
        "",
        f"> {len(scores)} agent(s) évalué(s)",
        "",
    ]

    sorted_scores = sorted(scores, key=lambda s: s.composite, reverse=True)
    for s in sorted_scores:
        icon = LEVEL_ICONS.get(s.level, "")
        lines.append(f"## {icon} {s.agent_id} — {s.composite:.0f}/100 ({s.level})")
        d = s.dimensions
        lines.extend([
            "",
            f"| Dimension | Score |",
            f"|-----------|-------|",
            f"| Fiabilité | {d.reliability:.0f} |",
            f"| Productivité | {d.productivity:.0f} |",
            f"| Apprentissage | {d.learning:.0f} |",
            f"| Adaptabilité | {d.adaptability:.0f} |",
            f"| Résilience | {d.resilience:.0f} |",
            f"| Influence | {d.influence:.0f} |",
            "",
        ])

    return "\n".join(lines)


def render_evolve(actions: list[EvolutionAction],
                  dry_run: bool = False) -> str:
    """Affiche les actions évolutives."""
    prefix = "🔍 DRY RUN — " if dry_run else ""
    lines = [
        f"# {prefix}🧬 Actions Évolutives",
        "",
    ]

    if not actions:
        lines.append("Aucune action à proposer.")
        return "\n".join(lines)

    for a in sorted(actions, key=lambda x: x.action):
        icon = ACTION_ICONS.get(a.action, "")
        lines.extend([
            f"## {icon} {a.agent_id} → {a.action}",
            "",
            f"**Raison** : {a.reason}",
            "",
            f"{a.detail}",
            "",
        ])
        if a.source_agents:
            lines.append(f"Sources : {', '.join(a.source_agents)}")
            lines.append("")

    return "\n".join(lines)


def render_history(history: list[GenerationRecord]) -> str:
    """Affiche l'historique des générations."""
    if not history:
        return "Aucun historique darwiniste disponible."

    lines = [
        "# 📜 Historique Darwiniste",
        "",
        "| Gén. | Date | Agents | Fitness moy. | Elite | Viable | Fragile | Obsolète |",
        "|------|------|--------|-------------|-------|--------|---------|----------|",
    ]

    for g in history:
        s = g.summary
        date = g.timestamp[:10] if g.timestamp else "?"
        lines.append(
            f"| {g.generation} | {date} | {s.get('agents_evaluated', 0)} | "
            f"{s.get('avg_fitness', 0):.1f} | {s.get('elite', 0)} | "
            f"{s.get('viable', 0)} | {s.get('fragile', 0)} | "
            f"{s.get('obsolete', 0)} |"
        )

    return "\n".join(lines)


def render_lineage(agent_id: str,
                   history: list[GenerationRecord]) -> str:
    """Affiche l'évolution d'un agent à travers les générations."""
    lines = [
        f"# 📈 Lignée de '{agent_id}'",
        "",
    ]

    found = False
    data_points = []

    for g in history:
        for s in g.scores:
            if s.get("agent_id", "").lower() == agent_id.lower():
                found = True
                data_points.append({
                    "generation": g.generation,
                    "timestamp": g.timestamp[:10],
                    "composite": s.get("composite", 0),
                    "level": s.get("level", "?"),
                    "dimensions": s.get("dimensions", {}),
                })

    if not found:
        lines.append(f"Aucune donnée trouvée pour l'agent '{agent_id}'.")
        return "\n".join(lines)

    lines.extend([
        "| Gén. | Date | Fitness | Niveau | Fiab. | Prod. | Appr. | Adapt. | Résil. | Infl. |",
        "|------|------|---------|--------|-------|-------|-------|--------|--------|-------|",
    ])

    for dp in data_points:
        d = dp["dimensions"]
        icon = LEVEL_ICONS.get(dp["level"], "")
        lines.append(
            f"| {dp['generation']} | {dp['timestamp']} | {dp['composite']:.0f} | "
            f"{icon} {dp['level']} | {d.get('reliability', 0):.0f} | "
            f"{d.get('productivity', 0):.0f} | {d.get('learning', 0):.0f} | "
            f"{d.get('adaptability', 0):.0f} | {d.get('resilience', 0):.0f} | "
            f"{d.get('influence', 0):.0f} |"
        )

    if len(data_points) >= 2:
        first = data_points[0]["composite"]
        last = data_points[-1]["composite"]
        delta = last - first
        trend = "↑" if delta > 0 else "↓" if delta < 0 else "→"
        lines.extend(["",
                       f"**Tendance** : {trend} {delta:+.0f} "
                       f"(Gén.{data_points[0]['generation']} → "
                       f"Gén.{data_points[-1]['generation']})"])

    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="BMAD Agent Darwinism — sélection naturelle des agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--project-root", default=".",
                        help="Racine du projet BMAD")
    parser.add_argument("--trace", default="_bmad-output/BMAD_TRACE.md",
                        help="Chemin vers BMAD_TRACE.md")

    sub = parser.add_subparsers(dest="command", help="Commande")

    # evaluate
    ev = sub.add_parser("evaluate", help="Évaluer la fitness des agents")
    ev.add_argument("--since", help="Date début")
    ev.add_argument("--json", action="store_true", help="Sortie JSON")

    # leaderboard
    sub.add_parser("leaderboard", help="Classement des agents")

    # evolve
    evo = sub.add_parser("evolve", help="Proposer des actions évolutives")
    evo.add_argument("--since", help="Date début")
    evo.add_argument("--dry-run", action="store_true",
                     help="Preview sans sauvegarder")
    evo.add_argument("--json", action="store_true", help="Sortie JSON")

    # history
    sub.add_parser("history", help="Historique des générations")

    # lineage
    lin = sub.add_parser("lineage", help="Évolution d'un agent spécifique")
    lin.add_argument("--agent", required=True, help="ID de l'agent")

    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    trace_path = Path(args.trace)
    if not trace_path.is_absolute():
        trace_path = project_root / trace_path

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "evaluate":
        scores = cmd_evaluate(project_root, trace_path, since=args.since)
        if not scores:
            print("Aucun agent trouvé dans BMAD_TRACE.")
            sys.exit(0)

        gen = scores[0].generation if scores else 0
        if hasattr(args, "json") and args.json:
            out = [s.to_dict() for s in scores]
            print(json.dumps(out, indent=2, ensure_ascii=False))
        else:
            print(render_evaluate(scores, gen))
            print(render_leaderboard(scores))

    elif args.command == "leaderboard":
        history = load_history(project_root)
        if not history:
            print("Aucun historique. Lancez 'evaluate' d'abord.")
            sys.exit(0)
        last_scores = [FitnessScore.from_dict(s)
                       for s in history[-1].scores]
        print(render_leaderboard(last_scores))

    elif args.command == "evolve":
        actions = cmd_evolve(project_root, trace_path,
                             since=args.since, dry_run=args.dry_run)
        if hasattr(args, "json") and args.json:
            out = [a.to_dict() for a in actions]
            print(json.dumps(out, indent=2, ensure_ascii=False))
        else:
            print(render_evolve(actions, dry_run=args.dry_run))

    elif args.command == "history":
        history = load_history(project_root)
        print(render_history(history))

    elif args.command == "lineage":
        history = load_history(project_root)
        print(render_lineage(args.agent, history))


if __name__ == "__main__":
    main()
