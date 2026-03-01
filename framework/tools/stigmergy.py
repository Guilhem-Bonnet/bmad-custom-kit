#!/usr/bin/env python3
"""
stigmergy.py — Coordination stigmergique entre agents BMAD.
=============================================================

Système de phéromones numériques : les agents déposent des signaux typés
dans l'environnement, d'autres agents les captent et adaptent leur
comportement. Pas de communication directe — l'environnement est le médium.

Phéromones :
  - NEED       🔵 — besoin (review, expertise, clarification)
  - ALERT      🔴 — danger (breaking change, dette technique, sécurité)
  - OPPORTUNITY 🟢 — amélioration potentielle
  - PROGRESS   🟡 — travail en cours
  - COMPLETE   ✅ — travail terminé, prêt pour la suite
  - BLOCK      🚧 — bloqué, en attente de résolution

Propriétés des phéromones :
  - intensity (0.0-1.0) — décroît avec le temps (demi-vie configurable)
  - location — zone affectée (fichier, domaine, feature)
  - tags — étiquettes libres pour filtrage croisé
  - reinforcements — nombre de renforcements par d'autres agents

Mécanismes :
  - Évaporation : intensité × 0.5^(age/half_life_hours)
  - Amplification : chaque renforcement augmente l'intensité de 0.2 (cap 1.0)
  - Seuil de détection : pheromone invisible sous 0.05 d'intensité

Usage :
  python3 stigmergy.py --project-root . emit --type NEED --location "src/auth" --text "review sécurité requise" --agent dev
  python3 stigmergy.py --project-root . sense                          # phéromones actives
  python3 stigmergy.py --project-root . sense --type ALERT             # alertes uniquement
  python3 stigmergy.py --project-root . sense --location "src/auth"    # zone spécifique
  python3 stigmergy.py --project-root . amplify --id PH-xxxx           # renforcer un signal
  python3 stigmergy.py --project-root . landscape                      # carte complète
  python3 stigmergy.py --project-root . trails                         # patterns émergents
  python3 stigmergy.py --project-root . evaporate                      # nettoyage des signaux morts
  python3 stigmergy.py --project-root . evaporate --dry-run

Stdlib only — aucune dépendance externe.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from math import pow as mpow
from pathlib import Path

# ── Constantes ────────────────────────────────────────────────────────────────

STIGMERGY_VERSION = "1.0.0"
PHEROMONE_FILE = "pheromone-board.json"

VALID_TYPES = {"NEED", "ALERT", "OPPORTUNITY", "PROGRESS", "COMPLETE", "BLOCK"}

TYPE_ICONS = {
    "NEED":        "🔵",
    "ALERT":       "🔴",
    "OPPORTUNITY": "🟢",
    "PROGRESS":    "🟡",
    "COMPLETE":    "✅",
    "BLOCK":       "🚧",
}

# Évaporation
DEFAULT_HALF_LIFE_HOURS = 72.0   # 3 jours de demi-vie
DETECTION_THRESHOLD = 0.05       # Invisible sous ce seuil
REINFORCEMENT_BOOST = 0.2        # Boost par amplification
MAX_INTENSITY = 1.0
DEFAULT_INTENSITY = 0.7


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class Pheromone:
    """Un signal phéromonique déposé dans l'environnement."""
    pheromone_id: str
    pheromone_type: str          # NEED | ALERT | OPPORTUNITY | PROGRESS | COMPLETE | BLOCK
    location: str                # zone affectée (fichier, domaine, feature)
    text: str                    # description du signal
    emitter: str                 # agent émetteur
    timestamp: str               # ISO 8601
    intensity: float = DEFAULT_INTENSITY
    tags: list[str] = field(default_factory=list)
    reinforcements: int = 0
    reinforced_by: list[str] = field(default_factory=list)
    resolved: bool = False
    resolved_by: str = ""
    resolved_at: str = ""

    def to_dict(self) -> dict:
        return {
            "pheromone_id": self.pheromone_id,
            "pheromone_type": self.pheromone_type,
            "location": self.location,
            "text": self.text,
            "emitter": self.emitter,
            "timestamp": self.timestamp,
            "intensity": round(self.intensity, 4),
            "tags": self.tags,
            "reinforcements": self.reinforcements,
            "reinforced_by": self.reinforced_by,
            "resolved": self.resolved,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Pheromone:
        return cls(
            pheromone_id=d.get("pheromone_id", ""),
            pheromone_type=d.get("pheromone_type", "NEED"),
            location=d.get("location", ""),
            text=d.get("text", ""),
            emitter=d.get("emitter", ""),
            timestamp=d.get("timestamp", ""),
            intensity=d.get("intensity", DEFAULT_INTENSITY),
            tags=d.get("tags", []),
            reinforcements=d.get("reinforcements", 0),
            reinforced_by=d.get("reinforced_by", []),
            resolved=d.get("resolved", False),
            resolved_by=d.get("resolved_by", ""),
            resolved_at=d.get("resolved_at", ""),
        )


@dataclass
class PheromoneBoard:
    """Le tableau de phéromones du projet."""
    version: str = STIGMERGY_VERSION
    half_life_hours: float = DEFAULT_HALF_LIFE_HOURS
    pheromones: list[Pheromone] = field(default_factory=list)
    total_emitted: int = 0
    total_evaporated: int = 0

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "half_life_hours": self.half_life_hours,
            "pheromones": [p.to_dict() for p in self.pheromones],
            "total_emitted": self.total_emitted,
            "total_evaporated": self.total_evaporated,
        }

    @classmethod
    def from_dict(cls, d: dict) -> PheromoneBoard:
        return cls(
            version=d.get("version", STIGMERGY_VERSION),
            half_life_hours=d.get("half_life_hours", DEFAULT_HALF_LIFE_HOURS),
            pheromones=[Pheromone.from_dict(p)
                        for p in d.get("pheromones", [])],
            total_emitted=d.get("total_emitted", 0),
            total_evaporated=d.get("total_evaporated", 0),
        )


@dataclass
class TrailPattern:
    """Un pattern de coordination émergent détecté."""
    pattern_type: str   # hot-zone | cold-zone | convergence | bottleneck | relay
    location: str
    description: str
    involved_agents: list[str] = field(default_factory=list)
    pheromone_count: int = 0
    avg_intensity: float = 0.0

    def to_dict(self) -> dict:
        return {
            "pattern_type": self.pattern_type,
            "location": self.location,
            "description": self.description,
            "involved_agents": self.involved_agents,
            "pheromone_count": self.pheromone_count,
            "avg_intensity": round(self.avg_intensity, 2),
        }


# ── Persistence ───────────────────────────────────────────────────────────────

def _board_path(project_root: Path) -> Path:
    return project_root / "_bmad-output" / PHEROMONE_FILE


def load_board(project_root: Path) -> PheromoneBoard:
    """Charge le pheromone board."""
    path = _board_path(project_root)
    if not path.exists():
        return PheromoneBoard()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return PheromoneBoard.from_dict(data)
    except (json.JSONDecodeError, OSError):
        return PheromoneBoard()


def save_board(project_root: Path, board: PheromoneBoard) -> None:
    """Sauvegarde le pheromone board."""
    path = _board_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(board.to_dict(), indent=2, ensure_ascii=False),
                    encoding="utf-8")


# ── ID Generation ─────────────────────────────────────────────────────────────

def _generate_id(ptype: str, location: str, text: str,
                 timestamp: str) -> str:
    """Génère un ID court de phéromone."""
    raw = f"{ptype}:{location}:{text}:{timestamp}"
    h = hashlib.sha256(raw.encode()).hexdigest()[:8]
    return f"PH-{h}"


# ── Évaporation ───────────────────────────────────────────────────────────────

def compute_current_intensity(pheromone: Pheromone,
                               half_life_hours: float,
                               now: datetime | None = None) -> float:
    """Calcule l'intensité actuelle après évaporation."""
    if now is None:
        now = datetime.now(tz=UTC)

    try:
        emit_time = datetime.fromisoformat(pheromone.timestamp)
        if emit_time.tzinfo is None:
            emit_time = emit_time.replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return pheromone.intensity

    age_hours = (now - emit_time).total_seconds() / 3600.0
    if age_hours <= 0:
        return pheromone.intensity

    # Decay : intensity × 0.5^(age / half_life)
    decay_factor = mpow(0.5, age_hours / half_life_hours)
    return pheromone.intensity * decay_factor


def evaporate(board: PheromoneBoard,
              now: datetime | None = None) -> tuple[PheromoneBoard, int]:
    """Supprime les phéromones sous le seuil de détection."""
    if now is None:
        now = datetime.now(tz=UTC)

    surviving = []
    evaporated = 0

    for p in board.pheromones:
        current = compute_current_intensity(p, board.half_life_hours, now)
        if current >= DETECTION_THRESHOLD and not p.resolved:
            surviving.append(p)
        else:
            evaporated += 1

    board.pheromones = surviving
    board.total_evaporated += evaporated
    return board, evaporated


# ── Actions ───────────────────────────────────────────────────────────────────

def emit_pheromone(board: PheromoneBoard, ptype: str, location: str,
                   text: str, emitter: str,
                   tags: list[str] | None = None,
                   intensity: float = DEFAULT_INTENSITY) -> Pheromone:
    """Dépose une phéromone sur le board."""
    now = datetime.now(tz=UTC).isoformat()
    pid = _generate_id(ptype, location, text, now)

    pheromone = Pheromone(
        pheromone_id=pid,
        pheromone_type=ptype,
        location=location,
        text=text,
        emitter=emitter,
        timestamp=now,
        intensity=min(max(intensity, 0.0), MAX_INTENSITY),
        tags=tags or [],
    )

    board.pheromones.append(pheromone)
    board.total_emitted += 1
    return pheromone


def amplify_pheromone(board: PheromoneBoard, pheromone_id: str,
                      agent: str) -> Pheromone | None:
    """Renforce une phéromone existante."""
    for p in board.pheromones:
        if p.pheromone_id == pheromone_id:
            p.intensity = min(p.intensity + REINFORCEMENT_BOOST, MAX_INTENSITY)
            p.reinforcements += 1
            if agent not in p.reinforced_by:
                p.reinforced_by.append(agent)
            return p
    return None


def resolve_pheromone(board: PheromoneBoard, pheromone_id: str,
                      agent: str) -> Pheromone | None:
    """Marque une phéromone comme résolue."""
    for p in board.pheromones:
        if p.pheromone_id == pheromone_id:
            p.resolved = True
            p.resolved_by = agent
            p.resolved_at = datetime.now(tz=UTC).isoformat()
            return p
    return None


def sense_pheromones(board: PheromoneBoard,
                     ptype: str | None = None,
                     location: str | None = None,
                     tag: str | None = None,
                     emitter: str | None = None,
                     include_resolved: bool = False,
                     now: datetime | None = None,
                     ) -> list[tuple[Pheromone, float]]:
    """Détecte les phéromones actives avec intensité décroissante."""
    if now is None:
        now = datetime.now(tz=UTC)

    results = []
    for p in board.pheromones:
        if not include_resolved and p.resolved:
            continue

        current = compute_current_intensity(p, board.half_life_hours, now)
        if current < DETECTION_THRESHOLD:
            continue

        if ptype and p.pheromone_type != ptype:
            continue
        if location and location.lower() not in p.location.lower():
            continue
        if tag and tag.lower() not in [t.lower() for t in p.tags]:
            continue
        if emitter and emitter.lower() != p.emitter.lower():
            continue

        results.append((p, current))

    # Trier par intensité décroissante
    results.sort(key=lambda x: x[1], reverse=True)
    return results


# ── Trail Analysis ────────────────────────────────────────────────────────────

def analyze_trails(board: PheromoneBoard,
                   now: datetime | None = None) -> list[TrailPattern]:
    """Détecte les patterns de coordination émergents."""
    if now is None:
        now = datetime.now(tz=UTC)

    patterns: list[TrailPattern] = []

    # Regrouper par location
    by_location: dict[str, list[tuple[Pheromone, float]]] = defaultdict(list)
    for p in board.pheromones:
        if p.resolved:
            continue
        current = compute_current_intensity(p, board.half_life_hours, now)
        if current >= DETECTION_THRESHOLD:
            by_location[p.location].append((p, current))

    for loc, items in by_location.items():
        agents = list({p.emitter for p, _ in items})
        avg_int = sum(i for _, i in items) / len(items) if items else 0

        # Hot zone : ≥ 3 phéromones actives dans la même zone
        if len(items) >= 3:
            patterns.append(TrailPattern(
                pattern_type="hot-zone",
                location=loc,
                description=f"{len(items)} signaux actifs — zone d'activité intense",
                involved_agents=agents,
                pheromone_count=len(items),
                avg_intensity=avg_int,
            ))

        # Convergence : ≥ 2 agents différents sur la même zone
        if len(agents) >= 2:
            patterns.append(TrailPattern(
                pattern_type="convergence",
                location=loc,
                description=f"{len(agents)} agents convergent sur cette zone",
                involved_agents=agents,
                pheromone_count=len(items),
                avg_intensity=avg_int,
            ))

        # Bottleneck : ≥ 2 BLOCK dans la même zone
        blocks = [p for p, _ in items if p.pheromone_type == "BLOCK"]
        if len(blocks) >= 2:
            patterns.append(TrailPattern(
                pattern_type="bottleneck",
                location=loc,
                description=f"{len(blocks)} blocages dans cette zone — goulot potentiel",
                involved_agents=[b.emitter for b in blocks],
                pheromone_count=len(blocks),
                avg_intensity=avg_int,
            ))

    # Cold zones : locations mentionnées dans les pheromones résolues mais
    # sans aucune phéromone active
    resolved_locs = {p.location for p in board.pheromones if p.resolved}
    active_locs = set(by_location.keys())
    cold_locs = resolved_locs - active_locs
    for loc in cold_locs:
        patterns.append(TrailPattern(
            pattern_type="cold-zone",
            location=loc,
            description="Zone précédemment active, désormais silencieuse",
            pheromone_count=0,
            avg_intensity=0.0,
        ))

    # Relay pattern : COMPLETE suivi de NEED/PROGRESS dans zone voisine
    completes = [(p, i) for p, i in
                 sense_pheromones(board, ptype="COMPLETE",
                                 include_resolved=True, now=now)
                 if i >= DETECTION_THRESHOLD]
    for cp, _ in completes:
        # Chercher un NEED ou PROGRESS dans la même location émis
        # par un agent différent
        for p in board.pheromones:
            if (p.pheromone_id != cp.pheromone_id and
                    p.location == cp.location and
                    p.emitter != cp.emitter and
                    p.pheromone_type in ("NEED", "PROGRESS") and
                    not p.resolved):
                curr = compute_current_intensity(
                    p, board.half_life_hours, now)
                if curr >= DETECTION_THRESHOLD:
                    patterns.append(TrailPattern(
                        pattern_type="relay",
                        location=cp.location,
                        description=f"Relais : {cp.emitter} → {p.emitter} "
                                    f"(complete → {p.pheromone_type.lower()})",
                        involved_agents=[cp.emitter, p.emitter],
                        pheromone_count=2,
                        avg_intensity=curr,
                    ))

    # Déduplicate patterns (même type + location)
    seen = set()
    unique_patterns = []
    for pat in patterns:
        key = f"{pat.pattern_type}:{pat.location}"
        if key not in seen:
            seen.add(key)
            unique_patterns.append(pat)

    return unique_patterns


# ── Rendering ─────────────────────────────────────────────────────────────────

def render_sense(items: list[tuple[Pheromone, float]]) -> str:
    """Affiche les phéromones détectées."""
    if not items:
        return "🌿 Aucune phéromone active détectée."

    lines = [
        "# 🐜 Phéromones Actives",
        "",
        f"> {len(items)} signal(aux) détecté(s)",
        "",
    ]

    for p, intensity in items:
        icon = TYPE_ICONS.get(p.pheromone_type, "❓")
        bar = _intensity_bar(intensity)
        lines.extend([
            f"## {icon} {p.pheromone_type} — `{p.pheromone_id}`",
            "",
            f"- **Zone** : {p.location}",
            f"- **Signal** : {p.text}",
            f"- **Émetteur** : {p.emitter}",
            f"- **Intensité** : {bar} ({intensity:.0%})",
            f"- **Renforcé** : {p.reinforcements}× "
            f"{'(' + ', '.join(p.reinforced_by) + ')' if p.reinforced_by else ''}",
        ])
        if p.tags:
            lines.append(f"- **Tags** : {', '.join(p.tags)}")
        lines.append("")

    return "\n".join(lines)


def render_landscape(board: PheromoneBoard,
                     now: datetime | None = None) -> str:
    """Affiche la carte complète du paysage phéromonique."""
    if now is None:
        now = datetime.now(tz=UTC)

    active = sense_pheromones(board, now=now)
    resolved = [p for p in board.pheromones if p.resolved]

    lines = [
        "# 🗺️ Paysage Phéromonique",
        "",
        f"- Signaux actifs : **{len(active)}**",
        f"- Résolus : **{len(resolved)}**",
        f"- Total émis : **{board.total_emitted}**",
        f"- Évaporés : **{board.total_evaporated}**",
        f"- Demi-vie : **{board.half_life_hours}h**",
        "",
    ]

    # Par type
    by_type: dict[str, list[tuple[Pheromone, float]]] = defaultdict(list)
    for p, i in active:
        by_type[p.pheromone_type].append((p, i))

    if by_type:
        lines.extend(["## Répartition par type", ""])
        lines.append("| Type | Count | Intensité moy. |")
        lines.append("|------|-------|----------------|")
        for ptype in VALID_TYPES:
            items = by_type.get(ptype, [])
            if items:
                icon = TYPE_ICONS.get(ptype, "")
                avg_i = sum(i for _, i in items) / len(items)
                lines.append(
                    f"| {icon} {ptype} | {len(items)} | {avg_i:.0%} |")
        lines.append("")

    # Par location (top 10)
    by_loc: dict[str, list[tuple[Pheromone, float]]] = defaultdict(list)
    for p, i in active:
        by_loc[p.location].append((p, i))

    if by_loc:
        sorted_locs = sorted(by_loc.items(),
                             key=lambda x: len(x[1]), reverse=True)
        lines.extend(["## Zones actives (top 10)", ""])
        lines.append("| Zone | Signaux | Agents | Intensité max |")
        lines.append("|------|---------|--------|---------------|")
        for loc, items in sorted_locs[:10]:
            agents = list({p.emitter for p, _ in items})
            max_i = max(i for _, i in items)
            lines.append(
                f"| {loc} | {len(items)} | {', '.join(agents)} | {max_i:.0%} |")
        lines.append("")

    # Par émetteur
    by_emitter: dict[str, int] = defaultdict(int)
    for p, _ in active:
        by_emitter[p.emitter] += 1

    if by_emitter:
        lines.extend(["## Agents actifs", ""])
        for agent, count in sorted(by_emitter.items(),
                                    key=lambda x: x[1], reverse=True):
            lines.append(f"- **{agent}** : {count} signal(aux)")
        lines.append("")

    return "\n".join(lines)


def render_trails(patterns: list[TrailPattern]) -> str:
    """Affiche les patterns de coordination détectés."""
    if not patterns:
        return "🌿 Aucun pattern de coordination émergent détecté."

    pattern_icons = {
        "hot-zone":     "🔥",
        "cold-zone":    "❄️",
        "convergence":  "🎯",
        "bottleneck":   "🚧",
        "relay":        "🔄",
    }

    lines = [
        "# 🐜 Trails — Patterns de coordination",
        "",
        f"> {len(patterns)} pattern(s) détecté(s)",
        "",
    ]

    for pat in sorted(patterns,
                      key=lambda p: p.pheromone_count, reverse=True):
        icon = pattern_icons.get(pat.pattern_type, "❓")
        lines.extend([
            f"## {icon} {pat.pattern_type.upper()} — {pat.location}",
            "",
            f"{pat.description}",
            "",
        ])
        if pat.involved_agents:
            lines.append(f"- **Agents** : {', '.join(pat.involved_agents)}")
        lines.append(
            f"- **Signaux** : {pat.pheromone_count} | "
            f"Intensité moy. : {pat.avg_intensity:.0%}")
        lines.append("")

    return "\n".join(lines)


def render_evaporate(evaporated: int, remaining: int,
                     dry_run: bool = False) -> str:
    """Affiche le résultat de l'évaporation."""
    prefix = "🔍 DRY RUN — " if dry_run else ""
    return (
        f"{prefix}🌬️ Évaporation terminée\n\n"
        f"- Phéromones évaporées : **{evaporated}**\n"
        f"- Phéromones restantes : **{remaining}**\n"
    )


def _intensity_bar(intensity: float, width: int = 10) -> str:
    """Barre visuelle d'intensité."""
    filled = int(intensity * width)
    return "█" * filled + "░" * (width - filled)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="BMAD Stigmergy — coordination par phéromones numériques",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--project-root", default=".",
                        help="Racine du projet BMAD")

    sub = parser.add_subparsers(dest="command", help="Commande")

    # emit
    em = sub.add_parser("emit", help="Déposer une phéromone")
    em.add_argument("--type", required=True, choices=sorted(VALID_TYPES),
                    help="Type de phéromone")
    em.add_argument("--location", required=True, help="Zone affectée")
    em.add_argument("--text", required=True, help="Description du signal")
    em.add_argument("--agent", required=True, help="Agent émetteur")
    em.add_argument("--tags", default="", help="Tags (comma-sep)")
    em.add_argument("--intensity", type=float, default=DEFAULT_INTENSITY,
                    help=f"Intensité initiale (défaut: {DEFAULT_INTENSITY})")

    # sense
    se = sub.add_parser("sense", help="Détecter les phéromones actives")
    se.add_argument("--type", default=None, help="Filtrer par type")
    se.add_argument("--location", default=None, help="Filtrer par zone")
    se.add_argument("--tag", default=None, help="Filtrer par tag")
    se.add_argument("--emitter", default=None, help="Filtrer par émetteur")
    se.add_argument("--include-resolved", action="store_true",
                    help="Inclure les phéromones résolues")
    se.add_argument("--json", action="store_true", help="Sortie JSON")

    # amplify
    amp = sub.add_parser("amplify", help="Renforcer une phéromone")
    amp.add_argument("--id", required=True, help="ID de la phéromone")
    amp.add_argument("--agent", required=True, help="Agent renforçant")

    # resolve
    res = sub.add_parser("resolve", help="Marquer une phéromone comme résolue")
    res.add_argument("--id", required=True, help="ID de la phéromone")
    res.add_argument("--agent", required=True, help="Agent résolvant")

    # landscape
    sub.add_parser("landscape", help="Carte du paysage phéromonique")

    # trails
    sub.add_parser("trails", help="Patterns de coordination émergents")

    # evaporate
    ev = sub.add_parser("evaporate", help="Nettoyer les signaux morts")
    ev.add_argument("--dry-run", action="store_true",
                    help="Preview sans modifier")

    # stats
    sub.add_parser("stats", help="Statistiques rapides")

    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    board = load_board(project_root)

    if args.command == "emit":
        tags = [t.strip() for t in args.tags.split(",")
                if t.strip()] if args.tags else []
        p = emit_pheromone(
            board, args.type, args.location, args.text,
            args.agent, tags=tags, intensity=args.intensity)
        save_board(project_root, board)
        icon = TYPE_ICONS.get(args.type, "")
        print(f"{icon} Phéromone émise : {p.pheromone_id}")
        print(f"   Type : {p.pheromone_type}")
        print(f"   Zone : {p.location}")
        print(f"   Signal : {p.text}")
        print(f"   Intensité : {p.intensity:.0%}")

    elif args.command == "sense":
        items = sense_pheromones(
            board, ptype=args.type, location=args.location,
            tag=args.tag, emitter=args.emitter,
            include_resolved=args.include_resolved)
        if hasattr(args, "json") and args.json:
            out = [{"pheromone": p.to_dict(), "current_intensity": round(i, 4)}
                   for p, i in items]
            print(json.dumps(out, indent=2, ensure_ascii=False))
        else:
            print(render_sense(items))

    elif args.command == "amplify":
        p = amplify_pheromone(board, args.id, args.agent)
        if p:
            save_board(project_root, board)
            print(f"⬆️ Phéromone {args.id} renforcée par {args.agent}")
            print(f"   Nouvelle intensité : {p.intensity:.0%}")
            print(f"   Renforcements : {p.reinforcements}")
        else:
            print(f"❌ Phéromone {args.id} introuvable", file=sys.stderr)
            sys.exit(1)

    elif args.command == "resolve":
        p = resolve_pheromone(board, args.id, args.agent)
        if p:
            save_board(project_root, board)
            print(f"✅ Phéromone {args.id} résolue par {args.agent}")
        else:
            print(f"❌ Phéromone {args.id} introuvable", file=sys.stderr)
            sys.exit(1)

    elif args.command == "landscape":
        print(render_landscape(board))

    elif args.command == "trails":
        patterns = analyze_trails(board)
        print(render_trails(patterns))

    elif args.command == "evaporate":
        if args.dry_run:
            # Preview: count without modifying
            _, count = evaporate(
                PheromoneBoard.from_dict(board.to_dict()))
            remaining = len(board.pheromones) - count
            print(render_evaporate(count, remaining, dry_run=True))
        else:
            _, count = evaporate(board)
            save_board(project_root, board)
            print(render_evaporate(count, len(board.pheromones)))

    elif args.command == "stats":
        active = sense_pheromones(board)
        resolved = sum(1 for p in board.pheromones if p.resolved)
        max_reinforced = max(
            (p.reinforcements for p in board.pheromones), default=0)
        print("# 📊 Statistiques Stigmergy")
        print("")
        print(f"- Signaux actifs : **{len(active)}**")
        print(f"- Résolus : **{resolved}**")
        print(f"- Total émis : **{board.total_emitted}**")
        print(f"- Total évaporés : **{board.total_evaporated}**")
        print(f"- Max renforcements : **{max_reinforced}**")
        if active:
            max_item = active[0]
            print(f"- Signal le plus fort : **{max_item[0].pheromone_id}** "
                  f"({max_item[1]:.0%})")


if __name__ == "__main__":
    main()
