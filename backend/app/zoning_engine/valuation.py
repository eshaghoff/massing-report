"""
Scenario valuation and highest-and-best-use ranking.

Provides rough $/SF benchmarks by borough and use type for feasibility-level
valuation estimates.  Scenarios are ranked by estimated total development value,
with residential SF prioritised in tiebreaks.

All numbers are order-of-magnitude estimates drawn from NYC DOF rolling sales,
industry comps, and publicly available market data.  They are NOT appraisals.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.schemas import DevelopmentScenario


# ──────────────────────────────────────────────────────────────────
# $/SF BENCHMARKS  (gross building area basis)
# ──────────────────────────────────────────────────────────────────
# Keys: borough code (1-5).  Values: $/SF by use type.
# Residential values represent average condo/rental new-development
# pricing.  Commercial is average retail/office.  CF is institutional.

VALUE_PER_SF: dict[int, dict[str, float]] = {
    1: {"residential": 1500, "commercial": 800, "cf": 500, "parking": 80},   # Manhattan
    2: {"residential": 500,  "commercial": 350, "cf": 300, "parking": 60},   # Bronx
    3: {"residential": 1000, "commercial": 600, "cf": 400, "parking": 70},   # Brooklyn
    4: {"residential": 700,  "commercial": 450, "cf": 350, "parking": 65},   # Queens
    5: {"residential": 550,  "commercial": 350, "cf": 300, "parking": 60},   # Staten Island
}

_FALLBACK_BOROUGH = 3  # Brooklyn as default


def get_value_benchmarks(borough: int) -> dict[str, float]:
    """Return $/SF benchmarks for a given borough.

    Falls back to Brooklyn (borough 3) for unknown borough codes.
    """
    return VALUE_PER_SF.get(borough, VALUE_PER_SF[_FALLBACK_BOROUGH])


def estimate_scenario_value(
    scenario: "DevelopmentScenario",
    borough: int,
) -> dict:
    """Estimate the total development value for a single scenario.

    Returns a dict with per-use values, total, and blended $/SF.
    """
    rates = get_value_benchmarks(borough)

    res_sf = getattr(scenario, "residential_sf", 0) or 0
    comm_sf = getattr(scenario, "commercial_sf", 0) or 0
    cf_sf = getattr(scenario, "cf_sf", 0) or 0
    pkg_sf = getattr(scenario, "parking_sf", 0) or 0
    gross = getattr(scenario, "total_gross_sf", 0) or 0

    res_val = res_sf * rates["residential"]
    comm_val = comm_sf * rates["commercial"]
    cf_val = cf_sf * rates["cf"]
    pkg_val = pkg_sf * rates["parking"]

    total = res_val + comm_val + cf_val + pkg_val
    blended = total / gross if gross > 0 else 0.0

    return {
        "residential_sf": res_sf,
        "commercial_sf": comm_sf,
        "cf_sf": cf_sf,
        "parking_sf": pkg_sf,
        "residential_value": res_val,
        "commercial_value": comm_val,
        "cf_value": cf_val,
        "parking_value": pkg_val,
        "total_estimated_value": total,
        "value_per_sf_blended": round(blended, 2),
        "rates_used": rates,
    }


def rank_scenarios(
    scenarios: list["DevelopmentScenario"],
    borough: int,
) -> list[dict]:
    """Rank scenarios by estimated total development value (descending).

    Tiebreak: higher residential SF wins (user preference: maximise
    residential first, then commercial, then CF).

    Returns a list of dicts ordered by rank, each containing:
      rank, scenario_name, scenario_index, valuation breakdown,
      is_highest_best flag.
    """
    if not scenarios:
        return []

    entries: list[dict] = []
    for idx, sc in enumerate(scenarios):
        val = estimate_scenario_value(sc, borough)
        entries.append({
            "scenario_index": idx,
            "scenario_name": getattr(sc, "name", f"Scenario {idx + 1}"),
            "valuation": val,
        })

    # Sort: primary = total estimated value desc, secondary = residential SF desc
    entries.sort(
        key=lambda e: (
            e["valuation"]["total_estimated_value"],
            e["valuation"]["residential_sf"],
        ),
        reverse=True,
    )

    ranked: list[dict] = []
    for rank, entry in enumerate(entries, start=1):
        ranked.append({
            "rank": rank,
            "scenario_index": entry["scenario_index"],
            "scenario_name": entry["scenario_name"],
            "is_highest_best": rank == 1,
            **entry["valuation"],
        })

    return ranked


def get_value_disclaimer() -> str:
    """Return standard disclaimer text for valuation estimates."""
    return (
        "Estimated values are rough order-of-magnitude benchmarks based on "
        "borough-level average $/SF for new development.  They do not "
        "constitute an appraisal, market study, or investment recommendation.  "
        "Actual values depend on market conditions, location within the "
        "borough, building quality, unit mix, amenities, and other factors.  "
        "Consult a licensed appraiser or broker for project-specific valuations."
    )
