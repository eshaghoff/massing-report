"""
Main zoning calculator: takes a LotProfile and produces ZoningEnvelope + scenarios.

Integrates all zoning rules:
  - FAR tables (residential, commercial, CF, manufacturing)
  - Height/setback (Quality Housing + Height Factor)
  - Open space ratio (HF districts)
  - Yards (front, rear, side)
  - Parking (auto, accessible, bicycle, loading)
  - Building types (detached, semi-detached, attached, apartment, tower)
  - Street wall / sliver law
  - Floor area exemptions
  - MIH options (inclusionary housing)
"""

from __future__ import annotations

import math

from app.models.schemas import (
    LotProfile, ZoningEnvelope, SkyExposurePlane, SetbackRules,
    DevelopmentScenario, MassingFloor, ParkingResult, ParkingOption,
    CoreEstimate, UnitMixResult, UnitMix, LossFactorResult,
    FloorAreaExemptions,
)
from app.zoning_engine.far_tables import (
    get_far_for_district, get_ih_bonus, COMMERCIAL_OVERLAY_FAR,
    get_uap_far, get_uap_bonus_far,
)
from app.zoning_engine.height_setback import (
    get_height_rules, FLOOR_HEIGHTS, QH_FLOOR_HEIGHTS,
    get_floor_heights, get_bulkhead_allowance,
)
from app.zoning_engine.yards import get_yard_requirements
from app.zoning_engine.parking import calculate_parking
from app.zoning_engine.use_groups import get_permitted_uses
from app.zoning_engine.open_space_ratio import calculate_hf_far, HF_OPEN_SPACE
from app.zoning_engine.building_types import (
    get_building_type_for_district, get_building_type_rules,
    get_max_units_by_lot_area, get_max_units_by_du_factor,
    calculate_tower_footprint,
)
from app.zoning_engine.street_wall import (
    get_sliver_law_height, get_street_wall_rules,
)
from app.zoning_engine.floor_area_exemptions import calculate_exempt_area
from app.zoning_engine.mih_options import (
    get_mih_bonus_far, get_mih_max_far, calculate_mih_program, get_all_mih_options,
)
from app.zoning_engine.dormers import get_dormer_rules, calculate_upper_floor_area
from app.zoning_engine.special_districts import (
    get_special_district_rules,
    apply_special_district_overrides,
    get_special_district_bonuses,
)
from app.zoning_engine.city_of_yes import calculate_uap_scenario, get_city_of_yes_summary
from app.zoning_engine.programs import check_all_programs, get_program_effects_summary, ProgramCategory


class ZoningCalculator:
    """Computes all allowable development parameters for a lot."""

    def calculate(self, lot: LotProfile) -> dict:
        """Full calculation: envelope + development scenarios."""
        primary_district = lot.zoning_districts[0] if lot.zoning_districts else None
        if not primary_district:
            raise ValueError("No zoning district found for this lot.")

        envelope = self.calculate_envelope(lot, primary_district)
        scenarios = self.generate_scenarios(lot, envelope, primary_district)

        # Attach building type and additional info
        btype_rules = get_building_type_rules(primary_district)
        street_wall = get_street_wall_rules(primary_district, lot.street_width)

        # Special district info
        spdist_codes = lot.special_districts or []
        special_district_info = self._get_special_district_info(spdist_codes)

        # City of Yes summary
        coy_summary = get_city_of_yes_summary(
            primary_district,
            lot_area=lot.lot_area or 0,
            borough=lot.borough,
            community_district=lot.pluto.cd if lot.pluto and lot.pluto.cd else 0,
            street_width=lot.street_width,
        )

        # ── Run all program checks ──
        program_results = check_all_programs(lot)
        program_effects = get_program_effects_summary(program_results)

        # ── Generate bonus scenarios for applicable programs with FAR bonuses ──
        bonus_scenarios = self._generate_bonus_scenarios(
            lot, envelope, primary_district, scenarios, program_results,
        )
        scenarios.extend(bonus_scenarios)

        return {
            "zoning_envelope": envelope,
            "scenarios": scenarios,
            "building_type": btype_rules,
            "street_wall": street_wall,
            "special_districts": special_district_info,
            "city_of_yes": coy_summary,
            "programs": {
                "results": program_results,
                "effects_summary": program_effects,
            },
        }

    def calculate_envelope(self, lot: LotProfile, district: str) -> ZoningEnvelope:
        """Calculate the full zoning envelope for a lot + district."""
        far = get_far_for_district(district)
        height = get_height_rules(district, lot.street_width)
        yards = get_yard_requirements(
            district,
            lot_type=lot.lot_type,
            lot_depth=lot.lot_depth or 100,
            lot_frontage=lot.lot_frontage or 50,
            street_width=lot.street_width,
        )

        lot_area = lot.lot_area or 0

        # ── Apply special district FAR overrides ──
        spdist_codes = lot.special_districts or []
        if spdist_codes:
            far = apply_special_district_overrides(far, spdist_codes)

        # ── Resolve residential FAR (may be HF/QH dict) ──
        res_far = far["residential"]
        if isinstance(res_far, dict):
            # For non-contextual districts with both HF and QH options,
            # use QH FAR for the base envelope.
            qh_val = res_far.get("qh", res_far.get("hf", 0))
            # QH FAR may itself be street-width dependent (e.g. R6:
            #   wide street = 3.0, narrow = 2.2)
            if isinstance(qh_val, dict):
                sw = lot.street_width or "narrow"
                res_far_val = qh_val.get(sw, qh_val.get("narrow", 0))
            else:
                res_far_val = qh_val
        else:
            res_far_val = res_far

        comm_far = far["commercial"] or 0
        cf_far = far["cf"] or 0
        mfg_far = far["manufacturing"]

        # ── Commercial overlay FAR ──
        overlay_comm_far = 0
        for overlay in lot.overlays:
            overlay_comm_far = max(overlay_comm_far, COMMERCIAL_OVERLAY_FAR.get(overlay, 0))
        if overlay_comm_far > 0 and comm_far == 0:
            comm_far = overlay_comm_far

        # ── IH / MIH bonus ──
        ih_bonus = 0
        if lot.is_mih_area:
            ih = get_mih_bonus_far(district)
            if ih:
                ih_bonus = ih

        # ── Sky exposure plane ──
        sep = None
        if height.get("sky_exposure_plane"):
            sp = height["sky_exposure_plane"]
            sep = SkyExposurePlane(
                start_height=sp["start_height"],
                ratio=sp["ratio"],
                direction=sp["direction"],
            )

        # ── Setbacks ──
        setback_val = height.get("setback_above_base", 0)
        setbacks = SetbackRules(
            front=0 if height.get("quality_housing") else yards.get("front_yard", 0),
            side_narrow=yards.get("side_yard_each", 0),
            side_wide=yards.get("side_yard_each", 0),
            rear=yards.get("rear_yard", 30),
            front_setback_above_base=setback_val,
        )

        # ── Sliver law height limit ──
        max_bldg_height = height.get("max_building_height")
        lot_front = lot.lot_frontage or 50
        sliver_height = get_sliver_law_height(district, lot_front)
        if sliver_height is not None:
            if max_bldg_height is not None:
                max_bldg_height = min(max_bldg_height, sliver_height)
            else:
                max_bldg_height = sliver_height

        return ZoningEnvelope(
            residential_far=res_far_val,
            commercial_far=comm_far,
            cf_far=cf_far,
            manufacturing_far=mfg_far,
            max_residential_zfa=res_far_val * lot_area if res_far_val else None,
            max_commercial_zfa=comm_far * lot_area if comm_far else None,
            max_cf_zfa=cf_far * lot_area if cf_far else None,
            ih_bonus_far=ih_bonus if ih_bonus else None,
            base_height_min=height.get("base_height_min"),
            base_height_max=height.get("base_height_max"),
            max_building_height=max_bldg_height,
            sky_exposure_plane=sep,
            setbacks=setbacks,
            front_yard=yards.get("front_yard", 0),
            rear_yard=yards.get("rear_yard", 30),
            side_yards_required=yards.get("side_yards_required", False),
            side_yard_width=yards.get("side_yard_each", 0),
            lot_coverage_max=yards.get("lot_coverage_max"),
            quality_housing=height.get("quality_housing", False),
            height_factor=height.get("height_factor", False),
        )

    def generate_scenarios(
        self, lot: LotProfile, envelope: ZoningEnvelope, district: str
    ) -> list[DevelopmentScenario]:
        """Generate multiple development scenarios."""
        scenarios = []
        lot_area = lot.lot_area or 0
        uses = get_permitted_uses(district)
        far_data = get_far_for_district(district)
        btype = get_building_type_for_district(district)

        # ── Buildable footprint (lot area minus yards) ──
        footprint = self._calculate_footprint(lot, envelope)

        # ── Tower-on-base footprints ──
        tower_info = calculate_tower_footprint(
            lot_area, district,
            lot_frontage=lot.lot_frontage or 50,
            lot_depth=lot.lot_depth or 100,
        )

        # ── Low-density unit limit (R1-R5: lot area per DU) ──
        max_units_by_area = get_max_units_by_lot_area(district, lot_area)

        # ── R6+ dwelling unit factor (ZR 23-52) ──
        # max_du = max_residential_floor_area / 680
        # Fractions ≥ 0.75 round up; fractions < 0.75 are dropped
        max_residential_zfa = (envelope.residential_far or 0) * lot_area
        max_units_by_du = get_max_units_by_du_factor(district, max_residential_zfa)

        # ── 1. Max Residential scenario ──
        if uses["residential_allowed"] and envelope.residential_far:
            scenario = self._build_residential_scenario(
                lot, envelope, district, footprint, "Max Residential",
                "Maximize residential floor area with ground-floor commercial if overlay permits.",
                max_units_by_area=max_units_by_area,
                max_units_by_du=max_units_by_du,
            )
            if scenario:
                scenarios.append(scenario)

        # ── 1b. Max Units scenario (unit-maximization approach) ──
        # Uses smaller unit sizes (studios/1BRs) to hit the DU factor maximum.
        # Only added if it produces more units than Max Residential.
        if uses["residential_allowed"] and envelope.residential_far and max_units_by_du:
            max_res_units = scenarios[0].total_units if scenarios else 0
            if max_units_by_du > max_res_units:
                scenario = self._build_max_units_scenario(
                    lot, envelope, district, footprint,
                    target_units=max_units_by_du,
                    max_units_by_area=max_units_by_area,
                )
                if scenario and scenario.total_units > max_res_units:
                    scenarios.append(scenario)

        # ── 1c. 4+1 Penthouse (No Elevator) scenario ──
        # NYC penthouse rule (ZR 12-10): a penthouse occupying ≤1/3 of roof
        # area doesn't count as a story. So 4 stories + penthouse = 4 stories
        # for code purposes → no elevator required, single staircase OK.
        if uses["residential_allowed"] and envelope.residential_far:
            scenario = self._build_penthouse_scenario(
                lot, envelope, district, footprint,
                max_units_by_area=max_units_by_area,
                max_units_by_du=max_units_by_du,
            )
            if scenario:
                scenarios.append(scenario)

        # ── 2. Max Commercial scenario ──
        if uses["commercial_allowed"] and envelope.commercial_far:
            scenario = self._build_commercial_scenario(
                lot, envelope, district, footprint,
            )
            if scenario:
                scenarios.append(scenario)

        # ── 3. Mixed-Use (ground floor retail + upper residential) ──
        if uses["residential_allowed"] and (uses["commercial_allowed"] or lot.overlays):
            scenario = self._build_mixed_use_scenario(
                lot, envelope, district, footprint,
                max_units_by_area=max_units_by_area,
                max_units_by_du=max_units_by_du,
            )
            if scenario:
                scenarios.append(scenario)

        # ── 4. Community Facility scenario (if CF FAR is higher) ──
        if uses["community_facility_allowed"] and envelope.cf_far:
            if envelope.cf_far > (envelope.residential_far or 0):
                scenario = self._build_cf_scenario(
                    lot, envelope, district, footprint,
                )
                if scenario:
                    scenarios.append(scenario)

        # ── 4b. Residential + CF combined-use scenario ──
        # Per ZR 24-10/24-16: uses can be combined as long as each component
        # does not exceed its own max FAR, and total building bulk does not
        # exceed the highest permitted FAR for any single use.
        # Triggered whenever CF FAR >= residential FAR (including equality).
        if (uses["residential_allowed"] and uses["community_facility_allowed"]
                and envelope.cf_far and envelope.residential_far
                and envelope.cf_far >= (envelope.residential_far or 0)):
            scenario = self._build_residential_cf_scenario(
                lot, envelope, district, footprint,
                max_units_by_area=max_units_by_area,
                max_units_by_du=max_units_by_du,
            )
            if scenario:
                scenarios.append(scenario)

        # ── 5. Height Factor option (if non-contextual R6-R10) ──
        if isinstance(far_data["residential"], dict):
            hf_far = far_data["residential"]["hf"]
            qh_raw = far_data["residential"]["qh"]
            # Resolve street-width-dependent QH FAR (e.g. R6: wide=3.0, narrow=2.2)
            if isinstance(qh_raw, dict):
                sw = lot.street_width or "narrow"
                qh_far = qh_raw.get(sw, qh_raw.get("narrow", 0))
            else:
                qh_far = qh_raw

            # Get HF-specific open space info
            hf_osr = calculate_hf_far(district, lot_area)

            # HF max FAR is from the open space ratio table, not the QH FAR
            hf_max_far = hf_osr.get("max_far_actual", qh_far) if hf_osr.get("is_height_factor") else qh_far

            # Get HF-specific height rules (sky exposure plane, not QH height caps)
            hf_height = get_height_rules(district, lot.street_width, program="hf")
            hf_sep = None
            if hf_height.get("sky_exposure_plane"):
                sp = hf_height["sky_exposure_plane"]
                hf_sep = SkyExposurePlane(
                    start_height=sp["start_height"],
                    ratio=sp["ratio"],
                    direction=sp["direction"],
                )

            hf_envelope = ZoningEnvelope(
                residential_far=hf_max_far,  # HF max FAR from OSR table
                commercial_far=envelope.commercial_far,
                cf_far=envelope.cf_far,
                max_residential_zfa=hf_max_far * lot_area,
                max_building_height=None,  # No height cap in HF
                sky_exposure_plane=hf_sep,
                setbacks=envelope.setbacks,
                quality_housing=False,
                height_factor=True,
                rear_yard=envelope.rear_yard,
                front_yard=envelope.front_yard,
                side_yards_required=envelope.side_yards_required,
                side_yard_width=envelope.side_yard_width,
                lot_coverage_max=envelope.lot_coverage_max,
            )

            # Apply sliver law to HF buildings
            lot_front = lot.lot_frontage or 50
            sliver_ht = get_sliver_law_height(district, lot_front)
            if sliver_ht is not None:
                hf_envelope.max_building_height = sliver_ht

            osr_desc = ""
            if hf_osr.get("is_height_factor"):
                min_os = hf_osr.get("min_open_space_sf", 0)
                osr_desc = f" Min open space: {min_os:,.0f} SF (OSR {hf_osr.get('min_osr', 0)}%)."

            # DU factor for HF: use the HF envelope's FAR
            hf_max_du = get_max_units_by_du_factor(district, hf_max_far * lot_area)

            scenario = self._build_residential_scenario(
                lot, hf_envelope, district, footprint,
                "Height Factor Option",
                f"Height Factor: FAR up to {hf_max_far:.2f}, no height limit, "
                f"sky exposure plane applies.{osr_desc}",
                max_units_by_du=hf_max_du,
            )
            if scenario:
                scenarios.append(scenario)

        # ── 6. Tower-on-base scenario (R9/R10/C6 high-density) ──
        if tower_info.get("is_tower") and uses["residential_allowed"]:
            scenario = self._build_tower_scenario(
                lot, envelope, district, tower_info,
            )
            if scenario:
                scenarios.append(scenario)

        # ── 7. IH Bonus scenario (MIH areas only) ──
        if lot.is_mih_area and envelope.ih_bonus_far:
            ih_far = (envelope.residential_far or 0) + envelope.ih_bonus_far
            ih_envelope = ZoningEnvelope(
                residential_far=ih_far,
                commercial_far=envelope.commercial_far,
                cf_far=envelope.cf_far,
                max_residential_zfa=ih_far * lot_area,
                max_building_height=envelope.max_building_height,
                base_height_min=envelope.base_height_min,
                base_height_max=envelope.base_height_max,
                sky_exposure_plane=envelope.sky_exposure_plane,
                setbacks=envelope.setbacks,
                quality_housing=envelope.quality_housing,
                rear_yard=envelope.rear_yard,
                ih_bonus_far=envelope.ih_bonus_far,
                front_yard=envelope.front_yard,
                side_yards_required=envelope.side_yards_required,
                side_yard_width=envelope.side_yard_width,
                lot_coverage_max=envelope.lot_coverage_max,
            )

            # Calculate MIH program details for the scenario
            mih_option = lot.mih_option or "option_1"
            mih_zfa = ih_far * lot_area

            ih_max_du = get_max_units_by_du_factor(district, ih_far * lot_area)

            scenario = self._build_residential_scenario(
                lot, ih_envelope, district, footprint,
                "With IH Bonus",
                f"Inclusionary Housing bonus: FAR {ih_far:.2f} "
                f"with affordable unit requirement ({mih_option.replace('_', ' ').title()}).",
                max_units_by_du=ih_max_du,
            )
            if scenario:
                # Attach MIH details
                mih_details = calculate_mih_program(
                    mih_option, scenario.residential_sf
                )
                scenario.description += (
                    f" {mih_details['affordable_pct']*100:.0f}% affordable "
                    f"({mih_details['estimated_affordable_units']} units at "
                    f"avg {mih_details['avg_ami']}% AMI)."
                )
                scenarios.append(scenario)

        # ── 8. UAP (Universal Affordability Preference) scenario ──
        # City of Yes: 20% FAR bonus for affordable housing at avg ≤60% AMI
        # Available citywide in R6-R12 (not just MIH areas)
        uap_far = get_uap_far(district)
        if uap_far and uses["residential_allowed"]:
            # Get height rules with affordable housing bonus
            uap_height = get_height_rules(district, lot.street_width, is_affordable=True)
            uap_max_height = uap_height.get("max_building_height")

            uap_bonus = get_uap_bonus_far(district, lot.street_width or "narrow") or 0
            base_res_far = envelope.residential_far or 0

            uap_envelope = ZoningEnvelope(
                residential_far=uap_far,
                commercial_far=envelope.commercial_far,
                cf_far=envelope.cf_far,
                max_residential_zfa=uap_far * lot_area,
                max_building_height=uap_max_height,
                base_height_min=uap_height.get("base_height_min") or envelope.base_height_min,
                base_height_max=uap_height.get("base_height_max") or envelope.base_height_max,
                sky_exposure_plane=envelope.sky_exposure_plane,
                setbacks=envelope.setbacks,
                quality_housing=uap_height.get("quality_housing", envelope.quality_housing),
                height_factor=uap_height.get("height_factor", envelope.height_factor),
                rear_yard=envelope.rear_yard,
                ih_bonus_far=uap_bonus,
                front_yard=envelope.front_yard,
                side_yards_required=envelope.side_yards_required,
                side_yard_width=envelope.side_yard_width,
                lot_coverage_max=envelope.lot_coverage_max,
            )

            # Apply sliver law
            lot_front = lot.lot_frontage or 50
            sliver_ht = get_sliver_law_height(district, lot_front)
            if sliver_ht is not None and uap_envelope.max_building_height:
                uap_envelope.max_building_height = min(
                    uap_envelope.max_building_height, sliver_ht
                )

            uap_max_du = get_max_units_by_du_factor(district, uap_far * lot_area)

            scenario = self._build_residential_scenario(
                lot, uap_envelope, district, footprint,
                "UAP (City of Yes)",
                f"Universal Affordability Preference: FAR {uap_far:.2f} "
                f"(+{uap_bonus:.2f} bonus) with affordable housing at avg ≤60% AMI. "
                f"Height: {uap_max_height or 'no cap'} ft.",
                max_units_by_du=uap_max_du,
            )
            if scenario:
                scenarios.append(scenario)

        return scenarios

    # ──────────────────────────────────────────────────────────────
    # FOOTPRINT CALCULATION
    # ──────────────────────────────────────────────────────────────

    def _calculate_footprint(self, lot: LotProfile, envelope: ZoningEnvelope) -> float:
        """Calculate buildable footprint in SF.

        Footprint = lot_width × (lot_depth - rear_yard - front_yard),
        adjusted for side yards when required, then capped by lot coverage max.

        Lot coverage maximum (ZR 23-15, 24-11): the building footprint on any
        floor may not exceed the stated percentage of the lot area.
        For example, R6A interior lot on a wide street = 65% lot coverage.
        """
        lot_depth = lot.lot_depth or 100
        lot_front = lot.lot_frontage or 50
        lot_area = lot.lot_area or (lot_front * lot_depth)

        # Subtract yards from effective building area
        effective_depth = lot_depth - envelope.rear_yard - envelope.front_yard
        effective_width = lot_front
        if envelope.side_yards_required:
            effective_width -= envelope.side_yard_width * 2

        footprint = effective_width * effective_depth

        # Apply lot coverage maximum
        if envelope.lot_coverage_max and lot_area > 0:
            max_coverage_sf = lot_area * (envelope.lot_coverage_max / 100)
            footprint = min(footprint, max_coverage_sf)

        return max(footprint, 0)

    # ──────────────────────────────────────────────────────────────
    # BONUS PROGRAM SCENARIOS
    # ──────────────────────────────────────────────────────────────

    def _generate_bonus_scenarios(
        self,
        lot: LotProfile,
        envelope: ZoningEnvelope,
        district: str,
        base_scenarios: list[DevelopmentScenario],
        program_results: list,
    ) -> list[DevelopmentScenario]:
        """Generate individual + combined bonus scenarios from applicable programs.

        For each applicable program with a FAR bonus, creates a "Max Res + {Program}"
        scenario.  Also creates one combined "Max Development (All Programs)" scenario
        stacking all applicable bonuses.

        Skips programs that already have dedicated scenarios (UAP, MIH) and programs
        that only impose restrictions or are informational (IBZ, LSRD).
        """
        # Programs that already generate their own scenarios in generate_scenarios()
        _SKIP_KEYS = {"mih", "uap", "voluntary_ih"}
        # Programs that don't grant quantitative FAR bonuses
        _INFO_ONLY_CATEGORIES = {
            ProgramCategory.USE_FLEXIBILITY,
            ProgramCategory.RESILIENCE,
            ProgramCategory.LARGE_SCALE,
        }

        bonus_programs = []
        for r in program_results:
            if not r.applicable or not r.effect:
                continue
            if r.program_key in _SKIP_KEYS:
                continue
            if r.category in _INFO_ONLY_CATEGORIES:
                continue
            if r.effect.far_bonus <= 0 and r.effect.far_override is None:
                continue
            bonus_programs.append(r)

        if not bonus_programs:
            return []

        lot_area = lot.lot_area or 0
        footprint = self._calculate_footprint(lot, envelope)
        scenarios: list[DevelopmentScenario] = []

        # ── Individual bonus scenarios ──
        for prog in bonus_programs:
            bonus_far = prog.effect.far_bonus
            if bonus_far <= 0:
                continue

            bonus_envelope = ZoningEnvelope(
                residential_far=(envelope.residential_far or 0) + bonus_far,
                commercial_far=envelope.commercial_far,
                cf_far=envelope.cf_far,
                max_residential_zfa=((envelope.residential_far or 0) + bonus_far) * lot_area,
                max_building_height=envelope.max_building_height,
                base_height_min=envelope.base_height_min,
                base_height_max=envelope.base_height_max,
                sky_exposure_plane=envelope.sky_exposure_plane,
                setbacks=envelope.setbacks,
                quality_housing=envelope.quality_housing,
                height_factor=envelope.height_factor,
                rear_yard=envelope.rear_yard,
                front_yard=envelope.front_yard,
                side_yards_required=envelope.side_yards_required,
                side_yard_width=envelope.side_yard_width,
                lot_coverage_max=envelope.lot_coverage_max,
            )

            from app.zoning_engine.building_types import get_max_units_by_du_factor
            new_far = (envelope.residential_far or 0) + bonus_far
            bonus_du = get_max_units_by_du_factor(district, new_far * lot_area)

            scenario = self._build_residential_scenario(
                lot, bonus_envelope, district, footprint,
                f"Max Res + {prog.program_name}",
                f"Base FAR {envelope.residential_far or 0:.2f} + "
                f"{bonus_far:.2f} bonus ({prog.program_name}). "
                f"Total FAR {new_far:.2f}.",
                max_units_by_du=bonus_du,
            )
            if scenario:
                scenarios.append(scenario)

        # ── Combined "All Programs" scenario ──
        if len(bonus_programs) >= 2:
            total_bonus = sum(p.effect.far_bonus for p in bonus_programs if p.effect)
            if total_bonus > 0:
                combined_far = (envelope.residential_far or 0) + total_bonus
                combined_envelope = ZoningEnvelope(
                    residential_far=combined_far,
                    commercial_far=envelope.commercial_far,
                    cf_far=envelope.cf_far,
                    max_residential_zfa=combined_far * lot_area,
                    max_building_height=envelope.max_building_height,
                    base_height_min=envelope.base_height_min,
                    base_height_max=envelope.base_height_max,
                    sky_exposure_plane=envelope.sky_exposure_plane,
                    setbacks=envelope.setbacks,
                    quality_housing=envelope.quality_housing,
                    height_factor=envelope.height_factor,
                    rear_yard=envelope.rear_yard,
                    front_yard=envelope.front_yard,
                    side_yards_required=envelope.side_yards_required,
                    side_yard_width=envelope.side_yard_width,
                    lot_coverage_max=envelope.lot_coverage_max,
                )

                from app.zoning_engine.building_types import get_max_units_by_du_factor
                combined_du = get_max_units_by_du_factor(district, combined_far * lot_area)

                names = ", ".join(p.program_name for p in bonus_programs)
                scenario = self._build_residential_scenario(
                    lot, combined_envelope, district, footprint,
                    "Max Development (All Programs)",
                    f"All applicable bonuses stacked: {names}. "
                    f"Total FAR {combined_far:.2f} (+{total_bonus:.2f} bonus).",
                    max_units_by_du=combined_du,
                )
                if scenario:
                    scenarios.append(scenario)

        return scenarios

    # ──────────────────────────────────────────────────────────────
    # SCENARIO BUILDERS
    # ──────────────────────────────────────────────────────────────

    def _build_residential_scenario(
        self, lot: LotProfile, envelope: ZoningEnvelope,
        district: str, footprint: float,
        name: str = "Max Residential",
        description: str = "",
        max_units_by_area: int | None = None,
        max_units_by_du: int | None = None,
    ) -> DevelopmentScenario | None:
        """Build a residential-focused development scenario."""
        lot_area = lot.lot_area or 0
        if not envelope.residential_far or footprint <= 0:
            return None

        max_zfa = envelope.residential_far * lot_area

        # Determine building type
        btype = get_building_type_for_district(district)

        # Determine number of floors
        num_floors, floor_height_total, floors = self._calculate_floors(
            max_zfa, footprint, envelope, "residential",
            district=district,
            lot_frontage=lot.lot_frontage or 50,
            lot_depth=lot.lot_depth or 100,
        )
        if num_floors == 0:
            return None

        total_gross = sum(f.gross_sf for f in floors)

        # Floor area exemptions — ZFA is gross minus exempt area
        exemptions = calculate_exempt_area(
            total_gross,
            building_type=self._map_btype_to_exemption(btype, num_floors),
            has_cellar=True,
            parking_sf_below_grade=0,
        )
        zfa = total_gross - exemptions["total_exempt_sf"]

        # Core and loss factor
        core = self._estimate_core(num_floors, footprint, total_gross, "residential")
        loss = self._calculate_loss(total_gross, core)
        net_residential = loss.net_rentable_area

        # Unit mix — apply the strictest unit cap:
        #   1. R1-R5: lot area per DU (max_units_by_area)
        #   2. R6-R12: dwelling unit factor of 680 (max_units_by_du, ZR 23-52)
        unit_mix = self._generate_unit_mix(net_residential)

        # Determine the binding unit cap
        unit_cap = None
        if max_units_by_area is not None:
            unit_cap = max_units_by_area
        if max_units_by_du is not None:
            if unit_cap is None:
                unit_cap = max_units_by_du
            else:
                unit_cap = min(unit_cap, max_units_by_du)

        if unit_cap is not None and unit_mix.total_units > unit_cap:
            # Re-generate unit mix to fit within the cap
            avg_unit_sf = net_residential / unit_cap if unit_cap > 0 else 700
            unit_mix = self._generate_unit_mix(
                unit_cap * avg_unit_sf, strategy="balanced"
            )
            # Force exact count if rounding caused a mismatch
            if unit_mix.total_units != unit_cap:
                unit_mix = self._generate_unit_mix(
                    unit_cap * 700, strategy="family" if avg_unit_sf > 800 else "balanced"
                )

        # Parking (comprehensive)
        parking_data = calculate_parking(
            district=district,
            unit_count=unit_mix.total_units,
            lot_area=lot_area,
            borough=lot.borough,
            community_district=lot.pluto.cd if lot.pluto and lot.pluto.cd else 0,
        )
        parking = ParkingResult(
            residential_spaces_required=parking_data["residential_spaces_required"],
            commercial_spaces_required=parking_data["commercial_spaces_required"],
            total_spaces_required=parking_data["total_spaces_required"],
            waiver_eligible=parking_data["waiver_eligible"],
            parking_options=[ParkingOption(**o) for o in parking_data["parking_options"]],
        )

        return DevelopmentScenario(
            name=name,
            description=description,
            total_gross_sf=total_gross,
            total_net_sf=net_residential,
            zoning_floor_area=round(zfa),
            residential_sf=net_residential,
            total_units=unit_mix.total_units,
            unit_mix=unit_mix,
            parking=parking,
            loss_factor=loss,
            core=core,
            floor_area_exemptions=FloorAreaExemptions(
                total_exempt_sf=exemptions["total_exempt_sf"],
                gross_building_area=exemptions["gross_building_area"],
                exemption_ratio=exemptions["exemption_ratio"],
                breakdown=exemptions["breakdown"],
            ),
            floors=floors,
            max_height_ft=floor_height_total,
            num_floors=num_floors,
            far_used=round(zfa / lot_area, 2) if lot_area else 0,
        )

    def _build_max_units_scenario(
        self, lot: LotProfile, envelope: ZoningEnvelope,
        district: str, footprint: float,
        target_units: int,
        max_units_by_area: int | None = None,
    ) -> DevelopmentScenario | None:
        """Build a scenario that maximizes dwelling unit count.

        Uses smaller unit sizes (studios/1BRs) to hit the DU factor maximum
        permitted by ZR 23-52.  Same floor area as Max Residential, but
        more (smaller) units.
        """
        lot_area = lot.lot_area or 0
        if not envelope.residential_far or footprint <= 0:
            return None

        # Apply lot-area-based cap if applicable (R1-R5)
        if max_units_by_area is not None:
            target_units = min(target_units, max_units_by_area)
        if target_units <= 0:
            return None

        max_zfa = envelope.residential_far * lot_area

        # Calculate floors the same way as Max Residential
        num_floors, floor_height_total, floors = self._calculate_floors(
            max_zfa, footprint, envelope, "residential",
            district=district,
            lot_frontage=lot.lot_frontage or 50,
            lot_depth=lot.lot_depth or 100,
        )
        if num_floors == 0:
            return None

        total_gross = sum(f.gross_sf for f in floors)

        # Floor area exemptions
        btype = get_building_type_for_district(district)
        exemptions = calculate_exempt_area(
            total_gross,
            building_type=self._map_btype_to_exemption(btype, num_floors),
            has_cellar=True,
            parking_sf_below_grade=0,
        )
        zfa = total_gross - exemptions["total_exempt_sf"]

        # Core and loss factor
        core = self._estimate_core(num_floors, footprint, total_gross, "residential")
        loss = self._calculate_loss(total_gross, core)
        net_residential = loss.net_rentable_area

        # Generate unit mix optimized for maximum unit count
        # Use "maximize_units" strategy (50% studios, 35% 1BRs)
        unit_mix = self._generate_unit_mix(
            target_units * 480,  # target smaller avg unit size
            strategy="maximize_units",
        )

        # Adjust unit count to hit exact target
        if unit_mix.total_units != target_units:
            # Scale the mix
            if unit_mix.total_units > 0:
                scale = target_units / unit_mix.total_units
                for u in unit_mix.units:
                    u.count = max(1, round(u.count * scale))
            # Trim or add to hit exact target
            actual = sum(u.count for u in unit_mix.units)
            diff = target_units - actual
            if diff > 0 and unit_mix.units:
                unit_mix.units[0].count += diff  # add to studios
            elif diff < 0 and unit_mix.units:
                for u in reversed(unit_mix.units):
                    reduction = min(u.count - 1, -diff)
                    if reduction > 0:
                        u.count -= reduction
                        diff += reduction
                    if diff >= 0:
                        break
            unit_mix.total_units = sum(u.count for u in unit_mix.units)
            unit_mix.average_unit_sf = round(
                net_residential / unit_mix.total_units, 0
            ) if unit_mix.total_units > 0 else 0

        # Verify units fit in the available space
        if unit_mix.total_units <= 0:
            return None

        # Parking
        parking_data = calculate_parking(
            district=district,
            unit_count=unit_mix.total_units,
            lot_area=lot_area,
            borough=lot.borough,
            community_district=lot.pluto.cd if lot.pluto and lot.pluto.cd else 0,
        )
        parking = ParkingResult(
            residential_spaces_required=parking_data["residential_spaces_required"],
            commercial_spaces_required=parking_data["commercial_spaces_required"],
            total_spaces_required=parking_data["total_spaces_required"],
            waiver_eligible=parking_data["waiver_eligible"],
            parking_options=[ParkingOption(**o) for o in parking_data["parking_options"]],
        )

        return DevelopmentScenario(
            name="Max Units",
            description=(
                f"Maximize dwelling unit count to {target_units} units "
                f"(DU factor: ZFA {max_zfa:,.0f} / 680 = {max_zfa/680:.2f}, "
                f"rounded per ZR 23-52). Uses smaller unit sizes."
            ),
            total_gross_sf=total_gross,
            total_net_sf=net_residential,
            zoning_floor_area=round(zfa),
            residential_sf=net_residential,
            total_units=unit_mix.total_units,
            unit_mix=unit_mix,
            parking=parking,
            loss_factor=loss,
            core=core,
            floor_area_exemptions=FloorAreaExemptions(
                total_exempt_sf=exemptions["total_exempt_sf"],
                gross_building_area=exemptions["gross_building_area"],
                exemption_ratio=exemptions["exemption_ratio"],
                breakdown=exemptions["breakdown"],
            ),
            floors=floors,
            max_height_ft=floor_height_total,
            num_floors=num_floors,
            far_used=round(zfa / lot_area, 2) if lot_area else 0,
        )

    def _build_penthouse_scenario(
        self, lot: LotProfile, envelope: ZoningEnvelope,
        district: str, footprint: float,
        max_units_by_area: int | None = None,
        max_units_by_du: int | None = None,
    ) -> DevelopmentScenario | None:
        """Build a 4+1 Penthouse scenario (no elevator required).

        NYC penthouse rule (ZR 12-10): A penthouse occupying ≤1/3 of the
        roof area does not count as a story for building code purposes.
        This means 4 full floors + a penthouse = "4 stories" per code,
        avoiding the 6-story elevator requirement.  Single staircase is
        used (≤6 stories, ≤4,000 SF plates).
        """
        lot_area = lot.lot_area or 0
        if not envelope.residential_far or footprint <= 0:
            return None

        max_zfa = envelope.residential_far * lot_area

        # Check height limit allows 5 physical levels
        # 4 × 10 ft typical + 1 × 15 ft ground + 1 × 10 ft penthouse ≈ 65 ft
        is_qh = envelope.quality_housing
        heights = get_floor_heights(is_qh)
        ground_height = heights.get("ground_residential", 12)
        typical_height = heights.get("typical_residential", 10)
        penthouse_height = typical_height  # same as normal floor

        total_height_needed = ground_height + 3 * typical_height + penthouse_height
        if envelope.max_building_height and total_height_needed > envelope.max_building_height:
            return None

        # Build 4 full floors
        floors = []
        total_sf = 0
        total_height = 0
        for i in range(4):
            fh = ground_height if i == 0 else typical_height
            floor_sf = min(footprint, max_zfa - total_sf)
            if floor_sf <= 0:
                break
            floors.append(MassingFloor(
                floor=i + 1,
                use="residential",
                gross_sf=floor_sf,
                net_sf=floor_sf * 0.82,
                height_ft=fh,
            ))
            total_sf += floor_sf
            total_height += fh

        if len(floors) < 4:
            return None  # Can't build 4 full floors

        # Penthouse: 1/3 of top floor area (ZR 12-10 max)
        penthouse_fp = footprint / 3.0
        penthouse_sf = min(penthouse_fp, max_zfa - total_sf)
        if penthouse_sf > 0:
            floors.append(MassingFloor(
                floor=5,
                use="residential",
                gross_sf=penthouse_sf,
                net_sf=penthouse_sf * 0.85,  # Smaller core on penthouse
                height_ft=penthouse_height,
            ))
            total_sf += penthouse_sf
            total_height += penthouse_height

        num_floors = len(floors)
        total_gross = sum(f.gross_sf for f in floors)

        # Floor area exemptions
        btype = get_building_type_for_district(district)
        exemptions = calculate_exempt_area(
            total_gross,
            building_type=self._map_btype_to_exemption(btype, 4),  # 4 stories per code
            has_cellar=True,
            parking_sf_below_grade=0,
        )
        zfa = total_gross - exemptions["total_exempt_sf"]

        # Core: single staircase, NO elevator (building is "4 stories" per code)
        core = self._estimate_core(4, footprint, total_gross, "residential")
        # Override: force single staircase, zero elevators
        core = CoreEstimate(
            elevators=0,
            stairs=1,
            elevator_sf_per_floor=0,
            stair_sf_per_floor=150,
            mechanical_sf_per_floor=core.mechanical_sf_per_floor,
            corridor_sf_per_floor=core.corridor_sf_per_floor,
            total_core_sf_per_floor=150 + core.mechanical_sf_per_floor + core.corridor_sf_per_floor,
            core_percentage=round(
                (150 + core.mechanical_sf_per_floor + core.corridor_sf_per_floor) / footprint * 100, 1
            ) if footprint > 0 else 0,
        )

        loss = self._calculate_loss(total_gross, core)
        net_residential = loss.net_rentable_area

        # Unit mix
        unit_mix = self._generate_unit_mix(net_residential)

        # Apply unit cap
        unit_cap = None
        if max_units_by_area is not None:
            unit_cap = max_units_by_area
        if max_units_by_du is not None:
            if unit_cap is None:
                unit_cap = max_units_by_du
            else:
                unit_cap = min(unit_cap, max_units_by_du)

        if unit_cap is not None and unit_mix.total_units > unit_cap:
            avg_unit_sf = net_residential / unit_cap if unit_cap > 0 else 700
            unit_mix = self._generate_unit_mix(unit_cap * avg_unit_sf, strategy="balanced")

        # Parking
        parking_data = calculate_parking(
            district=district,
            unit_count=unit_mix.total_units,
            lot_area=lot_area,
            borough=lot.borough,
            community_district=lot.pluto.cd if lot.pluto and lot.pluto.cd else 0,
        )
        parking = ParkingResult(
            residential_spaces_required=parking_data["residential_spaces_required"],
            commercial_spaces_required=parking_data["commercial_spaces_required"],
            total_spaces_required=parking_data["total_spaces_required"],
            waiver_eligible=parking_data["waiver_eligible"],
            parking_options=[ParkingOption(**o) for o in parking_data["parking_options"]],
        )

        # Display as 4.3 floors (4 full + penthouse at 1/3 area)
        penthouse_fraction = round(penthouse_sf / footprint, 1) if footprint > 0 and penthouse_sf > 0 else 0
        display_floors = 4 + penthouse_fraction

        return DevelopmentScenario(
            name="4+1 Penthouse (No Elevator)",
            description=(
                f"{display_floors} floors: 4 full floors + penthouse at 1/3 roof "
                f"area ({penthouse_sf:,.0f} SF, ZR 12-10). "
                f"Penthouse doesn't count as a story → no elevator required. "
                f"Single staircase saves ~150 SF/floor."
            ),
            total_gross_sf=total_gross,
            total_net_sf=net_residential,
            zoning_floor_area=round(zfa),
            residential_sf=net_residential,
            total_units=unit_mix.total_units,
            unit_mix=unit_mix,
            parking=parking,
            loss_factor=loss,
            core=core,
            floor_area_exemptions=FloorAreaExemptions(
                total_exempt_sf=exemptions["total_exempt_sf"],
                gross_building_area=exemptions["gross_building_area"],
                exemption_ratio=exemptions["exemption_ratio"],
                breakdown=exemptions["breakdown"],
            ),
            floors=floors,
            max_height_ft=total_height,
            num_floors=num_floors,
            far_used=round(zfa / lot_area, 2) if lot_area else 0,
        )

    def _build_commercial_scenario(
        self, lot: LotProfile, envelope: ZoningEnvelope,
        district: str, footprint: float,
    ) -> DevelopmentScenario | None:
        """Build a commercial-focused development scenario."""
        lot_area = lot.lot_area or 0
        if not envelope.commercial_far or footprint <= 0:
            return None

        max_zfa = envelope.commercial_far * lot_area
        num_floors, floor_height_total, floors = self._calculate_floors(
            max_zfa, footprint, envelope, "commercial",
            district=district,
            lot_frontage=lot.lot_frontage or 50,
            lot_depth=lot.lot_depth or 100,
        )
        if num_floors == 0:
            return None

        total_gross = sum(f.gross_sf for f in floors)

        # Floor area exemptions for commercial
        exemptions = calculate_exempt_area(
            total_gross,
            building_type="commercial_office",
            has_cellar=True,
            parking_sf_below_grade=0,
        )
        zfa = total_gross - exemptions["total_exempt_sf"]

        core = self._estimate_core(num_floors, footprint, total_gross, "commercial")
        loss = self._calculate_loss(total_gross, core)

        return DevelopmentScenario(
            name="Max Commercial",
            description="Maximize commercial floor area.",
            total_gross_sf=total_gross,
            total_net_sf=loss.net_rentable_area,
            zoning_floor_area=round(zfa),
            commercial_sf=loss.net_rentable_area,
            loss_factor=loss,
            core=core,
            floor_area_exemptions=FloorAreaExemptions(
                total_exempt_sf=exemptions["total_exempt_sf"],
                gross_building_area=exemptions["gross_building_area"],
                exemption_ratio=exemptions["exemption_ratio"],
                breakdown=exemptions["breakdown"],
            ),
            floors=floors,
            max_height_ft=floor_height_total,
            num_floors=num_floors,
            far_used=round(zfa / lot_area, 2) if lot_area else 0,
        )

    def _build_mixed_use_scenario(
        self, lot: LotProfile, envelope: ZoningEnvelope,
        district: str, footprint: float,
        max_units_by_area: int | None = None,
        max_units_by_du: int | None = None,
    ) -> DevelopmentScenario | None:
        """Build mixed-use scenario: ground floor retail + upper residential."""
        lot_area = lot.lot_area or 0
        res_far = envelope.residential_far or 0
        comm_far = envelope.commercial_far or 0
        if res_far <= 0 or footprint <= 0:
            return None

        # Ground floor commercial (1 floor)
        ground_floor_height = FLOOR_HEIGHTS["ground_commercial"]
        commercial_sf = footprint  # Full ground floor

        # Remaining FAR for residential
        remaining_zfa = res_far * lot_area - commercial_sf
        if remaining_zfa <= 0:
            return None

        # Calculate residential floors — use ceil so partial top floors fill max FAR
        res_floors = max(1, math.ceil(remaining_zfa / footprint))
        max_height = envelope.max_building_height
        if max_height:
            available_height = max_height - ground_floor_height
            max_res_floors = max(1, int(available_height / FLOOR_HEIGHTS["typical_residential"]))
            res_floors = min(res_floors, max_res_floors)

        # Build floor list
        floors = [
            MassingFloor(
                floor=1, use="commercial",
                gross_sf=commercial_sf,
                net_sf=commercial_sf * 0.93,
                height_ft=ground_floor_height,
            )
        ]
        total_height = ground_floor_height
        res_sf_remaining = remaining_zfa
        for i in range(res_floors):
            fh = FLOOR_HEIGHTS["typical_residential"]
            # Last floor may be partial to fill remaining ZFA exactly
            floor_sf = min(footprint, res_sf_remaining)
            if floor_sf <= 0:
                break
            floors.append(MassingFloor(
                floor=i + 2, use="residential",
                gross_sf=floor_sf,
                net_sf=floor_sf * 0.82,
                height_ft=fh,
            ))
            res_sf_remaining -= floor_sf
            total_height += fh

        total_gross = sum(f.gross_sf for f in floors)
        total_res_gross = sum(f.gross_sf for f in floors if f.use == "residential")
        num_floors = len(floors)

        # Floor area exemptions for mixed-use
        exemptions = calculate_exempt_area(
            total_gross,
            building_type="mixed_use",
            has_cellar=True,
            parking_sf_below_grade=0,
        )
        zfa = total_gross - exemptions["total_exempt_sf"]

        core = self._estimate_core(num_floors, footprint, total_gross, "mixed")
        loss = self._calculate_loss(total_res_gross, core)
        net_residential = loss.net_rentable_area
        unit_mix = self._generate_unit_mix(net_residential)

        # Apply strictest unit cap (lot area per DU or DU factor)
        unit_cap = None
        if max_units_by_area is not None:
            unit_cap = max_units_by_area
        if max_units_by_du is not None:
            if unit_cap is None:
                unit_cap = max_units_by_du
            else:
                unit_cap = min(unit_cap, max_units_by_du)

        if unit_cap is not None and unit_mix.total_units > unit_cap:
            avg_unit_sf = net_residential / unit_cap if unit_cap > 0 else 700
            unit_mix = self._generate_unit_mix(
                unit_cap * avg_unit_sf, strategy="balanced"
            )
            if unit_mix.total_units != unit_cap:
                unit_mix = self._generate_unit_mix(
                    unit_cap * 700, strategy="family" if avg_unit_sf > 800 else "balanced"
                )

        parking_data = calculate_parking(
            district=district,
            unit_count=unit_mix.total_units,
            commercial_sf=commercial_sf,
            lot_area=lot_area,
            borough=lot.borough,
            community_district=lot.pluto.cd if lot.pluto and lot.pluto.cd else 0,
        )
        parking = ParkingResult(
            residential_spaces_required=parking_data["residential_spaces_required"],
            commercial_spaces_required=parking_data["commercial_spaces_required"],
            total_spaces_required=parking_data["total_spaces_required"],
            waiver_eligible=parking_data["waiver_eligible"],
            parking_options=[ParkingOption(**o) for o in parking_data["parking_options"]],
        )

        return DevelopmentScenario(
            name="Mixed-Use (Retail + Residential)",
            description="Ground floor retail with upper floor residential — most common outer-borough development.",
            total_gross_sf=total_gross,
            total_net_sf=net_residential + commercial_sf * 0.93,
            zoning_floor_area=round(zfa),
            residential_sf=net_residential,
            commercial_sf=commercial_sf * 0.93,
            total_units=unit_mix.total_units,
            unit_mix=unit_mix,
            parking=parking,
            loss_factor=loss,
            core=core,
            floor_area_exemptions=FloorAreaExemptions(
                total_exempt_sf=exemptions["total_exempt_sf"],
                gross_building_area=exemptions["gross_building_area"],
                exemption_ratio=exemptions["exemption_ratio"],
                breakdown=exemptions["breakdown"],
            ),
            floors=floors,
            max_height_ft=total_height,
            num_floors=num_floors,
            far_used=round(zfa / lot_area, 2) if lot_area else 0,
        )

    def _build_cf_scenario(
        self, lot: LotProfile, envelope: ZoningEnvelope,
        district: str, footprint: float,
    ) -> DevelopmentScenario | None:
        """Build a community facility scenario."""
        lot_area = lot.lot_area or 0
        if not envelope.cf_far or footprint <= 0:
            return None

        max_zfa = envelope.cf_far * lot_area
        num_floors, floor_height_total, floors = self._calculate_floors(
            max_zfa, footprint, envelope, "community_facility",
            district=district,
            lot_frontage=lot.lot_frontage or 50,
            lot_depth=lot.lot_depth or 100,
        )
        if num_floors == 0:
            return None

        # Relabel floors
        for f in floors:
            f.use = "community_facility"

        total_gross = sum(f.gross_sf for f in floors)

        # Floor area exemptions for CF
        exemptions = calculate_exempt_area(
            total_gross,
            building_type="commercial_office",  # CF uses similar exemptions
            has_cellar=True,
            parking_sf_below_grade=0,
        )
        zfa = total_gross - exemptions["total_exempt_sf"]

        core = self._estimate_core(num_floors, footprint, total_gross, "cf")
        loss = self._calculate_loss(total_gross, core)

        return DevelopmentScenario(
            name="Community Facility",
            description=f"Community facility use with higher FAR ({envelope.cf_far}).",
            total_gross_sf=total_gross,
            total_net_sf=loss.net_rentable_area,
            zoning_floor_area=round(zfa),
            cf_sf=loss.net_rentable_area,
            loss_factor=loss,
            core=core,
            floor_area_exemptions=FloorAreaExemptions(
                total_exempt_sf=exemptions["total_exempt_sf"],
                gross_building_area=exemptions["gross_building_area"],
                exemption_ratio=exemptions["exemption_ratio"],
                breakdown=exemptions["breakdown"],
            ),
            floors=floors,
            max_height_ft=floor_height_total,
            num_floors=num_floors,
            far_used=round(zfa / lot_area, 2) if lot_area else 0,
        )

    def _build_residential_cf_scenario(
        self, lot: LotProfile, envelope: ZoningEnvelope,
        district: str, footprint: float,
        max_units_by_area: int | None = None,
        max_units_by_du: int | None = None,
    ) -> DevelopmentScenario | None:
        """Build a combined Residential + Community Facility scenario.

        Per ZR 24-10/24-16: uses can be combined as long as:
          - Residential component does not exceed max residential FAR
          - CF component does not exceed max CF FAR
          - Total building bulk does not exceed highest permitted single-use FAR

        For R6: res FAR=3.0 (wide), CF FAR=4.8.
        Strategy: use full residential FAR + fill remaining with CF up to total cap.
        The total building is limited to the CF FAR (the highest single-use FAR).
        """
        lot_area = lot.lot_area or 0
        res_far = envelope.residential_far or 0
        cf_far = envelope.cf_far or 0
        if res_far <= 0 or cf_far <= 0 or footprint <= 0:
            return None

        # Total building FAR cannot exceed the highest single-use FAR
        max_total_far = max(res_far, cf_far)
        max_res_zfa = res_far * lot_area
        cf_zfa = min(cf_far * lot_area, (max_total_far - res_far) * lot_area)
        total_zfa = max_res_zfa + cf_zfa

        # Determine how many floors of each use can fit in the envelope
        max_height = envelope.max_building_height
        ground_ht = FLOOR_HEIGHTS["ground_commercial"]
        typical_res_ht = FLOOR_HEIGHTS["typical_residential"]
        typical_cf_ht = FLOOR_HEIGHTS["typical_cf"]

        # Strategy: CF on lower floors (ground + a few), residential above
        # Ground floor: CF (14 ft)
        cf_floor_sf = footprint
        cf_floors_needed = max(1, math.ceil(cf_zfa / footprint))

        # Cap CF floors by available height
        if max_height:
            # Reserve at least 2 residential floors above CF
            cf_max_height = max_height - (2 * typical_res_ht)
            cf_floors_by_ht = max(1, int(cf_max_height / typical_cf_ht))
            cf_floors_needed = min(cf_floors_needed, cf_floors_by_ht)

        # Build floor list
        floors = []
        total_height = 0
        total_cf_sf = 0
        total_res_sf = 0

        # CF floors (lower portion)
        for i in range(cf_floors_needed):
            fh = ground_ht if i == 0 else typical_cf_ht
            floor_sf = min(footprint, cf_zfa - total_cf_sf)
            if floor_sf <= 0:
                break
            if max_height and total_height + fh > max_height:
                break
            floors.append(MassingFloor(
                floor=i + 1, use="community_facility",
                gross_sf=floor_sf, net_sf=floor_sf * 0.88,
                height_ft=fh,
            ))
            total_cf_sf += floor_sf
            total_height += fh

        # Residential floors (upper portion)
        remaining_res_zfa = max_res_zfa
        while remaining_res_zfa > 0:
            if max_height and total_height + typical_res_ht > max_height:
                break
            floor_sf = min(footprint, remaining_res_zfa)
            if floor_sf <= 0:
                break
            floor_num = len(floors) + 1
            floors.append(MassingFloor(
                floor=floor_num, use="residential",
                gross_sf=floor_sf, net_sf=floor_sf * 0.82,
                height_ft=typical_res_ht,
            ))
            total_res_sf += floor_sf
            remaining_res_zfa -= floor_sf
            total_height += typical_res_ht

        if not floors:
            return None

        total_gross = sum(f.gross_sf for f in floors)
        total_res_gross = sum(f.gross_sf for f in floors if f.use == "residential")
        total_cf_gross = sum(f.gross_sf for f in floors if f.use == "community_facility")
        num_floors = len(floors)

        # Floor area exemptions
        exemptions = calculate_exempt_area(
            total_gross,
            building_type="mixed_use",
            has_cellar=True,
            parking_sf_below_grade=0,
        )
        zfa = total_gross - exemptions["total_exempt_sf"]

        # Core and loss (apply to residential only)
        core = self._estimate_core(num_floors, footprint, total_gross, "mixed")
        loss = self._calculate_loss(total_res_gross, core)
        net_residential = loss.net_rentable_area

        # Unit mix from actual built residential area
        unit_mix = self._generate_unit_mix(net_residential)

        # Apply DU factor cap
        unit_cap = None
        if max_units_by_area is not None:
            unit_cap = max_units_by_area
        if max_units_by_du is not None:
            if unit_cap is None:
                unit_cap = max_units_by_du
            else:
                unit_cap = min(unit_cap, max_units_by_du)

        if unit_cap is not None and unit_mix.total_units > unit_cap:
            avg_unit_sf = net_residential / unit_cap if unit_cap > 0 else 700
            unit_mix = self._generate_unit_mix(
                unit_cap * avg_unit_sf, strategy="balanced"
            )

        # Parking
        parking_data = calculate_parking(
            district=district,
            unit_count=unit_mix.total_units,
            lot_area=lot_area,
            borough=lot.borough,
            community_district=lot.pluto.cd if lot.pluto and lot.pluto.cd else 0,
        )
        parking = ParkingResult(
            residential_spaces_required=parking_data["residential_spaces_required"],
            commercial_spaces_required=parking_data["commercial_spaces_required"],
            total_spaces_required=parking_data["total_spaces_required"],
            waiver_eligible=parking_data["waiver_eligible"],
            parking_options=[ParkingOption(**o) for o in parking_data["parking_options"]],
        )

        cf_net = total_cf_gross * 0.88  # CF efficiency
        res_far_used = round(total_res_gross / lot_area, 2) if lot_area else 0
        cf_far_used = round(total_cf_gross / lot_area, 2) if lot_area else 0

        return DevelopmentScenario(
            name="Residential + Community Facility",
            description=(
                f"Combined use: residential (FAR {res_far_used}) + "
                f"CF (FAR {cf_far_used}). Total bulk limited to highest "
                f"single-use FAR ({max(res_far, cf_far):.1f})."
            ),
            total_gross_sf=total_gross,
            total_net_sf=net_residential + cf_net,
            zoning_floor_area=round(zfa),
            residential_sf=net_residential,
            cf_sf=cf_net,
            total_units=unit_mix.total_units,
            unit_mix=unit_mix,
            parking=parking,
            loss_factor=loss,
            core=core,
            floor_area_exemptions=FloorAreaExemptions(
                total_exempt_sf=exemptions["total_exempt_sf"],
                gross_building_area=exemptions["gross_building_area"],
                exemption_ratio=exemptions["exemption_ratio"],
                breakdown=exemptions["breakdown"],
            ),
            floors=floors,
            max_height_ft=total_height,
            num_floors=num_floors,
            far_used=round(zfa / lot_area, 2) if lot_area else 0,
        )

    def _build_tower_scenario(
        self, lot: LotProfile, envelope: ZoningEnvelope,
        district: str, tower_info: dict,
    ) -> DevelopmentScenario | None:
        """Build a tower-on-base scenario for high-density districts.

        Tower-on-base (ZR 23-65): building has a wide base (podium) at
        the street wall, then sets back to a narrower tower above.
        """
        lot_area = lot.lot_area or 0
        if not envelope.residential_far or lot_area <= 0:
            return None

        max_zfa = envelope.residential_far * lot_area
        base_footprint = tower_info.get("base_footprint_sf", 0)
        tower_footprint = tower_info.get("tower_footprint_sf", 0)
        base_max_ht = tower_info.get("base_height_max", 85)

        if base_footprint <= 0 or tower_footprint <= 0:
            return None

        # Build base floors (at street wall)
        base_floors_count = max(1, int(base_max_ht / FLOOR_HEIGHTS["typical_residential"]))
        ground_ht = FLOOR_HEIGHTS["ground_commercial"]
        typical_ht = FLOOR_HEIGHTS["typical_residential"]

        floors = []
        total_sf = 0
        total_height = 0

        # Ground floor (retail in base)
        ground_sf = min(base_footprint, max_zfa)
        floors.append(MassingFloor(
            floor=1, use="commercial",
            gross_sf=ground_sf, net_sf=ground_sf * 0.93,
            height_ft=ground_ht,
        ))
        total_sf += ground_sf
        total_height += ground_ht

        # Base floors 2+
        for i in range(1, base_floors_count):
            floor_sf = min(base_footprint, max_zfa - total_sf)
            if floor_sf <= 0:
                break
            floors.append(MassingFloor(
                floor=i + 1, use="residential",
                gross_sf=floor_sf, net_sf=floor_sf * 0.82,
                height_ft=typical_ht,
            ))
            total_sf += floor_sf
            total_height += typical_ht

        # Tower floors (above base, smaller footprint)
        remaining_zfa = max_zfa - total_sf
        tower_floor_count = max(0, math.ceil(remaining_zfa / tower_footprint)) if tower_footprint > 0 else 0

        # Height limit (if any)
        if envelope.max_building_height:
            remaining_height = envelope.max_building_height - total_height
            max_tower_floors = max(0, int(remaining_height / typical_ht))
            tower_floor_count = min(tower_floor_count, max_tower_floors)

        # Cap tower to reasonable height
        tower_floor_count = min(tower_floor_count, 80)

        for i in range(tower_floor_count):
            floor_sf = min(tower_footprint, max_zfa - total_sf)
            if floor_sf <= 0:
                break
            floor_num = len(floors) + 1
            floors.append(MassingFloor(
                floor=floor_num, use="residential",
                gross_sf=floor_sf, net_sf=floor_sf * 0.82,
                height_ft=typical_ht,
            ))
            total_sf += floor_sf
            total_height += typical_ht

        if len(floors) <= 1:
            return None

        total_gross = sum(f.gross_sf for f in floors)
        total_res_gross = sum(f.gross_sf for f in floors if f.use == "residential")
        num_floors = len(floors)

        # Floor area exemptions for tower
        exemptions = calculate_exempt_area(
            total_gross,
            building_type="residential_tower" if num_floors > 20 else "residential_elevator",
            has_cellar=True,
            parking_sf_below_grade=0,
        )
        zfa = total_gross - exemptions["total_exempt_sf"]

        core = self._estimate_core(num_floors, tower_footprint, total_gross, "residential")
        loss = self._calculate_loss(total_res_gross, core)
        net_residential = loss.net_rentable_area
        unit_mix = self._generate_unit_mix(net_residential)

        parking_data = calculate_parking(
            district=district,
            unit_count=unit_mix.total_units,
            commercial_sf=floors[0].gross_sf,
            lot_area=lot_area,
            borough=lot.borough,
            community_district=lot.pluto.cd if lot.pluto and lot.pluto.cd else 0,
        )
        parking = ParkingResult(
            residential_spaces_required=parking_data["residential_spaces_required"],
            commercial_spaces_required=parking_data["commercial_spaces_required"],
            total_spaces_required=parking_data["total_spaces_required"],
            waiver_eligible=parking_data["waiver_eligible"],
            parking_options=[ParkingOption(**o) for o in parking_data["parking_options"]],
        )

        return DevelopmentScenario(
            name="Tower-on-Base",
            description=(
                f"Tower-on-base: {base_floors_count}-story podium "
                f"({base_footprint:,.0f} SF footprint) + "
                f"{tower_floor_count}-story tower "
                f"({tower_footprint:,.0f} SF footprint, "
                f"{tower_info.get('tower_coverage_pct', 0):.0f}% lot coverage)."
            ),
            total_gross_sf=total_gross,
            total_net_sf=net_residential + floors[0].net_sf,
            zoning_floor_area=round(zfa),
            residential_sf=net_residential,
            commercial_sf=floors[0].net_sf,
            total_units=unit_mix.total_units,
            unit_mix=unit_mix,
            parking=parking,
            loss_factor=loss,
            core=core,
            floor_area_exemptions=FloorAreaExemptions(
                total_exempt_sf=exemptions["total_exempt_sf"],
                gross_building_area=exemptions["gross_building_area"],
                exemption_ratio=exemptions["exemption_ratio"],
                breakdown=exemptions["breakdown"],
            ),
            floors=floors,
            max_height_ft=total_height,
            num_floors=num_floors,
            far_used=round(zfa / lot_area, 2) if lot_area else 0,
        )

    # ──────────────────────────────────────────────────────────────
    # FLOOR CALCULATION
    # ──────────────────────────────────────────────────────────────

    def _calculate_floors(
        self, max_zfa: float, footprint: float,
        envelope: ZoningEnvelope, use_type: str,
        district: str = "",
        lot_frontage: float = 50,
        lot_depth: float = 100,
    ) -> tuple[int, float, list[MassingFloor]]:
        """Calculate number of floors that fit within zoning constraints.

        Uses correct QH floor heights when applicable.
        Applies dormer rules to upper floors in contextual districts.
        """
        if footprint <= 0:
            return 0, 0, []

        # Use QH floor heights if this is a Quality Housing envelope
        is_qh = envelope.quality_housing
        heights = get_floor_heights(is_qh)

        floor_height_key = f"typical_{use_type}" if f"typical_{use_type}" in heights else "typical_residential"
        typical_height = heights.get(floor_height_key, 10)
        ground_height = heights.get(f"ground_{use_type}", typical_height)

        # Use ceil so partial top floors are included — always build to max FAR
        max_floors_by_area = max(1, math.ceil(max_zfa / footprint))

        # Limit by height
        if envelope.max_building_height:
            max_height = envelope.max_building_height
            available = max_height - ground_height
            max_floors_by_height = 1 + max(0, int(available / typical_height))
            num_floors = min(max_floors_by_area, max_floors_by_height)
        else:
            num_floors = max_floors_by_area

        # Cap at reasonable maximum
        num_floors = min(num_floors, 100)

        # Get dormer rules for upper floor area adjustment
        dormer = get_dormer_rules(district) if district else {"eligible": False}
        base_max_ht = envelope.base_height_max or 0
        setback = envelope.setbacks.front_setback_above_base if envelope.setbacks else 0

        # Build floor list, adjusting upper floors for setback + dormer
        floors = []
        total_sf = 0
        total_height = 0
        for i in range(num_floors):
            fh = ground_height if i == 0 else typical_height
            current_height = total_height + fh

            # Determine floor footprint
            if is_qh and base_max_ht > 0 and total_height >= base_max_ht and setback > 0:
                # Floor is above base height — apply setback (with dormer adjustment)
                if dormer.get("eligible"):
                    floor_fp = calculate_upper_floor_area(
                        footprint, lot_frontage, lot_depth, setback, district,
                    )
                else:
                    # Full setback: reduce depth by setback amount
                    effective_depth = max(0, lot_depth - setback)
                    floor_fp = lot_frontage * effective_depth
                    floor_fp = min(floor_fp, footprint)
            else:
                floor_fp = footprint

            floor_sf = min(floor_fp, max_zfa - total_sf)
            if floor_sf <= 0:
                break

            floors.append(MassingFloor(
                floor=i + 1,
                use=use_type,
                gross_sf=floor_sf,
                net_sf=floor_sf * 0.82,
                height_ft=fh,
            ))
            total_sf += floor_sf
            total_height += fh

        return len(floors), total_height, floors

    # ──────────────────────────────────────────────────────────────
    # CORE / LOSS / UNIT MIX
    # ──────────────────────────────────────────────────────────────

    def _estimate_core(
        self, num_floors: int, footprint: float,
        total_gross: float, use_type: str,
    ) -> CoreEstimate:
        """Estimate vertical core requirements."""
        # Elevators
        if num_floors <= 6:
            elevators = max(0, num_floors - 3)  # 0 for <=3, 1-3 for 4-6
            elevators = min(elevators, 1)
        elif num_floors <= 12:
            elevators = 2
        elif num_floors <= 20:
            elevators = 3
        elif num_floors <= 30:
            elevators = 4
        else:
            elevators = 4 + (num_floors - 30) // 15

        # Stairs — NYC single-stair reform (2024):
        # ≤6 stories AND ≤4,000 SF floor plates → single staircase allowed
        if num_floors <= 6 and footprint <= 4000:
            stairs = 1
        elif num_floors <= 30:
            stairs = 2
        else:
            stairs = 3

        elevator_sf = elevators * 75
        stair_sf = stairs * 150
        mechanical_sf = footprint * 0.03  # 3% per floor for MEP
        corridor_sf = footprint * 0.08  # corridors

        total_core = elevator_sf + stair_sf + mechanical_sf + corridor_sf
        core_pct = (total_core / footprint * 100) if footprint > 0 else 0

        return CoreEstimate(
            elevators=elevators,
            stairs=stairs,
            elevator_sf_per_floor=elevator_sf,
            stair_sf_per_floor=stair_sf,
            mechanical_sf_per_floor=mechanical_sf,
            corridor_sf_per_floor=corridor_sf,
            total_core_sf_per_floor=total_core,
            core_percentage=round(core_pct, 1),
        )

    def _calculate_loss(self, gross_sf: float, core: CoreEstimate) -> LossFactorResult:
        """Calculate loss factor from gross to net."""
        common = gross_sf * (core.core_percentage / 100)
        # Add lobby (ground floor ~500 SF)
        common += 500
        net = gross_sf - common
        loss_pct = (common / gross_sf * 100) if gross_sf > 0 else 0

        return LossFactorResult(
            gross_building_area=gross_sf,
            total_common_area=round(common, 0),
            net_rentable_area=round(max(net, 0), 0),
            loss_factor_pct=round(loss_pct, 1),
            efficiency_ratio=round(net / gross_sf, 3) if gross_sf > 0 else 0,
        )

    def _generate_unit_mix(
        self, net_residential_sf: float, strategy: str = "balanced",
    ) -> UnitMixResult:
        """Generate a unit mix based on net residential area."""
        if net_residential_sf <= 0:
            return UnitMixResult(units=[], total_units=0, average_unit_sf=0, units_per_floor=0)

        unit_sizes = {
            "studio": 400,
            "1br": 625,
            "2br": 875,
            "3br": 1150,
        }

        if strategy == "maximize_units":
            mix_pcts = {"studio": 0.50, "1br": 0.35, "2br": 0.10, "3br": 0.05}
        elif strategy == "family":
            mix_pcts = {"studio": 0.05, "1br": 0.20, "2br": 0.45, "3br": 0.30}
        elif strategy == "luxury":
            mix_pcts = {"studio": 0.05, "1br": 0.25, "2br": 0.40, "3br": 0.30}
        else:  # balanced
            mix_pcts = {"studio": 0.15, "1br": 0.40, "2br": 0.30, "3br": 0.15}

        # Calculate weighted average unit size
        avg_size = sum(unit_sizes[t] * pct for t, pct in mix_pcts.items())
        total_units = max(1, int(net_residential_sf / avg_size))

        units = []
        for unit_type, pct in mix_pcts.items():
            count = max(0, round(total_units * pct))
            if count > 0:
                units.append(UnitMix(
                    type=unit_type,
                    count=count,
                    avg_sf=unit_sizes[unit_type],
                ))

        actual_total = sum(u.count for u in units)
        actual_avg = net_residential_sf / actual_total if actual_total > 0 else 0

        return UnitMixResult(
            units=units,
            total_units=actual_total,
            average_unit_sf=round(actual_avg, 0),
            units_per_floor=0,  # Filled in by caller if needed
        )

    # ──────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────

    def _map_btype_to_exemption(self, btype: str, num_floors: int) -> str:
        """Map building type to floor area exemption category."""
        if btype in ("detached", "semi_detached", "attached"):
            return "residential_walkup"
        if num_floors <= 6:
            return "residential_walkup"
        if num_floors <= 20:
            return "residential_elevator"
        return "residential_tower"

    def _get_special_district_info(self, spdist_codes: list[str]) -> dict:
        """Gather special district information for the result.

        Returns a dict with applicable special district rules,
        available bonuses, and mandatory requirements.
        """
        if not spdist_codes:
            return {
                "applicable": False,
                "districts": [],
                "bonuses": [],
                "mandatory_inclusionary": False,
                "tdr_available": False,
            }

        districts = []
        mandatory_ih = False
        tdr_available = False

        for code in spdist_codes:
            rules = get_special_district_rules(code)
            if rules:
                districts.append({
                    "code": code,
                    "name": rules["name"],
                    "description": rules.get("description", ""),
                    "has_far_override": "far_override" in rules and rules["far_override"] is not None,
                })
                if rules.get("mandatory_inclusionary"):
                    mandatory_ih = True
                if rules.get("tdr_available"):
                    tdr_available = True

        bonuses = get_special_district_bonuses(spdist_codes)

        return {
            "applicable": len(districts) > 0,
            "districts": districts,
            "bonuses": bonuses,
            "mandatory_inclusionary": mandatory_ih,
            "tdr_available": tdr_available,
        }
