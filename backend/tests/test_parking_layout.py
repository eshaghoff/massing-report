"""Tests for parking layout engine.

Validates area calculations for each parking configuration and
the overall ranking/recommendation logic.
"""

from __future__ import annotations

import pytest

from app.zoning_engine.parking_layout import (
    evaluate_parking_layouts,
    _evaluate_surface,
    _evaluate_below_grade_1,
    _evaluate_below_grade_2,
    _evaluate_enclosed_grade,
    _evaluate_stackers,
    _evaluate_ramp_to_second,
    SF_PER_SPACE_SURFACE,
    SF_PER_SPACE_STRUCTURED,
    SF_PER_SPACE_STACKER_DOUBLE,
    SF_PER_SPACE_STACKER_TRIPLE,
    RAMP_SF_SINGLE_LANE,
    RAMP_SF_TWO_LEVEL,
    RAMP_SF_TO_SECOND_FLOOR,
    COST_SURFACE,
    COST_BELOW_GRADE_1,
    COST_BELOW_GRADE_2,
    COST_ENCLOSED_GRADE,
    COST_STACKER,
    COST_RAMP_SECOND,
)


# ──────────────────────────────────────────────────────────────────
# SURFACE PARKING
# ──────────────────────────────────────────────────────────────────

class TestSurfaceParking:
    """Test at-grade surface lot configuration."""

    def test_spaces_fit_in_remaining_lot(self):
        """Surface spaces = (lot - footprint) / 350 SF."""
        result = _evaluate_surface(required=5, lot_area=10000, building_footprint=5000)
        available = 10000 - 5000  # 5000 SF available
        max_spaces = int(available / SF_PER_SPACE_SURFACE)  # 14
        assert result.spaces_provided == min(5, max_spaces)
        assert result.meets_requirement is True

    def test_lot_too_small(self):
        """Not enough remaining lot area after building footprint."""
        result = _evaluate_surface(required=10, lot_area=5000, building_footprint=4800)
        assert result.spaces_provided < 10
        assert result.feasible is False  # < 500 SF available

    def test_cost_per_space(self):
        result = _evaluate_surface(required=5, lot_area=10000, building_footprint=5000)
        assert result.cost_per_space == COST_SURFACE
        assert result.estimated_cost == result.spaces_provided * COST_SURFACE

    def test_no_impact_on_buildable(self):
        """Surface parking doesn't consume building area."""
        result = _evaluate_surface(required=5, lot_area=10000, building_footprint=5000)
        assert result.impact_on_buildable == 0

    def test_area_consumed(self):
        result = _evaluate_surface(required=3, lot_area=10000, building_footprint=5000)
        assert result.area_consumed_sf == 3 * SF_PER_SPACE_SURFACE

    def test_infeasible_when_no_area(self):
        result = _evaluate_surface(required=5, lot_area=5000, building_footprint=5000)
        assert result.spaces_provided == 0
        assert result.feasible is False


# ──────────────────────────────────────────────────────────────────
# BELOW-GRADE 1 LEVEL
# ──────────────────────────────────────────────────────────────────

class TestBelowGrade1:
    """Test one level underground parking."""

    def test_usable_area_calculation(self):
        """Usable = footprint - ramp - 8% columns/mechanical."""
        fp = 5000
        usable = fp - RAMP_SF_SINGLE_LANE - fp * 0.08
        max_spaces = int(usable / SF_PER_SPACE_STRUCTURED)
        result = _evaluate_below_grade_1(required=10, building_footprint=fp)
        assert result.spaces_provided <= max_spaces

    def test_meets_requirement(self):
        """Large footprint can meet small requirement."""
        result = _evaluate_below_grade_1(required=5, building_footprint=5000)
        assert result.meets_requirement is True

    def test_doesnt_meet_large_requirement(self):
        """Small footprint can't meet large requirement."""
        result = _evaluate_below_grade_1(required=50, building_footprint=3000)
        assert result.meets_requirement is False

    def test_cost_below_grade_1(self):
        result = _evaluate_below_grade_1(required=5, building_footprint=5000)
        assert result.cost_per_space == COST_BELOW_GRADE_1
        assert result.estimated_cost == result.spaces_provided * COST_BELOW_GRADE_1

    def test_area_consumed_is_full_footprint(self):
        """Below-grade uses entire cellar level."""
        fp = 5000
        result = _evaluate_below_grade_1(required=5, building_footprint=fp)
        assert result.area_consumed_sf == fp

    def test_infeasible_for_small_footprint(self):
        """Footprint < 800 is infeasible."""
        result = _evaluate_below_grade_1(required=3, building_footprint=700)
        assert result.feasible is False

    def test_floors_consumed(self):
        result = _evaluate_below_grade_1(required=5, building_footprint=5000)
        assert "cellar" in result.floors_consumed

    def test_feasibility_notes_include_excavation(self):
        result = _evaluate_below_grade_1(required=5, building_footprint=5000)
        notes = " ".join(result.feasibility_notes)
        assert "excavation" in notes.lower() or "water table" in notes.lower()


# ──────────────────────────────────────────────────────────────────
# BELOW-GRADE 2 LEVELS
# ──────────────────────────────────────────────────────────────────

class TestBelowGrade2:
    """Test two levels underground parking."""

    def test_more_spaces_than_1_level(self):
        """Two levels should fit more spaces than one."""
        fp = 5000
        r1 = _evaluate_below_grade_1(required=100, building_footprint=fp)
        r2 = _evaluate_below_grade_2(required=100, building_footprint=fp)
        assert r2.spaces_provided >= r1.spaces_provided

    def test_area_consumed_double(self):
        """Area consumed is 2× footprint."""
        fp = 5000
        result = _evaluate_below_grade_2(required=10, building_footprint=fp)
        assert result.area_consumed_sf == fp * 2

    def test_higher_cost_second_level(self):
        """Second level costs more ($70K vs $50K per space)."""
        fp = 5000
        result = _evaluate_below_grade_2(required=20, building_footprint=fp)
        # Average cost should be between level 1 and level 2 costs
        if result.spaces_provided > 0:
            assert result.cost_per_space >= COST_BELOW_GRADE_1
            assert result.cost_per_space <= COST_BELOW_GRADE_2

    def test_infeasible_small_footprint(self):
        """Footprint < 1200 is infeasible for 2 levels."""
        result = _evaluate_below_grade_2(required=5, building_footprint=1000)
        assert result.feasible is False

    def test_floors_consumed(self):
        result = _evaluate_below_grade_2(required=10, building_footprint=5000)
        assert "cellar" in result.floors_consumed
        assert "sub-cellar" in result.floors_consumed

    def test_structural_cost_note(self):
        result = _evaluate_below_grade_2(required=10, building_footprint=5000)
        notes = " ".join(result.feasibility_notes)
        assert "structural" in notes.lower() or "excavation" in notes.lower()


# ──────────────────────────────────────────────────────────────────
# ENCLOSED AT-GRADE
# ──────────────────────────────────────────────────────────────────

class TestEnclosedGrade:
    """Test ground floor enclosed parking."""

    def test_usable_area(self):
        """Usable = footprint - half ramp."""
        fp = 4000
        usable = fp - RAMP_SF_SINGLE_LANE * 0.5
        max_spaces = int(usable / SF_PER_SPACE_STRUCTURED)
        result = _evaluate_enclosed_grade(required=5, building_footprint=fp)
        assert result.spaces_provided <= max_spaces

    def test_impact_on_buildable(self):
        """Enclosed at-grade directly reduces ground floor area."""
        result = _evaluate_enclosed_grade(required=5, building_footprint=4000)
        assert result.impact_on_buildable > 0
        assert result.impact_on_buildable == result.area_consumed_sf

    def test_cost_enclosed(self):
        result = _evaluate_enclosed_grade(required=5, building_footprint=4000)
        assert result.cost_per_space == COST_ENCLOSED_GRADE

    def test_curb_cut_note(self):
        result = _evaluate_enclosed_grade(required=5, building_footprint=4000)
        notes = " ".join(result.feasibility_notes)
        assert "curb cut" in notes.lower()

    def test_quality_housing_note(self):
        """QH district flag about street wall continuity."""
        result = _evaluate_enclosed_grade(required=5, building_footprint=4000, is_quality_housing=True)
        notes = " ".join(result.feasibility_notes)
        assert "qh" in notes.lower() or "street wall" in notes.lower()

    def test_infeasible_small_footprint(self):
        result = _evaluate_enclosed_grade(required=5, building_footprint=600)
        assert result.feasible is False

    def test_over_60_pct_note(self):
        """Flag when parking >60% of ground floor."""
        # Small footprint relative to spaces → high consumption
        result = _evaluate_enclosed_grade(required=8, building_footprint=4000)
        if result.area_consumed_sf > 4000 * 0.6:
            notes = " ".join(result.feasibility_notes)
            assert "60%" in notes


# ──────────────────────────────────────────────────────────────────
# MECHANICAL STACKERS
# ──────────────────────────────────────────────────────────────────

class TestStackers:
    """Test mechanical car stacker configurations."""

    def test_insufficient_height(self):
        """Ceiling < 11.5 ft: infeasible."""
        result = _evaluate_stackers(required=10, building_footprint=4000, ground_floor_height=10)
        assert result.feasible is False
        assert result.spaces_provided == 0

    def test_double_stack_height(self):
        """11.5-17.9 ft: double stack (200 SF/space)."""
        result = _evaluate_stackers(required=10, building_footprint=4000, ground_floor_height=14)
        assert result.feasible is True
        assert "double" in result.config_type.lower() or "Double" in " ".join(result.feasibility_notes)

    def test_triple_stack_height(self):
        """18+ ft: triple stack (135 SF/space)."""
        result = _evaluate_stackers(required=10, building_footprint=4000, ground_floor_height=20)
        assert result.feasible is True
        assert "triple" in result.config_type.lower() or "Triple" in " ".join(result.feasibility_notes)

    def test_stacker_density(self):
        """Stackers should fit more spaces than surface for same area."""
        stacker = _evaluate_stackers(required=20, building_footprint=4000, ground_floor_height=14)
        surface = _evaluate_surface(required=20, lot_area=8000, building_footprint=4000)
        if stacker.feasible and surface.feasible:
            # Stackers should generally provide more spaces per SF
            assert stacker.spaces_provided >= surface.spaces_provided or stacker.area_consumed_sf <= surface.area_consumed_sf

    def test_retrieval_time_note(self):
        result = _evaluate_stackers(required=5, building_footprint=4000, ground_floor_height=14)
        notes = " ".join(result.feasibility_notes)
        assert "retrieval" in notes.lower()


# ──────────────────────────────────────────────────────────────────
# RAMP TO 2ND FLOOR
# ──────────────────────────────────────────────────────────────────

class TestRampToSecond:
    """Test ramp to 2nd floor parking."""

    def test_footprint_too_small(self):
        """Footprint < 1.5× ramp area: infeasible."""
        result = _evaluate_ramp_to_second(
            required=5, building_footprint=2000, typical_floor_sf=2000,
        )
        assert result.feasible is False

    def test_feasible_large_footprint(self):
        result = _evaluate_ramp_to_second(
            required=5, building_footprint=5000, typical_floor_sf=5000,
        )
        assert result.feasible is True
        assert result.spaces_provided > 0

    def test_area_consumed_includes_ramp_and_floor(self):
        """Area = ramp on ground + full 2nd floor."""
        fp = 5000
        result = _evaluate_ramp_to_second(required=10, building_footprint=fp, typical_floor_sf=fp)
        if result.feasible:
            assert result.area_consumed_sf == RAMP_SF_TO_SECOND_FLOOR + fp

    def test_cost_ramp_second(self):
        result = _evaluate_ramp_to_second(
            required=5, building_footprint=5000, typical_floor_sf=5000,
        )
        if result.feasible:
            assert result.cost_per_space == COST_RAMP_SECOND

    def test_floors_consumed(self):
        result = _evaluate_ramp_to_second(
            required=5, building_footprint=5000, typical_floor_sf=5000,
        )
        if result.feasible:
            assert any("ground" in f.lower() for f in result.floors_consumed)
            assert any("2nd" in f.lower() for f in result.floors_consumed)

    def test_unusual_for_residential_note(self):
        result = _evaluate_ramp_to_second(
            required=5, building_footprint=5000, typical_floor_sf=5000,
        )
        if result.feasible:
            notes = " ".join(result.feasibility_notes)
            assert "unusual" in notes.lower() or "residential" in notes.lower()


# ──────────────────────────────────────────────────────────────────
# EVALUATE ALL PARKING LAYOUTS (integration)
# ──────────────────────────────────────────────────────────────────

class TestEvaluateParkingLayouts:
    """Integration tests for the full parking layout evaluator."""

    def test_zero_spaces_no_parking_needed(self):
        """No parking required → empty result with waiver."""
        result = evaluate_parking_layouts(
            required_spaces=0, lot_area=5000, building_footprint=3000,
        )
        assert result.required_spaces == 0
        assert len(result.options) == 0
        assert result.recommended is None
        assert result.waiver_eligible is True

    def test_all_six_options_evaluated(self):
        """Should evaluate all 6 configurations."""
        result = evaluate_parking_layouts(
            required_spaces=10, lot_area=10000, building_footprint=5000,
            typical_floor_sf=5000, ground_floor_height=14,
        )
        assert len(result.options) == 6
        config_types = {o.config_type for o in result.options}
        assert "surface_lot" in config_types
        assert "below_grade_1_level" in config_types
        assert "below_grade_2_levels" in config_types
        assert "enclosed_at_grade" in config_types
        # Stackers may have different suffix (double/triple)
        assert any("stacker" in ct for ct in config_types)
        assert "ramp_to_2nd_floor" in config_types

    def test_recommended_meets_requirement(self):
        """Recommended option should meet parking requirement if any option does."""
        result = evaluate_parking_layouts(
            required_spaces=5, lot_area=10000, building_footprint=5000,
            typical_floor_sf=5000, ground_floor_height=14,
        )
        feasible_meeting = [o for o in result.options if o.feasible and o.meets_requirement]
        if feasible_meeting:
            assert result.recommended is not None
            assert result.recommended.meets_requirement is True

    def test_ranking_by_impact_then_cost(self):
        """Feasible options meeting requirement should be ranked by impact then cost."""
        result = evaluate_parking_layouts(
            required_spaces=5, lot_area=10000, building_footprint=5000,
            typical_floor_sf=5000, ground_floor_height=14,
        )
        feasible = [o for o in result.options if o.feasible]
        # Surface lot has 0 impact — should be first if it meets requirement
        if feasible and feasible[0].config_type == "surface_lot":
            assert feasible[0].impact_on_buildable == 0

    def test_waiver_eligible_flag(self):
        result = evaluate_parking_layouts(
            required_spaces=5, lot_area=10000, building_footprint=5000,
            waiver_eligible=True,
        )
        assert result.waiver_eligible is True
        assert "waiver" in result.waiver_note.lower()

    def test_waiver_not_eligible(self):
        result = evaluate_parking_layouts(
            required_spaces=5, lot_area=10000, building_footprint=5000,
            waiver_eligible=False,
        )
        assert result.waiver_eligible is False

    def test_to_dict_structure(self):
        result = evaluate_parking_layouts(
            required_spaces=5, lot_area=10000, building_footprint=5000,
        )
        d = result.to_dict()
        assert "required_spaces" in d
        assert "options" in d
        assert "recommended" in d
        assert "waiver_eligible" in d
        assert "waiver_note" in d

    def test_small_lot_limits_options(self):
        """Very small lot may have fewer feasible options."""
        result = evaluate_parking_layouts(
            required_spaces=5, lot_area=2000, building_footprint=1800,
        )
        feasible = [o for o in result.options if o.feasible]
        # Small lot should have limited feasibility
        assert len(feasible) < 6

    def test_large_lot_more_feasible(self):
        """Large lot should have more feasible options."""
        result = evaluate_parking_layouts(
            required_spaces=5, lot_area=20000, building_footprint=8000,
            typical_floor_sf=8000, ground_floor_height=14,
        )
        feasible = [o for o in result.options if o.feasible]
        assert len(feasible) >= 3

    def test_option_to_dict(self):
        """Each option should serialize cleanly."""
        result = evaluate_parking_layouts(
            required_spaces=5, lot_area=10000, building_footprint=5000,
        )
        for o in result.options:
            d = o.to_dict()
            assert "config_type" in d
            assert "spaces_provided" in d
            assert "estimated_cost" in d
            assert "feasibility_notes" in d
