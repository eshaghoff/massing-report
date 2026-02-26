"""Tests for the assemblage engine."""

from __future__ import annotations

import pytest
from shapely.geometry import box, Polygon
import json

from app.models.schemas import LotProfile, PlutoData, ZoningEnvelope
from app.zoning_engine.assemblage import (
    validate_contiguity,
    merge_lots,
    calculate_delta,
    identify_key_unlocks,
    analyze_assemblage,
    AssemblageDelta,
    ScenarioDelta,
)
from app.zoning_engine.calculator import ZoningCalculator


# ──────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────

def _make_lot(
    bbl: str,
    block: int,
    lot_num: int,
    area: float = 2500,
    frontage: float = 25,
    depth: float = 100,
    district: str = "R6",
    lot_type: str = "interior",
    geometry: dict | None = None,
    borough: int = 3,
    address: str | None = None,
) -> LotProfile:
    """Create a test LotProfile."""
    pluto = PlutoData(
        bbl=bbl,
        address=address or f"{lot_num} Test St",
        zonedist1=district,
        lotarea=area,
        lotfront=frontage,
        lotdepth=depth,
    )
    return LotProfile(
        bbl=bbl,
        borough=borough,
        block=block,
        lot=lot_num,
        pluto=pluto,
        geometry=geometry,
        zoning_districts=[district],
        lot_area=area,
        lot_frontage=frontage,
        lot_depth=depth,
        lot_type=lot_type,
        street_width="narrow",
    )


def _make_adjacent_geometry(
    lot1_x: float = 0,
    lot1_width: float = 25,
    lot2_width: float = 25,
    depth: float = 100,
) -> tuple[dict, dict]:
    """Create GeoJSON geometry for two adjacent rectangular lots.

    Lot 1 is at x=[lot1_x, lot1_x+lot1_width], y=[0, depth]
    Lot 2 is at x=[lot1_x+lot1_width, lot1_x+lot1_width+lot2_width], y=[0, depth]
    """
    poly1 = box(lot1_x, 0, lot1_x + lot1_width, depth)
    poly2 = box(lot1_x + lot1_width, 0, lot1_x + lot1_width + lot2_width, depth)
    return (
        json.loads(json.dumps(poly1.__geo_interface__)),
        json.loads(json.dumps(poly2.__geo_interface__)),
    )


def _make_through_lot_geometry(
    width: float = 25,
    depth1: float = 100,
    depth2: float = 100,
) -> tuple[dict, dict]:
    """Create two lots that together form a through lot (back-to-back).

    Lot 1: y=[0, depth1], Lot 2: y=[depth1, depth1+depth2]
    """
    poly1 = box(0, 0, width, depth1)
    poly2 = box(0, depth1, width, depth1 + depth2)
    return (
        json.loads(json.dumps(poly1.__geo_interface__)),
        json.loads(json.dumps(poly2.__geo_interface__)),
    )


# ──────────────────────────────────────────────────────────────────
# CONTIGUITY TESTS
# ──────────────────────────────────────────────────────────────────

class TestContiguityValidation:
    """Test contiguity validation."""

    def test_adjacent_lots_with_geometry(self):
        """Two adjacent lots with shared boundary → contiguous."""
        geom1, geom2 = _make_adjacent_geometry()
        lot1 = _make_lot("3012340001", 1234, 1, geometry=geom1)
        lot2 = _make_lot("3012340002", 1234, 2, geometry=geom2)
        ok, method, msg = validate_contiguity([lot1, lot2])
        assert ok is True
        assert method == "geometry"

    def test_non_contiguous_lots_with_geometry(self):
        """Two lots with gap between them → not contiguous."""
        poly1 = box(0, 0, 25, 100)
        poly2 = box(100, 0, 125, 100)  # 75 ft gap
        geom1 = json.loads(json.dumps(poly1.__geo_interface__))
        geom2 = json.loads(json.dumps(poly2.__geo_interface__))
        lot1 = _make_lot("3012340001", 1234, 1, geometry=geom1)
        lot2 = _make_lot("3012340099", 1234, 99, geometry=geom2)
        ok, method, msg = validate_contiguity([lot1, lot2])
        assert ok is False
        assert "not contiguous" in msg.lower() or "not contiguous" in msg

    def test_three_lots_contiguous(self):
        """Three lots in a row → all contiguous."""
        poly1 = box(0, 0, 25, 100)
        poly2 = box(25, 0, 50, 100)
        poly3 = box(50, 0, 75, 100)
        g1 = json.loads(json.dumps(poly1.__geo_interface__))
        g2 = json.loads(json.dumps(poly2.__geo_interface__))
        g3 = json.loads(json.dumps(poly3.__geo_interface__))
        lot1 = _make_lot("3012340001", 1234, 1, geometry=g1)
        lot2 = _make_lot("3012340002", 1234, 2, geometry=g2)
        lot3 = _make_lot("3012340003", 1234, 3, geometry=g3)
        ok, method, msg = validate_contiguity([lot1, lot2, lot3])
        assert ok is True

    def test_block_adjacency_fallback(self):
        """Without geometry, uses block + lot number adjacency."""
        lot1 = _make_lot("3012340001", 1234, 1)
        lot2 = _make_lot("3012340002", 1234, 2)
        ok, method, msg = validate_contiguity([lot1, lot2])
        assert ok is True
        assert method == "block_adjacency"

    def test_block_adjacency_large_gap(self):
        """Lot numbers with large gap → likely not contiguous."""
        lot1 = _make_lot("3012340001", 1234, 1)
        lot2 = _make_lot("3012340050", 1234, 50)
        ok, method, msg = validate_contiguity([lot1, lot2])
        assert ok is False


# ──────────────────────────────────────────────────────────────────
# LOT MERGING TESTS
# ──────────────────────────────────────────────────────────────────

class TestLotMerging:
    """Test lot merging functionality."""

    def test_merge_two_interior_lots(self):
        """Merge two interior lots → area sums, frontage sums."""
        lot1 = _make_lot("3012340001", 1234, 1, area=2500, frontage=25, depth=100)
        lot2 = _make_lot("3012340002", 1234, 2, area=2500, frontage=25, depth=100)
        merged, warnings = merge_lots([lot1, lot2])
        assert merged.lot_area == 5000
        assert merged.lot_frontage == 50
        assert merged.lot_depth == 100
        assert "R6" in merged.zoning_districts

    def test_merge_preserves_wider_street(self):
        """Merged lot uses widest street width."""
        lot1 = _make_lot("3012340001", 1234, 1)
        lot1.street_width = "narrow"
        lot2 = _make_lot("3012340002", 1234, 2)
        lot2.street_width = "wide"
        merged, _ = merge_lots([lot1, lot2])
        assert merged.street_width == "wide"

    def test_merge_detects_split_zone(self):
        """Lots in different districts → split-zoned warning."""
        lot1 = _make_lot("3012340001", 1234, 1, district="R6")
        lot2 = _make_lot("3012340002", 1234, 2, district="R7A")
        merged, warnings = merge_lots([lot1, lot2])
        assert merged.split_zone is True
        assert any("split" in w.lower() or "multiple" in w.lower() for w in warnings)
        assert "R6" in merged.zoning_districts
        assert "R7A" in merged.zoning_districts

    def test_merge_three_lots(self):
        """Three lots merge with correct total area."""
        lots = [
            _make_lot("3012340001", 1234, 1, area=2000, frontage=20),
            _make_lot("3012340002", 1234, 2, area=2500, frontage=25),
            _make_lot("3012340003", 1234, 3, area=3000, frontage=30),
        ]
        merged, _ = merge_lots(lots)
        assert merged.lot_area == 7500
        assert merged.lot_frontage == 75

    def test_merge_with_geometry(self):
        """Merging with geometry produces union polygon."""
        geom1, geom2 = _make_adjacent_geometry()
        lot1 = _make_lot("3012340001", 1234, 1, geometry=geom1,
                         area=2500, frontage=25, depth=100)
        lot2 = _make_lot("3012340002", 1234, 2, geometry=geom2,
                         area=2500, frontage=25, depth=100)
        merged, warnings = merge_lots([lot1, lot2])
        assert merged.geometry is not None

    def test_through_lot_detection(self):
        """Lots on different streets → through lot detected."""
        lot1 = _make_lot("3012340001", 1234, 1, address="100 MAIN ST")
        lot2 = _make_lot("3012340002", 1234, 2, address="101 ELM ST")
        merged, _ = merge_lots([lot1, lot2])
        assert merged.lot_type == "through"

    def test_corner_lot_detection(self):
        """If any individual lot is corner, merged is corner."""
        lot1 = _make_lot("3012340001", 1234, 1, lot_type="interior")
        lot2 = _make_lot("3012340002", 1234, 2, lot_type="corner")
        merged, _ = merge_lots([lot1, lot2])
        assert merged.lot_type == "corner"


# ──────────────────────────────────────────────────────────────────
# DELTA CALCULATION TESTS
# ──────────────────────────────────────────────────────────────────

class TestDeltaCalculation:
    """Test assemblage delta calculations."""

    def test_delta_detects_additional_sf(self):
        """Merged building has more SF than sum of individuals."""
        calc = ZoningCalculator()
        # Two adjacent R6 lots
        lot1 = _make_lot("3012340001", 1234, 1, area=2500, frontage=25,
                         depth=100, district="R6")
        lot2 = _make_lot("3012340002", 1234, 2, area=2500, frontage=25,
                         depth=100, district="R6")

        ind1 = calc.calculate(lot1)
        ind2 = calc.calculate(lot2)
        individual_analyses = [ind1, ind2]

        # Merge
        merged, _ = merge_lots([lot1, lot2])
        merged_analysis = calc.calculate(merged)

        delta = calculate_delta(
            [lot1, lot2], individual_analyses, merged, merged_analysis,
        )

        # Check that delta has scenario deltas
        assert len(delta.scenario_deltas) > 0

    def test_lot_area_change_near_zero(self):
        """Merged lot area should equal sum of individuals."""
        lot1 = _make_lot("3012340001", 1234, 1, area=2500)
        lot2 = _make_lot("3012340002", 1234, 2, area=3000)
        merged, _ = merge_lots([lot1, lot2])

        delta = calculate_delta(
            [lot1, lot2],
            [{"scenarios": []}, {"scenarios": []}],
            merged,
            {"scenarios": []},
        )
        assert delta.lot_area_change == 0


# ──────────────────────────────────────────────────────────────────
# KEY UNLOCK TESTS
# ──────────────────────────────────────────────────────────────────

class TestKeyUnlocks:
    """Test key unlock identification."""

    def test_through_lot_unlock(self):
        """Through lot creation is identified as key unlock."""
        lot1 = _make_lot("3012340001", 1234, 1, lot_type="interior")
        lot2 = _make_lot("3012340002", 1234, 2, lot_type="interior")
        merged, _ = merge_lots([lot1, lot2])
        merged.lot_type = "through"  # Force through lot

        delta = AssemblageDelta()
        unlocks = identify_key_unlocks([lot1, lot2], merged, delta)
        assert any("through lot" in u.lower() for u in unlocks)

    def test_corner_lot_unlock(self):
        """Corner lot creation is identified as key unlock."""
        lot1 = _make_lot("3012340001", 1234, 1, lot_type="interior")
        lot2 = _make_lot("3012340002", 1234, 2, lot_type="interior")
        merged, _ = merge_lots([lot1, lot2])
        merged.lot_type = "corner"

        delta = AssemblageDelta()
        unlocks = identify_key_unlocks([lot1, lot2], merged, delta)
        assert any("corner lot" in u.lower() for u in unlocks)

    def test_sliver_law_unlock(self):
        """Merged lot width >= 45 ft eliminates sliver law."""
        lot1 = _make_lot("3012340001", 1234, 1, frontage=20)
        lot2 = _make_lot("3012340002", 1234, 2, frontage=25)
        merged, _ = merge_lots([lot1, lot2])
        assert merged.lot_frontage >= 45

        delta = AssemblageDelta()
        unlocks = identify_key_unlocks([lot1, lot2], merged, delta)
        assert any("sliver" in u.lower() for u in unlocks)

    def test_split_zone_unlock(self):
        """Lots in different districts flag split-zone opportunity."""
        lot1 = _make_lot("3012340001", 1234, 1, district="R6")
        lot2 = _make_lot("3012340002", 1234, 2, district="R7A")
        merged, _ = merge_lots([lot1, lot2])

        delta = AssemblageDelta()
        unlocks = identify_key_unlocks([lot1, lot2], merged, delta)
        assert any("different districts" in u.lower() or "averaging" in u.lower() for u in unlocks)

    def test_footprint_gain_unlock(self):
        """Side yard elimination gain is flagged."""
        lot1 = _make_lot("3012340001", 1234, 1)
        lot2 = _make_lot("3012340002", 1234, 2)
        merged, _ = merge_lots([lot1, lot2])

        delta = AssemblageDelta(footprint_gain_sf=500)
        unlocks = identify_key_unlocks([lot1, lot2], merged, delta)
        assert any("side yard" in u.lower() or "footprint" in u.lower() for u in unlocks)

    def test_lot_area_threshold_10k(self):
        """Merged lot exceeding 10,000 SF threshold is flagged."""
        lot1 = _make_lot("3012340001", 1234, 1, area=6000, frontage=60)
        lot2 = _make_lot("3012340002", 1234, 2, area=5000, frontage=50)
        merged, _ = merge_lots([lot1, lot2])

        delta = AssemblageDelta()
        unlocks = identify_key_unlocks([lot1, lot2], merged, delta)
        assert any("10,000" in u for u in unlocks)


# ──────────────────────────────────────────────────────────────────
# FULL ANALYSIS TESTS
# ──────────────────────────────────────────────────────────────────

class TestFullAssemblageAnalysis:
    """Integration tests for the full assemblage pipeline."""

    def test_two_lot_assemblage(self):
        """Full assemblage of two R6 lots runs without errors."""
        lot1 = _make_lot("3012340001", 1234, 1, area=2500, frontage=25,
                         depth=100, district="R6")
        lot2 = _make_lot("3012340002", 1234, 2, area=2500, frontage=25,
                         depth=100, district="R6")
        result = analyze_assemblage([lot1, lot2])
        assert result.contiguity_validated
        assert result.merged_lot.lot_area == 5000
        assert len(result.individual_analyses) == 2
        assert len(result.merged_analysis.get("scenarios", [])) > 0
        assert len(result.delta.scenario_deltas) > 0

    def test_assemblage_requires_two_lots(self):
        """Assemblage with only 1 lot raises ValueError."""
        lot1 = _make_lot("3012340001", 1234, 1)
        with pytest.raises(ValueError, match="at least 2"):
            analyze_assemblage([lot1])

    def test_assemblage_to_dict(self):
        """Assemblage result serializes to dict correctly."""
        lot1 = _make_lot("3012340001", 1234, 1, area=2500, frontage=25,
                         depth=100, district="R6")
        lot2 = _make_lot("3012340002", 1234, 2, area=2500, frontage=25,
                         depth=100, district="R6")
        result = analyze_assemblage([lot1, lot2])
        d = result.to_dict()
        assert "individual_lots" in d
        assert "merged_lot" in d
        assert "delta" in d
        assert "key_unlocks" in d["delta"]

    def test_three_lot_assemblage(self):
        """Three lots assemble correctly."""
        lots = [
            _make_lot("3012340001", 1234, 1, area=2000, frontage=20, depth=100, district="R6"),
            _make_lot("3012340002", 1234, 2, area=2000, frontage=20, depth=100, district="R6"),
            _make_lot("3012340003", 1234, 3, area=2000, frontage=20, depth=100, district="R6"),
        ]
        result = analyze_assemblage(lots)
        assert result.merged_lot.lot_area == 6000
        assert result.merged_lot.lot_frontage == 60
        assert len(result.individual_analyses) == 3

    def test_assemblage_different_districts(self):
        """Lots in different districts produce split-zone warning."""
        lot1 = _make_lot("3012340001", 1234, 1, area=2500, frontage=25,
                         depth=100, district="R6")
        lot2 = _make_lot("3012340002", 1234, 2, area=2500, frontage=25,
                         depth=100, district="R7A")
        result = analyze_assemblage([lot1, lot2])
        assert result.merged_lot.split_zone is True
        assert any("split" in w.lower() or "multiple" in w.lower()
                    for w in result.warnings)
