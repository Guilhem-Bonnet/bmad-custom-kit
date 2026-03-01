#!/usr/bin/env python3
"""
Tests pour dream.py — BMAD Dream Mode.

Fonctions testées :
  - collect_sources()
  - _parse_markdown_entries()
  - _parse_trace_entries()
  - _parse_shared_context_sections()
  - _extract_keywords()
  - _similarity()
  - find_cross_connections()
  - find_recurring_patterns()
  - find_tensions()
  - find_opportunities()
  - validate_insight()
  - deduplicate_insights()
  - dream()
  - render_journal()
  - write_journal()
  - DreamSource, DreamInsight dataclasses
"""

import importlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

KIT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(KIT_DIR / "framework" / "tools"))


def _import_dream():
    return importlib.import_module("dream")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_memory_tree(root: Path, learnings=None, decisions=None,
                        trace=None, failures=None, shared=None,
                        contradictions=None):
    """Créer un arbre mémoire minimal pour les tests."""
    mem = root / "_bmad" / "_memory"
    mem.mkdir(parents=True, exist_ok=True)

    if learnings:
        ld = mem / "agent-learnings"
        ld.mkdir(exist_ok=True)
        for name, content in learnings.items():
            (ld / name).write_text(content, encoding="utf-8")

    if decisions:
        (mem / "decisions-log.md").write_text(decisions, encoding="utf-8")

    if failures:
        (mem / "failure-museum.md").write_text(failures, encoding="utf-8")

    if shared:
        (mem / "shared-context.md").write_text(shared, encoding="utf-8")

    if contradictions:
        (mem / "contradiction-log.md").write_text(contradictions, encoding="utf-8")

    if trace:
        out = root / "_bmad-output"
        out.mkdir(parents=True, exist_ok=True)
        (out / "BMAD_TRACE.md").write_text(trace, encoding="utf-8")


# ── Test DreamSource / DreamInsight ───────────────────────────────────────────

class TestDataClasses(unittest.TestCase):
    def setUp(self):
        self.mod = _import_dream()

    def test_dream_source_defaults(self):
        src = self.mod.DreamSource(name="test.md", kind="learnings")
        self.assertEqual(src.entries, [])
        self.assertEqual(src.dates, [])

    def test_dream_insight_defaults(self):
        ins = self.mod.DreamInsight(
            title="t", description="d", sources=["a"],
            category="pattern", confidence=0.5,
        )
        self.assertEqual(ins.agents_relevant, [])
        self.assertFalse(ins.actionable)


# ── Test _parse_markdown_entries ──────────────────────────────────────────────

class TestParseMarkdownEntries(unittest.TestCase):
    def setUp(self):
        self.mod = _import_dream()
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_parses_dated_entries(self):
        f = self.tmpdir / "test.md"
        f.write_text(
            "# Learnings\n"
            "- [2025-01-15] Important learning about caching\n"
            "- [2025-01-20] Another learning about API design\n",
            encoding="utf-8",
        )
        entries = self.mod._parse_markdown_entries(f)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0][0], "2025-01-15")
        self.assertIn("caching", entries[0][1])

    def test_filters_by_since(self):
        f = self.tmpdir / "test.md"
        f.write_text(
            "- [2025-01-01] Old entry\n"
            "- [2025-06-01] New entry\n",
            encoding="utf-8",
        )
        entries = self.mod._parse_markdown_entries(f, since="2025-03-01")
        self.assertEqual(len(entries), 1)
        self.assertIn("New", entries[0][1])

    def test_handles_undated_entries(self):
        f = self.tmpdir / "test.md"
        f.write_text(
            "- entry without date\n"
            "* another entry\n",
            encoding="utf-8",
        )
        entries = self.mod._parse_markdown_entries(f)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0][0], "")  # no date

    def test_skips_headers_and_blanks(self):
        f = self.tmpdir / "test.md"
        f.write_text("# Header\n\n## Sub\n\n- Actual entry\n", encoding="utf-8")
        entries = self.mod._parse_markdown_entries(f)
        self.assertEqual(len(entries), 1)

    def test_missing_file(self):
        entries = self.mod._parse_markdown_entries(self.tmpdir / "nope.md")
        self.assertEqual(entries, [])

    def test_empty_file(self):
        f = self.tmpdir / "empty.md"
        f.write_text("", encoding="utf-8")
        entries = self.mod._parse_markdown_entries(f)
        self.assertEqual(entries, [])


# ── Test _parse_trace_entries ─────────────────────────────────────────────────

class TestParseTraceEntries(unittest.TestCase):
    def setUp(self):
        self.mod = _import_dream()
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_parses_standard_trace(self):
        f = self.tmpdir / "BMAD_TRACE.md"
        f.write_text(
            "[2025-06-01 10:00] [DECISION] [architect] Chose microservices arch\n"
            "[2025-06-01 10:05] [INFO] [dev] Starting implementation\n"
            "[2025-06-01 10:10] [CHECKPOINT] [pm] Sprint review done\n"
            "[2025-06-01 10:15] [FAILURE] [qa] Test suite broken\n",
            encoding="utf-8",
        )
        entries = self.mod._parse_trace_entries(f)
        # INFO is not included (only DECISION, CHECKPOINT, FAILURE, REMEMBER)
        self.assertEqual(len(entries), 3)

    def test_filters_by_agent(self):
        f = self.tmpdir / "trace.md"
        f.write_text(
            "[2025-06-01 10:00] [DECISION] [dev] Choice A\n"
            "[2025-06-01 10:05] [DECISION] [architect] Choice B\n",
            encoding="utf-8",
        )
        entries = self.mod._parse_trace_entries(f, agent_filter="dev")
        self.assertEqual(len(entries), 1)
        self.assertIn("dev", entries[0][1])

    def test_filters_by_since(self):
        f = self.tmpdir / "trace.md"
        f.write_text(
            "[2025-01-01 10:00] [DECISION] [dev] Old\n"
            "[2025-07-01 10:00] [DECISION] [dev] New\n",
            encoding="utf-8",
        )
        entries = self.mod._parse_trace_entries(f, since="2025-06-01")
        self.assertEqual(len(entries), 1)
        self.assertIn("New", entries[0][1])

    def test_missing_file(self):
        entries = self.mod._parse_trace_entries(self.tmpdir / "nope.md")
        self.assertEqual(entries, [])


# ── Test _parse_shared_context_sections ───────────────────────────────────────

class TestParseSharedContext(unittest.TestCase):
    def setUp(self):
        self.mod = _import_dream()

    def test_extracts_sections(self):
        content = (
            "## Section A\nContent A\n\n"
            "## Section B\nContent B line 1\nContent B line 2\n"
        )
        sections = self.mod._parse_shared_context_sections(content)
        self.assertEqual(len(sections), 2)
        self.assertIn("Section A", sections[0])
        self.assertIn("Content B line 1", sections[1])

    def test_empty_content(self):
        sections = self.mod._parse_shared_context_sections("")
        self.assertEqual(sections, [])

    def test_no_headers(self):
        content = "Just a plain paragraph\nwith no headers"
        sections = self.mod._parse_shared_context_sections(content)
        self.assertEqual(len(sections), 1)


# ── Test _extract_keywords ────────────────────────────────────────────────────

class TestExtractKeywords(unittest.TestCase):
    def setUp(self):
        self.mod = _import_dream()

    def test_removes_stopwords(self):
        kw = self.mod._extract_keywords("the api is in the database server")
        self.assertNotIn("the", kw)
        self.assertNotIn("is", kw)
        self.assertIn("api", kw)
        self.assertIn("database", kw)
        self.assertIn("server", kw)

    def test_ignores_short_words(self):
        kw = self.mod._extract_keywords("go do it up in db")
        # All words are < 3 chars → empty (db=2)
        for w in kw:
            self.assertGreaterEqual(len(w), 3)

    def test_case_insensitive(self):
        kw = self.mod._extract_keywords("PostgreSQL database")
        self.assertIn("postgresql", kw)
        self.assertIn("database", kw)

    def test_empty_string(self):
        kw = self.mod._extract_keywords("")
        self.assertEqual(kw, set())


# ── Test _similarity ──────────────────────────────────────────────────────────

class TestSimilarity(unittest.TestCase):
    def setUp(self):
        self.mod = _import_dream()

    def test_identical_texts(self):
        sim = self.mod._similarity("database caching layer", "database caching layer")
        self.assertEqual(sim, 1.0)

    def test_completely_different(self):
        sim = self.mod._similarity("database caching layer", "banana orange fruit")
        self.assertEqual(sim, 0.0)

    def test_partial_overlap(self):
        sim = self.mod._similarity(
            "database caching performance",
            "database indexing performance"
        )
        self.assertGreater(sim, 0.0)
        self.assertLess(sim, 1.0)

    def test_empty_text(self):
        sim = self.mod._similarity("", "something")
        self.assertEqual(sim, 0.0)


# ── Test collect_sources ──────────────────────────────────────────────────────

class TestCollectSources(unittest.TestCase):
    def setUp(self):
        self.mod = _import_dream()
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_collects_learnings(self):
        _create_memory_tree(self.tmpdir, learnings={
            "dev.md": "# Dev Learnings\n- [2025-06-01] Caching improves latency\n",
        })
        sources = self.mod.collect_sources(self.tmpdir)
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].kind, "learnings")
        self.assertEqual(len(sources[0].entries), 1)

    def test_collects_decisions(self):
        _create_memory_tree(self.tmpdir, decisions=(
            "# Decisions\n- [2025-06-01] Chose PostgreSQL for persistence\n"
        ))
        sources = self.mod.collect_sources(self.tmpdir)
        self.assertTrue(any(s.kind == "decisions" for s in sources))

    def test_collects_trace(self):
        _create_memory_tree(self.tmpdir, trace=(
            "[2025-06-01 10:00] [DECISION] [dev] Implemented caching\n"
        ))
        sources = self.mod.collect_sources(self.tmpdir)
        self.assertTrue(any(s.kind == "trace" for s in sources))

    def test_collects_failures(self):
        _create_memory_tree(self.tmpdir, failures=(
            "# Failure Museum\n- [2025-06-01] Cache invalidation bug\n"
        ))
        sources = self.mod.collect_sources(self.tmpdir)
        self.assertTrue(any(s.kind == "failure-museum" for s in sources))

    def test_collects_shared_context(self):
        _create_memory_tree(self.tmpdir, shared=(
            "## Current Arch\nMicroservices with Redis cache\n"
        ))
        sources = self.mod.collect_sources(self.tmpdir)
        self.assertTrue(any(s.kind == "shared-context" for s in sources))

    def test_collects_contradictions(self):
        _create_memory_tree(self.tmpdir, contradictions=(
            "# Contradictions\n- [2025-06-01] SQL vs NoSQL debate ongoing\n"
        ))
        sources = self.mod.collect_sources(self.tmpdir)
        self.assertTrue(any(s.kind == "contradictions" for s in sources))

    def test_agent_filter(self):
        _create_memory_tree(self.tmpdir, learnings={
            "dev.md": "- [2025-06-01] Dev learning\n",
            "architect.md": "- [2025-06-01] Arch learning\n",
        })
        sources = self.mod.collect_sources(self.tmpdir, agent_filter="dev")
        self.assertEqual(len(sources), 1)
        self.assertIn("dev", sources[0].name)

    def test_since_filter(self):
        _create_memory_tree(self.tmpdir, learnings={
            "dev.md": "- [2025-01-01] Old\n- [2025-07-01] New\n",
        })
        sources = self.mod.collect_sources(self.tmpdir, since="2025-06-01")
        self.assertEqual(len(sources), 1)
        self.assertEqual(len(sources[0].entries), 1)

    def test_empty_project(self):
        sources = self.mod.collect_sources(self.tmpdir)
        self.assertEqual(sources, [])

    def test_all_sources_combined(self):
        _create_memory_tree(
            self.tmpdir,
            learnings={"dev.md": "- [2025-06-01] L1\n"},
            decisions="- [2025-06-01] D1\n",
            trace="[2025-06-01 10:00] [DECISION] [dev] T1\n",
            failures="- [2025-06-01] F1\n",
            shared="## Ctx\nContent\n",
            contradictions="- [2025-06-01] C1\n",
        )
        sources = self.mod.collect_sources(self.tmpdir)
        self.assertEqual(len(sources), 6)
        kinds = {s.kind for s in sources}
        self.assertEqual(kinds, {
            "learnings", "decisions", "trace",
            "failure-museum", "shared-context", "contradictions",
        })


# ── Test find_cross_connections ───────────────────────────────────────────────

class TestFindCrossConnections(unittest.TestCase):
    def setUp(self):
        self.mod = _import_dream()

    def test_finds_connection_between_different_kinds(self):
        src_a = self.mod.DreamSource(
            name="learnings/dev.md", kind="learnings",
            entries=["database caching performance optimization layer"],
        )
        src_b = self.mod.DreamSource(
            name="decisions-log.md", kind="decisions",
            entries=["database caching performance optimization system"],
        )
        insights = self.mod.find_cross_connections([src_a, src_b])
        self.assertGreater(len(insights), 0)
        self.assertEqual(insights[0].category, "connection")

    def test_ignores_same_kind(self):
        src_a = self.mod.DreamSource(
            name="learnings/dev.md", kind="learnings",
            entries=["database caching"],
        )
        src_b = self.mod.DreamSource(
            name="learnings/arch.md", kind="learnings",
            entries=["database caching"],
        )
        insights = self.mod.find_cross_connections([src_a, src_b])
        self.assertEqual(len(insights), 0)

    def test_no_connection_different_topics(self):
        src_a = self.mod.DreamSource(
            name="learnings/dev.md", kind="learnings",
            entries=["banana smoothie recipe"],
        )
        src_b = self.mod.DreamSource(
            name="decisions-log.md", kind="decisions",
            entries=["kubernetes deployment strategy"],
        )
        insights = self.mod.find_cross_connections([src_a, src_b])
        self.assertEqual(len(insights), 0)

    def test_empty_sources(self):
        insights = self.mod.find_cross_connections([])
        self.assertEqual(insights, [])


# ── Test find_recurring_patterns ──────────────────────────────────────────────

class TestFindRecurringPatterns(unittest.TestCase):
    def setUp(self):
        self.mod = _import_dream()

    def test_detects_recurring_keyword(self):
        src_a = self.mod.DreamSource(
            name="learnings/dev.md", kind="learnings",
            entries=[
                "caching improved performance significantly",
                "added caching layer",
                "caching invalidation needs work",
            ],
        )
        src_b = self.mod.DreamSource(
            name="decisions-log.md", kind="decisions",
            entries=["implemented caching strategy for sessions"],
        )
        insights = self.mod.find_recurring_patterns([src_a, src_b])
        # "caching" should appear across 2 different source names with ≥3 total
        caching_found = any("caching" in i.title.lower() for i in insights)
        self.assertTrue(caching_found)

    def test_no_pattern_single_source(self):
        src = self.mod.DreamSource(
            name="a.md", kind="learnings",
            entries=["unique banana entry"],
        )
        insights = self.mod.find_recurring_patterns([src])
        self.assertEqual(insights, [])

    def test_empty_sources(self):
        insights = self.mod.find_recurring_patterns([])
        self.assertEqual(insights, [])


# ── Test find_tensions ────────────────────────────────────────────────────────

class TestFindTensions(unittest.TestCase):
    def setUp(self):
        self.mod = _import_dream()

    def test_detects_tension(self):
        src_a = self.mod.DreamSource(
            name="learnings/dev.md", kind="learnings",
            entries=["caching database layer optimization must always remain enabled"],
        )
        src_b = self.mod.DreamSource(
            name="failure-museum.md", kind="failure-museum",
            entries=["danger caching database layer optimization caused stale data"],
        )
        insights = self.mod.find_tensions([src_a, src_b])
        self.assertGreater(len(insights), 0)
        self.assertEqual(insights[0].category, "tension")

    def test_no_tension_in_same_source(self):
        src = self.mod.DreamSource(
            name="a.md", kind="learnings",
            entries=[
                "must always cache data",
                "avoid caching large datasets",
            ],
        )
        insights = self.mod.find_tensions([src])
        self.assertEqual(len(insights), 0)

    def test_no_tension_different_topics(self):
        src_a = self.mod.DreamSource(
            name="a.md", kind="learnings",
            entries=["must always validate input"],
        )
        src_b = self.mod.DreamSource(
            name="b.md", kind="decisions",
            entries=["danger from network latency"],
        )
        insights = self.mod.find_tensions([src_a, src_b])
        # Different topics so similarity < 0.3
        # (validate/input vs network/latency → no overlap)
        self.assertEqual(len(insights), 0)


# ── Test find_opportunities ───────────────────────────────────────────────────

class TestFindOpportunities(unittest.TestCase):
    def setUp(self):
        self.mod = _import_dream()

    def test_finds_todo(self):
        src = self.mod.DreamSource(
            name="learnings/dev.md", kind="learnings",
            entries=["TODO: refactor the caching layer"],
        )
        insights = self.mod.find_opportunities([src])
        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0].category, "opportunity")
        self.assertTrue(insights[0].actionable)

    def test_finds_improvement_markers(self):
        markers_entries = [
            "à améliorer: error handling",
            "could be better at logging",
            "not yet implemented: retry logic",
            "automatiser les tests de regression",
        ]
        src = self.mod.DreamSource(
            name="notes.md", kind="learnings",
            entries=markers_entries,
        )
        insights = self.mod.find_opportunities([src])
        self.assertEqual(len(insights), 4)

    def test_no_opportunities(self):
        src = self.mod.DreamSource(
            name="a.md", kind="learnings",
            entries=["Everything works perfectly fine"],
        )
        insights = self.mod.find_opportunities([src])
        self.assertEqual(insights, [])

    def test_one_marker_per_entry(self):
        """Even if entry has multiple markers, only one insight per entry."""
        src = self.mod.DreamSource(
            name="a.md", kind="learnings",
            entries=["TODO: automatiser simplifier le process"],
        )
        insights = self.mod.find_opportunities([src])
        self.assertEqual(len(insights), 1)


# ── Test validate_insight ─────────────────────────────────────────────────────

class TestValidateInsight(unittest.TestCase):
    def setUp(self):
        self.mod = _import_dream()
        self.sources = [
            self.mod.DreamSource(name="a.md", kind="learnings"),
            self.mod.DreamSource(name="b.md", kind="decisions"),
        ]

    def test_valid_insight(self):
        ins = self.mod.DreamInsight(
            title="Test", description="Valid description text here",
            sources=["a.md"], category="pattern", confidence=0.7,
        )
        self.assertTrue(self.mod.validate_insight(ins, self.sources))

    def test_no_sources(self):
        ins = self.mod.DreamInsight(
            title="T", description="Description text here",
            sources=[], category="pattern", confidence=0.5,
        )
        self.assertFalse(self.mod.validate_insight(ins, self.sources))

    def test_invalid_source_reference(self):
        ins = self.mod.DreamInsight(
            title="T", description="Description text here",
            sources=["nonexistent.md"], category="pattern", confidence=0.5,
        )
        self.assertFalse(self.mod.validate_insight(ins, self.sources))

    def test_zero_confidence(self):
        ins = self.mod.DreamInsight(
            title="T", description="Description texte",
            sources=["a.md"], category="pattern", confidence=0.0,
        )
        self.assertFalse(self.mod.validate_insight(ins, self.sources))

    def test_empty_description(self):
        ins = self.mod.DreamInsight(
            title="T", description="",
            sources=["a.md"], category="pattern", confidence=0.5,
        )
        self.assertFalse(self.mod.validate_insight(ins, self.sources))

    def test_short_description(self):
        ins = self.mod.DreamInsight(
            title="T", description="Short",
            sources=["a.md"], category="pattern", confidence=0.5,
        )
        self.assertFalse(self.mod.validate_insight(ins, self.sources))


# ── Test deduplicate_insights ─────────────────────────────────────────────────

class TestDeduplicateInsights(unittest.TestCase):
    def setUp(self):
        self.mod = _import_dream()

    def test_removes_duplicates(self):
        ins_a = self.mod.DreamInsight(
            title="A", description="database caching performance optimization layer strategy",
            sources=["a.md"], category="pattern", confidence=0.6,
        )
        ins_b = self.mod.DreamInsight(
            title="B", description="database caching performance optimization layer approach",
            sources=["b.md"], category="pattern", confidence=0.8,
        )
        result = self.mod.deduplicate_insights([ins_a, ins_b])
        self.assertEqual(len(result), 1)
        # Higher confidence kept
        self.assertEqual(result[0].confidence, 0.8)

    def test_keeps_different_insights(self):
        ins_a = self.mod.DreamInsight(
            title="A", description="database caching layer performance",
            sources=["a.md"], category="pattern", confidence=0.6,
        )
        ins_b = self.mod.DreamInsight(
            title="B", description="kubernetes deployment orchestration strategy",
            sources=["b.md"], category="connection", confidence=0.5,
        )
        result = self.mod.deduplicate_insights([ins_a, ins_b])
        self.assertEqual(len(result), 2)

    def test_empty_list(self):
        result = self.mod.deduplicate_insights([])
        self.assertEqual(result, [])


# ── Test dream() orchestrator ─────────────────────────────────────────────────

class TestDream(unittest.TestCase):
    def setUp(self):
        self.mod = _import_dream()
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_returns_empty_no_sources(self):
        result = self.mod.dream(self.tmpdir)
        self.assertEqual(result, [])

    def test_returns_insights_from_rich_data(self):
        _create_memory_tree(
            self.tmpdir,
            learnings={
                "dev.md": (
                    "- [2025-06-01] TODO: refactor caching layer\n"
                    "- [2025-06-02] caching improved performance database\n"
                    "- [2025-06-03] caching invalidation still problematic\n"
                ),
            },
            decisions=(
                "- [2025-06-01] Implemented caching strategy database sessions layer\n"
            ),
            failures=(
                "- [2025-06-01] caching caused stale data problem in database\n"
            ),
        )
        insights = self.mod.dream(self.tmpdir)
        self.assertGreater(len(insights), 0)
        # Should be sorted by confidence desc
        if len(insights) >= 2:
            self.assertGreaterEqual(insights[0].confidence, insights[1].confidence)

    def test_respects_max_insights(self):
        # Create many overlapping entries to generate lots of insights
        entries = "\n".join(
            f"- [2025-06-{i:02d}] TODO: refactor item {i} needs improvement"
            for i in range(1, 25)
        )
        _create_memory_tree(
            self.tmpdir,
            learnings={"dev.md": entries},
            decisions=entries.replace("TODO:", "Decided:"),
        )
        insights = self.mod.dream(self.tmpdir)
        self.assertLessEqual(len(insights), self.mod.MAX_INSIGHTS)

    def test_validation_filters_bad_insights(self):
        _create_memory_tree(
            self.tmpdir,
            learnings={"dev.md": "- [2025-06-01] small entry\n"},
        )
        # With validation on: insights with bad data should be filtered
        insights = self.mod.dream(self.tmpdir, do_validate=True)
        for ins in insights:
            self.assertGreater(ins.confidence, 0)
            self.assertGreater(len(ins.description), 0)

    def test_since_filter_propagates(self):
        _create_memory_tree(
            self.tmpdir,
            learnings={
                "dev.md": (
                    "- [2025-01-01] Old learning about caching database layer performance\n"
                    "- [2025-07-01] New learning about caching database layer optimization\n"
                ),
            },
        )
        insights_all = self.mod.dream(self.tmpdir, since=None, do_validate=False)
        insights_recent = self.mod.dream(self.tmpdir, since="2025-06-01", do_validate=False)
        # recent should have fewer or equal insights
        self.assertLessEqual(len(insights_recent), len(insights_all))


# ── Test render_journal ───────────────────────────────────────────────────────

class TestRenderJournal(unittest.TestCase):
    def setUp(self):
        self.mod = _import_dream()
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_renders_markdown(self):
        sources = [
            self.mod.DreamSource(name="a.md", kind="learnings", entries=["e1"]),
        ]
        insights = [
            self.mod.DreamInsight(
                title="Test Insight", description="Some description here",
                sources=["a.md"], category="pattern", confidence=0.8,
            ),
        ]
        md = self.mod.render_journal(insights, sources, self.tmpdir)
        self.assertIn("Dream Journal", md)
        self.assertIn("Test Insight", md)
        self.assertIn("pattern", md)
        self.assertIn("a.md", md)

    def test_includes_summary_table(self):
        sources = [self.mod.DreamSource(name="a.md", kind="learnings", entries=["e"])]
        insights = [
            self.mod.DreamInsight(
                title="T", description="D" * 20, sources=["a.md"],
                category="pattern", confidence=0.7,
            ),
        ]
        md = self.mod.render_journal(insights, sources, self.tmpdir)
        self.assertIn("Résumé", md)
        self.assertIn("Catégorie", md)

    def test_includes_since_info(self):
        sources = [self.mod.DreamSource(name="a.md", kind="learnings", entries=["e"])]
        insights = []
        md = self.mod.render_journal(insights, sources, self.tmpdir, since="2025-01-01")
        self.assertIn("2025-01-01", md)


# ── Test write_journal ────────────────────────────────────────────────────────

class TestWriteJournal(unittest.TestCase):
    def setUp(self):
        self.mod = _import_dream()
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_writes_file(self):
        content = "# Test Journal\nHello"
        path = self.mod.write_journal(content, self.tmpdir)
        self.assertTrue(path.exists())
        self.assertEqual(path.read_text(encoding="utf-8"), content)

    def test_creates_output_dir(self):
        deep = self.tmpdir / "sub" / "project"
        deep.mkdir(parents=True)
        content = "# Test"
        path = self.mod.write_journal(content, deep)
        self.assertTrue(path.exists())

    def test_archives_previous(self):
        # Write first journal
        self.mod.write_journal("First", self.tmpdir)
        # Write second — should archive first
        self.mod.write_journal("Second", self.tmpdir)
        journal_path = self.tmpdir / "_bmad-output" / "dream-journal.md"
        self.assertEqual(journal_path.read_text(encoding="utf-8"), "Second")
        archives = list((self.tmpdir / "_bmad-output" / "dream-archives").glob("*.md"))
        self.assertEqual(len(archives), 1)

    def test_dry_run_no_write(self, ):
        content = "# DryRun"
        path = self.mod.write_journal(content, self.tmpdir, dry_run=True)
        self.assertFalse(path.exists())


# ── Test dream_quick ──────────────────────────────────────────────────────────

class TestDreamQuick(unittest.TestCase):
    """Tests pour dream_quick() — mode rapide O(n)."""

    def setUp(self):
        self.mod = _import_dream()
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_returns_empty_no_sources(self):
        result = self.mod.dream_quick(self.tmpdir)
        self.assertEqual(result, [])

    def test_returns_insights_from_data(self):
        _create_memory_tree(
            self.tmpdir,
            learnings={
                "dev.md": (
                    "- [2025-06-01] TODO: refactor caching layer\n"
                    "- [2025-06-02] caching improved performance database\n"
                    "- [2025-06-03] caching invalidation still problematic\n"
                ),
            },
            decisions=(
                "- [2025-06-01] Implemented caching strategy database layer\n"
            ),
        )
        insights = self.mod.dream_quick(self.tmpdir)
        # May return 0 if data not rich enough, but function must not crash
        self.assertIsInstance(insights, list)

    def test_respects_quick_max(self):
        entries = "\n".join(
            f"- [2025-06-{i:02d}] TODO: refactor item {i} needs improvement"
            for i in range(1, 25)
        )
        _create_memory_tree(
            self.tmpdir,
            learnings={"dev.md": entries},
            decisions=entries.replace("TODO:", "Decided:"),
        )
        insights = self.mod.dream_quick(self.tmpdir)
        self.assertLessEqual(len(insights), self.mod.QUICK_MAX_INSIGHTS)

    def test_only_patterns_and_opportunities(self):
        """dream_quick ne doit retourner que des patterns et opportunities."""
        _create_memory_tree(
            self.tmpdir,
            learnings={
                "dev.md": (
                    "- [2025-06-01] caching layer needs refactor database\n"
                    "- [2025-06-02] caching performance database slow\n"
                    "- [2025-06-03] caching invalidation database problem\n"
                ),
            },
            decisions=(
                "- [2025-06-01] caching database strategy implemented\n"
            ),
        )
        insights = self.mod.dream_quick(self.tmpdir)
        for ins in insights:
            self.assertIn(ins.category, ("pattern", "opportunity"))

    def test_sorted_by_confidence_desc(self):
        entries = "\n".join(
            f"- [2025-06-{i:02d}] TODO: refactor item {i} caching performance"
            for i in range(1, 15)
        )
        _create_memory_tree(
            self.tmpdir,
            learnings={"dev.md": entries},
            decisions=entries.replace("TODO:", "Decided:"),
        )
        insights = self.mod.dream_quick(self.tmpdir)
        for i in range(len(insights) - 1):
            self.assertGreaterEqual(insights[i].confidence,
                                    insights[i + 1].confidence)

    def test_since_filter(self):
        _create_memory_tree(
            self.tmpdir,
            learnings={
                "dev.md": (
                    "- [2025-01-01] Old caching database layer performance\n"
                    "- [2025-07-01] New caching database layer optimization\n"
                ),
            },
        )
        all_ins = self.mod.dream_quick(self.tmpdir, since=None)
        recent = self.mod.dream_quick(self.tmpdir, since="2025-06-01")
        self.assertLessEqual(len(recent), len(all_ins))

    def test_agent_filter(self):
        _create_memory_tree(
            self.tmpdir,
            learnings={
                "dev.md": "- [2025-06-01] dev caching database\n",
                "qa.md": "- [2025-06-01] qa testing coverage\n",
            },
        )
        insights = self.mod.dream_quick(self.tmpdir, agent_filter="dev")
        self.assertIsInstance(insights, list)


# ── Test _INSIGHT_TO_PHEROMONE mapping ────────────────────────────────────────

class TestInsightToPheromone(unittest.TestCase):
    def setUp(self):
        self.mod = _import_dream()

    def test_mapping_keys(self):
        mapping = self.mod._INSIGHT_TO_PHEROMONE
        self.assertIn("tension", mapping)
        self.assertIn("opportunity", mapping)
        self.assertIn("connection", mapping)
        self.assertIn("pattern", mapping)

    def test_mapping_values_are_valid_pheromone_types(self):
        valid_types = {"NEED", "ALERT", "OPPORTUNITY", "PROGRESS", "COMPLETE", "BLOCK"}
        mapping = self.mod._INSIGHT_TO_PHEROMONE
        for value in mapping.values():
            self.assertIn(value, valid_types)


# ── Test emit_to_stigmergy ───────────────────────────────────────────────────

class TestEmitToStigmergy(unittest.TestCase):
    """Tests pour emit_to_stigmergy() — bridge dream → stigmergy."""

    def setUp(self):
        self.mod = _import_dream()
        self.tmpdir = Path(tempfile.mkdtemp())
        # Créer le dossier _bmad-output pour le board stigmergy
        (self.tmpdir / "_bmad-output").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_returns_zero_empty_list(self):
        count = self.mod.emit_to_stigmergy([], self.tmpdir)
        self.assertEqual(count, 0)

    def test_emits_pheromones_for_insights(self):
        insights = [
            self.mod.DreamInsight(
                title="Test Pattern",
                description="Recurring caching issue",
                sources=["dev.md"],
                category="pattern",
                confidence=0.7,
            ),
            self.mod.DreamInsight(
                title="Test Opportunity",
                description="Optimization opportunity",
                sources=["qa.md"],
                category="opportunity",
                confidence=0.8,
            ),
        ]
        count = self.mod.emit_to_stigmergy(insights, self.tmpdir)
        self.assertEqual(count, 2)

    def test_pheromone_board_saved(self):
        insights = [
            self.mod.DreamInsight(
                title="Saved Test",
                description="Should persist on board",
                sources=["dev.md"],
                category="tension",
                confidence=0.6,
            ),
        ]
        self.mod.emit_to_stigmergy(insights, self.tmpdir)
        # Verify board file was created
        board_file = self.tmpdir / "_bmad-output" / "pheromone-board.json"
        self.assertTrue(board_file.exists())

    def test_pheromone_has_dream_prefix(self):
        insights = [
            self.mod.DreamInsight(
                title="Prefix Test",
                description="Should have [dream] prefix",
                sources=["dev.md"],
                category="connection",
                confidence=0.5,
            ),
        ]
        self.mod.emit_to_stigmergy(insights, self.tmpdir)

        # Load board and check text prefix
        sg = importlib.import_module("stigmergy")
        board = sg.load_board(self.tmpdir)
        self.assertTrue(len(board.pheromones) > 0)
        for p in board.pheromones:
            self.assertTrue(p.text.startswith("[dream]"))

    def test_pheromone_has_auto_dream_tag(self):
        insights = [
            self.mod.DreamInsight(
                title="Tag Test",
                description="Should have auto-dream tag",
                sources=["system"],
                category="pattern",
                confidence=0.5,
            ),
        ]
        self.mod.emit_to_stigmergy(insights, self.tmpdir)

        sg = importlib.import_module("stigmergy")
        board = sg.load_board(self.tmpdir)
        for p in board.pheromones:
            self.assertIn("auto-dream", p.tags)

    def test_intensity_capped(self):
        insights = [
            self.mod.DreamInsight(
                title="Cap Test",
                description="Confidence 0.95 should be capped at 0.9",
                sources=["dev.md"],
                category="opportunity",
                confidence=0.95,
            ),
        ]
        self.mod.emit_to_stigmergy(insights, self.tmpdir)

        sg = importlib.import_module("stigmergy")
        board = sg.load_board(self.tmpdir)
        for p in board.pheromones:
            self.assertLessEqual(p.intensity, 0.9)

    def test_category_to_pheromone_type(self):
        """Chaque catégorie d'insight doit mapper vers le bon type phéromone."""
        sg = importlib.import_module("stigmergy")
        for category, expected_type in self.mod._INSIGHT_TO_PHEROMONE.items():
            # Fresh tmpdir per iteration to avoid accumulated state
            cat_dir = Path(tempfile.mkdtemp())
            (cat_dir / "_bmad-output").mkdir(parents=True, exist_ok=True)
            try:
                insights = [
                    self.mod.DreamInsight(
                        title=f"Test {category}",
                        description=f"Testing {category} mapping",
                        sources=["dev.md"],
                        category=category,
                        confidence=0.6,
                    ),
                ]
                count = self.mod.emit_to_stigmergy(insights, cat_dir)
                self.assertGreater(count, 0,
                                   f"emit should succeed for {category}")

                board = sg.load_board(cat_dir)
                self.assertTrue(len(board.pheromones) > 0,
                                f"board should have pheromones for {category}")
                last = board.pheromones[-1]
                self.assertEqual(last.pheromone_type, expected_type,
                                 f"{category} should map to {expected_type}")
            finally:
                shutil.rmtree(cat_dir, ignore_errors=True)

    def test_unknown_category_defaults_to_need(self):
        insights = [
            self.mod.DreamInsight(
                title="Unknown",
                description="Category not in mapping",
                sources=["dev.md"],
                category="unknown_cat",
                confidence=0.5,
            ),
        ]
        self.mod.emit_to_stigmergy(insights, self.tmpdir)

        sg = importlib.import_module("stigmergy")
        board = sg.load_board(self.tmpdir)
        self.assertEqual(board.pheromones[-1].pheromone_type, "NEED")


# ── Test QUICK_MAX_INSIGHTS constant ─────────────────────────────────────────

class TestQuickMaxInsights(unittest.TestCase):
    def test_constant_is_positive_int(self):
        mod = _import_dream()
        self.assertIsInstance(mod.QUICK_MAX_INSIGHTS, int)
        self.assertGreater(mod.QUICK_MAX_INSIGHTS, 0)

    def test_quick_max_less_than_max(self):
        mod = _import_dream()
        self.assertLess(mod.QUICK_MAX_INSIGHTS, mod.MAX_INSIGHTS)


if __name__ == "__main__":
    unittest.main()
