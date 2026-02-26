"""
NYC Zoning Resolution FAR (Floor Area Ratio) tables.

Updated to reflect City of Yes for Housing Opportunity (adopted Dec 5, 2024).

For districts R6-R10 without a letter suffix, two options exist:
  - Height Factor (HF): lower FAR, no height limit, sky exposure plane applies
  - Quality Housing (QH): higher FAR, height limit applies

The residential_far field stores either a single float (contextual/letter districts)
or a dict {"hf": float, "qh": float} for non-contextual districts.

Sources:
  - ZR Section 23-22 (Floor Area Regulations in R6-R12 Districts)
  - City of Yes for Housing Opportunity (ULURP N 240187 ZRY)
"""

from __future__ import annotations

# ──────────────────────────────────────────────────────────────────
# RESIDENTIAL DISTRICTS (ZR 23-22)
# ──────────────────────────────────────────────────────────────────

RESIDENTIAL_FAR = {
    # Low density (R1-R3)
    "R1":    {"residential": 0.50, "commercial": None, "cf": None},
    "R1-1":  {"residential": 0.50, "commercial": None, "cf": None},
    "R1-2":  {"residential": 0.50, "commercial": None, "cf": None},
    "R1-2A": {"residential": 0.50, "commercial": None, "cf": None},
    "R2":    {"residential": 0.50, "commercial": None, "cf": None},
    "R2A":   {"residential": 0.50, "commercial": None, "cf": None},
    "R2X":   {"residential": 0.50, "commercial": None, "cf": None},
    "R3-1":  {"residential": 0.50, "commercial": None, "cf": None},
    "R3-2":  {"residential": 0.50, "commercial": None, "cf": None},
    "R3A":   {"residential": 0.50, "commercial": None, "cf": None},
    "R3X":   {"residential": 0.50, "commercial": None, "cf": None},

    # Medium-low density (R4)
    "R4":    {"residential": 0.75, "commercial": None, "cf": 2.0},
    "R4-1":  {"residential": 0.75, "commercial": None, "cf": 2.0},
    "R4A":   {"residential": 0.75, "commercial": None, "cf": 2.0},
    "R4B":   {"residential": 0.90, "commercial": None, "cf": 2.0},

    # Medium density (R5)
    "R5":    {"residential": 1.25, "commercial": None, "cf": 2.0},
    "R5A":   {"residential": 1.10, "commercial": None, "cf": 2.0},
    "R5B":   {"residential": 1.35, "commercial": None, "cf": 2.0},
    "R5D":   {"residential": 2.00, "commercial": None, "cf": 2.0},

    # ── R6 district group (ZR 23-22, City of Yes amendments) ──
    # R6 non-contextual: HF uses open space ratio; QH FAR is street-width dependent:
    #   - Wide street (within 100 ft): R6-1 rules = same as R6A = FAR 3.0
    #   - Narrow street: R6-2 rules = FAR 2.2
    # The "qh" value here stores {"wide": 3.0, "narrow": 2.2} for the calculator
    # to resolve based on actual street width.
    "R6": {
        "residential": {"hf": 0.78, "qh": {"wide": 3.0, "narrow": 2.2}},
        "commercial": None,
        "cf": 4.8,
    },
    "R6A":   {"residential": 3.0,  "commercial": None, "cf": 3.0},
    "R6B":   {"residential": 2.0,  "commercial": None, "cf": 2.0},
    # R6D — new contextual district (City of Yes addition)
    "R6D":   {"residential": 2.50, "commercial": None, "cf": 2.5},

    # ── R7 district group ──
    # R7-1, R7-2 non-contextual: QH FAR is street-width dependent:
    #   - Wide street (outside Manhattan Core): R7A equivalent = FAR 4.0
    #   - Narrow street / Manhattan Core: FAR 3.44
    # R7-1 and R7-2 have identical bulk; R7-2 has lower parking requirements.
    "R7-1": {
        "residential": {"hf": 0.87, "qh": {"wide": 4.0, "narrow": 3.44}},
        "commercial": None,
        "cf": 6.5,
    },
    "R7-2": {
        "residential": {"hf": 0.87, "qh": {"wide": 4.0, "narrow": 3.44}},
        "commercial": None,
        "cf": 6.5,
    },
    "R7A":   {"residential": 4.0,  "commercial": None, "cf": 4.0},
    "R7B":   {"residential": 3.0,  "commercial": None, "cf": 3.0},
    "R7D":   {"residential": 4.66, "commercial": None, "cf": 4.66},
    "R7X":   {"residential": 5.0,  "commercial": None, "cf": 5.0},

    # ── R8 district group ──
    # R8 non-contextual: QH FAR is street-width dependent:
    #   - Wide street (outside Manhattan Core): R8A equivalent = FAR 7.2
    #   - Narrow street / Manhattan Core: FAR 6.02
    "R8": {
        "residential": {"hf": 0.94, "qh": {"wide": 7.2, "narrow": 6.02}},
        "commercial": None,
        "cf": 6.5,
    },
    "R8A":   {"residential": 6.02, "commercial": None, "cf": 6.5},
    "R8B":   {"residential": 4.0,  "commercial": None, "cf": 4.0},
    "R8X":   {"residential": 6.02, "commercial": None, "cf": 6.5},

    # ── R9 district group ──
    "R9": {
        "residential": {"hf": 0.99, "qh": 7.52},
        "commercial": None,
        "cf": 10.0,
    },
    "R9A":   {"residential": 7.52, "commercial": None, "cf": 10.0},
    "R9X":   {"residential": 9.0,  "commercial": None, "cf": 10.0},
    "R9D":   {"residential": 9.0,  "commercial": None, "cf": 9.0},

    # ── R10 district group ──
    "R10": {
        "residential": {"hf": 10.0, "qh": 10.0},
        "commercial": None,
        "cf": 10.0,
    },
    "R10A":  {"residential": 10.0, "commercial": None, "cf": 10.0},
    "R10X":  {"residential": 10.0, "commercial": None, "cf": 10.0},

    # ── R11 and R12 (City of Yes new high-density districts) ──
    "R11":   {"residential": 12.0, "commercial": None, "cf": 12.0},
    "R12":   {"residential": 15.0, "commercial": None, "cf": 15.0},
}

# ──────────────────────────────────────────────────────────────────
# UNIVERSAL AFFORDABILITY PREFERENCE (UAP) — City of Yes
# Maximum FAR when providing affordable housing at ≤60% AMI avg.
# Source: ZR 23-22 as amended, effective Dec 5, 2024.
# ──────────────────────────────────────────────────────────────────

UAP_AFFORDABLE_FAR = {
    # district: max FAR with qualifying affordable housing
    "R6":    3.90,
    "R6A":   3.90,
    "R6B":   2.40,
    "R6D":   3.00,
    "R7-1":  5.01,
    "R7-2":  5.01,
    "R7A":   5.01,
    "R7B":   3.90,
    "R7D":   5.60,
    "R7X":   6.00,
    "R8":    7.20,
    "R8A":   7.20,
    "R8B":   4.80,
    "R8X":   7.20,
    "R9":    9.02,
    "R9A":   9.02,
    "R9D":   10.80,
    "R9X":   10.80,
    "R10":   12.00,
    "R10A":  12.00,
    "R10X":  12.00,
    "R11":   15.00,
    "R12":   18.00,
}

# ──────────────────────────────────────────────────────────────────
# COMMERCIAL DISTRICTS
# ──────────────────────────────────────────────────────────────────

COMMERCIAL_FAR = {
    # C1 and C2 (local retail / service)
    "C1-1":  {"residential": None, "commercial": 1.0,  "cf": 1.0},
    "C1-2":  {"residential": None, "commercial": 1.0,  "cf": 1.0},
    "C1-3":  {"residential": None, "commercial": 1.0,  "cf": 1.0},
    "C1-4":  {"residential": None, "commercial": 1.0,  "cf": 2.0},
    "C1-5":  {"residential": None, "commercial": 1.0,  "cf": 2.0},
    "C1-6":  {"residential": None, "commercial": 2.0,  "cf": 4.8},
    "C1-6A": {"residential": None, "commercial": 2.0,  "cf": 3.0},
    "C1-7":  {"residential": None, "commercial": 2.0,  "cf": 4.8},
    "C1-7A": {"residential": None, "commercial": 2.0,  "cf": 4.0},
    "C1-8":  {"residential": None, "commercial": 2.0,  "cf": 6.5},
    "C1-8A": {"residential": None, "commercial": 2.0,  "cf": 6.02},
    "C1-8X": {"residential": None, "commercial": 2.0,  "cf": 6.02},
    "C1-9":  {"residential": None, "commercial": 2.0,  "cf": 10.0},
    "C1-9A": {"residential": None, "commercial": 2.0,  "cf": 7.52},

    "C2-1":  {"residential": None, "commercial": 1.0,  "cf": 1.0},
    "C2-2":  {"residential": None, "commercial": 1.0,  "cf": 1.0},
    "C2-3":  {"residential": None, "commercial": 1.0,  "cf": 1.0},
    "C2-4":  {"residential": None, "commercial": 1.0,  "cf": 2.0},
    "C2-5":  {"residential": None, "commercial": 1.0,  "cf": 2.0},
    "C2-6":  {"residential": None, "commercial": 2.0,  "cf": 4.8},
    "C2-6A": {"residential": None, "commercial": 2.0,  "cf": 3.0},
    "C2-7":  {"residential": None, "commercial": 2.0,  "cf": 4.8},
    "C2-7A": {"residential": None, "commercial": 2.0,  "cf": 4.0},
    "C2-7X": {"residential": None, "commercial": 2.0,  "cf": 5.0},
    "C2-8":  {"residential": None, "commercial": 2.0,  "cf": 6.5},
    "C2-8A": {"residential": None, "commercial": 2.0,  "cf": 6.02},

    # C3 & C4 (general / regional commercial)
    "C3":    {"residential": None, "commercial": 0.50, "cf": None},
    "C3A":   {"residential": None, "commercial": 0.50, "cf": None},
    "C4-1":  {"residential": None, "commercial": 1.0,  "cf": 1.0},
    "C4-2":  {"residential": None, "commercial": 2.0,  "cf": 2.0},
    "C4-2A": {"residential": None, "commercial": 2.0,  "cf": 3.0},
    "C4-2F": {"residential": None, "commercial": 3.4,  "cf": 3.4},
    "C4-3":  {"residential": None, "commercial": 2.0,  "cf": 4.8},
    "C4-3A": {"residential": None, "commercial": 3.0,  "cf": 3.0},
    "C4-4":  {"residential": None, "commercial": 3.4,  "cf": 6.5},
    "C4-4A": {"residential": None, "commercial": 4.0,  "cf": 4.0},
    "C4-4D": {"residential": None, "commercial": 4.2,  "cf": 4.2},
    "C4-4L": {"residential": None, "commercial": 1.0,  "cf": 2.0},
    "C4-5":  {"residential": None, "commercial": 3.4,  "cf": 6.5},
    "C4-5A": {"residential": None, "commercial": 4.0,  "cf": 4.0},
    "C4-5D": {"residential": None, "commercial": 4.2,  "cf": 4.2},
    "C4-5X": {"residential": None, "commercial": 5.0,  "cf": 5.0},
    "C4-6":  {"residential": None, "commercial": 3.4,  "cf": 6.5},
    "C4-6A": {"residential": None, "commercial": 6.02, "cf": 6.5},
    "C4-7":  {"residential": None, "commercial": 3.4,  "cf": 6.5},

    # C5 (restricted central commercial — Midtown)
    "C5-1":  {"residential": None, "commercial": 10.0, "cf": 10.0},
    "C5-2":  {"residential": None, "commercial": 10.0, "cf": 10.0},
    "C5-2.5":{"residential": None, "commercial": 13.0, "cf": 13.0},
    "C5-3":  {"residential": None, "commercial": 15.0, "cf": 15.0},
    "C5-5":  {"residential": None, "commercial": 10.0, "cf": 10.0},
    "C5-P":  {"residential": None, "commercial": 10.0, "cf": 10.0},

    # C6 (general central commercial)
    "C6-1":  {"residential": None, "commercial": 6.0,  "cf": 6.0},
    "C6-1A": {"residential": None, "commercial": 6.0,  "cf": 6.0},
    "C6-1G": {"residential": None, "commercial": 6.0,  "cf": 6.0},
    "C6-2":  {"residential": None, "commercial": 6.0,  "cf": 6.5},
    "C6-2A": {"residential": None, "commercial": 6.0,  "cf": 6.5},
    "C6-2G": {"residential": None, "commercial": 6.0,  "cf": 6.5},
    "C6-2M": {"residential": None, "commercial": 6.0,  "cf": 6.5},
    "C6-3":  {"residential": None, "commercial": 6.0,  "cf": 6.5},
    "C6-3A": {"residential": None, "commercial": 6.0,  "cf": 6.5},
    "C6-3D": {"residential": None, "commercial": 6.0,  "cf": 6.5},
    "C6-3X": {"residential": None, "commercial": 9.0,  "cf": 9.0},
    "C6-4":  {"residential": None, "commercial": 10.0, "cf": 10.0},
    "C6-4.5":{"residential": None, "commercial": 12.0, "cf": 12.0},
    "C6-4A": {"residential": None, "commercial": 10.0, "cf": 10.0},
    "C6-4M": {"residential": None, "commercial": 10.0, "cf": 10.0},
    "C6-4X": {"residential": None, "commercial": 10.0, "cf": 10.0},
    "C6-5":  {"residential": None, "commercial": 10.0, "cf": 10.0},
    "C6-5.5":{"residential": None, "commercial": 12.0, "cf": 12.0},
    "C6-6":  {"residential": None, "commercial": 15.0, "cf": 15.0},
    "C6-6.5":{"residential": None, "commercial": 15.0, "cf": 15.0},
    "C6-7":  {"residential": None, "commercial": 15.0, "cf": 15.0},
    "C6-7T": {"residential": None, "commercial": 15.0, "cf": 15.0},
    "C6-9":  {"residential": None, "commercial": 18.0, "cf": 18.0},

    # C7 (amusement)
    "C7":    {"residential": None, "commercial": 2.0,  "cf": None},

    # C8 (automotive / heavy commercial)
    "C8-1":  {"residential": None, "commercial": 1.0,  "cf": 2.4},
    "C8-2":  {"residential": None, "commercial": 2.0,  "cf": 4.8},
    "C8-3":  {"residential": None, "commercial": 2.0,  "cf": 6.5},
    "C8-4":  {"residential": None, "commercial": 5.0,  "cf": 6.5},
}

# C1-C2 commercial districts allow residential at the equivalent R district FAR.
# The residential FAR for C4+ depends on the equivalent residential district.
# In mixed-use commercial districts (C1-C6), residential FAR follows the
# mapped residential district equivalent. We handle this in the calculator.

COMMERCIAL_RESIDENTIAL_EQUIVALENTS = {
    "C4-1":  "R5",    "C4-2":  "R6",    "C4-2A": "R6A",
    "C4-2F": "R7A",   "C4-3":  "R7-1",  "C4-3A": "R6A",
    "C4-4":  "R8",    "C4-4A": "R7A",   "C4-4D": "R7D",
    "C4-4L": "R5",    "C4-5":  "R9",    "C4-5A": "R7A",
    "C4-5D": "R7D",   "C4-5X": "R7X",   "C4-6":  "R10",
    "C4-6A": "R8A",   "C4-7":  "R10",
    "C5-1":  "R10",   "C5-2":  "R10",   "C5-2.5":"R10",
    "C5-3":  "R10",   "C5-5":  "R10",   "C5-P":  "R10",
    "C6-1":  "R7-2",  "C6-1A": "R7A",   "C6-1G": "R7A",
    "C6-2":  "R8",    "C6-2A": "R8A",   "C6-2G": "R8A",
    "C6-2M": "R8",    "C6-3":  "R9",    "C6-3A": "R9A",
    "C6-3D": "R9",    "C6-3X": "R9X",   "C6-4":  "R10",
    "C6-4.5":"R10",   "C6-4A": "R10A",  "C6-4M": "R10",
    "C6-4X": "R10",   "C6-5":  "R10",   "C6-5.5":"R10",
    "C6-6":  "R10",   "C6-6.5":"R10",   "C6-7":  "R10",
    "C6-7T": "R10",   "C6-9":  "R10",
}

# ──────────────────────────────────────────────────────────────────
# MANUFACTURING DISTRICTS
# ──────────────────────────────────────────────────────────────────

MANUFACTURING_FAR = {
    "M1-1":  {"residential": None, "commercial": 1.0,  "cf": 2.4,  "manufacturing": 1.0},
    "M1-2":  {"residential": None, "commercial": 2.0,  "cf": 4.8,  "manufacturing": 2.0},
    "M1-3":  {"residential": None, "commercial": 2.0,  "cf": 6.5,  "manufacturing": 2.0},
    "M1-4":  {"residential": None, "commercial": 2.0,  "cf": 6.5,  "manufacturing": 2.0},
    "M1-5":  {"residential": None, "commercial": 5.0,  "cf": 6.5,  "manufacturing": 5.0},
    "M1-5A": {"residential": None, "commercial": 5.0,  "cf": 6.5,  "manufacturing": 5.0},
    "M1-5B": {"residential": None, "commercial": 5.0,  "cf": 6.5,  "manufacturing": 5.0},
    "M1-5M": {"residential": None, "commercial": 5.0,  "cf": 6.5,  "manufacturing": 5.0},
    "M1-6":  {"residential": None, "commercial": 10.0, "cf": 10.0, "manufacturing": 10.0},
    "M1-6D": {"residential": None, "commercial": 10.0, "cf": 10.0, "manufacturing": 10.0},
    "M1-6M": {"residential": None, "commercial": 10.0, "cf": 10.0, "manufacturing": 10.0},
    "M2-1":  {"residential": None, "commercial": None, "cf": None,  "manufacturing": 2.0},
    "M2-2":  {"residential": None, "commercial": None, "cf": None,  "manufacturing": 5.0},
    "M2-3":  {"residential": None, "commercial": None, "cf": None,  "manufacturing": 10.0},
    "M2-4":  {"residential": None, "commercial": None, "cf": None,  "manufacturing": 15.0},
    "M3-1":  {"residential": None, "commercial": None, "cf": None,  "manufacturing": 2.0},
    "M3-2":  {"residential": None, "commercial": None, "cf": None,  "manufacturing": 2.0},
}

# ──────────────────────────────────────────────────────────────────
# COMMERCIAL OVERLAY MAPPINGS (on residential base districts)
# ──────────────────────────────────────────────────────────────────

# Commercial overlays add commercial FAR on top of residential base district.
# The overlay determines max commercial floor area.
COMMERCIAL_OVERLAY_FAR = {
    "C1-1": 1.0,
    "C1-2": 1.0,
    "C1-3": 1.0,
    "C1-4": 1.0,
    "C1-5": 1.0,
    "C2-1": 1.0,
    "C2-2": 1.0,
    "C2-3": 1.0,
    "C2-4": 1.0,
    "C2-5": 1.0,
}

# Ground floor commercial depth limits for overlays
OVERLAY_COMMERCIAL_DEPTH = {
    "C1-1": 40,  # 40 ft from street line
    "C1-2": 40,
    "C1-3": 40,
    "C1-4": 40,
    "C1-5": 40,
    "C2-1": 40,
    "C2-2": 40,
    "C2-3": 40,
    "C2-4": 40,
    "C2-5": 40,
}

# ──────────────────────────────────────────────────────────────────
# INCLUSIONARY HOUSING (IH) / MIH BONUS FAR
# Now superseded by UAP for most purposes, but MIH still applies
# in designated MIH areas as a mandatory requirement.
# ──────────────────────────────────────────────────────────────────

# MIH areas: the MIH max FAR is the affordable housing FAR cap.
# Under City of Yes, UAP replaces the old voluntary IH program
# and provides a citywide 20% FAR bonus for affordable housing.
# In MIH areas, the MIH max may differ from UAP max.
MIH_BONUS = {
    "R6":   {"base_qh": 2.20, "mih_max": 2.75},
    "R6A":  {"base_qh": 3.0,  "mih_max": 3.6},
    "R6B":  {"base_qh": 2.0,  "mih_max": 2.4},
    "R6D":  {"base_qh": 2.5,  "mih_max": 3.0},
    "R7-1": {"base_qh": 3.44, "mih_max": 4.0},
    "R7-2": {"base_qh": 3.44, "mih_max": 4.6},
    "R7A":  {"base_qh": 4.0,  "mih_max": 4.6},
    "R7B":  {"base_qh": 3.0,  "mih_max": 3.9},
    "R7D":  {"base_qh": 4.66, "mih_max": 5.6},
    "R7X":  {"base_qh": 5.0,  "mih_max": 6.0},
    "R8":   {"base_qh": 6.02, "mih_max": 7.2},
    "R8A":  {"base_qh": 6.02, "mih_max": 7.2},
    "R8B":  {"base_qh": 4.0,  "mih_max": 4.8},
    "R8X":  {"base_qh": 6.02, "mih_max": 7.2},
    "R9":   {"base_qh": 7.52, "mih_max": 8.5},
    "R9A":  {"base_qh": 7.52, "mih_max": 9.0},
    "R9D":  {"base_qh": 9.0,  "mih_max": 10.8},
    "R9X":  {"base_qh": 9.0,  "mih_max": 9.7},
    "R10":  {"base_qh": 10.0, "mih_max": 12.0},
    "R10A": {"base_qh": 10.0, "mih_max": 12.0},
    "R10X": {"base_qh": 10.0, "mih_max": 12.0},
    "R11":  {"base_qh": 12.0, "mih_max": 15.0},
    "R12":  {"base_qh": 15.0, "mih_max": 18.0},
}


def get_far_for_district(district: str) -> dict:
    """Look up FAR values for a given zoning district.

    Returns dict with keys: residential, commercial, cf, manufacturing.
    residential may be a float or a dict {"hf": float, "qh": float}.
    """
    district = district.strip().upper()

    if district in RESIDENTIAL_FAR:
        entry = RESIDENTIAL_FAR[district]
        return {
            "residential": entry["residential"],
            "commercial": entry.get("commercial"),
            "cf": entry.get("cf"),
            "manufacturing": None,
        }

    if district in COMMERCIAL_FAR:
        entry = COMMERCIAL_FAR[district]
        # Get residential equivalent if it exists
        res_far = None
        equiv = COMMERCIAL_RESIDENTIAL_EQUIVALENTS.get(district)
        if equiv and equiv in RESIDENTIAL_FAR:
            res_far = RESIDENTIAL_FAR[equiv]["residential"]
        return {
            "residential": res_far,
            "commercial": entry["commercial"],
            "cf": entry.get("cf"),
            "manufacturing": None,
        }

    if district in MANUFACTURING_FAR:
        entry = MANUFACTURING_FAR[district]
        return {
            "residential": None,
            "commercial": entry.get("commercial"),
            "cf": entry.get("cf"),
            "manufacturing": entry.get("manufacturing"),
        }

    return {"residential": None, "commercial": None, "cf": None, "manufacturing": None}


def get_uap_far(district: str) -> float | None:
    """Get the maximum FAR with UAP affordable housing bonus.

    Under City of Yes, UAP provides a ~20% FAR increase in R6-R12 districts
    for developments that include affordable housing at weighted avg ≤60% AMI.

    Returns the maximum total FAR (market-rate + affordable) or None if
    district is not eligible for UAP.
    """
    district = district.strip().upper()

    # Direct lookup
    if district in UAP_AFFORDABLE_FAR:
        return UAP_AFFORDABLE_FAR[district]

    # For non-contextual districts with HF/QH, use the district code
    # (UAP_AFFORDABLE_FAR already maps R6, R7-1, etc.)
    return None


def get_uap_bonus_far(district: str, street_width: str = "narrow") -> float | None:
    """Get the bonus FAR available through UAP (above base).

    Returns the additional FAR that the affordable housing provides,
    or None if district is not eligible.

    Args:
        district: Zoning district code
        street_width: "wide" or "narrow" (needed for districts with
            street-width-dependent QH FAR, e.g. R6)
    """
    district = district.strip().upper()
    uap_max = get_uap_far(district)
    if uap_max is None:
        return None

    # Get the base residential FAR
    base_far = get_far_for_district(district)
    res_far = base_far["residential"]
    if isinstance(res_far, dict):
        # For HF/QH districts, use QH as the base for UAP
        qh_val = res_far.get("qh", 0)
        # QH may itself be street-width dependent (e.g. R6)
        if isinstance(qh_val, dict):
            base_val = qh_val.get(street_width, qh_val.get("narrow", 0))
        else:
            base_val = qh_val
    elif res_far is not None:
        base_val = res_far
    else:
        return None

    bonus = uap_max - base_val
    return round(bonus, 2) if bonus > 0 else None


def get_ih_bonus(district: str) -> float | None:
    """Get additional FAR available through Inclusionary Housing bonus.

    In MIH areas, this is the mandatory IH bonus. Outside MIH areas,
    UAP has replaced the old voluntary IH program.
    """
    district = district.strip().upper()
    entry = MIH_BONUS.get(district)
    if not entry:
        return None
    return entry["mih_max"] - entry["base_qh"]
