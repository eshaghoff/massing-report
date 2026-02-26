"""Sliding-scale pricing for zoning feasibility reports."""

from __future__ import annotations


# Pricing tiers: (max_sf, rate_per_sf_dollars)
# Applied in order; each tier applies to the SF in that range.
TIERS = [
    (20_000, 0.05),   # First 20,000 SF at $0.05/SF
    (50_000, 0.04),   # 20,001 - 50,000 SF at $0.04/SF
    (float("inf"), 0.03),  # Above 50,000 SF at $0.03/SF
]

MINIMUM_PRICE_CENTS = 5000  # $50 minimum per report


def calculate_price(buildable_sf: float) -> dict:
    """Calculate report price using sliding scale.

    Args:
        buildable_sf: Maximum buildable square footage (typically max ZFA).

    Returns:
        dict with price_cents, price_dollars, breakdown, effective_rate.
    """
    sf_remaining = max(buildable_sf, 0)
    total_cents = 0
    breakdown = []
    prev_cap = 0

    for cap, rate in TIERS:
        if sf_remaining <= 0:
            break
        tier_sf = min(sf_remaining, cap - prev_cap)
        subtotal = tier_sf * rate
        breakdown.append({
            "range": f"{prev_cap + 1:,.0f} - {min(cap, buildable_sf):,.0f} SF"
                     if cap != float("inf")
                     else f"Above {prev_cap:,.0f} SF",
            "sf": round(tier_sf),
            "rate": rate,
            "subtotal": round(subtotal, 2),
        })
        total_cents += subtotal * 100
        sf_remaining -= tier_sf
        prev_cap = cap

    total_cents = max(int(round(total_cents)), MINIMUM_PRICE_CENTS)

    return {
        "buildable_sf": round(buildable_sf),
        "price_cents": total_cents,
        "price_dollars": total_cents / 100,
        "breakdown": breakdown,
        "effective_rate": round(total_cents / 100 / max(buildable_sf, 1), 4),
    }
