#!/usr/bin/env python3
"""
BMAD Agent Benchmark Engine — BM-51
====================================
Analyse BMAD_TRACE.md + mémoire Qdrant pour produire des métriques
objectives de performance des agents.

Usage:
    python3 agent-bench.py --report
    python3 agent-bench.py --report --since 2026-01-01
    python3 agent-bench.py --report --agent forge
    python3 agent-bench.py --improve           # génère bench-context.md pour Sentinel
    python3 agent-bench.py --summary           # une ligne par agent
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


# ── Structures ────────────────────────────────────────────────────────────────

@dataclass
class TraceEntry:
    """Une entrée parsée depuis BMAD_TRACE.md"""
    timestamp: str
    agent: str
    story: str
    entry_type: str   # GIT-COMMIT, DECISION, REMEMBER, FAILURE, CHECKPOINT, AC-PASS, AC-FAIL
    content: str
    raw_line: str


@dataclass
class AgentMetrics:
    """Métriques agrégées par agent"""
    agent_id: str
    stories_touched: set[str] = field(default_factory=set)
    decisions_count: int = 0
    failures_count: int = 0
    failure_patterns: list[str] = field(default_factory=list)
    ac_pass_count: int = 0
    ac_fail_count: int = 0
    checkpoints_created: int = 0
    commits_attributed: int = 0
    learnings_count: int = 0
    last_activity: Optional[str] = None
    cycle_times_days: list[float] = field(default_factory=list)

    @property
    def ac_pass_rate(self) -> float:
        total = self.ac_pass_count + self.ac_fail_count
        return (self.ac_pass_count / total * 100) if total > 0 else 0.0

    @property
    def activity_score(self) -> int:
        """Score composite 0-100 basé sur les métriques disponibles"""
        score = 0
        # Stories multiples = polyvalence
        score += min(len(self.stories_touched) * 5, 20)
        # Décisions = contribution active
        score += min(self.decisions_count * 3, 20)
        # AC pass rate
        score += int(self.ac_pass_rate * 0.3)
        # Learnings stockés = capitalisation
        score += min(self.learnings_count * 4, 20)
        # Commits = livraisons réelles
        score += min(self.commits_attributed * 2, 10)
        return min(score, 100)


@dataclass
class SessionMetrics:
    """Métriques globales de la session/période"""
    period_start: Optional[str]
    period_end: Optional[str]
    total_entries: int = 0
    total_commits: int = 0
    total_decisions: int = 0
    total_failures: int = 0
    total_checkpoints: int = 0
    agents: dict[str, AgentMetrics] = field(default_factory=dict)
    failure_patterns: dict[str, int] = field(default_factory=dict)
    story_cycle_times: dict[str, float] = field(default_factory=dict)


# ── Parser BMAD_TRACE ─────────────────────────────────────────────────────────

def parse_trace(trace_path: Path, since: Optional[str] = None, agent_filter: Optional[str] = None) -> SessionMetrics:
    """Parse BMAD_TRACE.md et retourne des métriques structurées."""
    if not trace_path.exists():
        return SessionMetrics(period_start=None, period_end=None)

    since_dt = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
        except ValueError:
            print(f"[WARN] Format --since invalide (attendu: YYYY-MM-DD) : {since}", file=sys.stderr)

    session = SessionMetrics(period_start=since, period_end=datetime.now(tz=timezone.utc).date().isoformat())
    entries: list[TraceEntry] = []

    # ── Patterns de parsing ─────────────────────────────────────────────────
    # Entête de section : ## 2026-02-27 14:30 | agent-name | story-id
    header_re = re.compile(
        r"^##\s+(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2})?)\s*\|\s*([^\|]+)\s*\|\s*(.+)$"
    )
    # Types d'entrées dans le contenu
    type_patterns = {
        "GIT-COMMIT":  re.compile(r"\[GIT-COMMIT\]"),
        "DECISION":    re.compile(r"\[DECISION\]"),
        "REMEMBER":    re.compile(r"\[REMEMBER:([^\]]+)\]"),
        "FAILURE":     re.compile(r"\[FAILURE\]|\[ÉCHEC\]|\bFAIL\b"),
        "AC-PASS":     re.compile(r"\[AC-PASS\]|\bAC.*PASS\b|\bpasse\b.*\bAC\b"),
        "AC-FAIL":     re.compile(r"\[AC-FAIL\]|\bAC.*FAIL\b|\béchec\b.*\bAC\b"),
        "CHECKPOINT":  re.compile(r"\[CHECKPOINT\]|checkpoint_id"),
    }

    # Patterns de failure fréquents
    failure_categorizer = {
        "test-failure":     re.compile(r"test.*fail|pytest.*error|go test.*FAIL|jest.*fail", re.IGNORECASE),
        "lint-error":       re.compile(r"lint|ruff|shellcheck|yamllint|golangci", re.IGNORECASE),
        "schema-invalid":   re.compile(r"schema|dna.*invalid|yaml.*invalid|\\$schema", re.IGNORECASE),
        "context-drift":    re.compile(r"drift|shared.context.*outdated|contexte.*désync", re.IGNORECASE),
        "ac-not-met":       re.compile(r"acceptance.criteria|AC-\d+.*fail|critère.*non", re.IGNORECASE),
        "syntax-error":     re.compile(r"syntax.*error|SyntaxError|bash.*error", re.IGNORECASE),
        "memory-miss":      re.compile(r"qdrant.*error|memory.*miss|recall.*empty", re.IGNORECASE),
    }

    current_header: dict = {}
    current_content_lines: list[str] = []

    def flush_entry() -> None:
        if not current_header:
            return
        content = "\n".join(current_content_lines).strip()
        if not content:
            return

        ts = current_header.get("ts", "")
        ag = current_header.get("agent", "system").strip().lower()
        st = current_header.get("story", "").strip()

        # Filtres
        if since_dt and ts:
            try:
                entry_dt = datetime.fromisoformat(ts.replace(" ", "T"))
                if entry_dt < since_dt:
                    return
            except ValueError:
                pass

        if agent_filter and agent_filter.lower() not in ag:
            return

        # Déterminer le type dominant
        entry_type = "GENERIC"
        for etype, pat in type_patterns.items():
            if pat.search(content):
                entry_type = etype
                break

        entry = TraceEntry(
            timestamp=ts,
            agent=ag,
            story=st,
            entry_type=entry_type,
            content=content,
            raw_line=content[:200],
        )
        entries.append(entry)

    with trace_path.open(encoding="utf-8", errors="replace") as f:
        for raw_line in f:
            line = raw_line.rstrip()
            m = header_re.match(line)
            if m:
                flush_entry()
                current_header = {"ts": m.group(1), "agent": m.group(2), "story": m.group(3)}
                current_content_lines = []
            elif current_header:
                current_content_lines.append(line)

    flush_entry()

    # ── Agrégation ─────────────────────────────────────────────────────────
    session.total_entries = len(entries)

    story_first_seen: dict[str, str] = {}
    story_last_seen: dict[str, str] = {}

    for entry in entries:
        ag = entry.agent
        if ag not in session.agents:
            session.agents[ag] = AgentMetrics(agent_id=ag)
        m = session.agents[ag]

        if entry.story:
            m.stories_touched.add(entry.story)
            if entry.story not in story_first_seen:
                story_first_seen[entry.story] = entry.timestamp
            story_last_seen[entry.story] = entry.timestamp

        m.last_activity = entry.timestamp

        if entry.entry_type == "GIT-COMMIT":
            m.commits_attributed += 1
            session.total_commits += 1
        elif entry.entry_type == "DECISION":
            m.decisions_count += 1
            session.total_decisions += 1
        elif entry.entry_type == "FAILURE":
            m.failures_count += 1
            session.total_failures += 1
            # Catégoriser l'échec
            for cat, pat in failure_categorizer.items():
                if pat.search(entry.content):
                    m.failure_patterns.append(cat)
                    session.failure_patterns[cat] = session.failure_patterns.get(cat, 0) + 1
                    break
            else:
                session.failure_patterns["other"] = session.failure_patterns.get("other", 0) + 1
        elif entry.entry_type == "AC-PASS":
            m.ac_pass_count += 1
        elif entry.entry_type == "AC-FAIL":
            m.ac_fail_count += 1
        elif entry.entry_type == "CHECKPOINT":
            m.checkpoints_created += 1
            session.total_checkpoints += 1
        elif entry.entry_type == "REMEMBER":
            m.learnings_count += 1

    # ── Cycle times (story start → last commit) ──────────────────────────
    for story_id in story_first_seen:
        if story_id in story_last_seen:
            try:
                t0 = datetime.fromisoformat(story_first_seen[story_id].replace(" ", "T"))
                t1 = datetime.fromisoformat(story_last_seen[story_id].replace(" ", "T"))
                delta_days = (t1 - t0).total_seconds() / 86400
                session.story_cycle_times[story_id] = round(delta_days, 2)
            except ValueError:
                pass

    return session


# ── Lecture mémoire Qdrant (si accessible) ───────────────────────────────────

def read_memory_stats(bmad_dir: Path) -> dict:
    """Lit les statistiques de la mémoire locale si disponibles."""
    stats: dict = {}

    # Fichiers de learnings locaux (fallback sans Qdrant)
    learnings_dir = bmad_dir / "_memory"
    if learnings_dir.exists():
        for item in learnings_dir.glob("agent-learnings*.md"):
            try:
                content = item.read_text(encoding="utf-8", errors="replace")
                lines = [l for l in content.splitlines() if l.startswith("- ") or l.startswith("* ")]
                stats[item.stem] = len(lines)
            except OSError:
                pass

    # Tentative API Qdrant local
    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:6333/collections", timeout=2) as r:
            data = json.loads(r.read())
            for col in data.get("result", {}).get("collections", []):
                stats[f"qdrant:{col['name']}"] = "accessible"
    except Exception:
        stats["qdrant"] = "offline"

    return stats


# ── Reporters ─────────────────────────────────────────────────────────────────

def report_text(session: SessionMetrics, memory_stats: dict, out: Path) -> None:
    """Génère le rapport Markdown de performance."""
    now = datetime.now(tz=timezone.utc).date().isoformat()

    lines: list[str] = [
        f"# BMAD Agent Benchmark Report — {now}",
        "",
        f"> Période : {session.period_start or 'all-time'} → {session.period_end}",
        f"> Entrées TRACE analysées : {session.total_entries}",
        "",
        "## Métriques globales",
        "",
        "| KPI | Valeur |",
        "|-----|--------|",
        f"| Commits TRACE | {session.total_commits} |",
        f"| Décisions | {session.total_decisions} |",
        f"| Failures | {session.total_failures} |",
        f"| Checkpoints | {session.total_checkpoints} |",
        f"| Agents actifs | {len(session.agents)} |",
    ]

    avg_cycle = (
        round(sum(session.story_cycle_times.values()) / len(session.story_cycle_times), 1)
        if session.story_cycle_times else None
    )
    if avg_cycle is not None:
        lines.append(f"| Cycle time moyen (stories) | {avg_cycle} jours |")

    lines += [
        "",
        "## Performance par agent",
        "",
        "| Agent | Score | Stories | Décisions | Failures | AC Pass% | Learnings | Commits |",
        "|-------|-------|---------|-----------|----------|----------|-----------|---------|",
    ]

    sorted_agents = sorted(session.agents.values(), key=lambda a: a.activity_score, reverse=True)
    for ag in sorted_agents:
        score_icon = "🟢" if ag.activity_score >= 70 else ("🟡" if ag.activity_score >= 40 else "🔴")
        ac_str = f"{ag.ac_pass_rate:.0f}%" if (ag.ac_pass_count + ag.ac_fail_count) > 0 else "n/a"
        lines.append(
            f"| `{ag.agent_id}` | {score_icon} {ag.activity_score}/100 | "
            f"{len(ag.stories_touched)} | {ag.decisions_count} | {ag.failures_count} | "
            f"{ac_str} | {ag.learnings_count} | {ag.commits_attributed} |"
        )

    # Patterns d'échec
    if session.failure_patterns:
        lines += [
            "",
            "## Patterns d'échec (fréquence)",
            "",
            "| Pattern | Occurrences | Priorité |",
            "|---------|-------------|---------|",
        ]
        sorted_failures = sorted(session.failure_patterns.items(), key=lambda x: x[1], reverse=True)
        for pat, count in sorted_failures:
            priority = "🔴 HAUTE" if count >= 5 else ("🟠 MOYENNE" if count >= 2 else "🟢 BASSE")
            lines.append(f"| `{pat}` | {count} | {priority} |")

    # Cycle times stories
    if session.story_cycle_times:
        lines += [
            "",
            "## Cycle times par story",
            "",
            "| Story | Durée (jours) | Évaluation |",
            "|-------|--------------|------------|",
        ]
        for story, days in sorted(session.story_cycle_times.items(), key=lambda x: x[1], reverse=True)[:10]:
            eval_str = "🔴 Long" if days > 7 else ("🟡 Normal" if days > 2 else "🟢 Rapide")
            lines.append(f"| `{story}` | {days} | {eval_str} |")

    # Mémoire
    if memory_stats:
        lines += [
            "",
            "## État mémoire",
            "",
            "| Source | Status |",
            "|--------|--------|",
        ]
        for k, v in memory_stats.items():
            lines.append(f"| `{k}` | {v} |")

    # Recommandations automatiques
    recs = _auto_recommendations(session)
    if recs:
        lines += [
            "",
            "## Recommandations automatiques",
            "",
            "> Générées par agent-bench.py — à valider par Sentinel",
            "",
        ]
        for i, rec in enumerate(recs, 1):
            lines.append(f"{i}. {rec}")

    lines += [
        "",
        "---",
        f"*Généré par `framework/tools/agent-bench.py` le {now}*",
        f"*Pour amélioration Sentinel : `bash bmad-init.sh bench --improve`*",
    ]

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✅ Rapport écrit : {out}")


def generate_bench_context(session: SessionMetrics, out: Path) -> None:
    """Génère bench-context.md — seed structuré pour Sentinel #bench-review."""
    now = datetime.now(tz=timezone.utc).date().isoformat()

    weak_agents = [
        ag for ag in session.agents.values()
        if ag.activity_score < 50 or ag.failures_count >= 3
    ]
    top_failures = sorted(session.failure_patterns.items(), key=lambda x: x[1], reverse=True)[:5]

    lines = [
        f"# Bench Context pour Sentinel — {now}",
        "",
        "> Fichier généré automatiquement par `bmad-init.sh bench --improve`.",
        "> À passer directement en contexte à Sentinel [BR], commande : `bench-review`.",
        "",
        "## Résumé de la période",
        "",
        f"- Durée analysée : {session.period_start or 'all-time'} → {session.period_end}",
        f"- Agents actifs : {len(session.agents)}",
        f"- Total failures : {session.total_failures}",
        f"- Total décisions : {session.total_decisions}",
        "",
        "## Agents nécessitant attention",
        "",
    ]

    if weak_agents:
        for ag in sorted(weak_agents, key=lambda a: a.activity_score):
            lines.append(f"### `{ag.agent_id}` — score {ag.activity_score}/100")
            lines.append(f"- Stories : {len(ag.stories_touched)}")
            lines.append(f"- Failures : {ag.failures_count}")
            if ag.failure_patterns:
                patterns = ", ".join(set(ag.failure_patterns[:5]))
                lines.append(f"- Patterns d'échec : {patterns}")
            lines.append(f"- Learnings capitalisés : {ag.learnings_count}")
            lines.append("")
    else:
        lines.append("_Aucun agent clairement sous-performant détecté._")
        lines.append("")

    lines += [
        "## Top patterns d'échec à traiter",
        "",
    ]
    if top_failures:
        for pat, count in top_failures:
            lines.append(f"- **{pat}** : {count} occurrence(s)")
    else:
        lines.append("_Aucun pattern d'échec significatif._")

    lines += [
        "",
        "## Questions pour Sentinel",
        "",
        "1. Quels prompts d'agents devraient être renforcés pour réduire les patterns d'échec ci-dessus ?",
        "2. Les agents à faible score ont-ils des personas/rules insuffisants ou des protocoles manquants ?",
        "3. Quels learnings Mnemo devraient être transformés en règles permanentes dans les agents ?",
        "4. Y a-t-il des patterns de réussite chez les agents à score élevé à dupliquer ?",
        "",
        "---",
        "> **Instructions pour Sentinel** : Analyser ce contexte via `#bench-review`,",
        "> produire des recommandations concrètes par agent, et lister les modifications",
        "> à soumettre à Bond pour application après validation de l'utilisateur.",
    ]

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✅ Bench context écrit : {out}")
    print(f"   → Ouvrez ce fichier et passez-le à Sentinel avec la commande : bench-review")


def _auto_recommendations(session: SessionMetrics) -> list[str]:
    """Génère des recommandations heuristiques basées sur les métriques."""
    recs: list[str] = []

    # Agents silencieux (aucune décision, aucun commit)
    silent = [
        ag for ag in session.agents.values()
        if ag.decisions_count == 0 and ag.commits_attributed == 0 and len(ag.stories_touched) > 1
    ]
    if silent:
        names = ", ".join(f"`{a.agent_id}`" for a in silent[:3])
        recs.append(f"🟡 Agents peu actifs (0 décision, 0 commit) : {names} — vérifier leurs protocoles d'activation")

    # Failures récurrentes
    for pat, count in session.failure_patterns.items():
        if count >= 5:
            recs.append(f"🔴 Pattern `{pat}` récurrent ({count}x) — ajouter une règle préventive dans les agents concernés")

    # Pas de learnings = aucune capitalisation
    no_learn = [ag for ag in session.agents.values() if ag.learnings_count == 0 and ag.stories_touched]
    if len(no_learn) > len(session.agents) * 0.5:
        recs.append("🟠 Moins de 50% des agents capitalisent des learnings — vérifier l'intégration Mnemo")

    # Cycle times longs
    long_stories = {k: v for k, v in session.story_cycle_times.items() if v > 14}
    if long_stories:
        recs.append(f"🟠 {len(long_stories)} story(ies) dépassent 14 jours — envisager checkpoints plus fréquents")

    if not recs:
        recs.append("🟢 Aucune anomalie majeure détectée automatiquement.")

    return recs


def summary_line(session: SessionMetrics) -> None:
    """Affiche une ligne de résumé par agent."""
    print(f"{'Agent':<20} {'Score':>6} {'Stories':>8} {'Decisions':>10} {'Failures':>9} {'AC%':>5}")
    print("-" * 65)
    for ag in sorted(session.agents.values(), key=lambda a: a.activity_score, reverse=True):
        ac_str = f"{ag.ac_pass_rate:.0f}%" if (ag.ac_pass_count + ag.ac_fail_count) > 0 else "  n/a"
        print(
            f"{ag.agent_id:<20} {ag.activity_score:>6}/100 {len(ag.stories_touched):>8} "
            f"{ag.decisions_count:>10} {ag.failures_count:>9} {ac_str:>5}"
        )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="BMAD Agent Benchmark — métriques de performance depuis BMAD_TRACE",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--report", action="store_true", help="Générer le rapport Markdown complet")
    parser.add_argument("--improve", action="store_true", help="Générer bench-context.md pour Sentinel")
    parser.add_argument("--summary", action="store_true", help="Résumé console par agent")
    parser.add_argument("--since", metavar="YYYY-MM-DD", help="Filtrer depuis cette date")
    parser.add_argument("--agent", metavar="AGENT_ID", help="Filtrer sur un agent spécifique")
    parser.add_argument(
        "--trace", metavar="PATH",
        default="_bmad-output/BMAD_TRACE.md",
        help="Chemin vers BMAD_TRACE.md (défaut: _bmad-output/BMAD_TRACE.md)",
    )
    parser.add_argument(
        "--out", metavar="PATH",
        default="_bmad-output/bench-reports/latest.md",
        help="Fichier de sortie du rapport",
    )
    parser.add_argument(
        "--bmad-dir", metavar="PATH",
        default="_bmad",
        help="Répertoire _bmad (pour lecture mémoire)",
    )

    args = parser.parse_args()

    if not args.report and not args.improve and not args.summary:
        parser.print_help()
        sys.exit(0)

    trace_path = Path(args.trace)
    bmad_dir = Path(args.bmad_dir)
    out_path = Path(args.out)

    if not trace_path.exists():
        print(f"[WARN] BMAD_TRACE introuvable : {trace_path}", file=sys.stderr)
        print("[INFO] Lancement avec données vides — exécutez des sessions BMAD pour alimenter le bench")

    print(f"📊 Parsing BMAD_TRACE : {trace_path}")
    session = parse_trace(trace_path, since=args.since, agent_filter=args.agent)
    memory_stats = read_memory_stats(bmad_dir)

    print(f"   {session.total_entries} entrées analysées, {len(session.agents)} agents, {session.total_failures} failures")

    if args.summary:
        summary_line(session)

    if args.report:
        report_text(session, memory_stats, out_path)

    if args.improve:
        bench_ctx_path = out_path.parent / "bench-context.md"
        generate_bench_context(session, bench_ctx_path)


if __name__ == "__main__":
    main()
