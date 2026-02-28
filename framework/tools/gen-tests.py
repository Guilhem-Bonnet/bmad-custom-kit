#!/usr/bin/env python3
"""
gen-tests.py — BM-29 : Test Scaffolding depuis les Acceptance Criteria du DNA
=============================================================================

Lit les `acceptance_criteria` déclarés dans un `archetype.dna.yaml` et génère
automatiquement un squelette de tests pour le framework cible.

Usage :
  python3 gen-tests.py --dna archetypes/web-app/archetype.dna.yaml --framework pytest
  python3 gen-tests.py --dna archetypes/infra-ops/archetype.dna.yaml --framework bats
  python3 gen-tests.py --dna archetypes/fix-loop/archetype.dna.yaml --output tests/

Frameworks supportés :
  pytest      Python pytest
  jest        JavaScript/TypeScript Jest
  bats        Bash Automated Testing System
  go-test     Go testing package
  rspec       Ruby RSpec
  vitest      Vite + Vitest (frontend)
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("⚠️  PyYAML requis : pip install pyyaml")
    sys.exit(1)


# ── Templates par framework ──────────────────────────────────────────────────

TEMPLATES = {
    "pytest": {
        "ext": ".py",
        "header": '''"""
Tests générés depuis {dna_path}
Archétype : {archetype_name} v{archetype_version}
Trait : {trait_name}
Généré le : {date}

⚠️  Squelette auto-généré — compléter les assertions et fixtures
"""
import pytest


''',
        "test_func": '''def test_{test_id}():
    """
    AC: {description}
    Enforcement: {enforcement}
    """
    # TODO: Implémenter le test
    # Contexte: {context}
    pytest.fail("Test non implémenté — AC: {description}")

''',
        "skip_soft": '''@pytest.mark.xfail(reason="Soft enforcement — recommandé mais non bloquant")
def test_{test_id}():
    """
    AC: {description}
    Enforcement: soft (non-bloquant)
    """
    # TODO: Implémenter la vérification
    pass

''',
    },

    "jest": {
        "ext": ".test.ts",
        "header": '''/**
 * Tests générés depuis {dna_path}
 * Archétype : {archetype_name} v{archetype_version}
 * Trait : {trait_name}
 * Généré le : {date}
 *
 * ⚠️  Squelette auto-généré — compléter les expects et mocks
 */

describe("{archetype_name} — {trait_name}", () => {{

''',
        "footer": "});\n",
        "test_func": '''  {skip}test("{test_id}: {description}", async () => {{
    // TODO: Implémenter le test
    // AC: {description}
    // Enforcement: {enforcement}
    // Contexte: {context}
    throw new Error("Test non implémenté");
  }});

''',
        "skip_soft": '  test.todo',
    },

    "bats": {
        "ext": ".bats",
        "header": '''#!/usr/bin/env bats
# Tests générés depuis {dna_path}
# Archétype : {archetype_name} v{archetype_version}
# Trait : {trait_name}
# Généré le : {date}
#
# ⚠️  Squelette auto-généré — compléter les assertions

''',
        "test_func": '''@test "{test_id}: {description}" {{
    # TODO: Implémenter le test
    # AC: {description}
    # Enforcement: {enforcement}
    skip "Test non implémenté"
}}

''',
    },

    "go-test": {
        "ext": "_test.go",
        "header": '''// Tests générés depuis {dna_path}
// Archétype : {archetype_name} v{archetype_version}
// Trait : {trait_name}
// Généré le : {date}
//
// ⚠️  Squelette auto-généré — compléter les assertions

package tests

import "testing"

''',
        "test_func": '''func Test_{test_id_pascal}(t *testing.T) {{
\t// AC: {description}
\t// Enforcement: {enforcement}
\t// Contexte: {context}
\tt.Skip("Test non implémenté — AC: {description}")
}}

''',
    },
}


# ── Utilitaires ──────────────────────────────────────────────────────────────

def to_snake(s: str) -> str:
    """Convertit une chaîne en snake_case pour les noms de fonctions."""
    return s.lower().replace(" ", "_").replace("-", "_").replace(":", "").replace("/", "_")[:60]


def to_pascal(s: str) -> str:
    """Convertit en PascalCase pour Go."""
    return "".join(w.capitalize() for w in s.replace("-", " ").replace("_", " ").split())[:60]


def load_dna(dna_path: str) -> dict:
    """Charge et valide un fichier archetype.dna.yaml."""
    path = Path(dna_path)
    if not path.exists():
        print(f"❌  Fichier DNA non trouvé : {dna_path}")
        sys.exit(1)

    with open(path) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        print(f"❌  Format DNA invalide dans {dna_path}")
        sys.exit(1)

    return data


def extract_ac_items(dna: dict) -> list[dict]:
    """
    Extrait les acceptance_criteria depuis un DNA.
    Cherche dans : traits[].acceptance_criteria[], constraints[], acceptance_criteria[]
    """
    items = []

    # Source 1 : acceptance_criteria directe au niveau racine
    for ac in dna.get("acceptance_criteria", []):
        items.append({
            "source": "root",
            "trait_name": dna.get("name", "root"),
            "id": ac.get("id", to_snake(ac.get("description", "unknown"))),
            "description": ac.get("description", ""),
            "enforcement": ac.get("enforcement", "hard"),
            "context": ac.get("context", ""),
            "triggers_on": ac.get("triggers_on", ["**/*"]),
        })

    # Source 2 : dans chaque trait
    for trait in dna.get("traits", []):
        for ac in trait.get("acceptance_criteria", []):
            items.append({
                "source": "trait",
                "trait_name": trait.get("name", "unknown-trait"),
                "id": ac.get("id", to_snake(ac.get("description", "unknown"))),
                "description": ac.get("description", ""),
                "enforcement": ac.get("enforcement", "hard"),
                "context": ac.get("context", trait.get("description", "")),
                "triggers_on": ac.get("triggers_on", ["**/*"]),
            })

    # Source 3 : dans les constraints (mappées en AC "hard")
    for constraint in dna.get("constraints", []):
        items.append({
            "source": "constraint",
            "trait_name": "constraints",
            "id": constraint.get("id", "unknown"),
            "description": constraint.get("description", ""),
            "enforcement": constraint.get("enforcement", "hard"),
            "context": f"Vérifié par: {constraint.get('checked_by', 'agent')}",
            "triggers_on": ["**/*"],
        })

    return items


def generate_tests(dna: dict, framework: str, output_dir: str, dna_path: str) -> list[str]:
    """Génère les fichiers de tests."""
    import datetime

    tmpl = TEMPLATES.get(framework)
    if not tmpl:
        print(f"❌  Framework non supporté : {framework}")
        print(f"   Supportés : {', '.join(TEMPLATES.keys())}")
        sys.exit(1)

    items = extract_ac_items(dna)

    if not items:
        print(f"⚠️  Aucun acceptance_criteria trouvé dans {dna_path}")
        print("   Ajoutez des sections `acceptance_criteria` dans vos traits ou contraintes.")
        return []

    # Grouper par trait
    by_trait: dict[str, list] = {}
    for item in items:
        trait = item["trait_name"]
        by_trait.setdefault(trait, []).append(item)

    generated_files = []
    os.makedirs(output_dir, exist_ok=True)

    archetype_name = dna.get("name", dna.get("id", "unknown"))
    archetype_version = dna.get("version", "1.0.0")
    date_str = datetime.date.today().isoformat()

    for trait_name, trait_items in by_trait.items():
        # Nom de fichier
        safe_trait = to_snake(trait_name)
        filename = f"test_{safe_trait}{tmpl['ext']}"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w") as f:
            # Header
            header = tmpl["header"].format(
                dna_path=dna_path,
                archetype_name=archetype_name,
                archetype_version=archetype_version,
                trait_name=trait_name,
                date=date_str,
            )
            f.write(header)

            # Tests
            for item in trait_items:
                test_id = to_snake(item["id"])
                test_id_pascal = to_pascal(item["id"])
                is_soft = item["enforcement"] == "soft"

                if framework == "go-test":
                    test_str = tmpl["test_func"].format(
                        test_id_pascal=test_id_pascal,
                        description=item["description"],
                        enforcement=item["enforcement"],
                        context=item["context"],
                    )
                elif framework == "jest":
                    skip = "test.skip(" if is_soft else ""
                    test_str = tmpl["test_func"].format(
                        test_id=test_id,
                        description=item["description"],
                        enforcement=item["enforcement"],
                        context=item["context"],
                        skip=skip,
                    )
                else:
                    # pytest, bats
                    if is_soft and "skip_soft" in tmpl:
                        test_str = tmpl["skip_soft"].format(
                            test_id=test_id,
                            description=item["description"],
                            enforcement=item["enforcement"],
                            context=item["context"],
                        )
                    else:
                        test_str = tmpl["test_func"].format(
                            test_id=test_id,
                            description=item["description"],
                            enforcement=item["enforcement"],
                            context=item["context"],
                        )

                f.write(test_str)

            # Footer si besoin (jest)
            if "footer" in tmpl:
                f.write(tmpl["footer"])

        generated_files.append(filepath)
        print(f"✅  Généré : {filepath} ({len(trait_items)} tests)")

    return generated_files


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Génère des squelettes de tests depuis les acceptance_criteria d'un DNA archétype BMAD",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples :
  python3 gen-tests.py --dna archetypes/web-app/archetype.dna.yaml --framework pytest
  python3 gen-tests.py --dna archetypes/infra-ops/archetype.dna.yaml --framework bats
  python3 gen-tests.py --dna archetypes/fix-loop/archetype.dna.yaml --output tests/fix-loop/

Ajoutez des acceptance_criteria dans votre DNA :
  traits:
    - name: "tdd-mandatory"
      acceptance_criteria:
        - id: "test-before-implement"
          description: "Les tests doivent être écrits AVANT l'implémentation"
          enforcement: "hard"
        """,
    )
    parser.add_argument("--dna", required=True, help="Chemin vers archetype.dna.yaml")
    parser.add_argument(
        "--framework",
        default="pytest",
        choices=list(TEMPLATES.keys()),
        help="Framework de test cible (défaut: pytest)",
    )
    parser.add_argument(
        "--output",
        default="tests/generated/",
        help="Dossier de sortie (défaut: tests/generated/)",
    )
    parser.add_argument(
        "--list-ac",
        action="store_true",
        help="Lister les AC trouvés sans générer de fichiers",
    )

    args = parser.parse_args()

    dna = load_dna(args.dna)
    items = extract_ac_items(dna)

    if args.list_ac:
        archetype_name = dna.get("name", dna.get("id", "unknown"))
        print(f"\n📋  Acceptance Criteria dans {args.dna}")
        print(f"    Archétype : {archetype_name}")
        print(f"    Total AC trouvés : {len(items)}\n")
        for item in items:
            enforcement_icon = "🔴" if item["enforcement"] == "hard" else "🟡"
            print(f"  {enforcement_icon} [{item['trait_name']}] {item['id']}")
            print(f"     {item['description']}")
        if not items:
            print("  (aucun — ajoutez des `acceptance_criteria` dans vos traits)")
        return

    print(f"\n🧪  Génération des tests depuis {args.dna}")
    print(f"    Framework : {args.framework}")
    print(f"    Output    : {args.output}\n")

    generated = generate_tests(dna, args.framework, args.output, args.dna)

    if generated:
        print(f"\n✅  {len(generated)} fichier(s) généré(s) dans {args.output}")
        print("\nProchaines étapes :")
        print("  1. Compléter les assertions dans chaque fonction de test")
        print("  2. Ajouter les fixtures / mocks nécessaires")
        print("  3. Lancer les tests : pytest/jest/bats selon votre framework")
        print("  4. Vérifier qu'ils ÉCHOUENT d'abord (TDD red phase)")
    else:
        print("⚠️  Aucun fichier généré. Vérifiez que votre DNA contient des `acceptance_criteria`.")
        print("   Lancez --list-ac pour inspecter le DNA.")


if __name__ == "__main__":
    main()
