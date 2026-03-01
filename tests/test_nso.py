#!/usr/bin/env python3
"""
Tests pour nso.py — Nervous System Orchestrator.

Fonctions testées :
  - _load_tool()
  - _run_dream(), _run_stigmergy(), _run_antifragile(), _run_darwinism(), _run_memory_lint()
  - run_nso()
  - render_report()
  - report_to_dict()
  - PhaseResult, NSOReport dataclasses
"""

import importlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

KIT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(KIT_DIR / "framework" / "tools"))


def _import_nso():
    return importlib.import_module("nso")


# ── Tests data classes ────────────────────────────────────────────────────────

class TestPhaseResult(unittest.TestCase):
    def setUp(self):
        self.mod = _import_nso()

    def test_defaults(self):
        pr = self.mod.PhaseResult(name="test", status="ok")
        self.assertEqual(pr.duration_ms, 0)
        self.assertEqual(pr.summary, "")
        self.assertEqual(pr.data, {})
        self.assertEqual(pr.error, "")


class TestNSOReport(unittest.TestCase):
    def setUp(self):
        self.mod = _import_nso()

    def test_empty_report(self):
        report = self.mod.NSOReport()
        self.assertEqual(report.ok_count, 0)
        self.assertEqual(report.error_count, 0)

    def test_counts(self):
        report = self.mod.NSOReport()
        report.phases = [
            self.mod.PhaseResult(name="a", status="ok"),
            self.mod.PhaseResult(name="b", status="ok"),
            self.mod.PhaseResult(name="c", status="error"),
            self.mod.PhaseResult(name="d", status="skip"),
        ]
        self.assertEqual(report.ok_count, 2)
        self.assertEqual(report.error_count, 1)


# ── Tests _load_tool ──────────────────────────────────────────────────────────

class TestLoadTool(unittest.TestCase):
    def setUp(self):
        self.mod = _import_nso()

    def test_loads_dream(self):
        tool = self.mod._load_tool("dream")
        self.assertIsNotNone(tool)
        self.assertTrue(hasattr(tool, "dream"))

    def test_loads_stigmergy(self):
        tool = self.mod._load_tool("stigmergy")
        self.assertIsNotNone(tool)
        self.assertTrue(hasattr(tool, "load_board"))

    def test_nonexistent_tool_returns_none(self):
        tool = self.mod._load_tool("nonexistent-tool-xyz")
        self.assertIsNone(tool)

    def test_loads_memory_lint(self):
        tool = self.mod._load_tool("memory-lint")
        self.assertIsNotNone(tool)
        self.assertTrue(hasattr(tool, "lint_memory"))


# ── Tests individual phase runners ────────────────────────────────────────────

class TestRunDream(unittest.TestCase):
    def setUp(self):
        self.mod = _import_nso()
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_empty_project_ok(self):
        result = self.mod._run_dream(self.tmpdir)
        self.assertEqual(result.status, "ok")
        self.assertIn("source", result.summary.lower())

    def test_quick_mode(self):
        result = self.mod._run_dream(self.tmpdir, quick=True)
        self.assertEqual(result.status, "ok")


class TestRunStigmergy(unittest.TestCase):
    def setUp(self):
        self.mod = _import_nso()
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_empty_board_ok(self):
        result = self.mod._run_stigmergy(self.tmpdir)
        self.assertEqual(result.status, "ok")
        self.assertIn("active", result.data)

    def test_returns_phase_result(self):
        result = self.mod._run_stigmergy(self.tmpdir)
        self.assertIsInstance(result, self.mod.PhaseResult)
        self.assertEqual(result.name, "stigmergy")


class TestRunAntifragile(unittest.TestCase):
    def setUp(self):
        self.mod = _import_nso()
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_returns_phase_result(self):
        result = self.mod._run_antifragile(self.tmpdir)
        self.assertIsInstance(result, self.mod.PhaseResult)
        # May be ok or error depending on data availability
        self.assertIn(result.status, ("ok", "error", "skip"))


class TestRunDarwinism(unittest.TestCase):
    def setUp(self):
        self.mod = _import_nso()
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_returns_phase_result(self):
        result = self.mod._run_darwinism(self.tmpdir)
        self.assertIsInstance(result, self.mod.PhaseResult)
        self.assertIn(result.status, ("ok", "error", "skip"))


class TestRunMemoryLint(unittest.TestCase):
    def setUp(self):
        self.mod = _import_nso()
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_empty_project_ok(self):
        result = self.mod._run_memory_lint(self.tmpdir)
        self.assertEqual(result.status, "ok")
        self.assertIn("entr", result.summary.lower())


# ── Tests run_nso orchestration ───────────────────────────────────────────────

class TestRunNSO(unittest.TestCase):
    def setUp(self):
        self.mod = _import_nso()
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_runs_all_phases(self):
        report = self.mod.run_nso(self.tmpdir)
        self.assertEqual(len(report.phases), 5)
        phase_names = [p.name for p in report.phases]
        self.assertIn("dream", phase_names)
        self.assertIn("stigmergy", phase_names)
        self.assertIn("memory-lint", phase_names)

    def test_has_timestamp(self):
        report = self.mod.run_nso(self.tmpdir)
        self.assertNotEqual(report.timestamp, "")

    def test_total_duration_positive(self):
        report = self.mod.run_nso(self.tmpdir)
        self.assertGreater(report.total_duration_ms, 0)

    def test_quick_mode(self):
        report = self.mod.run_nso(self.tmpdir, quick=True)
        self.assertIsInstance(report, self.mod.NSOReport)


# ── Tests render_report ──────────────────────────────────────────────────────

class TestRenderReport(unittest.TestCase):
    def setUp(self):
        self.mod = _import_nso()

    def test_renders_table(self):
        report = self.mod.NSOReport(timestamp="2026-02-28 10:00")
        report.phases = [
            self.mod.PhaseResult(name="dream", status="ok",
                                 duration_ms=100, summary="3 insights"),
            self.mod.PhaseResult(name="stigmergy", status="ok",
                                 duration_ms=50, summary="5 actives"),
        ]
        text = self.mod.render_report(report)
        self.assertIn("dream", text)
        self.assertIn("stigmergy", text)
        self.assertIn("Nervous System", text)

    def test_shows_errors(self):
        report = self.mod.NSOReport()
        report.phases = [
            self.mod.PhaseResult(name="dream", status="error",
                                 error="boom"),
        ]
        text = self.mod.render_report(report)
        self.assertIn("boom", text)
        self.assertIn("Erreurs", text)


# ── Tests report_to_dict ─────────────────────────────────────────────────────

class TestReportToDict(unittest.TestCase):
    def setUp(self):
        self.mod = _import_nso()

    def test_dict_structure(self):
        report = self.mod.NSOReport(timestamp="2026-02-28")
        report.phases = [
            self.mod.PhaseResult(name="dream", status="ok",
                                 data={"insights": 3}),
        ]
        d = self.mod.report_to_dict(report)
        self.assertIn("version", d)
        self.assertIn("summary", d)
        self.assertIn("phases", d)
        self.assertIn("dream", d["phases"])
        self.assertEqual(d["phases"]["dream"]["data"]["insights"], 3)

    def test_version_present(self):
        d = self.mod.report_to_dict(self.mod.NSOReport())
        self.assertEqual(d["version"], "1.0.0")


# ── Tests constantes ─────────────────────────────────────────────────────────

class TestConstants(unittest.TestCase):
    def setUp(self):
        self.mod = _import_nso()

    def test_phases_list(self):
        self.assertEqual(len(self.mod.PHASES), 5)
        self.assertIn("dream", self.mod.PHASES)
        self.assertIn("memory-lint", self.mod.PHASES)


if __name__ == "__main__":
    unittest.main()
