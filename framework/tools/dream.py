#!/usr/bin/env python3
"""
dream.py — BMAD Dream Mode : consolidation hors-session et insights émergents.
==============================================================================

Simule une phase de "rêve" : les agents relisent learnings, decisions, trace,
failure museum et shared-context, puis produisent des insights cross-domaine
qu'aucun agent n'aurait formulés en session.

Mode read-only : aucun fichier n'est modifié. Les insights sont écrits dans
_bmad-output/dream-journal.md pour review humain.

Usage :
  python3 dream.py --project-root .                   # Dream complet
  python3 dream.py --project-root . --since 2026-01-01 # Depuis une date
  python3 dream.py --project-root . --agent dev        # Focus un agent
  python3 dream.py --project-root . --validate         # Valider les insights (no hallucination)
  python3 dream.py --project-root . --dry-run          # Preview sans écrire

Stdlib only — aucune dépendance externe.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# ── Constantes ────────────────────────────────────────────────────────────────

MAX_INSIGHTS = 12          # Plafond d'insights par dream
MIN_SOURCES = 2            # Un insight doit croiser ≥ 2 sources
SIMILARITY_THRESHOLD = 0.6 # Seuil de détection doublon
STALENESS_DAYS = 7         # Insight plus ancien = moindre poids


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class DreamSource:
    """Une source de données pour le dream."""
    name: str          # ex. "learnings/dev.md"
    kind: str          # learnings | decisions | trace | failure-museum | shared-context
    entries: list[str] = field(default_factory=list)
    dates: list[str] = field(default_factory=list)


@dataclass
class DreamInsight:
    """Un insight émergent produit par le dream."""
    title: str
    description: str
    sources: list[str]        # noms des fichiers sources
    category: str             # pattern | tension | opportunity | connection
    confidence: float         # 0.0 - 1.0
    agents_relevant: list[str] = field(default_factory=list)
    actionable: bool = False


# ── Collecte des sources ──────────────────────────────────────────────────────

def collect_sources(project_root: Path, since: str | None = None,
                    agent_filter: str | None = None) -> list[DreamSource]:
    """Collecte toutes les sources de mémoire du projet."""
    sources: list[DreamSource] = []
    memory_dir = project_root / "_bmad" / "_memory"

    # 1. Learnings
    learnings_dir = memory_dir / "agent-learnings"
    if learnings_dir.exists():
        for f in sorted(learnings_dir.glob("*.md")):
            if agent_filter and agent_filter.lower() not in f.stem.lower():
                continue
            entries = _parse_markdown_entries(f, since)
            if entries:
                sources.append(DreamSource(
                    name=f"learnings/{f.name}",
                    kind="learnings",
                    entries=[e[1] for e in entries],
                    dates=[e[0] for e in entries],
                ))

    # 2. Decisions log
    decisions_file = memory_dir / "decisions-log.md"
    if decisions_file.exists():
        entries = _parse_markdown_entries(decisions_file, since)
        if entries:
            sources.append(DreamSource(
                name="decisions-log.md",
                kind="decisions",
                entries=[e[1] for e in entries],
                dates=[e[0] for e in entries],
            ))

    # 3. BMAD_TRACE
    trace_file = project_root / "_bmad-output" / "BMAD_TRACE.md"
    if trace_file.exists():
        entries = _parse_trace_entries(trace_file, since, agent_filter)
        if entries:
            sources.append(DreamSource(
                name="BMAD_TRACE.md",
                kind="trace",
                entries=[e[1] for e in entries],
                dates=[e[0] for e in entries],
            ))

    # 4. Failure Museum
    failure_file = memory_dir / "failure-museum.md"
    if failure_file.exists():
        entries = _parse_markdown_entries(failure_file, since)
        if entries:
            sources.append(DreamSource(
                name="failure-museum.md",
                kind="failure-museum",
                entries=[e[1] for e in entries],
                dates=[e[0] for e in entries],
            ))

    # 5. Shared context
    shared_file = memory_dir / "shared-context.md"
    if shared_file.exists():
        content = shared_file.read_text(encoding="utf-8")
        sections = _parse_shared_context_sections(content)
        if sections:
            sources.append(DreamSource(
                name="shared-context.md",
                kind="shared-context",
                entries=sections,
            ))

    # 6. Contradiction log
    contradiction_file = memory_dir / "contradiction-log.md"
    if contradiction_file.exists():
        entries = _parse_markdown_entries(contradiction_file, since)
        if entries:
            sources.append(DreamSource(
                name="contradiction-log.md",
                kind="contradictions",
                entries=[e[1] for e in entries],
                dates=[e[0] for e in entries],
            ))

    return sources


def _parse_markdown_entries(path: Path, since: str | None = None) -> list[tuple[str, str]]:
    """Parse un fichier markdown et retourne [(date, text), ...]."""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return []

    entries: list[tuple[str, str]] = []
    date_pattern = re.compile(r'\[(\d{4}-\d{2}-\d{2})')

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Chercher une date dans la ligne
        match = date_pattern.search(line)
        entry_date = match.group(1) if match else ""
        if since and entry_date and entry_date < since:
            continue
        if line.startswith("- ") or line.startswith("* "):
            entries.append((entry_date, line[2:].strip()))

    return entries


def _parse_trace_entries(path: Path, since: str | None = None,
                         agent_filter: str | None = None) -> list[tuple[str, str]]:
    """Parse BMAD_TRACE.md pour les entrées pertinentes."""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return []

    entries: list[tuple[str, str]] = []
    trace_pattern = re.compile(
        r'\[(\d{4}-\d{2}-\d{2})[^\]]*\]\s*\[(\w+)\]\s*\[([^\]]+)\]\s*(.*)'
    )

    for line in content.splitlines():
        match = trace_pattern.match(line.strip())
        if not match:
            continue
        entry_date, level, agent, payload = match.groups()
        if since and entry_date < since:
            continue
        if agent_filter and agent_filter.lower() not in agent.lower():
            continue
        # Focus sur DECISION, CHECKPOINT, FAILURE
        if level in ("DECISION", "CHECKPOINT", "FAILURE", "REMEMBER"):
            entries.append((entry_date, f"[{agent}] [{level}] {payload}"))

    return entries


def _parse_shared_context_sections(content: str) -> list[str]:
    """Extrait les sections non-vides du shared-context."""
    sections: list[str] = []
    current = ""
    for line in content.splitlines():
        if line.startswith("## "):
            if current.strip():
                sections.append(current.strip())
            current = line + "\n"
        else:
            current += line + "\n"
    if current.strip():
        sections.append(current.strip())
    return sections


# ── Analyse et génération d'insights ──────────────────────────────────────────

def _extract_keywords(text: str) -> set[str]:
    """Extrait les mots-clés significatifs d'un texte."""
    # Mots vides français + anglais
    stopwords = {
        "le", "la", "les", "de", "du", "des", "un", "une", "et", "ou", "en",
        "à", "au", "aux", "pour", "par", "sur", "dans", "avec", "que", "qui",
        "est", "sont", "a", "ont", "sera", "seront", "pas", "ne", "ni", "mais",
        "the", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "shall",
        "should", "may", "might", "can", "could", "of", "to", "in", "for",
        "on", "with", "at", "by", "from", "as", "into", "about", "between",
        "after", "before", "not", "no", "but", "or", "and", "if", "then",
        "than", "too", "very", "just", "don", "it", "its", "this", "that",
    }
    words = re.findall(r'[a-zA-ZÀ-ÿ]{3,}', text.lower())
    return {w for w in words if w not in stopwords}


def _similarity(text_a: str, text_b: str) -> float:
    """Similarité cosine simplifiée par overlap de keywords."""
    ka = _extract_keywords(text_a)
    kb = _extract_keywords(text_b)
    if not ka or not kb:
        return 0.0
    intersection = ka & kb
    union = ka | kb
    return len(intersection) / len(union) if union else 0.0


def find_cross_connections(sources: list[DreamSource]) -> list[DreamInsight]:
    """Trouve les connexions croisées entre sources différentes."""
    insights: list[DreamInsight] = []

    # Comparer chaque paire de sources de types DIFFÉRENTS
    for i, src_a in enumerate(sources):
        for j, src_b in enumerate(sources):
            if j <= i or src_a.kind == src_b.kind:
                continue
            for entry_a in src_a.entries:
                for entry_b in src_b.entries:
                    sim = _similarity(entry_a, entry_b)
                    if sim >= SIMILARITY_THRESHOLD:
                        # Connexion détectée !
                        insights.append(DreamInsight(
                            title=f"Connexion {src_a.kind} ↔ {src_b.kind}",
                            description=(
                                f"Pattern partagé entre [{src_a.name}] et [{src_b.name}] :\n"
                                f"  • {entry_a[:120]}...\n"
                                f"  • {entry_b[:120]}..."
                            ),
                            sources=[src_a.name, src_b.name],
                            category="connection",
                            confidence=round(sim, 2),
                        ))

    return insights


def find_recurring_patterns(sources: list[DreamSource]) -> list[DreamInsight]:
    """Détecte les patterns qui reviennent fréquemment."""
    insights: list[DreamInsight] = []

    # Compter les keywords globalement
    keyword_freq: dict[str, list[str]] = {}  # keyword → [source_names]
    keyword_entries: dict[str, list[str]] = {}  # keyword → [entries]

    for src in sources:
        for entry in src.entries:
            keywords = _extract_keywords(entry)
            for kw in keywords:
                keyword_freq.setdefault(kw, []).append(src.name)
                keyword_entries.setdefault(kw, []).append(entry)

    # Trouver les keywords qui apparaissent dans ≥ MIN_SOURCES sources différentes
    for kw, src_names in keyword_freq.items():
        unique_sources = list(set(src_names))
        if len(unique_sources) >= MIN_SOURCES and len(src_names) >= 3:
            sample_entries = keyword_entries[kw][:3]
            insights.append(DreamInsight(
                title=f"Pattern récurrent : '{kw}'",
                description=(
                    f"Le terme '{kw}' apparaît dans {len(unique_sources)} sources "
                    f"({len(src_names)} occurrences) :\n" +
                    "\n".join(f"  • {e[:100]}..." for e in sample_entries)
                ),
                sources=unique_sources,
                category="pattern",
                confidence=min(0.9, 0.3 + 0.1 * len(unique_sources)),
            ))

    return insights


def find_tensions(sources: list[DreamSource]) -> list[DreamInsight]:
    """Détecte les tensions et contradictions potentielles."""
    insights: list[DreamInsight] = []

    # Mots indicateurs de tension
    tension_markers = {
        "positive": ["toujours", "always", "must", "doit", "jamais", "never",
                      "obligatoire", "required", "important", "critical"],
        "negative": ["éviter", "avoid", "ne pas", "never", "jamais", "danger",
                      "risque", "problème", "échec", "fail", "broken", "cassé"],
    }

    positive_entries: list[tuple[str, str]] = []  # (source, entry)
    negative_entries: list[tuple[str, str]] = []

    for src in sources:
        for entry in src.entries:
            entry_lower = entry.lower()
            if any(m in entry_lower for m in tension_markers["positive"]):
                positive_entries.append((src.name, entry))
            if any(m in entry_lower for m in tension_markers["negative"]):
                negative_entries.append((src.name, entry))

    # Croiser positifs et négatifs sur les mêmes sujets
    for pos_src, pos_entry in positive_entries:
        for neg_src, neg_entry in negative_entries:
            if pos_src == neg_src:
                continue
            sim = _similarity(pos_entry, neg_entry)
            if sim >= 0.3:  # Seuil plus bas pour les tensions
                insights.append(DreamInsight(
                    title=f"Tension détectée entre {pos_src} et {neg_src}",
                    description=(
                        f"Possible contradiction sur le même sujet :\n"
                        f"  ✅ [{pos_src}] {pos_entry[:120]}...\n"
                        f"  ❌ [{neg_src}] {neg_entry[:120]}..."
                    ),
                    sources=[pos_src, neg_src],
                    category="tension",
                    confidence=round(sim + 0.1, 2),
                ))

    return insights


def find_opportunities(sources: list[DreamSource]) -> list[DreamInsight]:
    """Identifie les opportunités d'amélioration non exploitées."""
    insights: list[DreamInsight] = []

    # Chercher les patterns "TODO", "à améliorer", "could be better"
    opportunity_markers = [
        "todo", "à améliorer", "could be better", "improvement", "optimiser",
        "refactorer", "simplifier", "automatiser", "manque", "missing",
        "pas encore", "not yet", "futur", "future", "éventuellement",
    ]

    for src in sources:
        for entry in src.entries:
            entry_lower = entry.lower()
            for marker in opportunity_markers:
                if marker in entry_lower:
                    insights.append(DreamInsight(
                        title=f"Opportunité dans {src.name}",
                        description=f"Signal d'amélioration : {entry[:150]}",
                        sources=[src.name],
                        category="opportunity",
                        confidence=0.5,
                        actionable=True,
                    ))
                    break  # Un seul marker suffit par entry

    return insights


# ── Validation ────────────────────────────────────────────────────────────────

def validate_insight(insight: DreamInsight, sources: list[DreamSource]) -> bool:
    """Vérifie qu'un insight est ancré dans les sources (pas d'hallucination)."""
    # Règle 1 : doit avoir ≥ 1 source existante
    if not insight.sources:
        return False

    # Règle 2 : les sources référencées doivent exister dans la collecte
    source_names = {s.name for s in sources}
    for ref in insight.sources:
        if ref not in source_names:
            return False

    # Règle 3 : confiance > 0
    if insight.confidence <= 0:
        return False

    # Règle 4 : description non vide
    if not insight.description or len(insight.description) < 10:
        return False

    return True


def deduplicate_insights(insights: list[DreamInsight]) -> list[DreamInsight]:
    """Supprime les insights trop similaires."""
    unique: list[DreamInsight] = []
    for ins in insights:
        is_dupe = False
        for existing in unique:
            if _similarity(ins.description, existing.description) > 0.7:
                # Garder celui avec la meilleure confiance
                if ins.confidence > existing.confidence:
                    unique.remove(existing)
                    unique.append(ins)
                is_dupe = True
                break
        if not is_dupe:
            unique.append(ins)
    return unique


# ── Orchestration principale ──────────────────────────────────────────────────

def dream(project_root: Path, since: str | None = None,
          agent_filter: str | None = None,
          do_validate: bool = True) -> list[DreamInsight]:
    """Exécute un cycle de dream complet."""

    # 1. Collecte
    sources = collect_sources(project_root, since, agent_filter)
    if not sources:
        return []

    # 2. Analyse multi-dimensionnelle
    all_insights: list[DreamInsight] = []
    all_insights.extend(find_cross_connections(sources))
    all_insights.extend(find_recurring_patterns(sources))
    all_insights.extend(find_tensions(sources))
    all_insights.extend(find_opportunities(sources))

    # 3. Validation
    if do_validate:
        all_insights = [i for i in all_insights if validate_insight(i, sources)]

    # 4. Déduplication
    all_insights = deduplicate_insights(all_insights)

    # 5. Tri par confiance décroissante
    all_insights.sort(key=lambda i: i.confidence, reverse=True)

    # 6. Plafonnement
    return all_insights[:MAX_INSIGHTS]


# ── Rendu ─────────────────────────────────────────────────────────────────────

CATEGORY_ICONS = {
    "connection": "🔗",
    "pattern": "🔄",
    "tension": "⚡",
    "opportunity": "💡",
}


def render_journal(insights: list[DreamInsight], sources: list[DreamSource],
                   project_root: Path, since: str | None = None) -> str:
    """Génère le dream-journal.md en Markdown."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total_entries = sum(len(s.entries) for s in sources)

    lines = [
        f"# 🌙 BMAD Dream Journal — {now}",
        "",
        f"> Consolidation hors-session — {len(sources)} sources, {total_entries} entrées analysées",
    ]
    if since:
        lines.append(f"> Période : depuis {since}")
    lines.extend(["", "---", ""])

    # Résumé par catégorie
    by_cat: dict[str, list[DreamInsight]] = {}
    for ins in insights:
        by_cat.setdefault(ins.category, []).append(ins)

    lines.append("## 📊 Résumé")
    lines.append("")
    lines.append("| Catégorie | Count | Confiance moy. |")
    lines.append("|-----------|-------|----------------|")
    for cat, cat_insights in sorted(by_cat.items()):
        icon = CATEGORY_ICONS.get(cat, "❓")
        avg_conf = sum(i.confidence for i in cat_insights) / len(cat_insights)
        lines.append(f"| {icon} {cat} | {len(cat_insights)} | {avg_conf:.0%} |")
    lines.extend(["", "---", ""])

    # Détail des insights
    lines.append("## 🧠 Insights")
    lines.append("")
    for idx, ins in enumerate(insights, 1):
        icon = CATEGORY_ICONS.get(ins.category, "❓")
        conf_bar = "█" * int(ins.confidence * 10) + "░" * (10 - int(ins.confidence * 10))
        lines.append(f"### {icon} {idx}. {ins.title}")
        lines.append("")
        lines.append(f"**Confiance** : `{conf_bar}` {ins.confidence:.0%}")
        lines.append(f"**Sources** : {', '.join(ins.sources)}")
        if ins.actionable:
            lines.append("**🎯 Actionable**")
        lines.append("")
        lines.append(ins.description)
        lines.append("")

    # Sources analysées
    lines.extend(["---", "", "## 📚 Sources analysées", ""])
    for src in sources:
        lines.append(f"- **{src.name}** ({src.kind}) — {len(src.entries)} entrées")
    lines.append("")

    return "\n".join(lines)


def write_journal(content: str, project_root: Path, dry_run: bool = False) -> Path:
    """Écrit le journal dans _bmad-output/dream-journal.md."""
    output_dir = project_root / "_bmad-output"
    output_dir.mkdir(parents=True, exist_ok=True)
    journal_path = output_dir / "dream-journal.md"

    if dry_run:
        print(content)
        return journal_path

    # Archiver le journal précédent s'il existe
    if journal_path.exists():
        archive_dir = output_dir / "dream-archives"
        archive_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M")
        archive_path = archive_dir / f"dream-journal-{ts}.md"
        journal_path.rename(archive_path)

    journal_path.write_text(content, encoding="utf-8")
    return journal_path


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="BMAD Dream Mode — consolidation hors-session et insights émergents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--project-root", default=".", help="Racine du projet BMAD")
    parser.add_argument("--since", default=None, help="Date début (YYYY-MM-DD)")
    parser.add_argument("--agent", default=None, help="Filtrer par agent")
    parser.add_argument("--validate", action="store_true", help="Valider les insights")
    parser.add_argument("--dry-run", action="store_true", help="Afficher sans écrire")
    parser.add_argument("--json", action="store_true", help="Sortie JSON")

    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()

    # Collecte
    sources = collect_sources(project_root, args.since, args.agent)
    if not sources:
        print("💤 Aucune source de mémoire trouvée — rien à rêver.")
        sys.exit(0)

    total_entries = sum(len(s.entries) for s in sources)
    print(f"🌙 Dream Mode — {len(sources)} sources, {total_entries} entrées")
    print()

    # Dream
    insights = dream(project_root, args.since, args.agent, args.validate)

    if not insights:
        print("😴 Aucun insight émergent détecté. Le système est cohérent.")
        sys.exit(0)

    # Sortie JSON
    if args.json:
        data = [
            {
                "title": i.title,
                "description": i.description,
                "sources": i.sources,
                "category": i.category,
                "confidence": i.confidence,
                "actionable": i.actionable,
            }
            for i in insights
        ]
        print(json.dumps(data, indent=2, ensure_ascii=False))
        sys.exit(0)

    # Rendu Markdown
    journal = render_journal(insights, sources, project_root, args.since)
    output_path = write_journal(journal, project_root, args.dry_run)

    if not args.dry_run:
        print(f"✅ {len(insights)} insights écrits dans {output_path}")
        print()
        # Preview compact
        for idx, ins in enumerate(insights[:5], 1):
            icon = CATEGORY_ICONS.get(ins.category, "❓")
            print(f"  {icon} {idx}. {ins.title} ({ins.confidence:.0%})")
        if len(insights) > 5:
            print(f"  ... et {len(insights) - 5} de plus dans le journal")


if __name__ == "__main__":
    main()
