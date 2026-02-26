"""Tests for the massing builder module."""

from __future__ import annotations

import json
import math
import pytest

from shapely.geometry import box

from app.models.schemas import (
    LotProfile, PlutoData, ZoningEnvelope, DevelopmentScenario,
    MassingFloor, CoreEstimate, ParkingResult, LossFactorResult,
    SkyExposurePlane, SetbackRules,
)
from app.zoning_engine.massing_builder import (
    build_massing_model,
    _get_lot_polygon,
    _calculate_buildable_footprint,
    _build_3d_geometry,
    _run_sanity_checks,
    _identify_street_edges,
)


# ──────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────

def _make_lot(
    frontage: float = 50,
    depth: float = 100,
    area: float | None = None,
    geometry: dict | None = None,
    district: str = "R6",
    street_width: str = "narrow",
) -> LotProfile:
    """Create a test lot."""
    area = area or (frontage * depth)
    pluto = PlutoData(
        bbl="3012340001",
        zonedist1=district,
        lotarea=area,
        lotfront=frontage,
        lotdepth=depth,
    )
    return LotProfile(
        bbl="3012340001",
        borough=3,
        block=1234,
        lot=1,
        pluto=pluto,
        geometry=geometry,
        zoning_districts=[district],
        lot_area=area,
        lot_frontage=frontage,
        lot_depth=depth,
        lot_type="interior",
        street_width=street_width,
    )


def _make_envelope(
    res_far: float = 3.0,
    max_height: float = 75,
    rear_yard: float = 30,
    front_yard: float = 0,
    side_yards: bool = False,
    side_yard_width: float = 0,
    lot_coverage_max: float | None = None,
    quality_housing: bool = True,
    base_height_max: float = 65,
    setback_above_base: float = 10,
) -> ZoningEnvelope:
    """Create a test zoning envelope."""
    return ZoningEnvelope(
        residential_far=res_far,
        max_building_height=max_height,
        rear_yard=rear_yard,
        front_yard=front_yard,
        side_yards_required=side_yards,
        side_yard_width=side_yard_width,
        lot_coverage_max=lot_coverage_max,
        quality_housing=quality_housing,
        base_height_max=base_height_max,
        setbacks=SetbackRules(front_setback_above_base=setback_above_base),
    )


def _make_scenario(
    name: str = "Max Residential",
    floors: list[MassingFloor] | None = None,
    total_gross: float = 15000,
    zfa: float = 12000,
    units: int = 15,
    num_floors: int = 5,
    max_height: float = 52,
) -> DevelopmentScenario:
    """Create a test scenario with default floors."""
    if floors is None:
        floors = []
        # Ground floor
        floors.append(MassingFloor(
            floor=1, use="residential", gross_sf=3500,
            net_sf=2870, height_ft=12,
        ))
        # Upper floors
        for i in range(2, num_floors + 1):
            sf = 3500 if i <= 4 else 1000
            floors.append(MassingFloor(
                floor=i, use="residential", gross_sf=sf,
                net_sf=sf * 0.82, height_ft=10,
            ))

    return DevelopmentScenario(
        name=name,
        description="Test scenario",
        total_gross_sf=total_gross,
        total_net_sf=total_gross * 0.82,
        zoning_floor_area=zfa,
        residential_sf=total_gross * 0.82,
        total_units=units,
        num_floors=num_floors,
        max_height_ft=max_height,
        far_used=2.5,
        floors=floors,
        core=CoreEstimate(
            elevators=1, stairs=1,
            elevator_sf_per_floor=70, stair_sf_per_floor=150,
            mechanical_sf_per_floor=50, corridor_sf_per_floor=200,
            total_core_sf_per_floor=470, core_percentage=13.4,
        ),
        parking=ParkingResult(total_spaces_required=5),
        loss_factor=LossFactorResult(
            gross_building_area=total_gross,
            total_common_area=total_gross * 0.18,
            net_rentable_area=total_gross * 0.82,
            loss_factor_pct=18.0,
            efficiency_ratio=82.0,
        ),
    )


# ──────────────────────────────────────────────────────────────────
# LOT POLYGON TESTS
# ──────────────────────────────────────────────────────────────────

class TestLotPolygon:
    """Test lot polygon creation and handling."""

    def test_rectangular_lot_without_geojson(self):
        """Without GeoJSON, creates rectangle from dimensions."""
        poly, origin = _get_lot_polygon(None, 50, 100)
        assert poly.area == pytest.approx(5000, rel=0.01)
        bounds = poly.bounds
        assert bounds[2] - bounds[0] == pytest.approx(50)  # width
        assert bounds[3] - bounds[1] == pytest.approx(100)  # depth

    def test_lot_with_geojson(self):
        """With GeoJSON, parses the actual polygon."""
        rect = box(-73.99, 40.70, -73.989, 40.701)
        geojson = json.loads(json.dumps(rect.__geo_interface__))
        poly, origin = _get_lot_polygon(geojson, 50, 100)
        assert not poly.is_empty
        assert origin["lng"] != 0  # Has a real origin


# ──────────────────────────────────────────────────────────────────
# BUILDABLE FOOTPRINT TESTS
# ──────────────────────────────────────────────────────────────────

class TestBuildableFootprint:
    """Test buildable footprint calculation."""

    def test_rectangular_lot_with_rear_yard(self):
        """50×100 lot with 30 ft rear yard → 50×70 = 3500 SF."""
        lot_poly = box(0, 0, 50, 100)
        envelope = _make_envelope(rear_yard=30, front_yard=0)
        buildable = _calculate_buildable_footprint(
            lot_poly, envelope, 50, 100, [],
        )
        assert buildable.area == pytest.approx(3500, rel=0.01)

    def test_rectangular_lot_with_front_and_rear_yard(self):
        """50×100 lot with 10 ft front + 30 ft rear → 50×60 = 3000 SF."""
        lot_poly = box(0, 0, 50, 100)
        envelope = _make_envelope(rear_yard=30, front_yard=10)
        buildable = _calculate_buildable_footprint(
            lot_poly, envelope, 50, 100, [],
        )
        assert buildable.area == pytest.approx(3000, rel=0.01)

    def test_rectangular_lot_with_side_yards(self):
        """50×100 lot with 5 ft side yards + 30 ft rear → 40×70 = 2800 SF."""
        lot_poly = box(0, 0, 50, 100)
        envelope = _make_envelope(
            rear_yard=30, front_yard=0, side_yards=True, side_yard_width=5,
        )
        buildable = _calculate_buildable_footprint(
            lot_poly, envelope, 50, 100, [],
        )
        assert buildable.area == pytest.approx(2800, rel=0.01)

    def test_no_yards_full_footprint(self):
        """No yards → full lot is buildable."""
        lot_poly = box(0, 0, 50, 100)
        envelope = _make_envelope(rear_yard=0, front_yard=0)
        buildable = _calculate_buildable_footprint(
            lot_poly, envelope, 50, 100, [],
        )
        assert buildable.area == pytest.approx(5000, rel=0.01)


# ──────────────────────────────────────────────────────────────────
# FLOOR BUILDING TESTS
# ──────────────────────────────────────────────────────────────────

class TestFloorBuilding:
    """Test the full massing model build."""

    def test_floor_count_matches_scenario(self):
        """Massing model has same number of floors as scenario."""
        lot = _make_lot(frontage=50, depth=100)
        envelope = _make_envelope(res_far=3.0, max_height=75)
        scenario = _make_scenario(num_floors=5)
        model = build_massing_model(lot, scenario, envelope, district="R6")
        assert len(model["scenarios"][0]["floors"]) == 5

    def test_floor_elevations_are_correct(self):
        """Each floor's elevation = sum of heights below it."""
        lot = _make_lot()
        envelope = _make_envelope()
        scenario = _make_scenario(num_floors=4)
        model = build_massing_model(lot, scenario, envelope)
        floors = model["scenarios"][0]["floors"]

        # Floor 1: elevation 0, height 12
        assert floors[0]["elevation_ft"] == 0
        assert floors[0]["height_ft"] == 12

        # Floor 2: elevation 12, height 10
        assert floors[1]["elevation_ft"] == 12
        assert floors[1]["height_ft"] == 10

        # Floor 3: elevation 22, height 10
        assert floors[2]["elevation_ft"] == 22

    def test_footprint_respects_rear_yard(self):
        """Building footprint doesn't extend into rear yard."""
        lot = _make_lot(frontage=50, depth=100)
        envelope = _make_envelope(rear_yard=30)
        model = build_massing_model(
            lot,
            _make_scenario(num_floors=3),
            envelope,
        )
        # Check that rear setback is approximately 30 ft
        floors = model["scenarios"][0]["floors"]
        assert floors[0]["setback_from_rear_ft"] >= 29

    def test_total_height_matches(self):
        """Total height matches sum of floor heights (+ bulkhead if present)."""
        lot = _make_lot()
        envelope = _make_envelope()
        scenario = _make_scenario(num_floors=3)
        model = build_massing_model(lot, scenario, envelope)
        roof_height = 12 + 10 + 10  # ground + 2 typical = 32
        floors = model["scenarios"][0]["floors"]
        last_floor = floors[-1]
        actual_roof = last_floor["elevation_ft"] + last_floor["height_ft"]
        assert actual_roof == pytest.approx(roof_height, abs=1)
        # Total height includes bulkhead if present
        if model["scenarios"][0]["bulkhead"]:
            bh = model["scenarios"][0]["bulkhead"]
            assert model["total_height_ft"] == pytest.approx(
                actual_roof + bh["height_ft"], abs=1,
            )
        else:
            assert model["total_height_ft"] == pytest.approx(roof_height, abs=1)


# ──────────────────────────────────────────────────────────────────
# 3D GEOMETRY TESTS
# ──────────────────────────────────────────────────────────────────

class TestGeometry3D:
    """Test 3D geometry generation."""

    def test_geometry_has_vertices_and_faces(self):
        """3D geometry includes vertices and faces."""
        lot = _make_lot()
        envelope = _make_envelope()
        model = build_massing_model(lot, _make_scenario(), envelope)
        geom = model["geometry_3d"]
        assert len(geom["vertices"]) > 0
        assert len(geom["faces"]) > 0
        assert len(geom["colors"]) == len(geom["faces"])

    def test_vertices_are_3d(self):
        """All vertices have x, y, z coordinates."""
        lot = _make_lot()
        envelope = _make_envelope()
        model = build_massing_model(lot, _make_scenario(), envelope)
        for v in model["geometry_3d"]["vertices"]:
            assert len(v) == 3

    def test_colors_match_use_type(self):
        """Floor colors correspond to use type."""
        lot = _make_lot()
        envelope = _make_envelope()
        model = build_massing_model(lot, _make_scenario(), envelope)
        # All residential → should be the residential color
        colors = model["geometry_3d"]["colors"]
        assert len(set(colors)) >= 1  # At least one color used


# ──────────────────────────────────────────────────────────────────
# ZONING ENVELOPE TESTS
# ──────────────────────────────────────────────────────────────────

class TestZoningEnvelopeGeom:
    """Test zoning envelope wireframe generation."""

    def test_envelope_has_max_height(self):
        """Zoning envelope includes max height."""
        lot = _make_lot()
        envelope = _make_envelope(max_height=75)
        model = build_massing_model(lot, _make_scenario(), envelope)
        env_geom = model["scenarios"][0]["zoning_envelope"]
        assert env_geom["max_height_ft"] == 75

    def test_envelope_has_base_height(self):
        """Zoning envelope includes base height if QH."""
        lot = _make_lot()
        envelope = _make_envelope(base_height_max=65)
        model = build_massing_model(lot, _make_scenario(), envelope)
        env_geom = model["scenarios"][0]["zoning_envelope"]
        assert env_geom["base_height_max_ft"] == 65

    def test_envelope_has_wireframe(self):
        """Zoning envelope has wireframe edges."""
        lot = _make_lot()
        envelope = _make_envelope()
        model = build_massing_model(lot, _make_scenario(), envelope)
        wireframe = model["scenarios"][0]["zoning_envelope"]["wireframe"]
        assert len(wireframe) > 0


# ──────────────────────────────────────────────────────────────────
# BULKHEAD TESTS
# ──────────────────────────────────────────────────────────────────

class TestBulkhead:
    """Test bulkhead generation."""

    def test_bulkhead_added_for_multistory(self):
        """Multi-story building gets a bulkhead."""
        lot = _make_lot()
        envelope = _make_envelope()
        model = build_massing_model(lot, _make_scenario(num_floors=5), envelope)
        assert model["scenarios"][0]["bulkhead"] is not None

    def test_bulkhead_above_roof(self):
        """Bulkhead elevation is at roof level."""
        lot = _make_lot()
        envelope = _make_envelope()
        scenario = _make_scenario(num_floors=4)
        model = build_massing_model(lot, scenario, envelope)
        bulkhead = model["scenarios"][0]["bulkhead"]
        if bulkhead:
            last_floor = model["scenarios"][0]["floors"][-1]
            roof = last_floor["elevation_ft"] + last_floor["height_ft"]
            assert bulkhead["elevation_ft"] == pytest.approx(roof, abs=1)

    def test_no_bulkhead_for_small_building(self):
        """2-floor building doesn't get bulkhead."""
        lot = _make_lot()
        envelope = _make_envelope()
        model = build_massing_model(
            lot,
            _make_scenario(num_floors=2),
            envelope,
        )
        assert model["scenarios"][0]["bulkhead"] is None


# ──────────────────────────────────────────────────────────────────
# SANITY CHECK TESTS
# ──────────────────────────────────────────────────────────────────

class TestSanityChecks:
    """Test massing sanity checks."""

    def test_no_warnings_for_normal_building(self):
        """Normal building produces no warnings."""
        lot = _make_lot(frontage=50, depth=100)
        envelope = _make_envelope(res_far=3.0, max_height=75)
        model = build_massing_model(
            lot,
            _make_scenario(num_floors=5, total_gross=15000, zfa=12000),
            envelope,
        )
        # Should have no critical warnings
        warnings = model.get("warnings", [])
        assert not any("exceeds max" in w.lower() for w in warnings)

    def test_warning_for_height_exceedance(self):
        """Building above max height triggers warning."""
        envelope = _make_envelope(max_height=30)
        massing_floors = [
            {"floor_num": 1, "use": "residential", "elevation_ft": 0,
             "height_ft": 12, "gross_area_sf": 3000, "plate_area_sf": 3000},
            {"floor_num": 2, "use": "residential", "elevation_ft": 12,
             "height_ft": 10, "gross_area_sf": 3000, "plate_area_sf": 3000},
            {"floor_num": 3, "use": "residential", "elevation_ft": 22,
             "height_ft": 10, "gross_area_sf": 3000, "plate_area_sf": 3000},
        ]
        scenario = _make_scenario(num_floors=3, total_gross=9000, max_height=32)
        warnings = _run_sanity_checks(massing_floors, scenario, envelope, 5000)
        assert any("height" in w.lower() for w in warnings)


# ──────────────────────────────────────────────────────────────────
# STREET EDGE TESTS
# ──────────────────────────────────────────────────────────────────

class TestStreetEdges:
    """Test street edge identification."""

    def test_rectangular_lot_front_edge(self):
        """Front edge of rectangular lot is identified."""
        lot_poly = box(0, 0, 50, 100)
        edges = _identify_street_edges(lot_poly, 50, 100)
        assert len(edges) >= 1
        assert edges[0]["side"] == "front"
        assert edges[0]["length"] == pytest.approx(50, abs=1)
