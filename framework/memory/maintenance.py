#!/usr/bin/env python3
"""
BMAD Memory Maintenance — Archivage, pruning et health-check automatique.

Usage:
    python maintenance.py status                     # État complet de la mémoire
    python maintenance.py health-check [--force]      # Check rapide pré-session (auto 1x/24h)
    python maintenance.py archive [days]              # Archiver mémoires > N jours (défaut: 30)
    python maintenance.py compact                     # Supprimer doublons/entrées faibles
    python maintenance.py prune-decisions [months]    # Archiver décisions > N mois (défaut: 6)
    python maintenance.py prune-learnings             # Détecter doublons dans agent-learnings
    python maintenance.py prune-activity [days]       # Compacter activity.jsonl > N jours (défaut: 90)
    python maintenance.py prune-all                   # Exécuter tous les prunings
    python maintenance.py export                      # Exporter tout en JSON lisible
    python maintenance.py memory-audit                # Audit complet mémoire (Mnemo)
    python maintenance.py consolidate-learnings [file] # Auto-merger doublons learnings (Mnemo)
    python maintenance.py context-drift               # Détecter drift shared-context (Mnemo)
"""

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path

MEMORY_DIR = Path(__file__).parent
MEMORIES_FILE = MEMORY_DIR / "memories.json"
ARCHIVE_DIR = MEMORY_DIR / "archives"
DECISIONS_LOG = MEMORY_DIR / "decisions-log.md"
LEARNINGS_DIR = MEMORY_DIR / "agent-learnings"
ACTIVITY_LOG = MEMORY_DIR / "activity.jsonl"


# ─── Configuration dynamique ────────────────────────────────────────────────

def _load_project_context() -> dict:
    """Charge project-context.yaml depuis la racine du projet.
    Retourne un dict vide si non trouvé."""
    try:
        import yaml
    except ImportError:
        return {}
    # Remonter depuis _bmad/_memory/ jusqu'à la racine projet
    for parent in [MEMORY_DIR.parent.parent, MEMORY_DIR.parent.parent.parent]:
        ctx_file = parent / "project-context.yaml"
        if ctx_file.exists():
            with open(ctx_file, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    return {}


def _get_infrastructure_pattern() -> str:
    """Retourne le pattern regex pour identifier les identifiants d'infra
    à partir de project-context.yaml. Fallback sur un pattern générique."""
    ctx = _load_project_context()
    infra = ctx.get("infrastructure", {})
    hosts = infra.get("hosts", {})

    # Construire le pattern à partir des noms d'hôtes du projet
    patterns = []
    for host_name in hosts:
        # Échapper les caractères spéciaux regex
        patterns.append(re.escape(host_name))

    # Ajouter les patterns de base VM/LXC si type proxmox
    if any("proxmox" in str(v).lower() for v in hosts.values()):
        patterns.extend([r"lxc\s*\d+", r"vm\s*\d+"])

    if not patterns:
        # Pattern générique : hostname, IP, identifiants communs
        return r"\b(server-\w+|host-\w+|node-\w+)\b"

    return r"\b(" + "|".join(patterns) + r")\b"


# ─── Fonctions de base ──────────────────────────────────────────────────────

def load_memories() -> list[dict]:
    if not MEMORIES_FILE.exists():
        return []
    with open(MEMORIES_FILE) as f:
        return json.load(f)


def save_memories(memories: list[dict]) -> None:
    with open(MEMORIES_FILE, "w") as f:
        json.dump(memories, f, indent=2, ensure_ascii=False)


def status():
    """Affiche l'état de la mémoire."""
    memories = load_memories()
    print(f"📊 État de la mémoire BMAD")
    print(f"   Entrées mémoire : {len(memories)}")
    print(f"   Fichier          : {MEMORIES_FILE}")
    print(f"   Taille           : {MEMORIES_FILE.stat().st_size if MEMORIES_FILE.exists() else 0} octets")

    # Decisions log
    if DECISIONS_LOG.exists():
        lines = [l for l in DECISIONS_LOG.read_text().splitlines() if l.startswith("## ")]
        print(f"   Décisions log    : {len(lines)} entrées")

    # Agent learnings
    if LEARNINGS_DIR.exists():
        for f in sorted(LEARNINGS_DIR.glob("*.md")):
            lines = [l for l in f.read_text().splitlines() if l.startswith("- ")]
            print(f"   Learnings {f.stem:12s}: {len(lines)} entrées")

    # Âge des entrées
    if memories:
        dates = []
        for m in memories:
            ts = m.get("timestamp") or m.get("created_at", "")
            if ts:
                try:
                    dates.append(datetime.fromisoformat(ts.replace("Z", "+00:00")))
                except (ValueError, AttributeError):
                    pass
        if dates:
            oldest = min(dates)
            newest = max(dates)
            print(f"   Plus ancienne    : {oldest.strftime('%Y-%m-%d %H:%M')}")
            print(f"   Plus récente     : {newest.strftime('%Y-%m-%d %H:%M')}")

    # Archives
    if ARCHIVE_DIR.exists():
        archives = list(ARCHIVE_DIR.glob("*.json"))
        print(f"   Archives         : {len(archives)} fichiers")


def archive(days: int = 30):
    """Archive les entrées plus anciennes que N jours."""
    memories = load_memories()
    if not memories:
        print("Aucune entrée à archiver.")
        return

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    keep = []
    to_archive = []

    for m in memories:
        ts = m.get("timestamp") or m.get("created_at", "")
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if dt < cutoff:
                    to_archive.append(m)
                    continue
            except (ValueError, AttributeError):
                pass
        keep.append(m)

    if not to_archive:
        print(f"Aucune entrée plus ancienne que {days} jours.")
        return

    # Sauvegarder l'archive
    ARCHIVE_DIR.mkdir(exist_ok=True)
    archive_file = ARCHIVE_DIR / f"archive-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    with open(archive_file, "w") as f:
        json.dump(to_archive, f, indent=2, ensure_ascii=False)

    # Garder les entrées récentes
    save_memories(keep)
    print(f"✅ Archivé {len(to_archive)} entrées → {archive_file.name}")
    print(f"   Restantes : {len(keep)}")


def compact():
    """Supprime les doublons et entrées à faible score."""
    memories = load_memories()
    if not memories:
        print("Aucune entrée à compacter.")
        return

    seen_texts = set()
    unique = []
    removed = 0

    for m in memories:
        text = m.get("memory", m.get("text", "")).strip().lower()
        # Dédupliquer par texte exact
        if text in seen_texts:
            removed += 1
            continue
        # Supprimer les entrées trop courtes (< 10 chars)
        if len(text) < 10:
            removed += 1
            continue
        seen_texts.add(text)
        unique.append(m)

    if removed == 0:
        print("Aucun doublon ou entrée faible trouvé.")
        return

    save_memories(unique)
    print(f"✅ Compacté : {removed} entrées supprimées, {len(unique)} restantes")


def export_readable():
    """Exporte la mémoire en format lisible."""
    memories = load_memories()
    print(f"# Export mémoire BMAD — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"# {len(memories)} entrées\n")
    for i, m in enumerate(memories, 1):
        agent = m.get("agent", "?")
        text = m.get("memory", m.get("text", ""))
        ts = m.get("timestamp", m.get("created_at", "?"))
        print(f"## [{i}] {agent} — {ts}")
        print(f"{text}\n")


# ─── Pruning décisions-log ──────────────────────────────────────────────────

def prune_decisions(months: int = 6):
    """Archive les sections du decisions-log plus anciennes que N mois."""
    if not DECISIONS_LOG.exists():
        print("Aucun decisions-log trouvé.")
        return

    content = DECISIONS_LOG.read_text(encoding="utf-8")
    lines = content.splitlines()
    cutoff = datetime.now() - timedelta(days=months * 30)

    # Identifier les sections par date (## YYYY-MM-DD)
    sections = []
    current_section = {"header": "", "lines": [], "date": None}

    for line in lines:
        date_match = re.match(r'^## (\d{4}-\d{2}-\d{2})', line)
        if date_match:
            if current_section["lines"]:
                sections.append(current_section)
            try:
                section_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
            except ValueError:
                section_date = None
            current_section = {"header": line, "lines": [line], "date": section_date}
        else:
            current_section["lines"].append(line)

    if current_section["lines"]:
        sections.append(current_section)

    # Séparer anciennes et récentes
    keep_sections = []
    archive_sections = []

    for s in sections:
        if s["date"] and s["date"] < cutoff:
            archive_sections.append(s)
        else:
            keep_sections.append(s)

    if not archive_sections:
        print(f"Aucune décision plus ancienne que {months} mois.")
        return

    # Archiver
    ARCHIVE_DIR.mkdir(exist_ok=True)
    archive_file = ARCHIVE_DIR / f"decisions-archive-{datetime.now().strftime('%Y%m%d')}.md"
    archive_content = "\n".join(
        "\n".join(s["lines"]) for s in archive_sections
    )
    with open(archive_file, "w", encoding="utf-8") as f:
        f.write(f"# Décisions archivées (> {months} mois)\n\n")
        f.write(archive_content)

    # Réécrire le fichier principal (header + sections récentes)
    keep_content = "\n".join(
        "\n".join(s["lines"]) for s in keep_sections
    )
    DECISIONS_LOG.write_text(keep_content, encoding="utf-8")

    archived_count = sum(
        1 for s in archive_sections
        for l in s["lines"] if l.startswith("|") and not l.startswith("| Agent")
    )
    print(f"✅ Archivé {len(archive_sections)} sections ({archived_count} décisions) → {archive_file.name}")
    print(f"   Restantes : {len([s for s in keep_sections if s['date']])}")


# ─── Pruning learnings (détection doublons) ─────────────────────────────────

def prune_learnings():
    """Détecte et signale les doublons dans les fichiers agent-learnings."""
    if not LEARNINGS_DIR.exists():
        print("Aucun répertoire agent-learnings trouvé.")
        return

    all_entries = []  # (file, line_num, text)
    for f in sorted(LEARNINGS_DIR.glob("*.md")):
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if line.startswith("- "):
                # Enlever le préfixe date si présent
                text = re.sub(r'^- \[\d{4}-\d{2}-\d{2}\]\s*', '', line).strip()
                if text:
                    all_entries.append((f.name, i, text, line))

    if not all_entries:
        print("Aucune entrée dans les learnings.")
        return

    # Détecter les doublons par similarité > 0.85
    duplicates = []
    seen = set()
    for i, (f1, l1, t1, raw1) in enumerate(all_entries):
        if i in seen:
            continue
        group = [(f1, l1, raw1)]
        for j, (f2, l2, t2, raw2) in enumerate(all_entries[i+1:], i+1):
            if j in seen:
                continue
            similarity = SequenceMatcher(None, t1.lower(), t2.lower()).ratio()
            if similarity > 0.85:
                group.append((f2, l2, raw2))
                seen.add(j)
        if len(group) > 1:
            duplicates.append(group)
            seen.add(i)

    if not duplicates:
        print(f"✅ Aucun doublon détecté parmi {len(all_entries)} learnings.")
        return

    print(f"⚠️  {len(duplicates)} groupes de doublons détectés :\n")
    for group in duplicates:
        print(f"  Groupe (similarité > 85%) :")
        for fname, lnum, raw in group:
            print(f"    📄 {fname}:{lnum} → {raw[:80]}...")
        print()

    print("  ℹ️  Supprimez manuellement les doublons pour ne garder que la version la plus complète.")


# ─── Pruning activity.jsonl ──────────────────────────────────────────────────

def prune_activity(days: int = 90):
    """Compacte le fichier activity.jsonl en ne gardant que les N derniers jours."""
    if not ACTIVITY_LOG.exists():
        print("Aucun fichier activity.jsonl trouvé.")
        return

    events = []
    with open(ACTIVITY_LOG, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    if not events:
        print("Activity log vide.")
        return

    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    keep = [e for e in events if e.get("ts", "") >= cutoff]
    archived = len(events) - len(keep)

    if archived == 0:
        print(f"✅ Toutes les {len(events)} entrées sont dans les {days} derniers jours.")
        return

    # Archiver les anciennes
    ARCHIVE_DIR.mkdir(exist_ok=True)
    archive_file = ARCHIVE_DIR / f"activity-archive-{datetime.now().strftime('%Y%m%d')}.jsonl"
    old_events = [e for e in events if e.get("ts", "") < cutoff]
    with open(archive_file, "w", encoding="utf-8") as f:
        for e in old_events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    # Réécrire le fichier principal
    with open(ACTIVITY_LOG, "w", encoding="utf-8") as f:
        for e in keep:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    print(f"✅ Archivé {archived} events → {archive_file.name}")
    print(f"   Restants : {len(keep)}")


# ─── Prune-all ───────────────────────────────────────────────────────────────

def prune_all():
    """Exécute tous les prunings avec les valeurs par défaut."""
    print("🧹 Pruning complet de la mémoire BMAD\n")

    print("─── 1. Mémoires JSON (compact) ───")
    compact()
    print()

    print("─── 2. Décisions-log (> 6 mois) ───")
    prune_decisions(6)
    print()

    print("─── 3. Agent Learnings (doublons) ───")
    prune_learnings()
    print()

    print("─── 4. Activity Log (> 90 jours) ───")
    prune_activity(90)
    print()

    print("🧹 Pruning terminé.")


# ─── Health Check (pré-session automatique) ───────────────────────────────────

HEALTH_STATE_FILE = MEMORY_DIR / ".last-health-check"
HEALTH_INTERVAL_HOURS = 24  # Ne pas vérifier plus d'une fois par 24h


def _should_run_health_check() -> bool:
    """Vérifie si le health-check doit s'exécuter (rate-limit 24h)."""
    if not HEALTH_STATE_FILE.exists():
        return True
    try:
        last_run = datetime.fromisoformat(HEALTH_STATE_FILE.read_text().strip())
        return (datetime.now() - last_run) > timedelta(hours=HEALTH_INTERVAL_HOURS)
    except (ValueError, OSError):
        return True


def _save_health_timestamp():
    """Enregistre le timestamp du dernier health-check."""
    HEALTH_STATE_FILE.write_text(datetime.now().isoformat())


def health_check(force: bool = False):
    """Health-check rapide de la mémoire — conçu pour être appelé en pré-session.

    Retourne un résumé compact en 1-3 lignes.
    Rate-limité à 1x par 24h sauf si force=True.
    Auto-prune les données expirées silencieusement.
    """
    if not force and not _should_run_health_check():
        return  # Silencieux si déjà vérifié récemment

    issues = []
    actions_taken = []

    # 1. Vérifier taille mémoire
    memories = load_memories()
    mem_count = len(memories)

    # 2. Vérifier doublons mémoire — auto-compact si trouvés
    if memories:
        seen_texts = set()
        dupes = 0
        for m in memories:
            text = m.get("memory", m.get("text", "")).strip().lower()
            if text in seen_texts or len(text) < 10:
                dupes += 1
            else:
                seen_texts.add(text)
        if dupes > 0:
            compact()  # Auto-fix
            actions_taken.append(f"compacté {dupes} doublons mémoire")

    # 3. Vérifier taille learnings (seuil: 100 lignes)
    if LEARNINGS_DIR.exists():
        for f in sorted(LEARNINGS_DIR.glob("*.md")):
            lines = [l for l in f.read_text(encoding="utf-8").splitlines()
                     if l.startswith("- ")]
            if len(lines) > 100:
                issues.append(f"learnings/{f.name}: {len(lines)} lignes (>100)")

    # 4. Vérifier décisions-log (archiver si > 6 mois)
    if DECISIONS_LOG.exists():
        content = DECISIONS_LOG.read_text(encoding="utf-8")
        cutoff = datetime.now() - timedelta(days=180)
        old_sections = 0
        for match in re.finditer(r'^## (\d{4}-\d{2}-\d{2})', content, re.MULTILINE):
            try:
                section_date = datetime.strptime(match.group(1), "%Y-%m-%d")
                if section_date < cutoff:
                    old_sections += 1
            except ValueError:
                pass
        if old_sections > 0:
            prune_decisions(6)  # Auto-archive
            actions_taken.append(f"archivé {old_sections} sections décisions >6 mois")

    # 5. Vérifier activity.jsonl (compacter si > 90j)
    if ACTIVITY_LOG.exists():
        try:
            with open(ACTIVITY_LOG, "r", encoding="utf-8") as f:
                events = [json.loads(l) for l in f if l.strip()]
            if events:
                cutoff_ts = (datetime.now() - timedelta(days=90)).isoformat()
                old_events = [e for e in events if e.get("ts", "") < cutoff_ts]
                if len(old_events) > 10:
                    prune_activity(90)  # Auto-archive
                    actions_taken.append(f"archivé {len(old_events)} events >90j")
        except (json.JSONDecodeError, OSError):
            pass

    # 6. Stats rapides si activity log existe
    if ACTIVITY_LOG.exists():
        try:
            with open(ACTIVITY_LOG, "r", encoding="utf-8") as f:
                events = [json.loads(l) for l in f if l.strip()]
            searches = [e for e in events if e.get("cmd") == "search"]
            if len(searches) >= 5:
                scores = [e.get("top_score", 0) for e in searches]
                hit_rate = sum(1 for s in scores if s >= 0.3) / len(scores) * 100
                if hit_rate < 50:
                    issues.append(f"hit rate search: {hit_rate:.0f}% (<50%)")
        except (json.JSONDecodeError, OSError):
            pass

    # Sauvegarder le timestamp
    _save_health_timestamp()

    # 7. Mnemo auto-check : cohérence shared-context vs mémoires récentes
    context_drifts = _detect_context_drift()
    if context_drifts:
        issues.extend(context_drifts)

    # Rapport compact
    if not issues and not actions_taken:
        print(f"🩺 Mémoire saine — {mem_count} entrées, aucun problème détecté.")
    else:
        parts = []
        if actions_taken:
            parts.append("Auto-fix: " + ", ".join(actions_taken))
        if issues:
            parts.append("⚠️ " + " | ".join(issues))
        print(f"🩺 Health-check — {mem_count} entrées. {' — '.join(parts)}")


# ─── Mnemo: Détection de drift shared-context ────────────────────────────────

SHARED_CONTEXT = MEMORY_DIR / "shared-context.md"
AGENT_MANIFEST = MEMORY_DIR.parent / "_config" / "agent-manifest.csv"


def _detect_context_drift() -> list[str]:
    """Compare shared-context.md avec agent-manifest.csv pour détecter les drifts.
    Retourne une liste de drifts détectés (vide si aucun).
    """
    drifts = []

    if not SHARED_CONTEXT.exists() or not AGENT_MANIFEST.exists():
        return drifts

    context_text = SHARED_CONTEXT.read_text(encoding="utf-8")

    # Extraire les agents du manifest
    manifest_agents = set()
    with open(AGENT_MANIFEST, "r", encoding="utf-8") as f:
        import csv
        reader = csv.DictReader(f)
        for row in reader:
            module = row.get("module", "")
            if module == "custom":
                manifest_agents.add(row.get("name", ""))

    # Extraire les agents mentionnés dans le tableau shared-context
    context_agents = set()
    in_agent_table = False
    for line in context_text.splitlines():
        if "Équipe d'Agents Custom" in line or "Équipe d'Agents" in line:
            in_agent_table = True
            continue
        if in_agent_table and line.startswith("|") and not line.startswith("| Agent") and not line.startswith("|---"):
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if parts:
                context_agents.add(parts[0])
        elif in_agent_table and not line.startswith("|") and line.strip() and not line.startswith("#"):
            in_agent_table = False

    # Comparer
    missing_in_context = manifest_agents - context_agents
    extra_in_context = context_agents - manifest_agents

    if missing_in_context:
        drifts.append(f"Agents dans manifest mais PAS dans shared-context : {', '.join(sorted(missing_in_context))}")
    if extra_in_context:
        drifts.append(f"Agents dans shared-context mais PAS dans manifest : {', '.join(sorted(extra_in_context))}")

    return drifts


# ─── Mnemo: Audit mémoire complet ────────────────────────────────────────────

def memory_audit():
    """Audit complet de la mémoire — contradictions, doublons, couverture."""
    print(f"🧠 Audit Mémoire Complet — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # 1. Stats de base
    memories = load_memories()
    print(f"── 1. Mémoires JSON : {len(memories)} entrées")

    # 2. Doublons mémoire
    seen_texts = set()
    dupes = 0
    for m in memories:
        text = m.get("memory", m.get("text", "")).strip().lower()
        if text in seen_texts or len(text) < 10:
            dupes += 1
        else:
            seen_texts.add(text)
    print(f"── 2. Doublons mémoire (exact) : {dupes}")
    if dupes > 0:
        compact()

    # 3. Contradictions potentielles (mêmes sujets, valeurs différentes)
    print(f"\n── 3. Contradictions potentielles :")
    contradiction_count = _detect_memory_contradictions(memories)

    # 4. Learnings
    print(f"\n── 4. Agent Learnings :")
    prune_learnings()

    # 5. Drift shared-context
    print(f"\n── 5. Drift shared-context :")
    drifts = _detect_context_drift()
    if drifts:
        for d in drifts:
            print(f"   ⚠️  {d}")
    else:
        print("   ✅ Aucun drift détecté.")

    # 6. Résumé
    print(f"\n── Résumé ──")
    score = 10
    if dupes > 0:
        score -= 1
    if contradiction_count > 0:
        score -= min(contradiction_count * 2, 4)
    if drifts:
        score -= len(drifts)
    score = max(0, score)
    print(f"   Score santé mémoire : {score}/10")


def _detect_memory_contradictions(memories: list[dict]) -> int:
    """Détecte les mémoires contradictoires (même sujet, valeurs numériques différentes).
    Utilise le pattern d'infrastructure de project-context.yaml."""
    contradictions = 0
    num_pattern = re.compile(r'\b(\d+(?:\.\d+)?)\s*(GB|MB|TB|Go|Mo|cores?|CPU|RAM)\b', re.IGNORECASE)

    # Pattern d'infra dynamique depuis project-context.yaml
    infra_pattern = _get_infrastructure_pattern()

    # Créer un index par mots-clés principaux
    subject_groups: dict[str, list[dict]] = {}
    for m in memories:
        text = m.get("memory", "").lower()
        identifiers = re.findall(infra_pattern, text, re.IGNORECASE)
        for ident in identifiers:
            key = ident.strip().lower() if isinstance(ident, str) else ident[0].strip().lower()
            if key not in subject_groups:
                subject_groups[key] = []
            subject_groups[key].append(m)

    for subject, mems in subject_groups.items():
        if len(mems) < 2:
            continue
        # Comparer les valeurs numériques dans les mémoires du même sujet
        for i in range(len(mems)):
            nums_i = num_pattern.findall(mems[i].get("memory", ""))
            for j in range(i + 1, len(mems)):
                nums_j = num_pattern.findall(mems[j].get("memory", ""))
                for (val_i, unit_i) in nums_i:
                    for (val_j, unit_j) in nums_j:
                        if unit_i.lower() == unit_j.lower() and val_i != val_j:
                            ts_i = mems[i].get("created_at", mems[i].get("metadata", {}).get("timestamp", ""))
                            ts_j = mems[j].get("created_at", mems[j].get("metadata", {}).get("timestamp", ""))
                            print(f"   ⚡ [{subject}] {val_i}{unit_i} ({ts_i[:10]}) vs {val_j}{unit_j} ({ts_j[:10]})")
                            contradictions += 1

    if contradictions == 0:
        print("   ✅ Aucune contradiction détectée.")
    return contradictions


# ─── Mnemo: Consolidation auto des learnings ─────────────────────────────────

def consolidate_learnings(target_file: str = None):
    """Auto-merge des doublons dans les fichiers agent-learnings.

    Si target_file est spécifié, ne traite que ce fichier.
    Appelé automatiquement en début de session agent (via agent-base.md).
    """
    if not LEARNINGS_DIR.exists():
        return

    files = []
    if target_file:
        target_path = LEARNINGS_DIR / f"{target_file}.md"
        if not target_path.exists():
            return  # Silencieux si le fichier n'existe pas
        files = [target_path]
    else:
        files = sorted(LEARNINGS_DIR.glob("*.md"))

    total_removed = 0
    for f in files:
        content = f.read_text(encoding="utf-8")
        lines = content.splitlines()
        entries = []  # (line_index, text_without_date, original_line)
        other_lines = []  # (line_index, original_line) — headers, blanks, etc.

        for i, line in enumerate(lines):
            if line.startswith("- "):
                text = re.sub(r'^- \[\d{4}-\d{2}-\d{2}\]\s*', '', line).strip()
                entries.append((i, text, line))
            else:
                other_lines.append((i, line))

        if len(entries) < 2:
            continue

        # Détecter doublons (similarité > 85%)
        keep = set(range(len(entries)))
        for i in range(len(entries)):
            if i not in keep:
                continue
            for j in range(i + 1, len(entries)):
                if j not in keep:
                    continue
                sim = SequenceMatcher(None, entries[i][1].lower(), entries[j][1].lower()).ratio()
                if sim > 0.85:
                    # Garder la plus longue (plus détaillée), supprimer l'autre
                    if len(entries[j][1]) > len(entries[i][1]):
                        keep.discard(i)
                    else:
                        keep.discard(j)

        removed = len(entries) - len(keep)
        if removed > 0:
            # Reconstruire le fichier
            kept_entry_lines = {entries[k][0] for k in keep}
            new_lines = []
            for i, line in enumerate(lines):
                is_entry = any(e[0] == i for e in entries)
                if not is_entry or i in kept_entry_lines:
                    new_lines.append(line)

            f.write_text("\n".join(new_lines), encoding="utf-8")
            total_removed += removed
            print(f"   🧠 {f.stem}: {removed} doublon(s) fusionné(s), {len(keep)} restants")

    if total_removed == 0 and not target_file:
        print("   ✅ Aucun doublon dans les learnings.")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]
    if cmd == "status":
        status()
    elif cmd == "archive":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        archive(days)
    elif cmd == "compact":
        compact()
    elif cmd == "prune-decisions":
        months = int(sys.argv[2]) if len(sys.argv) > 2 else 6
        prune_decisions(months)
    elif cmd == "prune-learnings":
        prune_learnings()
    elif cmd == "prune-activity":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 90
        prune_activity(days)
    elif cmd == "prune-all":
        prune_all()
    elif cmd == "health-check":
        force = "--force" in sys.argv
        health_check(force)
    elif cmd == "export":
        export_readable()
    elif cmd == "memory-audit":
        memory_audit()
    elif cmd == "consolidate-learnings":
        target = sys.argv[2] if len(sys.argv) > 2 else None
        consolidate_learnings(target)
    elif cmd == "context-drift":
        drifts = _detect_context_drift()
        if drifts:
            print("⚠️  Drifts détectés :")
            for d in drifts:
                print(f"  - {d}")
        else:
            print("✅ shared-context.md cohérent avec agent-manifest.csv.")
    else:
        print(f"Commande inconnue : {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
