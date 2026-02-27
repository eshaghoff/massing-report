from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional


class AddressLookupRequest(BaseModel):
    address: str


class BBLResponse(BaseModel):
    bbl: str
    borough: int
    block: int
    lot: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    neighbourhood: Optional[str] = None


class PlutoData(BaseModel):
    bbl: str
    address: Optional[str] = None
    zonedist1: Optional[str] = None
    zonedist2: Optional[str] = None
    zonedist3: Optional[str] = None
    zonedist4: Optional[str] = None
    overlay1: Optional[str] = None
    overlay2: Optional[str] = None
    spdist1: Optional[str] = None
    spdist2: Optional[str] = None
    spdist3: Optional[str] = None
    ltdheight: Optional[str] = None
    splitzone: Optional[str] = None
    landuse: Optional[str] = None
    lotarea: Optional[float] = None
    lotfront: Optional[float] = None
    lotdepth: Optional[float] = None
    bldgarea: Optional[float] = None
    numbldgs: Optional[int] = None
    numfloors: Optional[float] = None
    assessland: Optional[float] = None
    assesstot: Optional[float] = None
    builtfar: Optional[float] = None
    residfar: Optional[float] = None
    commfar: Optional[float] = None
    facilfar: Optional[float] = None
    yearbuilt: Optional[int] = None
    yearalter1: Optional[int] = None
    yearalter2: Optional[int] = None
    irrlotcode: Optional[str] = None
    ext: Optional[str] = None
    cd: Optional[int] = None
    ct2010: Optional[str] = None
    cb2010: Optional[str] = None
    zipcode: Optional[str] = None


class LotProfile(BaseModel):
    bbl: str
    address: Optional[str] = None
    borough: int
    block: int
    lot: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    pluto: Optional[PlutoData] = None
    geometry: Optional[dict] = None  # GeoJSON
    zoning_districts: list[str] = []
    overlays: list[str] = []
    special_districts: list[str] = []
    limited_height: Optional[str] = None
    split_zone: bool = False
    lot_area: Optional[float] = None
    lot_frontage: Optional[float] = None
    lot_depth: Optional[float] = None
    lot_type: str = "interior"  # interior, corner, through, irregular
    street_width: str = "narrow"  # narrow (<75ft) or wide (>=75ft)
    is_mih_area: bool = False
    mih_option: Optional[str] = None
    is_historic_district: bool = False
    flood_zone: Optional[str] = None
    coastal_zone: bool = False
    neighbourhood: Optional[str] = None
    cross_streets: Optional[str] = None
    block_description: Optional[str] = None


class SkyExposurePlane(BaseModel):
    start_height: float
    ratio: float
    direction: str


class SetbackRules(BaseModel):
    front: float = 0
    side_narrow: float = 0
    side_wide: float = 0
    rear: float = 0
    front_setback_above_base: float = 0


class ZoningEnvelope(BaseModel):
    residential_far: Optional[float] = None
    commercial_far: Optional[float] = None
    cf_far: Optional[float] = None
    manufacturing_far: Optional[float] = None
    max_residential_zfa: Optional[float] = None
    max_commercial_zfa: Optional[float] = None
    max_cf_zfa: Optional[float] = None
    ih_bonus_far: Optional[float] = None
    base_height_min: Optional[float] = None
    base_height_max: Optional[float] = None
    max_building_height: Optional[float] = None
    sky_exposure_plane: Optional[SkyExposurePlane] = None
    setbacks: Optional[SetbackRules] = None
    front_yard: float = 0
    rear_yard: float = 30
    side_yards_required: bool = False
    side_yard_width: float = 0
    lot_coverage_max: Optional[float] = None
    quality_housing: bool = False
    height_factor: bool = False


class ParkingOption(BaseModel):
    type: str
    sf_per_space: int
    total_sf: int
    estimated_cost: Optional[int] = None
    floors_consumed: Optional[float] = None


class ParkingResult(BaseModel):
    residential_spaces_required: int = 0
    commercial_spaces_required: int = 0
    total_spaces_required: int = 0
    waiver_eligible: bool = False
    parking_options: list[ParkingOption] = []


class CoreEstimate(BaseModel):
    elevators: int
    stairs: int
    elevator_sf_per_floor: float
    stair_sf_per_floor: float
    mechanical_sf_per_floor: float
    corridor_sf_per_floor: float
    total_core_sf_per_floor: float
    core_percentage: float


class UnitMix(BaseModel):
    type: str
    count: int
    avg_sf: int


class UnitMixResult(BaseModel):
    units: list[UnitMix]
    total_units: int
    average_unit_sf: float
    units_per_floor: float


class LossFactorResult(BaseModel):
    gross_building_area: float
    total_common_area: float
    net_rentable_area: float
    loss_factor_pct: float
    efficiency_ratio: float


class MassingFloor(BaseModel):
    floor: int
    use: str  # residential, commercial, community_facility, parking
    gross_sf: float
    net_sf: float
    height_ft: float


class FloorAreaExemptions(BaseModel):
    """Floor area exempt from zoning floor area (ZFA) per ZR 12-10."""
    total_exempt_sf: float = 0
    gross_building_area: float = 0  # ZFA + exempt = what you actually build
    exemption_ratio: float = 0      # exempt / ZFA
    breakdown: dict = {}


class DevelopmentScenario(BaseModel):
    name: str
    description: str
    total_gross_sf: float
    total_net_sf: float
    zoning_floor_area: Optional[float] = None  # Gross minus exemptions (counts toward FAR)
    residential_sf: float = 0
    commercial_sf: float = 0
    cf_sf: float = 0
    parking_sf: float = 0
    total_units: int = 0
    unit_mix: Optional[UnitMixResult] = None
    parking: Optional[ParkingResult] = None
    loss_factor: Optional[LossFactorResult] = None
    core: Optional[CoreEstimate] = None
    floor_area_exemptions: Optional[FloorAreaExemptions] = None
    floors: list[MassingFloor] = []
    max_height_ft: float = 0
    num_floors: int = 0
    far_used: float = 0  # ZFA / lot_area (not gross / lot_area)
    massing_geometry: Optional[dict] = None  # 3D geometry for Three.js


class SpecialDistrictInfo(BaseModel):
    """Special district summary for the lot."""
    applicable: bool = False
    districts: list[dict] = []
    bonuses: list[dict] = []
    mandatory_inclusionary: bool = False
    tdr_available: bool = False


class CalculationResult(BaseModel):
    lot_profile: LotProfile
    zoning_envelope: ZoningEnvelope
    scenarios: list[DevelopmentScenario] = []
    building_type: Optional[dict] = None
    street_wall: Optional[dict] = None
    special_districts: Optional[SpecialDistrictInfo] = None
    city_of_yes: Optional[dict] = None


class AssemblageRequest(BaseModel):
    bbls: list[str]


class ReportRequest(BaseModel):
    bbl: str
    assemblage_bbls: Optional[list[str]] = None
    selected_scenarios: Optional[list[str]] = None
