"""Phase 1 tests for cas_native.inference.meta_logic_repair.

Coverage:
  - Parser: PartitionOf / CoverOf / Product, with various cluster
    counts and member shapes; returns None for non-meta-logic
    sources.
  - Relation-type repair: PartitionOf rendered as cover, CoverOf
    rendered as partition, Product mismatches; inflection
    preservation (partitions -> covers, partitioning -> covering,
    partitioned -> covered); case preservation.
  - No-op: source already correct, no relation word found.
  - Cluster cardinality: counted from rendered text, flagged when
    it disagrees with source (NOT rewritten).
  - Cluster member drift: per-cluster missing-indicator flagging,
    flag-only invariant.
"""
from __future__ import annotations

from cas_native.inference.meta_logic_repair import (
    ClusterMemberDrift,
    MetaLogicRelation,
    MetaLogicRepairLog,
    NoeticCluster,
    parse_meta_logic,
    repair_meta_logic_rendering,
)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def test_parse_partition_of_with_three_clusters():
    cas = (
        "PartitionOf(Noetics, NoeticCluster{^5}, "
        "NoeticCluster{^1, ^2, ^3, ^4, ^6, ^7, ^8, ^9}, "
        "NoeticCluster{^0})"
    )
    rel = parse_meta_logic(cas)
    assert rel is not None
    assert rel.relation_type == "PartitionOf"
    assert rel.universe == "Noetics"
    assert rel.cluster_count == 3
    assert rel.clusters[0].noetics == (5,)
    assert rel.clusters[1].noetics == (1, 2, 3, 4, 6, 7, 8, 9)
    assert rel.clusters[2].noetics == (0,)


def test_parse_cover_of_with_two_clusters():
    cas = (
        "CoverOf(Noetics, NoeticCluster{^1, ^2, ^3, ^4, ^5, ^6, ^7}, "
        "NoeticCluster{^0, ^4, ^8, ^9})"
    )
    rel = parse_meta_logic(cas)
    assert rel is not None
    assert rel.relation_type == "CoverOf"
    assert rel.universe == "Noetics"
    assert rel.cluster_count == 2


def test_parse_product_no_universe():
    cas = "Product(NoeticCluster{^5, ^9}, NoeticCluster{^0, ^1, ^9})"
    rel = parse_meta_logic(cas)
    assert rel is not None
    assert rel.relation_type == "Product"
    assert rel.universe is None
    assert rel.cluster_count == 2
    assert rel.clusters[0].noetics == (5, 9)
    assert rel.clusters[1].noetics == (0, 1, 9)


def test_parse_returns_none_for_non_meta_logic_sources():
    """The structural gate: state literals, rpm_chains, recipes,
    fractals, CRO must all return None so Phase 1 no-ops on them."""
    assert parse_meta_logic("^0^P|A") is None
    assert parse_meta_logic("let stageA = ^0^P; stageA -> stageB") is None
    assert parse_meta_logic("Θ(Ω_x) = 1*^7^O + 2*^6^C → Ω_x") is None
    assert parse_meta_logic("Φ<3:7:1>") is None
    assert parse_meta_logic("(^4^C|A × ^4^C|E) = ^4^C|Ω_clarity") is None


def test_parse_returns_none_when_no_clusters_found():
    """Defensive: a relation name with no NoeticCluster bodies isn't
    a usable parse — return None so Phase 1 doesn't touch it."""
    assert parse_meta_logic("PartitionOf(Noetics)") is None


# ---------------------------------------------------------------------------
# No-op contract
# ---------------------------------------------------------------------------

def test_repair_no_op_for_non_meta_logic_source():
    rendered = "Something that struck a chord."
    out, log = repair_meta_logic_rendering(
        source_cas="^4^C|A", rendered=rendered,
    )
    assert out == rendered
    assert log.relation_parsed is False
    assert log.n_repairs == 0


def test_repair_no_op_for_empty_rendered():
    cas = "Product(NoeticCluster{^5}, NoeticCluster{^0})"
    out, log = repair_meta_logic_rendering(source_cas=cas, rendered="")
    assert out == ""
    assert log.relation_parsed is False


# ---------------------------------------------------------------------------
# Relation-type repair (the core of Phase 1)
# ---------------------------------------------------------------------------

def test_repair_no_changes_when_relation_already_correct():
    cas = "PartitionOf(Noetics, NoeticCluster{^5}, NoeticCluster{^0})"
    rendered = "The set partitions into two groups: ..."
    out, log = repair_meta_logic_rendering(source_cas=cas, rendered=rendered)
    assert out == rendered
    assert log.relation_parsed is True
    assert log.relation_matched_pre_repair is True
    assert log.relation_matched_post_repair is True
    assert log.n_repairs == 0


def test_repair_cover_rendered_as_partition_record_18_pattern():
    """Audit's record-18 finding: source is CoverOf but rendered
    text says 'partition'. Phase 1 must rewrite to 'cover'."""
    cas = (
        "CoverOf(Noetics, NoeticCluster{^1, ^2, ^3}, "
        "NoeticCluster{^4, ^5, ^6})"
    )
    rendered = (
        "The complete set of ten ways of thinking partitions into "
        "two groups."
    )
    out, log = repair_meta_logic_rendering(source_cas=cas, rendered=rendered)
    assert "covers" in out
    assert "partitions" not in out
    assert log.relation_matched_pre_repair is False
    assert log.relation_matched_post_repair is True
    assert len(log.repairs) == 1
    assert log.repairs[0].kind == "relation_type"
    assert log.repairs[0].found_word == "partitions"
    assert log.repairs[0].new_word == "covers"


def test_repair_partition_rendered_as_cover():
    cas = "PartitionOf(Noetics, NoeticCluster{^5}, NoeticCluster{^0})"
    rendered = "The set covers two regions of thought."
    out, log = repair_meta_logic_rendering(source_cas=cas, rendered=rendered)
    assert "partitions" in out
    assert "covers" not in out
    assert log.repairs[0].new_word == "partitions"


def test_repair_product_rendered_as_partition():
    cas = "Product(NoeticCluster{^5, ^9}, NoeticCluster{^0, ^1})"
    rendered = "The relation partitions the noetics into two clusters."
    out, log = repair_meta_logic_rendering(source_cas=cas, rendered=rendered)
    # Product has no -s/-ed/-ing variants; Product takes "" or "s".
    # "partitions" -> the code keeps the suffix 's' so it becomes "products".
    assert "products" in out
    assert "partitions" not in out


def test_repair_preserves_ing_inflection():
    cas = "CoverOf(Noetics, NoeticCluster{^1}, NoeticCluster{^2})"
    rendered = "By partitioning into two regions..."
    out, log = repair_meta_logic_rendering(source_cas=cas, rendered=rendered)
    assert "covering" in out
    assert "partitioning" not in out


def test_repair_preserves_ed_inflection():
    cas = "CoverOf(Noetics, NoeticCluster{^1}, NoeticCluster{^2})"
    rendered = "The set was partitioned into two."
    out, log = repair_meta_logic_rendering(source_cas=cas, rendered=rendered)
    assert "covered" in out
    assert "partitioned" not in out


def test_repair_into_product_collapses_inflected_suffix():
    """Product has no -ed or -ing variants; coercion drops the suffix
    so we don't emit 'producting' or 'producted'."""
    cas = "Product(NoeticCluster{^5}, NoeticCluster{^0})"
    rendered = "By partitioning the noetics..."
    out, log = repair_meta_logic_rendering(source_cas=cas, rendered=rendered)
    assert "product" in out
    assert "partitioning" not in out
    assert "producting" not in out


def test_repair_preserves_capitalization():
    """If the wrong word starts a sentence (capitalized), the
    replacement must also be capitalized."""
    cas = "CoverOf(Noetics, NoeticCluster{^1}, NoeticCluster{^2})"
    rendered = "Partitions of this set fall into two groups."
    out, log = repair_meta_logic_rendering(source_cas=cas, rendered=rendered)
    assert "Covers" in out
    assert "Partitions" not in out


def test_repair_no_op_when_no_relation_word_found():
    """Rendered text without any relation word: log it as
    not-matched, don't synthesize one."""
    cas = "PartitionOf(Noetics, NoeticCluster{^5}, NoeticCluster{^0})"
    rendered = "Two distinct groupings of cognitive operations."
    out, log = repair_meta_logic_rendering(source_cas=cas, rendered=rendered)
    assert out == rendered
    assert log.relation_matched_pre_repair is False
    assert log.relation_matched_post_repair is False
    assert log.n_repairs == 0


# ---------------------------------------------------------------------------
# Cluster cardinality (flag-only)
# ---------------------------------------------------------------------------

def test_cluster_count_matches_when_rendered_text_says_correct_count():
    cas = (
        "PartitionOf(Noetics, NoeticCluster{^5}, "
        "NoeticCluster{^1, ^2}, NoeticCluster{^0})"
    )
    rendered = "The set partitions into three groups: ..."
    out, log = repair_meta_logic_rendering(source_cas=cas, rendered=rendered)
    assert log.expected_cluster_count == 3
    assert log.found_cluster_word_count == 3
    assert log.cluster_count_matches is True


def test_cluster_count_logged_when_rendered_says_wrong_count():
    """Phase 1 must FLAG cluster cardinality drift but NOT rewrite
    it. Audit's record-16 hint: source has 3 clusters, rendered
    might claim only 2 or describe one."""
    cas = (
        "PartitionOf(Noetics, NoeticCluster{^5}, "
        "NoeticCluster{^1, ^2}, NoeticCluster{^0})"
    )
    rendered = "The set partitions into two groups."
    out, log = repair_meta_logic_rendering(source_cas=cas, rendered=rendered)
    assert log.expected_cluster_count == 3
    assert log.found_cluster_word_count == 2
    assert log.cluster_count_matches is False
    # Phase 1 invariant: cluster count is FLAGGED, not rewritten.
    # The "two groups" phrase survives unchanged in the output.
    assert "two groups" in out


# ---------------------------------------------------------------------------
# Cluster membership (flag-only)
# ---------------------------------------------------------------------------

def test_member_drift_flagged_when_indicator_missing():
    """Source cluster contains ^9 (popped to mind) but rendered text
    has no "popped" / "just clicked" indicator anywhere. Flag-only."""
    cas = (
        "PartitionOf(Noetics, NoeticCluster{^9}, NoeticCluster{^0})"
    )
    rendered = (
        "The set partitions into two groups: a foundational thought "
        "and an idea about something else."
    )
    out, log = repair_meta_logic_rendering(source_cas=cas, rendered=rendered)
    assert len(log.member_drifts) >= 1
    # Cluster 0 expects ^9 -> "popped"; not present, so it's drifted.
    drift = next(d for d in log.member_drifts if d.cluster_index == 0)
    assert 9 in drift.expected_noetics


def test_member_drift_does_not_rewrite_text():
    """Phase 1 invariant: cluster member drift is FLAGGED, NEVER
    rewrites the rendered text."""
    cas = "PartitionOf(Noetics, NoeticCluster{^9}, NoeticCluster{^0})"
    rendered = (
        "The set partitions into two groups: a foundational thought "
        "and an idea about something else."
    )
    out, log = repair_meta_logic_rendering(source_cas=cas, rendered=rendered)
    # Output equals input — no rewriting happened despite drift logged.
    assert out == rendered


def test_no_member_drift_when_all_indicators_present():
    """When every source-cluster Noetic has at least one indicator
    in rendered text, no drift entry is emitted."""
    cas = "PartitionOf(Noetics, NoeticCluster{^9}, NoeticCluster{^0})"
    rendered = (
        "The set partitions into two groups: an idea that just clicked "
        "and a foundational thought."
    )
    out, log = repair_meta_logic_rendering(source_cas=cas, rendered=rendered)
    assert log.member_drifts == []


# ---------------------------------------------------------------------------
# Log structure
# ---------------------------------------------------------------------------

def test_log_to_dict_serializable():
    cas = (
        "CoverOf(Noetics, NoeticCluster{^1, ^2}, NoeticCluster{^9})"
    )
    rendered = "The set partitions into two groups."
    _, log = repair_meta_logic_rendering(source_cas=cas, rendered=rendered)
    d = log.to_dict()
    for key in [
        "relation_parsed", "expected_relation",
        "found_relation_pre_repair", "found_relation_post_repair",
        "relation_matched_pre_repair", "relation_matched_post_repair",
        "expected_cluster_count", "found_cluster_word_count",
        "cluster_count_matches", "n_repairs", "repairs",
        "n_member_drifts", "member_drifts",
    ]:
        assert key in d, key
    import json
    json.dumps(d)
