"""
Master registry of all NYC zoning programs and special circumstances.

Every property is checked against every registered program during report
generation.  Programs are categorized as:

  - AFFORDABLE_HOUSING:  MIH, UAP, Voluntary IH
  - COMMERCIAL_BONUS:    FRESH
  - SPECIAL_DISTRICT:    All 20+ special districts
  - TRANSFER_RIGHTS:     Landmark TDR, Special District TDR banks
  - LARGE_SCALE:         LSRD, LSGD
  - USE_FLEXIBILITY:     Office conversion, IBZ, IIA, ADU, Shared Housing
  - BULK_ENVELOPE:       Quality Housing, Transit Parking, Overlays, CF FAR
  - RESILIENCE:          Coastal / flood zone requirements

Usage::

    from app.zoning_engine.programs import check_all_programs
    results = check_all_programs(lot_profile)
    applicable = [r for r in results if r.applicable]
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from app.models.schemas import LotProfile

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────────────────────────

class ProgramCategory(str, Enum):
    AFFORDABLE_HOUSING = "affordable_housing"
    COMMERCIAL_BONUS = "commercial_bonus"
    SPECIAL_DISTRICT = "special_district"
    TRANSFER_RIGHTS = "transfer_rights"
    LARGE_SCALE = "large_scale"
    USE_FLEXIBILITY = "use_flexibility"
    BULK_ENVELOPE = "bulk_envelope"
    RESILIENCE = "resilience"


@dataclass
class ProgramEffect:
    """Quantified effect of a program on development parameters."""
    far_bonus: float = 0.0
    far_override: Optional[float] = None
    height_bonus_ft: float = 0.0
    height_override_ft: Optional[float] = None
    parking_reduction_pct: float = 0.0
    use_restriction: Optional[str] = None
    use_allowance: Optional[str] = None
    mandatory_affordable_pct: float = 0.0
    description: str = ""
    details: dict = field(default_factory=dict)


@dataclass
class ProgramResult:
    """Result of checking one program against one property."""
    program_key: str
    program_name: str
    category: ProgramCategory
    applicable: bool
    eligible: bool
    effect: Optional[ProgramEffect] = None
    reason: str = ""
    source_zr: str = ""


@dataclass
class ProgramDefinition:
    """Definition of a single zoning program."""
    key: str
    name: str
    category: ProgramCategory
    description: str
    source_zr: str
    check_fn: Callable[[LotProfile], ProgramResult]


# ──────────────────────────────────────────────────────────────────
# REGISTRY
# ──────────────────────────────────────────────────────────────────

PROGRAM_REGISTRY: dict[str, ProgramDefinition] = {}


def register_program(prog: ProgramDefinition) -> None:
    """Register a program in the global registry."""
    PROGRAM_REGISTRY[prog.key] = prog


def check_all_programs(lot: LotProfile) -> list[ProgramResult]:
    """Run every registered program against a lot."""
    results: list[ProgramResult] = []
    for key, prog in PROGRAM_REGISTRY.items():
        try:
            result = prog.check_fn(lot)
            results.append(result)
        except Exception as exc:
            logger.warning("Program %s check failed: %s", key, exc)
            results.append(ProgramResult(
                program_key=key,
                program_name=prog.name,
                category=prog.category,
                applicable=False,
                eligible=False,
                reason=f"Error evaluating: {exc}",
            ))
    return results


def get_applicable_programs(lot: LotProfile) -> list[ProgramResult]:
    """Return only programs that apply to this lot."""
    return [r for r in check_all_programs(lot) if r.applicable]


def get_program_effects_summary(results: list[ProgramResult]) -> dict:
    """Aggregate effects across all applicable programs."""
    total_far = 0.0
    total_height = 0.0
    restrictions: list[str] = []
    allowances: list[str] = []
    max_affordable = 0.0

    for r in results:
        if r.applicable and r.effect:
            total_far += r.effect.far_bonus
            total_height += r.effect.height_bonus_ft
            if r.effect.use_restriction:
                restrictions.append(r.effect.use_restriction)
            if r.effect.use_allowance:
                allowances.append(r.effect.use_allowance)
            max_affordable = max(max_affordable, r.effect.mandatory_affordable_pct)

    return {
        "total_far_bonus": round(total_far, 2),
        "total_height_bonus_ft": total_height,
        "use_restrictions": restrictions,
        "use_allowances": allowances,
        "mandatory_affordable_pct": max_affordable,
        "applicable_count": sum(1 for r in results if r.applicable),
        "total_checked": len(results),
    }


# ======================================================================
#  CHECK FUNCTIONS  —  one per program, registered at module import
# ======================================================================

# Helper to get primary district
def _primary(lot: LotProfile) -> str:
    return lot.zoning_districts[0] if lot.zoning_districts else ""


# ── 1. MIH ────────────────────────────────────────────────────────

def _check_mih(lot: LotProfile) -> ProgramResult:
    from app.zoning_engine.mih_options import get_mih_bonus_far
    applicable = lot.is_mih_area
    bonus = get_mih_bonus_far(_primary(lot)) if applicable else None
    return ProgramResult(
        program_key="mih",
        program_name="Mandatory Inclusionary Housing (MIH)",
        category=ProgramCategory.AFFORDABLE_HOUSING,
        applicable=applicable,
        eligible=applicable,
        effect=ProgramEffect(
            far_bonus=bonus or 0,
            mandatory_affordable_pct=0.25,
            description=(
                f"MIH area: +{bonus:.2f} FAR bonus with 25-30% "
                "affordable units required."
            ) if bonus else "MIH designated area; affordable units required.",
            details={"mih_bonus_far": bonus},
        ) if applicable else None,
        reason="Site in MIH-designated area" if applicable
               else "Site not in an MIH-designated area",
        source_zr="ZR 23-154",
    )

register_program(ProgramDefinition(
    key="mih", name="Mandatory Inclusionary Housing (MIH)",
    category=ProgramCategory.AFFORDABLE_HOUSING,
    description="Mandatory affordable housing with FAR bonus in designated areas",
    source_zr="ZR 23-154", check_fn=_check_mih,
))


# ── 2. UAP ────────────────────────────────────────────────────────

def _check_uap(lot: LotProfile) -> ProgramResult:
    from app.zoning_engine.far_tables import get_uap_bonus_far
    district = _primary(lot)
    bonus = get_uap_bonus_far(district, lot.street_width or "narrow")
    applicable = bonus is not None and bonus > 0
    return ProgramResult(
        program_key="uap",
        program_name="Universal Affordability Preference (UAP)",
        category=ProgramCategory.AFFORDABLE_HOUSING,
        applicable=applicable,
        eligible=applicable,
        effect=ProgramEffect(
            far_bonus=bonus or 0,
            mandatory_affordable_pct=0.20,
            description=(
                f"+{bonus:.2f} FAR bonus (City of Yes) for affordable "
                "housing at weighted avg <= 60% AMI."
            ) if bonus else "",
        ) if applicable else None,
        reason="UAP available (R6+ district)" if applicable
               else "UAP not available (district below R6 or not residential)",
        source_zr="ZR 23-154 (City of Yes)",
    )

register_program(ProgramDefinition(
    key="uap", name="Universal Affordability Preference (UAP)",
    category=ProgramCategory.AFFORDABLE_HOUSING,
    description="~20% FAR bonus citywide for affordable housing (City of Yes)",
    source_zr="ZR 23-154 (City of Yes)", check_fn=_check_uap,
))


# ── 3. Voluntary IH (legacy, superseded by UAP) ──────────────────

def _check_voluntary_ih(lot: LotProfile) -> ProgramResult:
    from app.zoning_engine.far_tables import get_ih_bonus
    district = _primary(lot)
    bonus = get_ih_bonus(district)
    applicable = bonus is not None and bonus > 0 and not lot.is_mih_area
    return ProgramResult(
        program_key="voluntary_ih",
        program_name="Voluntary Inclusionary Housing (R10+)",
        category=ProgramCategory.AFFORDABLE_HOUSING,
        applicable=applicable,
        eligible=bonus is not None and bonus > 0,
        effect=ProgramEffect(
            far_bonus=bonus or 0,
            description=f"+{bonus:.2f} FAR for voluntary affordable housing"
                        if bonus else "",
        ) if applicable else None,
        reason="Voluntary IH bonus available (high-density district)" if applicable
               else "Not applicable (superseded by UAP or MIH, or district not eligible)",
        source_zr="ZR 23-90",
    )

register_program(ProgramDefinition(
    key="voluntary_ih", name="Voluntary Inclusionary Housing (R10+)",
    category=ProgramCategory.AFFORDABLE_HOUSING,
    description="Legacy IH bonus for R10+ districts (mostly superseded by UAP)",
    source_zr="ZR 23-90", check_fn=_check_voluntary_ih,
))


# ── 4. FRESH ──────────────────────────────────────────────────────

def _check_fresh(lot: LotProfile) -> ProgramResult:
    from app.zoning_engine.fresh import is_fresh_eligible, get_fresh_bonus
    eligible = is_fresh_eligible(lot)
    bonus = get_fresh_bonus(lot) if eligible else None
    return ProgramResult(
        program_key="fresh",
        program_name="FRESH Food Store Program",
        category=ProgramCategory.COMMERCIAL_BONUS,
        applicable=eligible,
        eligible=eligible,
        effect=ProgramEffect(
            far_bonus=bonus["far_bonus"] if bonus else 0,
            height_bonus_ft=bonus["height_bonus_ft"] if bonus else 0,
            description=bonus["description"] if bonus else "",
            details=bonus or {},
        ) if eligible else None,
        reason="Site in FRESH-eligible food desert area" if eligible
               else "Site not in a mapped FRESH zone",
        source_zr="ZR 63-02",
    )

register_program(ProgramDefinition(
    key="fresh", name="FRESH Food Store Program",
    category=ProgramCategory.COMMERCIAL_BONUS,
    description="FAR bonus for grocery stores in food desert areas",
    source_zr="ZR 63-02", check_fn=_check_fresh,
))


# ── 5-26. SPECIAL DISTRICTS ──────────────────────────────────────

def _make_special_district_checker(sd_code: str):
    """Factory: return a check_fn for a specific special district code."""

    def _check(lot: LotProfile) -> ProgramResult:
        from app.zoning_engine.special_districts import (
            get_special_district_rules,
            get_special_district_bonuses,
        )
        spdist_codes = lot.special_districts or []
        applicable = sd_code in spdist_codes
        rules = get_special_district_rules(sd_code)
        name = rules["name"] if rules else f"Special District {sd_code}"
        desc = rules.get("description", "") if rules else ""

        effect = None
        if applicable and rules:
            overrides = rules.get("far_override", {})
            # Sum up any bonus FAR available
            bonus_far = 0
            for bonus_info in rules.get("bonuses", {}).values():
                bonus_far += bonus_info.get("max_additional_far", 0)
            mih = rules.get("mandatory_inclusionary", False)
            effect = ProgramEffect(
                far_bonus=bonus_far,
                mandatory_affordable_pct=0.25 if mih else 0,
                description=desc,
                details={"far_override": overrides} if overrides else {},
            )

        return ProgramResult(
            program_key=f"sd_{sd_code.lower()}",
            program_name=name,
            category=ProgramCategory.SPECIAL_DISTRICT,
            applicable=applicable,
            eligible=applicable,
            effect=effect,
            reason=f"Site in {name}" if applicable
                   else f"Site not in {name}",
            source_zr=f"NYC ZR ({sd_code})",
        )

    return _check


# Register every known special district
_SPECIAL_DISTRICT_CODES = [
    "MiD", "HY", "LIC", "DB", "EC", "CL", "WCh", "GC", "TMU",
    "SRD", "BR", "CI", "GI",
    # New districts added in this implementation:
    "FW", "WP", "HRW", "BPC", "LM", "EM", "125", "CR", "EC2",
]

for _sd in _SPECIAL_DISTRICT_CODES:
    _checker = _make_special_district_checker(_sd)
    register_program(ProgramDefinition(
        key=f"sd_{_sd.lower()}",
        name=f"Special District: {_sd}",
        category=ProgramCategory.SPECIAL_DISTRICT,
        description=f"Special {_sd} district overlay",
        source_zr=f"NYC ZR ({_sd})",
        check_fn=_checker,
    ))


# ── 27. LANDMARK TDR ─────────────────────────────────────────────

def _check_landmark_tdr(lot: LotProfile) -> ProgramResult:
    from app.zoning_engine.tdr import is_landmark_tdr_eligible, get_landmark_tdr_bonus
    eligible = is_landmark_tdr_eligible(lot)
    # Use max of residential/commercial FAR for bonus calculation
    from app.zoning_engine.far_tables import get_far_for_district
    district = _primary(lot)
    far_data = get_far_for_district(district)
    res = far_data.get("residential") or 0
    if isinstance(res, dict):
        qh = res.get("qh", 0)
        res = max(qh.values()) if isinstance(qh, dict) else qh
    comm = far_data.get("commercial") or 0
    base_far = max(res, comm)

    bonus = get_landmark_tdr_bonus(lot, base_far) if eligible else None
    return ProgramResult(
        program_key="landmark_tdr",
        program_name="Landmark Transfer of Development Rights",
        category=ProgramCategory.TRANSFER_RIGHTS,
        applicable=eligible,
        eligible=eligible,
        effect=ProgramEffect(
            far_bonus=bonus["far_bonus"] if bonus else 0,
            description=bonus["description"] if bonus else "",
            details=bonus or {},
        ) if eligible and bonus else None,
        reason="District eligible to receive landmark TDR" if eligible
               else "District not eligible for landmark TDR (requires R6+ or commercial)",
        source_zr="ZR 74-79",
    )

register_program(ProgramDefinition(
    key="landmark_tdr", name="Landmark Transfer of Development Rights",
    category=ProgramCategory.TRANSFER_RIGHTS,
    description="TDR from designated landmarks (City of Yes: chair cert, non-adjacent OK)",
    source_zr="ZR 74-79", check_fn=_check_landmark_tdr,
))


# ── 28-30. SPECIAL DISTRICT TDR BANKS ────────────────────────────

def _check_east_midtown_tdr(lot: LotProfile) -> ProgramResult:
    applicable = "EM" in (lot.special_districts or [])
    from app.zoning_engine.tdr import check_special_district_tdr
    tdr = check_special_district_tdr(lot) if applicable else None
    is_em = tdr and tdr.get("type") == "east_midtown_tdr"
    return ProgramResult(
        program_key="east_midtown_tdr",
        program_name="East Midtown TDR Bank",
        category=ProgramCategory.TRANSFER_RIGHTS,
        applicable=bool(is_em),
        eligible=bool(is_em),
        effect=ProgramEffect(
            far_bonus=tdr["far_bonus"] if is_em else 0,
            description=tdr["description"] if is_em else "",
            details=tdr or {},
        ) if is_em else None,
        reason="Site in East Midtown TDR subdistrict" if is_em
               else "Site not in East Midtown subdistrict",
        source_zr="ZR 81-64",
    )

register_program(ProgramDefinition(
    key="east_midtown_tdr", name="East Midtown TDR Bank",
    category=ProgramCategory.TRANSFER_RIGHTS,
    description="Landmark preservation TDR bank in East Midtown",
    source_zr="ZR 81-64", check_fn=_check_east_midtown_tdr,
))


def _check_west_chelsea_tdr(lot: LotProfile) -> ProgramResult:
    applicable = "WCh" in (lot.special_districts or [])
    from app.zoning_engine.tdr import check_special_district_tdr
    tdr = check_special_district_tdr(lot) if applicable else None
    is_wch = tdr and tdr.get("type") == "west_chelsea_tdr"
    return ProgramResult(
        program_key="west_chelsea_tdr",
        program_name="West Chelsea / High Line TDR",
        category=ProgramCategory.TRANSFER_RIGHTS,
        applicable=bool(is_wch),
        eligible=bool(is_wch),
        effect=ProgramEffect(
            far_bonus=tdr["far_bonus"] if is_wch else 0,
            description=tdr["description"] if is_wch else "",
            details=tdr or {},
        ) if is_wch else None,
        reason="Site in West Chelsea High Line TDR area" if is_wch
               else "Site not in West Chelsea district",
        source_zr="ZR 98-04",
    )

register_program(ProgramDefinition(
    key="west_chelsea_tdr", name="West Chelsea / High Line TDR",
    category=ProgramCategory.TRANSFER_RIGHTS,
    description="High Line corridor TDR for West Chelsea",
    source_zr="ZR 98-04", check_fn=_check_west_chelsea_tdr,
))


def _check_hudson_yards_tdr(lot: LotProfile) -> ProgramResult:
    applicable = "HY" in (lot.special_districts or [])
    from app.zoning_engine.tdr import check_special_district_tdr
    tdr = check_special_district_tdr(lot) if applicable else None
    is_hy = tdr and tdr.get("type") == "hudson_yards_tdr"
    return ProgramResult(
        program_key="hudson_yards_tdr",
        program_name="Hudson Yards Development Rights",
        category=ProgramCategory.TRANSFER_RIGHTS,
        applicable=bool(is_hy),
        eligible=bool(is_hy),
        effect=ProgramEffect(
            far_bonus=tdr["far_bonus"] if is_hy else 0,
            description=tdr["description"] if is_hy else "",
            details=tdr or {},
        ) if is_hy else None,
        reason="Site in Hudson Yards TDR district" if is_hy
               else "Site not in Hudson Yards district",
        source_zr="ZR 93-32",
    )

register_program(ProgramDefinition(
    key="hudson_yards_tdr", name="Hudson Yards Development Rights",
    category=ProgramCategory.TRANSFER_RIGHTS,
    description="Eastern Rail Yard development rights in Hudson Yards",
    source_zr="ZR 93-32", check_fn=_check_hudson_yards_tdr,
))


# ── 31. LSRD ─────────────────────────────────────────────────────

def _check_lsrd(lot: LotProfile) -> ProgramResult:
    from app.zoning_engine.large_scale import is_lsrd_eligible, get_lsrd_details
    eligible = is_lsrd_eligible(lot)
    details = get_lsrd_details(lot) if eligible else None
    return ProgramResult(
        program_key="lsrd",
        program_name="Large-Scale Residential Development (LSRD)",
        category=ProgramCategory.LARGE_SCALE,
        applicable=eligible,
        eligible=eligible,
        effect=ProgramEffect(
            description=details["description"] if details else "",
            details=details or {},
        ) if eligible else None,
        reason=details["description"] if details
               else f"Lot area {lot.lot_area or 0:,.0f} SF < 65,340 SF minimum "
                    "or district not eligible",
        source_zr="ZR 78-00",
    )

register_program(ProgramDefinition(
    key="lsrd", name="Large-Scale Residential Development (LSRD)",
    category=ProgramCategory.LARGE_SCALE,
    description="Bulk modification for sites >= 1.5 acres in R3-R10",
    source_zr="ZR 78-00", check_fn=_check_lsrd,
))


# ── 32. LSGD ─────────────────────────────────────────────────────

def _check_lsgd(lot: LotProfile) -> ProgramResult:
    from app.zoning_engine.large_scale import is_lsgd_eligible, get_lsgd_details
    eligible = is_lsgd_eligible(lot)
    details = get_lsgd_details(lot) if eligible else None
    return ProgramResult(
        program_key="lsgd",
        program_name="Large-Scale General Development (LSGD)",
        category=ProgramCategory.LARGE_SCALE,
        applicable=eligible,
        eligible=eligible,
        effect=ProgramEffect(
            description=details["description"] if details else "",
            details=details or {},
        ) if eligible else None,
        reason=details["description"] if details
               else f"Lot area {lot.lot_area or 0:,.0f} SF < 65,340 SF minimum "
                    "or district not eligible",
        source_zr="ZR 74-74",
    )

register_program(ProgramDefinition(
    key="lsgd", name="Large-Scale General Development (LSGD)",
    category=ProgramCategory.LARGE_SCALE,
    description="Bulk modification for mixed-use sites >= 1.5 acres",
    source_zr="ZR 74-74", check_fn=_check_lsgd,
))


# ── 33. Office-to-Residential Conversion ─────────────────────────

def _check_office_conversion(lot: LotProfile) -> ProgramResult:
    from app.zoning_engine.city_of_yes import is_office_conversion_eligible
    district = _primary(lot)
    year = lot.pluto.yearbuilt if lot.pluto else None
    eligible = is_office_conversion_eligible(district, year)
    return ProgramResult(
        program_key="office_conversion",
        program_name="Office-to-Residential Conversion (City of Yes)",
        category=ProgramCategory.USE_FLEXIBILITY,
        applicable=eligible,
        eligible=eligible,
        effect=ProgramEffect(
            use_allowance="residential_in_commercial_mfg",
            description="Office buildings (pre-1991) may convert to residential.",
        ) if eligible else None,
        reason="Eligible district with pre-1991 building" if eligible
               else "District not eligible or building too new (post-1990)",
        source_zr="ZR 15-00 (City of Yes)",
    )

register_program(ProgramDefinition(
    key="office_conversion",
    name="Office-to-Residential Conversion (City of Yes)",
    category=ProgramCategory.USE_FLEXIBILITY,
    description="Convert pre-1991 offices to residential in eligible districts",
    source_zr="ZR 15-00 (City of Yes)", check_fn=_check_office_conversion,
))


# ── 34. IBZ ───────────────────────────────────────────────────────

def _check_ibz(lot: LotProfile) -> ProgramResult:
    from app.zoning_engine.industrial import is_ibz, get_ibz_restrictions
    in_ibz = is_ibz(lot)
    restrictions = get_ibz_restrictions(lot) if in_ibz else None
    return ProgramResult(
        program_key="ibz",
        program_name="Industrial Business Zone (IBZ)",
        category=ProgramCategory.USE_FLEXIBILITY,
        applicable=in_ibz,
        eligible=in_ibz,
        effect=ProgramEffect(
            use_restriction="no_residential",
            description=restrictions["description"] if restrictions else "",
            details=restrictions or {},
        ) if in_ibz else None,
        reason="Site in Industrial Business Zone" if in_ibz
               else "Site not in an IBZ (not M-district or not mapped IBZ area)",
        source_zr="NYC Executive Order (2006)",
    )

register_program(ProgramDefinition(
    key="ibz", name="Industrial Business Zone (IBZ)",
    category=ProgramCategory.USE_FLEXIBILITY,
    description="Use restrictions in mapped industrial zones",
    source_zr="NYC Executive Order (2006)", check_fn=_check_ibz,
))


# ── 35. IIA ───────────────────────────────────────────────────────

def _check_iia(lot: LotProfile) -> ProgramResult:
    from app.zoning_engine.industrial import is_iia_eligible, get_iia_incentives
    eligible = is_iia_eligible(lot)
    incentives = get_iia_incentives(lot) if eligible else None
    return ProgramResult(
        program_key="iia",
        program_name="Industrial Incentive Area (IIA)",
        category=ProgramCategory.USE_FLEXIBILITY,
        applicable=eligible,
        eligible=eligible,
        effect=ProgramEffect(
            description=incentives["description"] if incentives else "",
            details=incentives or {},
        ) if eligible else None,
        reason="Site in IIA with tax incentives" if eligible
               else "Site not in an Industrial Incentive Area",
        source_zr="NYC IIA Designation (2022)",
    )

register_program(ProgramDefinition(
    key="iia", name="Industrial Incentive Area (IIA)",
    category=ProgramCategory.USE_FLEXIBILITY,
    description="Tax incentives for industrial development in IBZ areas",
    source_zr="NYC IIA Designation (2022)", check_fn=_check_iia,
))


# ── 36. ADU ───────────────────────────────────────────────────────

def _check_adu(lot: LotProfile) -> ProgramResult:
    from app.zoning_engine.city_of_yes import is_adu_eligible
    district = _primary(lot)
    eligible = is_adu_eligible(district)
    return ProgramResult(
        program_key="adu",
        program_name="Accessory Dwelling Unit (ADU)",
        category=ProgramCategory.USE_FLEXIBILITY,
        applicable=eligible,
        eligible=eligible,
        effect=ProgramEffect(
            description=(
                "As-of-right ADU construction: max 800 SF, 1 per lot, "
                "16 ft max height if detached."
            ),
        ) if eligible else None,
        reason="ADU eligible (R1-R5 district)" if eligible
               else "ADU not available (requires R1-R5 district)",
        source_zr="ZR 12-10 (City of Yes)",
    )

register_program(ProgramDefinition(
    key="adu", name="Accessory Dwelling Unit (ADU)",
    category=ProgramCategory.USE_FLEXIBILITY,
    description="As-of-right ADU in R1-R5 districts (City of Yes)",
    source_zr="ZR 12-10 (City of Yes)", check_fn=_check_adu,
))


# ── 37. Shared Housing (SRO) ─────────────────────────────────────

def _check_shared_housing(lot: LotProfile) -> ProgramResult:
    district = _primary(lot)
    # Shared housing allowed in R6+ (City of Yes)
    import re
    m = re.match(r"^R(\d+)", district)
    eligible = m is not None and int(m.group(1)) >= 6
    return ProgramResult(
        program_key="shared_housing",
        program_name="Shared Housing / SRO (City of Yes)",
        category=ProgramCategory.USE_FLEXIBILITY,
        applicable=eligible,
        eligible=eligible,
        effect=ProgramEffect(
            use_allowance="shared_housing",
            description=(
                "Shared housing legalized: min 150 SF habitable room, "
                "shared facilities permitted."
            ),
        ) if eligible else None,
        reason="Shared housing permitted (R6+ district)" if eligible
               else "Shared housing not permitted (requires R6+)",
        source_zr="ZR 12-10 (City of Yes)",
    )

register_program(ProgramDefinition(
    key="shared_housing", name="Shared Housing / SRO (City of Yes)",
    category=ProgramCategory.USE_FLEXIBILITY,
    description="Legalized shared housing in R6+ districts",
    source_zr="ZR 12-10 (City of Yes)", check_fn=_check_shared_housing,
))


# ── 38. Quality Housing Program ──────────────────────────────────

def _check_quality_housing(lot: LotProfile) -> ProgramResult:
    from app.zoning_engine.height_setback import get_height_rules
    district = _primary(lot)
    h = get_height_rules(district, lot.street_width)
    applicable = h.get("quality_housing", False)
    return ProgramResult(
        program_key="quality_housing",
        program_name="Quality Housing Program",
        category=ProgramCategory.BULK_ENVELOPE,
        applicable=applicable,
        eligible=applicable,
        effect=ProgramEffect(
            description=(
                f"Quality Housing: base height {h.get('base_height_min', 0):.0f}"
                f"-{h.get('base_height_max', 0):.0f} ft, "
                f"max {h.get('max_building_height', 'N/A')} ft."
            ),
        ) if applicable else None,
        reason="QH program applies (contextual district)" if applicable
               else "QH not applicable (height factor or low-density district)",
        source_zr="ZR 23-15",
    )

register_program(ProgramDefinition(
    key="quality_housing", name="Quality Housing Program",
    category=ProgramCategory.BULK_ENVELOPE,
    description="Height/setback rules for contextual districts",
    source_zr="ZR 23-15", check_fn=_check_quality_housing,
))


# ── 39. Transit Zone Parking Waiver ──────────────────────────────

def _check_transit_parking(lot: LotProfile) -> ProgramResult:
    from app.zoning_engine.parking import get_parking_zone
    borough = lot.borough
    cd = lot.pluto.cd if lot.pluto and lot.pluto.cd else 0
    zone = get_parking_zone(borough, cd)
    applicable = zone <= 1  # Zone 0 or 1 = no parking required
    zone_names = {
        0: "Manhattan Core (no residential parking required)",
        1: "Inner Transit Zone (no residential parking required)",
        2: "Outer Transit Zone (reduced parking with waivers)",
        3: "Beyond Greater Transit Zone (standard requirements)",
    }
    return ProgramResult(
        program_key="transit_parking_waiver",
        program_name="Transit Zone Parking Waiver",
        category=ProgramCategory.BULK_ENVELOPE,
        applicable=applicable,
        eligible=zone <= 2,  # Eligible includes zone 2 (reduced)
        effect=ProgramEffect(
            parking_reduction_pct=100.0 if zone <= 1 else 50.0 if zone == 2 else 0,
            description=zone_names.get(zone, "Unknown zone"),
        ) if zone <= 2 else None,
        reason=zone_names.get(zone, f"Parking zone {zone}"),
        source_zr="ZR 25-00 (City of Yes)",
    )

register_program(ProgramDefinition(
    key="transit_parking_waiver", name="Transit Zone Parking Waiver",
    category=ProgramCategory.BULK_ENVELOPE,
    description="Reduced or eliminated parking in transit zones (City of Yes)",
    source_zr="ZR 25-00 (City of Yes)", check_fn=_check_transit_parking,
))


# ── 40. Commercial Overlay ───────────────────────────────────────

def _check_commercial_overlay(lot: LotProfile) -> ProgramResult:
    from app.zoning_engine.far_tables import COMMERCIAL_OVERLAY_FAR
    overlays = lot.overlays or []
    best_far = 0.0
    best_overlay = ""
    for o in overlays:
        ofar = COMMERCIAL_OVERLAY_FAR.get(o, 0)
        if ofar > best_far:
            best_far = ofar
            best_overlay = o
    applicable = best_far > 0
    return ProgramResult(
        program_key="commercial_overlay",
        program_name="Commercial Overlay",
        category=ProgramCategory.BULK_ENVELOPE,
        applicable=applicable,
        eligible=applicable,
        effect=ProgramEffect(
            far_bonus=best_far,
            description=(
                f"Commercial overlay {best_overlay}: "
                f"{best_far:.1f} FAR for ground-floor commercial."
            ),
        ) if applicable else None,
        reason=f"Overlay {best_overlay} ({best_far:.1f} commercial FAR)" if applicable
               else "No commercial overlay on this lot",
        source_zr="ZR 32-00",
    )

register_program(ProgramDefinition(
    key="commercial_overlay", name="Commercial Overlay",
    category=ProgramCategory.BULK_ENVELOPE,
    description="Ground-floor commercial FAR from C1-C8 overlays",
    source_zr="ZR 32-00", check_fn=_check_commercial_overlay,
))


# ── 41. Community Facility FAR ───────────────────────────────────

def _check_cf_far(lot: LotProfile) -> ProgramResult:
    from app.zoning_engine.far_tables import get_far_for_district
    district = _primary(lot)
    far_data = get_far_for_district(district)
    cf_far = far_data.get("cf") or 0
    applicable = cf_far > 0
    lot_area = lot.lot_area or 0
    return ProgramResult(
        program_key="cf_far",
        program_name="Community Facility FAR Allowance",
        category=ProgramCategory.BULK_ENVELOPE,
        applicable=applicable,
        eligible=applicable,
        effect=ProgramEffect(
            far_override=cf_far,
            description=(
                f"CF FAR {cf_far:.2f} "
                f"({cf_far * lot_area:,.0f} SF) for schools, houses of "
                "worship, hospitals, etc."
            ),
        ) if applicable else None,
        reason=f"CF FAR {cf_far:.2f} available" if applicable
               else "No community facility FAR in this district",
        source_zr="ZR 24-11",
    )

register_program(ProgramDefinition(
    key="cf_far", name="Community Facility FAR Allowance",
    category=ProgramCategory.BULK_ENVELOPE,
    description="Higher FAR for community facility uses (schools, hospitals, etc.)",
    source_zr="ZR 24-11", check_fn=_check_cf_far,
))


# ── 42. Coastal / Flood Zone ─────────────────────────────────────

def _check_coastal_flood(lot: LotProfile) -> ProgramResult:
    fz = lot.flood_zone
    cz = lot.coastal_zone
    applicable = bool(fz) or cz
    desc_parts = []
    if fz:
        desc_parts.append(f"FEMA flood zone {fz}")
    if cz:
        desc_parts.append("coastal zone")
    return ProgramResult(
        program_key="coastal_flood",
        program_name="Coastal Flood Resilience Requirements",
        category=ProgramCategory.RESILIENCE,
        applicable=applicable,
        eligible=applicable,
        effect=ProgramEffect(
            description=(
                f"Site in {', '.join(desc_parts)}. "
                "Freeboard +2 ft above BFE, elevated utilities, "
                "wet/dry floodproofing required."
            ),
            details={"flood_zone": fz, "coastal_zone": cz},
        ) if applicable else None,
        reason=f"In {', '.join(desc_parts)}" if applicable
               else "Site not in a flood zone or coastal area",
        source_zr="ZR Appendix A (Flood Resilience)",
    )

register_program(ProgramDefinition(
    key="coastal_flood", name="Coastal Flood Resilience Requirements",
    category=ProgramCategory.RESILIENCE,
    description="Flood and coastal resilience requirements",
    source_zr="ZR Appendix A", check_fn=_check_coastal_flood,
))
