#!/usr/bin/env python3
"""
adversarial-consensus.py — Protocole de consensus adversarial pour décisions critiques.
========================================================================================

Implémente un protocole Byzantine Fault Tolerant simplifié pour les décisions
architecturales / techniques majeures. 3 votants + 1 devil's advocate.

Chaque votant analyse la proposition sous un angle différent (technique, business,
risque). Le devil's advocate tente activement de la casser. Si le consensus survit,
la décision est validée et enregistrée.

Usage :
  python3 adversarial-consensus.py --project-root . --proposal "Utiliser PostgreSQL pour le cache sessions"
  python3 adversarial-consensus.py --project-root . --proposal-file proposal.md
  python3 adversarial-consensus.py --project-root . --proposal "..." --threshold 0.75
  python3 adversarial-consensus.py --project-root . --history    # Voir les décisions passées
  python3 adversarial-consensus.py --project-root . --stats      # Statistiques de consensus

Stdlib only — aucune dépendance externe.
"""

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# ── Constantes ────────────────────────────────────────────────────────────────

VOTERS_COUNT = 3           # Nombre de votants
CONSENSUS_THRESHOLD = 0.66 # 2/3 requis pour passer
MAX_ROUNDS = 3             # Rounds de débat maximum
HISTORY_FILE = "consensus-history.json"


# ── Perspectives des votants ──────────────────────────────────────────────────

@dataclass
class VoterPerspective:
    """Perspective d'analyse d'un votant."""
    id: str
    name: str
    icon: str
    focus: str            # Ce que ce votant évalue
    criteria: list[str]   # Critères d'évaluation


VOTER_PERSPECTIVES = [
    VoterPerspective(
        id="technical",
        name="Analyste Technique",
        icon="🔧",
        focus="Faisabilité technique et qualité d'implémentation",
        criteria=[
            "Complexité d'implémentation (lignes de code, deps)",
            "Impact sur la performance runtime",
            "Compatibilité avec l'architecture existante",
            "Maintenabilité long terme",
            "Testabilité",
        ],
    ),
    VoterPerspective(
        id="business",
        name="Analyste Business",
        icon="📊",
        focus="Valeur business et alignement stratégique",
        criteria=[
            "Valeur ajoutée pour l'utilisateur final",
            "Coût (tokens, compute, stockage)",
            "Time-to-market",
            "Différenciation concurrentielle",
            "Scalabilité business (plus d'utilisateurs = ?)",
        ],
    ),
    VoterPerspective(
        id="risk",
        name="Analyste Risques",
        icon="⚠️",
        focus="Risques, edge cases et failure modes",
        criteria=[
            "Modes de défaillance identifiés",
            "Réversibilité de la décision",
            "Dépendances externes / vendor lock-in",
            "Sécurité et données sensibles",
            "Risque de dette technique",
        ],
    ),
]

DEVIL_ADVOCATE = VoterPerspective(
    id="devil",
    name="Avocat du Diable",
    icon="😈",
    focus="Destruction systématique de la proposition",
    criteria=[
        "Quel est le PIRE scénario réaliste ?",
        "Quelle hypothèse implicite est fausse ?",
        "Quelle alternative simple a été ignorée ?",
        "Quel coût caché n'a pas été mentionné ?",
        "Pourquoi est-ce que ça va échouer dans 6 mois ?",
    ],
)


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class Vote:
    """Vote d'un participant."""
    voter_id: str
    voter_name: str
    verdict: str          # approve | reject | abstain
    confidence: float     # 0.0 - 1.0
    rationale: str
    criteria_scores: dict[str, float] = field(default_factory=dict)
    concerns: list[str] = field(default_factory=list)


@dataclass
class DevilChallenge:
    """Challenge de l'avocat du diable."""
    attack_vector: str    # L'angle d'attaque
    severity: str         # critical | major | minor
    description: str
    mitigation: str       # Mitigation proposée (peut être vide)


@dataclass
class ConsensusResult:
    """Résultat du protocole de consensus."""
    proposal: str
    timestamp: str
    votes: list[Vote]
    devil_challenges: list[DevilChallenge]
    consensus_reached: bool
    consensus_score: float   # 0.0 - 1.0
    final_verdict: str       # approved | rejected | inconclusive
    surviving_concerns: list[str]
    decision_hash: str


# ── Analyse heuristique de la proposition ─────────────────────────────────────

def _extract_tech_signals(proposal: str) -> dict:
    """Extrait les signaux techniques d'une proposition."""
    text = proposal.lower()
    signals = {
        "has_database": any(w in text for w in ["sql", "postgres", "mongo", "redis", "database", "db", "sqlite"]),
        "has_api": any(w in text for w in ["api", "rest", "graphql", "endpoint", "grpc"]),
        "has_infra": any(w in text for w in ["docker", "kubernetes", "k8s", "cloud", "aws", "gcp", "azure", "terraform"]),
        "has_security": any(w in text for w in ["auth", "token", "secret", "encrypt", "ssl", "tls", "security"]),
        "has_performance": any(w in text for w in ["cache", "performance", "latency", "throughput", "scaling"]),
        "has_migration": any(w in text for w in ["migrat", "upgrade", "remplac", "switch", "transition"]),
        "has_new_dep": any(w in text for w in ["installer", "install", "ajouter", "dependency", "library", "package"]),
        "word_count": len(text.split()),
    }
    return signals


def _score_criterion(proposal: str, criterion: str, signals: dict) -> float:
    """Score heuristique d'un critère (0.0-1.0, 1.0 = bon)."""
    criterion_lower = criterion.lower()

    # Complexité : plus c'est long + deps = plus complexe
    if "complexité" in criterion_lower or "complexity" in criterion_lower:
        base = 0.7
        if signals["has_new_dep"]:
            base -= 0.2
        if signals["word_count"] > 50:
            base -= 0.1
        return max(0.1, min(1.0, base))

    # Performance
    if "performance" in criterion_lower:
        return 0.5 if signals["has_performance"] else 0.7

    # Compatibilité
    if "compatib" in criterion_lower or "architecture" in criterion_lower:
        base = 0.6
        if signals["has_migration"]:
            base -= 0.15
        return max(0.1, min(1.0, base))

    # Maintenabilité
    if "maintenab" in criterion_lower:
        return 0.5 if signals["has_new_dep"] else 0.7

    # Testabilité
    if "testab" in criterion_lower:
        return 0.6

    # Valeur ajoutée
    if "valeur" in criterion_lower or "value" in criterion_lower:
        return 0.7

    # Coût
    if "coût" in criterion_lower or "cost" in criterion_lower:
        base = 0.6
        if signals["has_infra"]:
            base -= 0.15
        return max(0.1, min(1.0, base))

    # Time to market
    if "time" in criterion_lower and "market" in criterion_lower:
        return 0.5 if signals["has_migration"] else 0.7

    # Différenciation
    if "différen" in criterion_lower or "concurren" in criterion_lower:
        return 0.6

    # Scalabilité
    if "scalab" in criterion_lower:
        return 0.5

    # Risque / défaillance
    if "défaillance" in criterion_lower or "failure" in criterion_lower:
        risk = 0.6
        if signals["has_infra"] or signals["has_security"]:
            risk -= 0.15
        return max(0.2, risk)

    # Réversibilité
    if "réversib" in criterion_lower or "reversib" in criterion_lower:
        return 0.4 if signals["has_migration"] else 0.7

    # Sécurité
    if "sécurité" in criterion_lower or "security" in criterion_lower:
        return 0.4 if signals["has_security"] else 0.8

    # Dette technique
    if "dette" in criterion_lower or "debt" in criterion_lower:
        return 0.5 if signals["has_new_dep"] else 0.7

    return 0.5  # Base par défaut


def evaluate_proposal(proposal: str, perspective: VoterPerspective,
                      context: dict | None = None) -> Vote:
    """Évalue une proposition depuis une perspective donnée."""
    signals = _extract_tech_signals(proposal)

    # Scorer chaque critère
    criteria_scores = {}
    for criterion in perspective.criteria:
        criteria_scores[criterion] = _score_criterion(proposal, criterion, signals)

    # Score global = moyenne pondérée
    avg_score = sum(criteria_scores.values()) / len(criteria_scores) if criteria_scores else 0.5

    # Identifier les concerns (scores < 0.5)
    concerns = [c for c, s in criteria_scores.items() if s < 0.5]

    # Déterminer le verdict
    if avg_score >= 0.65:
        verdict = "approve"
    elif avg_score >= 0.45:
        verdict = "abstain"
    else:
        verdict = "reject"

    # Confiance basée sur la variance des scores
    scores_list = list(criteria_scores.values())
    if scores_list:
        variance = sum((s - avg_score) ** 2 for s in scores_list) / len(scores_list)
        confidence = max(0.3, 1.0 - variance * 2)
    else:
        confidence = 0.5

    # Générer la rationale
    rationale_parts = []
    if perspective.id == "technical":
        if signals["has_new_dep"]:
            rationale_parts.append("Introduction de dépendances externes → complexité accrue")
        if signals["has_migration"]:
            rationale_parts.append("Migration requise → risque de régression")
        if avg_score >= 0.6:
            rationale_parts.append("Architecture compatible avec l'existant")
    elif perspective.id == "business":
        if avg_score >= 0.6:
            rationale_parts.append("Aligné avec la valeur utilisateur")
        if signals["has_infra"]:
            rationale_parts.append("Coûts d'infrastructure à surveiller")
    elif perspective.id == "risk":
        if signals["has_security"]:
            rationale_parts.append("Implications sécurité identifiées — review approfondi recommandé")
        if signals["has_migration"]:
            rationale_parts.append("Point de non-retour potentiel — plan de rollback requis")

    rationale = " | ".join(rationale_parts) if rationale_parts else f"Score global : {avg_score:.0%}"

    return Vote(
        voter_id=perspective.id,
        voter_name=f"{perspective.icon} {perspective.name}",
        verdict=verdict,
        confidence=round(confidence, 2),
        rationale=rationale,
        criteria_scores=criteria_scores,
        concerns=concerns,
    )


def devil_advocate_analysis(proposal: str, votes: list[Vote]) -> list[DevilChallenge]:
    """Le devil's advocate tente de casser la proposition."""
    challenges: list[DevilChallenge] = []
    signals = _extract_tech_signals(proposal)

    # Attack 1 : Hypothèse implicite
    if signals["word_count"] < 20:
        challenges.append(DevilChallenge(
            attack_vector="Proposition sous-spécifiée",
            severity="critical",
            description="La proposition manque de détails. Les hypothèses implicites "
                        "ne sont pas documentées — chaque non-dit est un risque.",
            mitigation="Exiger une RFC détaillée avec hypothèses explicites, "
                        "contraintes et critères de succès mesurables.",
        ))

    # Attack 2 : Alternative ignorée
    challenges.append(DevilChallenge(
        attack_vector="Alternatives non évaluées",
        severity="major",
        description="Aucune alternative n'a été formellement comparée. "
                    "Comment savoir que c'est la meilleure option sans benchmark ?",
        mitigation="Documenter au minimum 2 alternatives avec pros/cons avant validation.",
    ))

    # Attack 3 : Pire scénario
    if signals["has_migration"]:
        challenges.append(DevilChallenge(
            attack_vector="Migration irréversible",
            severity="critical",
            description="Si la migration échoue à mi-chemin, quel est le plan de rollback ? "
                        "Le coût d'un échec peut dépasser le bénéfice attendu.",
            mitigation="Exiger un runbook de rollback testé avant de commencer.",
        ))

    if signals["has_security"]:
        challenges.append(DevilChallenge(
            attack_vector="Surface d'attaque élargie",
            severity="critical",
            description="Tout ajout sécuritaire est aussi un vecteur d'attaque potentiel. "
                        "Qui va maintenir et patcher cette composante dans 2 ans ?",
            mitigation="Audit sécurité obligatoire + propriétaire désigné pour les patches.",
        ))

    if signals["has_new_dep"]:
        challenges.append(DevilChallenge(
            attack_vector="Dépendance fantôme",
            severity="major",
            description="Chaque dépendance externe est un risque supply chain. "
                        "Que se passe-t-il si le mainteneur abandonne le projet ?",
            mitigation="Vérifier : licence, activité du repo, alternatives stdlib.",
        ))

    # Attack 4 : Les concerns non résolus des votants
    all_concerns = []
    for vote in votes:
        all_concerns.extend(vote.concerns)
    if all_concerns:
        unique_concerns = list(set(all_concerns))
        challenges.append(DevilChallenge(
            attack_vector="Concerns non résolus des votants",
            severity="major",
            description=f"{len(unique_concerns)} critères d'évaluation sont sous le seuil : "
                        + ", ".join(unique_concerns[:3]),
            mitigation="Adresser chaque concern avec un plan d'action spécifique.",
        ))

    # Attack 5 : Coût dans 6 mois
    challenges.append(DevilChallenge(
        attack_vector="Coût de maintenance à 6 mois",
        severity="minor",
        description="Quel est le coût récurrent de cette décision ? "
                    "Documentation, formation, monitoring, incidents — "
                    "le TCO est toujours plus élevé que l'implémentation initiale.",
        mitigation="Estimer le TCO 6 mois (pas seulement le coût initial).",
    ))

    return challenges


# ── Protocole de consensus ────────────────────────────────────────────────────

def run_consensus(proposal: str, project_root: Path,
                  threshold: float = CONSENSUS_THRESHOLD,
                  context: dict | None = None) -> ConsensusResult:
    """Exécute le protocole de consensus complet."""
    timestamp = datetime.now().isoformat()

    # Phase 1 : Votes
    votes: list[Vote] = []
    for perspective in VOTER_PERSPECTIVES:
        vote = evaluate_proposal(proposal, perspective, context)
        votes.append(vote)

    # Phase 2 : Devil's Advocate
    challenges = devil_advocate_analysis(proposal, votes)

    # Phase 3 : Calcul du consensus
    approve_count = sum(1 for v in votes if v.verdict == "approve")
    reject_count = sum(1 for v in votes if v.verdict == "reject")

    consensus_score = approve_count / len(votes) if votes else 0.0

    # Ajuster pour les challenges critiques
    critical_challenges = sum(1 for c in challenges if c.severity == "critical")
    if critical_challenges > 0:
        consensus_score *= max(0.5, 1.0 - 0.15 * critical_challenges)

    consensus_reached = consensus_score >= threshold
    if consensus_reached:
        final_verdict = "approved"
    elif reject_count > approve_count:
        final_verdict = "rejected"
    else:
        final_verdict = "inconclusive"

    # Concerns survivants
    surviving = []
    for c in challenges:
        if c.severity in ("critical", "major") and not c.mitigation:
            surviving.append(c.description)
    for v in votes:
        surviving.extend(v.concerns)

    # Hash de décision pour traçabilité
    decision_hash = hashlib.sha256(
        f"{proposal}:{timestamp}".encode()
    ).hexdigest()[:12]

    return ConsensusResult(
        proposal=proposal,
        timestamp=timestamp,
        votes=votes,
        devil_challenges=challenges,
        consensus_reached=consensus_reached,
        consensus_score=round(consensus_score, 2),
        final_verdict=final_verdict,
        surviving_concerns=list(set(surviving))[:10],
        decision_hash=decision_hash,
    )


# ── Persistance ───────────────────────────────────────────────────────────────

def save_result(result: ConsensusResult, project_root: Path) -> Path:
    """Sauvegarde le résultat dans l'historique."""
    output_dir = project_root / "_bmad-output"
    output_dir.mkdir(parents=True, exist_ok=True)
    history_path = output_dir / HISTORY_FILE

    history = []
    if history_path.exists():
        try:
            history = json.loads(history_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    entry = {
        "hash": result.decision_hash,
        "timestamp": result.timestamp,
        "proposal": result.proposal[:200],
        "verdict": result.final_verdict,
        "score": result.consensus_score,
        "votes": [
            {"voter": v.voter_id, "verdict": v.verdict, "confidence": v.confidence}
            for v in result.votes
        ],
        "critical_challenges": sum(1 for c in result.devil_challenges if c.severity == "critical"),
        "surviving_concerns": len(result.surviving_concerns),
    }
    history.append(entry)
    history_path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    return history_path


def load_history(project_root: Path) -> list[dict]:
    """Charge l'historique des décisions."""
    path = project_root / "_bmad-output" / HISTORY_FILE
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


# ── Rendu ─────────────────────────────────────────────────────────────────────

VERDICT_ICONS = {"approved": "✅", "rejected": "❌", "inconclusive": "🟡"}
SEVERITY_ICONS = {"critical": "🔴", "major": "🟠", "minor": "🟡"}
VOTE_ICONS = {"approve": "✅", "reject": "❌", "abstain": "🟡"}


def render_report(result: ConsensusResult) -> str:
    """Génère le rapport de consensus en Markdown."""
    icon = VERDICT_ICONS.get(result.final_verdict, "❓")
    lines = [
        f"# {icon} Rapport de Consensus — {result.decision_hash}",
        "",
        f"> **Proposition** : {result.proposal}",
        f"> **Date** : {result.timestamp}",
        f"> **Verdict** : **{result.final_verdict.upper()}** (score: {result.consensus_score:.0%})",
        "",
        "---",
        "",
        "## 🗳️ Votes",
        "",
        "| Votant | Verdict | Confiance | Rationale |",
        "|--------|---------|-----------|-----------|",
    ]

    for v in result.votes:
        v_icon = VOTE_ICONS.get(v.verdict, "❓")
        lines.append(
            f"| {v.voter_name} | {v_icon} {v.verdict} | {v.confidence:.0%} | {v.rationale} |"
        )
    lines.extend(["", "---", ""])

    # Détail des scores par critère
    lines.append("## 📊 Scores détaillés")
    lines.append("")
    for v in result.votes:
        lines.append(f"### {v.voter_name}")
        lines.append("")
        for criterion, score in v.criteria_scores.items():
            bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
            flag = " ⚠️" if score < 0.5 else ""
            lines.append(f"- `{bar}` {score:.0%} — {criterion}{flag}")
        lines.append("")

    # Devil's Advocate
    lines.extend(["---", "", "## 😈 Challenges de l'Avocat du Diable", ""])
    for c in result.devil_challenges:
        sev_icon = SEVERITY_ICONS.get(c.severity, "❓")
        lines.append(f"### {sev_icon} [{c.severity.upper()}] {c.attack_vector}")
        lines.append("")
        lines.append(c.description)
        if c.mitigation:
            lines.append("")
            lines.append(f"**Mitigation** : {c.mitigation}")
        lines.append("")

    # Surviving concerns
    if result.surviving_concerns:
        lines.extend(["---", "", "## ⚠️ Concerns non résolus", ""])
        for concern in result.surviving_concerns:
            lines.append(f"- {concern}")
        lines.append("")

    # Conclusion
    lines.extend(["---", "", "## 🏛️ Conclusion", ""])
    if result.consensus_reached:
        lines.append(
            f"Le consensus est **atteint** ({result.consensus_score:.0%} ≥ seuil). "
            f"La proposition peut avancer sous réserve d'adresser les concerns survivants."
        )
    else:
        lines.append(
            f"Le consensus n'est **PAS atteint** ({result.consensus_score:.0%} < seuil). "
            f"La proposition doit être révisée ou abandonnée."
        )
    lines.append("")

    return "\n".join(lines)


def render_history_table(history: list[dict]) -> str:
    """Affiche l'historique en tableau."""
    if not history:
        return "Aucune décision dans l'historique."

    lines = [
        "| # | Date | Hash | Verdict | Score | Proposal |",
        "|---|------|------|---------|-------|----------|",
    ]
    for i, entry in enumerate(reversed(history), 1):
        ts = entry.get("timestamp", "?")[:10]
        icon = VERDICT_ICONS.get(entry.get("verdict", ""), "❓")
        lines.append(
            f"| {i} | {ts} | `{entry.get('hash', '?')}` | "
            f"{icon} {entry.get('verdict', '?')} | {entry.get('score', 0):.0%} | "
            f"{entry.get('proposal', '?')[:60]}... |"
        )
    return "\n".join(lines)


def render_stats(history: list[dict]) -> str:
    """Statistiques agrégées."""
    if not history:
        return "Aucune décision dans l'historique."

    total = len(history)
    approved = sum(1 for h in history if h.get("verdict") == "approved")
    rejected = sum(1 for h in history if h.get("verdict") == "rejected")
    inconclusive = total - approved - rejected
    avg_score = sum(h.get("score", 0) for h in history) / total

    lines = [
        "## 📊 Statistiques du Consensus",
        "",
        f"- **Total décisions** : {total}",
        f"- **Approuvées** : {approved} ({approved/total:.0%})",
        f"- **Rejetées** : {rejected} ({rejected/total:.0%})",
        f"- **Inconclusives** : {inconclusive} ({inconclusive/total:.0%})",
        f"- **Score moyen** : {avg_score:.0%}",
        "",
    ]
    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="BMAD Adversarial Consensus Protocol — décisions critiques validées par consensus BFT",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--project-root", default=".", help="Racine du projet BMAD")
    parser.add_argument("--proposal", default=None, help="Proposition à évaluer (texte)")
    parser.add_argument("--proposal-file", default=None, help="Fichier contenant la proposition")
    parser.add_argument("--threshold", type=float, default=CONSENSUS_THRESHOLD,
                        help=f"Seuil de consensus (défaut: {CONSENSUS_THRESHOLD})")
    parser.add_argument("--history", action="store_true", help="Afficher l'historique")
    parser.add_argument("--stats", action="store_true", help="Afficher les statistiques")
    parser.add_argument("--json", action="store_true", help="Sortie JSON")
    parser.add_argument("--dry-run", action="store_true", help="Ne pas sauvegarder")

    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()

    # Mode historique
    if args.history:
        history = load_history(project_root)
        print(render_history_table(history))
        return

    # Mode stats
    if args.stats:
        history = load_history(project_root)
        print(render_stats(history))
        return

    # Charger la proposition
    proposal = args.proposal
    if args.proposal_file:
        pf = Path(args.proposal_file)
        if not pf.exists():
            print(f"❌ Fichier non trouvé : {args.proposal_file}", file=sys.stderr)
            sys.exit(1)
        proposal = pf.read_text(encoding="utf-8").strip()

    if not proposal:
        print("❌ Proposition requise (--proposal ou --proposal-file)", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    # Exécuter le consensus
    print("🏛️  Adversarial Consensus Protocol")
    print(f"📝 Proposition : {proposal[:100]}{'...' if len(proposal) > 100 else ''}")
    print(f"🎯 Seuil : {args.threshold:.0%}")
    print()

    result = run_consensus(proposal, project_root, args.threshold)

    # Sortie JSON
    if args.json:
        data = {
            "hash": result.decision_hash,
            "verdict": result.final_verdict,
            "score": result.consensus_score,
            "consensus_reached": result.consensus_reached,
            "votes": [{"voter": v.voter_id, "verdict": v.verdict, "confidence": v.confidence} for v in result.votes],
            "challenges_critical": sum(1 for c in result.devil_challenges if c.severity == "critical"),
        }
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        report = render_report(result)
        print(report)

    # Sauvegarder
    if not args.dry_run:
        save_result(result, project_root)
        icon = VERDICT_ICONS.get(result.final_verdict, "❓")
        print(f"\n{icon} Décision {result.decision_hash} enregistrée dans consensus-history.json")


if __name__ == "__main__":
    main()
