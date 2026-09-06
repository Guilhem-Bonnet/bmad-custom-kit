"""Shared pytest fixtures for Grimoire-kit tests."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

# ── Path setup ────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "framework" / "tools"

#: Le vrai répertoire personnel, capturé à l'import de ce module — donc avant
#: que la fixture d'isolation ne détourne ``HOME``. C'est la seule référence
#: qui permette encore de prouver qu'un test n'a pas touché l'état réel.
REAL_HOME = Path.home()

#: Variables qui décident où le kit écrit son état hors projet. Elles sont
#: toutes détournées, mais aucune n'est le vrai garde-fou : ``HOME`` l'est.
#: Les poser explicitement rend la protection lisible et survit à un code qui
#: consulterait la variable sans passer par ``Path.home()``.
_USER_STATE_VARS = ("GRIMOIRE_COCKPIT_HOME", "GRIMOIRE_SHARED_HOME", "GRIMOIRE_EMBEDDING_CACHE")

#: Variables par lesquelles git redirige ses écritures. Elles sont posées dans
#: l'environnement de tout hook git, donc présentes dès que la suite tourne
#: depuis un `git commit` — le gate pre-commit, précisément. Un `git init`
#: dans un tmp_path crée alors le dépôt à `GIT_DIR`, et tout ce que le test
#: croit écrire dans son bac à sable atterrit dans le dépôt réel.
_GIT_REDIRECT_VARS = (
    "GIT_DIR",
    "GIT_COMMON_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_NAMESPACE",
    "GIT_PREFIX",
)


# ── Isolation de l'état utilisateur ───────────────────────────────────────────


@pytest.fixture(scope="session", autouse=True)
def _isolate_user_state(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    """Empêche la suite de tests d'écrire où que ce soit sous le vrai ``$HOME``.

    ``grimoire init`` enregistre le projet créé auprès du cockpit, sauf si
    ``GRIMOIRE_NO_COCKPIT`` est posé. Chaque test qui lançait ``init`` sans ce
    garde-fou ajoutait une entrée au registre de la machine, pointant vers un
    répertoire pytest éphémère. Constaté sur un poste de développement :
    **10 378 entrées mortes** pour un seul projet réel.

    Le garde-fou vit ici et non dans chaque fichier de test, parce qu'un
    garde-fou qu'il faut penser à écrire finit toujours par manquer quelque
    part. La première version de cette fixture n'a pourtant détourné qu'une
    variable, et la démonstration est arrivée tout de suite : la mémoire
    transverse a débarqué avec sa propre racine machine, ``~/.grimoire/shared``,
    protégée test par test — exactement le motif que cette fixture existait
    pour supprimer.

    D'où la bascule : ce n'est plus une liste de variables qui protège, c'est
    ``HOME`` lui-même. Toute racine dérivée de ``Path.home()``, présente ou à
    venir, tombe dans le répertoire temporaire sans que personne ait à y
    penser. Les variables du kit restent posées par-dessus, pour rester
    lisibles et pour couvrir un lecteur qui les consulterait directement.
    """
    home = tmp_path_factory.mktemp("user-home")
    with pytest.MonkeyPatch.context() as mp:
        # ``Path.home()`` lit ``HOME`` sur POSIX et ``USERPROFILE`` sur Windows.
        mp.setenv("HOME", str(home))
        mp.setenv("USERPROFILE", str(home))
        for name, subdir in (
            ("XDG_CACHE_HOME", "cache"),
            ("XDG_CONFIG_HOME", "config"),
            ("XDG_DATA_HOME", "data"),
            ("XDG_STATE_HOME", "state"),
        ):
            mp.setenv(name, str(home / subdir))
        for var in _USER_STATE_VARS:
            mp.setenv(var, str(home / ".grimoire" / var.removeprefix("GRIMOIRE_").lower()))
        # Troisième vecteur de redirection, après HOME et les racines du kit :
        # l'environnement git. Les retirer rend `git init` et `git rev-parse`
        # relatifs au répertoire courant, comme hors hook.
        for var in _GIT_REDIRECT_VARS:
            mp.delenv(var, raising=False)
        # Rich formate l'aide de la CLI à la largeur du terminal. Sous 80
        # colonnes — la valeur d'un runner CI — un nom d'option long est coupé
        # en deux, et une assertion `"--interactive" in result.output` échoue
        # pour une raison qui n'a rien à voir avec ce qu'elle teste. On fixe la
        # largeur pour que la sortie soit la même partout.
        mp.setenv("COLUMNS", "200")
        yield


@pytest.fixture(scope="session")
def real_home() -> Path:
    """Le vrai ``$HOME``, pour les tests qui doivent prouver qu'on n'y touche pas."""
    return REAL_HOME


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Absolute path to the Grimoire-kit project root."""
    return ROOT


@pytest.fixture(scope="session")
def tools_dir() -> Path:
    """Absolute path to framework/tools/."""
    return TOOLS


@pytest.fixture
def tmp_grimoire_memory(tmp_path: Path) -> Path:
    """Temporary project with _grimoire/_memory/ directory."""
    (tmp_path / "_grimoire" / "_memory").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def tmp_grimoire_project(tmp_path: Path) -> Path:
    """Temporary project with standard Grimoire directory structure."""
    (tmp_path / "_grimoire" / "_memory").mkdir(parents=True)
    (tmp_path / "_grimoire-output").mkdir(parents=True)
    (tmp_path / "framework" / "tools").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def init_project(tmp_path: Path) -> Path:
    """Fully initialised Grimoire project with valid config."""
    (tmp_path / "_grimoire" / "_memory").mkdir(parents=True)
    (tmp_path / "_grimoire-output").mkdir(parents=True)
    (tmp_path / "project-context.yaml").write_text(
        'project:\n  name: "test-project"\n'
        'memory:\n  backend: "local"\n'
        'agents:\n  archetype: "minimal"\n',
        encoding="utf-8",
    )
    return tmp_path


# ── Markers ───────────────────────────────────────────────────────────────────
# Markers are registered in pyproject.toml [tool.pytest.ini_options].
# Usage:
#   @pytest.mark.slow          — long-running tests
#   @pytest.mark.integration   — tests requiring external services
#   @pytest.mark.regression    — known regression tests


# ── Vue de travail (web/workspace/) ───────────────────────────────────────────
#
# Le projet jetable est **réellement** initialisé — ``grimoire init`` puis
# ``grimoire standard init --profile governed`` — et pas fabriqué à la main. Un
# faux projet ne prouverait rien de ce que la vue de travail lit : ni les étages
# du kit, ni les empreintes confrontées au catalogue des digests, ni le board
# gouverné, ni ce que ``doctor`` trouve. Environ une seconde, payée une fois par
# session.

import subprocess  # noqa: E402
import sys  # noqa: E402


def _grimoire(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "grimoire", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )


def _init_real_project(root: Path, name: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=str(root), check=False, capture_output=True)
    created = _grimoire(["init", ".", "-y", "--name", name], root)
    if not (root / "_grimoire" / "kit").is_dir():
        pytest.skip(f"`grimoire init` indisponible ici : {created.stderr[-400:]}")
    _grimoire(["standard", "init", "--profile", "governed"], root)


@pytest.fixture(scope="session")
def real_project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Un projet Grimoire réel, enrôlé au standard `governed`."""
    root = tmp_path_factory.mktemp("workspace-a") / "projet-a"
    _init_real_project(root, "projet-a")
    return root


@pytest.fixture(scope="session")
def second_project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Un second projet réel — il n'existe que pour prouver qu'on ne les confond pas."""
    root = tmp_path_factory.mktemp("workspace-b") / "projet-b"
    _init_real_project(root, "projet-b")
    return root


@pytest.fixture
def project_with_task(real_project: Path) -> Iterator[tuple[Path, str]]:
    """Le projet réel, avec une tâche ouverte au Mission Ledger.

    La tâche est créée par le CLI, donc elle passe par le ledger et le board
    comme n'importe quelle autre — c'est la seule façon d'obtenir un identifiant
    que ``task trace`` sait retrouver.
    """
    from grimoire.missions.service import TaskService

    if not TaskService(real_project).has_ledger:
        _grimoire(
            [
                "task", "add", "Vérifier la vue de travail",
                "-a", "Les six espaces s'ouvrent",
                "-a", "Aucune couleur hors tokens",
                "--owner", "winston",
            ],
            real_project,
        )
    tasks = TaskService(real_project).list_tasks()
    if not tasks:
        pytest.skip("`grimoire task add` n'a pas ouvert de tâche dans cet environnement")
    yield real_project, tasks[0].id


@pytest.fixture
def project_with_blueprint(real_project: Path) -> Iterator[tuple[Path, str]]:
    """Le projet réel, avec un blueprint multi-nœuds sous `_grimoire/blueprints/`.

    Créé par le CLI (`grimoire blueprint new --template pipeline`) plutôt
    qu'écrit à la main : c'est ce qui garantit un fichier que `blueprint
    validate`/`simulate`/`compile` savent lire, avec plusieurs nœuds connectés
    — un seul nœud isolé ne prouverait ni la mise en page en colonnes de
    l'espace Concevoir, ni le rendu des arêtes.
    """
    bp_id = "workspace-demo"
    target = real_project / "_grimoire" / "blueprints" / f"{bp_id}.blueprint.json"
    if not target.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        result = _grimoire(
            ["blueprint", "new", bp_id, "--out", str(target), "--template", "pipeline"],
            real_project,
        )
        if not target.is_file():
            pytest.skip(f"`grimoire blueprint new` n'a pas produit de fichier ici : {result.stderr[-400:]}")
    yield real_project, bp_id
