"""``docs/glossaire.md`` dérive de ``framework/glossary.yaml`` : un test le vérifie.

Spécification §3.2 : « la documentation en dérive ». Si quelqu'un modifie le
glossaire sans régénérer la page, ce test échoue en disant exactement la
commande qui répare — pas seulement « ça diverge ».
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "gen-glossaire-doc.py"
OUTPUT = ROOT / "docs" / "glossaire.md"


def _import_generator():
    spec = importlib.util.spec_from_file_location("gen_glossaire_doc", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["gen_glossaire_doc"] = module
    spec.loader.exec_module(module)
    return module


def test_docs_glossaire_est_a_jour() -> None:
    """Le remède, s'il échoue : `python scripts/gen-glossaire-doc.py`."""
    generator = _import_generator()

    rendered = generator.render()
    current = OUTPUT.read_text(encoding="utf-8")

    assert rendered == current, (
        "docs/glossaire.md est désynchronisé de framework/glossary.yaml — "
        "régénérez : python scripts/gen-glossaire-doc.py"
    )


def test_docs_glossaire_cite_chaque_entree_par_son_ancre() -> None:
    """Un terme lié pointe vers `#<id>` ; l'ancre doit exister dans la page."""
    generator = _import_generator()
    entries = generator._entries()

    text = OUTPUT.read_text(encoding="utf-8")
    manquantes = [e["id"] for e in entries if f"{{: #{e['id']} }}" not in text]

    assert not manquantes, f"ancres absentes de docs/glossaire.md : {manquantes}"


def test_docs_glossaire_est_reference_dans_mkdocs() -> None:
    mkdocs = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")

    assert "glossaire.md" in mkdocs, "docs/glossaire.md n'est référencé nulle part dans mkdocs.yml"
