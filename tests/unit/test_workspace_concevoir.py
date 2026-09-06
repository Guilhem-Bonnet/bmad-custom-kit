"""Ce que l'espace Concevoir lit, prouvé sur un projet réellement initialisé.

`workspace_api.blueprints_view` existe parce que `/api/blueprints`
(`project_health.flows`) ne porte ni le genre (v1 classique ou Studio v2), ni
les agents délégués, ni l'équipe déclarée, ni la date de dernière
modification — les quatre colonnes que la Liste de la spec (§4) réclame en
plus du nom et de la validation. Chaque test décrit un défaut qu'il empêche.
"""

from __future__ import annotations

import json
from pathlib import Path

from grimoire.tools import workspace_api as wa


def test_un_projet_sans_blueprint_rend_une_liste_vide(tmp_path: Path) -> None:
    """Le niveau Projet doit pouvoir dire « aucun blueprint » sans planter.

    Un `tmp_path` nu, pas `real_project` : ce dernier est partagé (portée
    session) avec d'autres tests de ce fichier qui y écrivent des blueprints,
    et l'ordre d'exécution ne doit jamais décider si ce test passe.
    """
    payload = wa.blueprints_view(tmp_path)

    assert payload == {"count": 0, "blueprints": []}


def test_un_blueprint_reel_porte_son_genre_et_sa_date_de_modification(
    project_with_blueprint: tuple[Path, str],
) -> None:
    """Sans `modified_at`, la colonne « dernière modification » de la Liste
    n'aurait rien à montrer — et sans le genre, le Board n'aurait qu'une
    colonne, quel que soit le projet."""
    root, bp_id = project_with_blueprint

    payload = wa.blueprints_view(root)

    assert payload["count"] == 1
    entry = payload["blueprints"][0]
    assert entry["id"] == bp_id
    assert entry["type"] == "blueprint"
    assert entry["genre"] == "blueprint", "un blueprint v1 (le template pipeline) n'est pas du Studio"
    assert entry["nodes"] >= 1
    assert entry["modified_at"], "la Liste ne peut pas afficher une modification jamais mesurée"
    assert entry["validated"] is False, "un blueprint neuf n'a jamais été marqué validé"


def test_un_blueprint_studio_est_distingue_d_un_blueprint_classique(
    real_project: Path,
) -> None:
    """`blueprintVersion: 2` (ou des nœuds sans `pins`) est un blueprint du
    Studio : le Board doit pouvoir le grouper à part d'un v1 classique."""
    blueprints_dir = real_project / "_grimoire" / "blueprints"
    blueprints_dir.mkdir(parents=True, exist_ok=True)
    (blueprints_dir / "studio-demo.blueprint.json").write_text(
        json.dumps(
            {
                "blueprintVersion": 2,
                "id": "studio-demo",
                "name": "Studio demo",
                "nodes": [{"id": "a", "kind": "pattern", "ref": "ORC-01", "label": "A"}],
                "edges": [],
            }
        ),
        encoding="utf-8",
    )

    payload = wa.blueprints_view(real_project)

    entry = next(b for b in payload["blueprints"] if b["id"] == "studio-demo")
    assert entry["genre"] == "studio"


def test_les_agents_delegues_sont_les_ids_d_extension_distincts(real_project: Path) -> None:
    """La colonne « agents » vient des nœuds `extension-node` réellement
    présents — jamais inventée quand aucun n'est déclaré."""
    blueprints_dir = real_project / "_grimoire" / "blueprints"
    blueprints_dir.mkdir(parents=True, exist_ok=True)
    (blueprints_dir / "delegue.blueprint.json").write_text(
        json.dumps(
            {
                "blueprintVersion": 1,
                "id": "delegue",
                "name": "Délégué",
                "nodes": [
                    {"id": "crew", "kind": "extension-node", "ref": "crewai/crewai-crew", "label": "Crew", "pins": []},
                    {"id": "crew2", "kind": "extension-node", "ref": "crewai/other-node", "label": "Crew 2", "pins": []},
                    {"id": "plan", "kind": "pattern", "ref": "ORC-01", "label": "Plan", "pins": []},
                ],
                "edges": [],
            }
        ),
        encoding="utf-8",
    )

    payload = wa.blueprints_view(real_project)

    entry = next(b for b in payload["blueprints"] if b["id"] == "delegue")
    assert entry["agents"] == ["crewai"], "un même id d'extension ne doit apparaître qu'une fois"


def test_un_blueprint_illisible_n_empeche_pas_les_autres_de_s_afficher(
    project_with_blueprint: tuple[Path, str],
) -> None:
    """Un JSON cassé à côté d'un blueprint valide ne doit pas faire
    disparaître ce dernier de la Liste — même défaut que `flows` évite déjà."""
    root, bp_id = project_with_blueprint
    broken = root / "_grimoire" / "blueprints" / "casse.blueprint.json"
    broken.write_text("{ ceci n'est pas du JSON", encoding="utf-8")

    payload = wa.blueprints_view(root)

    ids = {b["id"] for b in payload["blueprints"]}
    assert bp_id in ids
    assert "casse" not in ids
