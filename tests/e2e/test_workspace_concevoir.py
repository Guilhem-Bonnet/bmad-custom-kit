"""Harnais Playwright de l'espace Concevoir (lot 3).

Complète `tests/e2e/test_workspace_shell.py` (qui ne teste que l'ouverture des
six espaces, encore vides au moment où il a été écrit) avec ce que la spec §4
demande de l'espace Concevoir : les trois niveaux de zoom, les trois vues,
sélection → inspecteur, validation → dock, et l'inspecteur à quatre onglets du
niveau Nœud.

Le projet servi porte un vrai blueprint multi-nœuds (`project_with_blueprint`,
créé par `grimoire blueprint new --template pipeline` — voir
`tests/conftest.py`) : sans lui, la toile n'aurait qu'un état vide à montrer,
et aucun de ces mécanismes ne serait exerçable.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page

pytest.importorskip("playwright.sync_api", reason="playwright absent — harnais e2e ignoré")


@pytest.fixture
def concevoir(workspace: Page, project_with_blueprint: tuple[Path, str]) -> tuple[Page, str]:
    """La coque, avec un blueprint réel déjà sur disque, ouverte sur Concevoir."""
    _root, bp_id = project_with_blueprint
    workspace.evaluate("() => window.GrimoireWorkspace.goto('concevoir')")
    workspace.wait_for_function("() => window.GrimoireWorkspace.space === 'concevoir'")
    workspace.wait_for_selector(".cv-card", timeout=15_000)
    return workspace, bp_id


# ── Niveau Projet : trois vues, sélection → inspecteur ──────────────────────


def test_concevoir_s_ouvre_sur_le_blueprint_reel_du_projet(concevoir: tuple[Page, str]) -> None:
    page, bp_id = concevoir

    assert page.locator(".cv-card").count() >= 1
    assert bp_id in page.locator("#canvas").inner_text()
    assert "démo" not in page.locator("#canvas").inner_text().lower()


def test_les_trois_vues_sont_proposees_au_niveau_projet(concevoir: tuple[Page, str]) -> None:
    page, _ = concevoir

    labels = [b.strip() for b in page.locator("#view-seg button").all_inner_texts()]
    assert labels == ["Carte", "Board", "Liste"]


def test_la_vue_liste_montre_les_six_colonnes_de_la_spec(concevoir: tuple[Page, str]) -> None:
    page, _ = concevoir
    page.locator('#view-seg button[data-value="liste"]').click()
    page.wait_for_selector("table.cv-table")

    headers = [h.strip() for h in page.locator("table.cv-table th").all_inner_texts()]
    assert headers == ["Nom", "Genre", "Agents", "Équipe", "Validation", "Dernière modification"]


def test_la_vue_board_groupe_par_genre(concevoir: tuple[Page, str]) -> None:
    page, _ = concevoir
    page.locator('#view-seg button[data-value="board"]').click()
    page.wait_for_selector(".cv-board-col")

    assert page.locator(".cv-board-col").count() >= 1


def test_la_selection_d_un_container_remplit_l_inspecteur(concevoir: tuple[Page, str]) -> None:
    page, bp_id = concevoir
    page.locator(".cv-card").first.click()

    page.wait_for_function(
        "(id) => document.getElementById('inspector-body').innerText.includes(id)", arg=bp_id
    )
    assert "Genre" in page.locator("#inspector-body").inner_text()


# ── Zoom Projet → Workflow : l'éditeur de graphe ────────────────────────────


def test_le_double_clic_zoome_sur_le_workflow_et_dessine_le_graphe(concevoir: tuple[Page, str]) -> None:
    page, _bp_id = concevoir
    page.locator(".cv-card").first.dblclick()

    page.wait_for_selector(".cv-node", timeout=15_000)

    assert page.locator('#zoom-seg button[aria-pressed="true"]').inner_text().strip() == "Workflow"
    assert page.locator(".cv-node").count() >= 1
    assert page.locator(".cv-svg path").count() >= 1, "un template `pipeline` a au moins une arête"


def test_valider_ecrit_le_verdict_dans_le_dock_problemes(concevoir: tuple[Page, str]) -> None:
    page, _ = concevoir
    page.locator(".cv-card").first.dblclick()
    page.wait_for_selector(".cv-node", timeout=15_000)

    page.get_by_role("button", name="Valider").click()
    page.wait_for_function(
        "() => document.querySelector('[data-dock-tab=\"problemes\"]').getAttribute('aria-selected') === 'true'"
    )
    dock_text = page.locator("#dock-body").inner_text()
    assert "blueprint validate" in dock_text


def test_la_bibliotheque_de_noeuds_liste_les_sept_primitives(concevoir: tuple[Page, str]) -> None:
    page, _ = concevoir
    page.locator(".cv-card").first.dblclick()
    page.wait_for_selector(".cv-node", timeout=15_000)

    # Scopé à la barre d'outils : le rail de la coque porte lui aussi un
    # bouton « Bibliothèque » (raccourci 2, non câblé — voir le module),
    # et `get_by_role` ferait sinon une correspondance ambiguë.
    page.locator(".cv-toolbar").get_by_role("button", name="Bibliothèque").click()
    page.wait_for_selector(".cv-prim", timeout=10_000)

    assert page.locator(".cv-prim").count() == 7


# ── Zoom Workflow → Nœud : inspecteur à quatre onglets ──────────────────────


def test_le_niveau_noeud_montre_un_inspecteur_a_quatre_onglets(concevoir: tuple[Page, str]) -> None:
    page, _ = concevoir
    page.locator(".cv-card").first.dblclick()
    page.wait_for_selector(".cv-node", timeout=15_000)
    page.locator(".cv-node").first.dblclick()

    page.wait_for_function(
        "() => document.querySelector('#zoom-seg button[aria-pressed=\"true\"]').textContent.trim() === 'Nœud'"
    )
    tabs = [t.strip() for t in page.locator(".cv-tab").all_inner_texts()]
    assert tabs == ["Propriétés", "Validation", "Coût", "Preuves"]


def test_les_quatre_onglets_du_noeud_changent_le_contenu_affiche(concevoir: tuple[Page, str]) -> None:
    page, _ = concevoir
    page.locator(".cv-card").first.dblclick()
    page.wait_for_selector(".cv-node", timeout=15_000)
    page.locator(".cv-node").first.dblclick()
    page.wait_for_selector(".cv-tab")

    first_panel = page.locator(".cv-tab-body").inner_text()
    page.get_by_role("button", name="Coût").click()
    page.wait_for_function(
        "(prev) => document.querySelector('.cv-tab-body').innerText !== prev", arg=first_panel
    )


# ── Critère 2, sur l'écran que ce lot ajoute ────────────────────────────────
#
# `test_workspace_shell.py` mesure le plancher sur l'espace par défaut
# (Piloter) : il ne verrait jamais un `font-size` posé en dur dans la toile de
# Concevoir. C'était le cas de `.cv-node .kind` avant correction — trouvé ici,
# pas à la lecture de la feuille.


def test_aucun_texte_du_graphe_sous_le_plancher_sombre(concevoir: tuple[Page, str]) -> None:
    page, _ = concevoir
    page.locator(".cv-card").first.dblclick()
    page.wait_for_selector(".cv-node", timeout=15_000)

    sizes = page.eval_on_selector_all(
        "#canvas .cv-node, #canvas .cv-node *",
        "(els) => els.map((el) => parseFloat(getComputedStyle(el).fontSize))",
    )
    assert sizes, "aucun texte mesuré dans le graphe"
    assert min(sizes) >= 13.0, f"un texte du graphe rend sous le plancher sombre : {min(sizes)}px"
