export interface BBLResponse {
  bbl: string;
  borough: number;
  block: number;
  lot: number;
  latitude?: number;
  longitude?: number;
}

export interface PlutoData {
  bbl: string;
  address?: string;
  zonedist1?: string;
  zonedist2?: string;
  zonedist3?: string;
  zonedist4?: string;
  overlay1?: string;
  overlay2?: string;
  spdist1?: string;
  spdist2?: string;
  spdist3?: string;
  ltdheight?: string;
  splitzone?: string;
  landuse?: string;
  lotarea?: number;
  lotfront?: number;
  lotdepth?: number;
  bldgarea?: number;
  numbldgs?: number;
  numfloors?: number;
  assessland?: number;
  assesstot?: number;
  builtfar?: number;
  residfar?: number;
  commfar?: number;
  facilfar?: number;
  yearbuilt?: number;
  irrlotcode?: string;
  cd?: number;
  zipcode?: string;
}

export interface SkyExposurePlane {
  start_height: number;
  ratio: number;
  direction: string;
}

export interface SetbackRules {
  front: number;
  side_narrow: number;
  side_wide: number;
  rear: number;
  front_setback_above_base: number;
}

export interface ZoningEnvelope {
  residential_far?: number;
  commercial_far?: number;
  cf_far?: number;
  manufacturing_far?: number;
  max_residential_zfa?: number;
  max_commercial_zfa?: number;
  max_cf_zfa?: number;
  ih_bonus_far?: number;
  base_height_min?: number;
  base_height_max?: number;
  max_building_height?: number;
  sky_exposure_plane?: SkyExposurePlane;
  setbacks?: SetbackRules;
  front_yard: number;
  rear_yard: number;
  side_yards_required: boolean;
  side_yard_width: number;
  lot_coverage_max?: number;
  quality_housing: boolean;
  height_factor: boolean;
}

export interface UnitMix {
  type: string;
  count: number;
  avg_sf: number;
}

export interface UnitMixResult {
  units: UnitMix[];
  total_units: number;
  average_unit_sf: number;
  units_per_floor: number;
}

export interface ParkingOption {
  type: string;
  sf_per_space: number;
  total_sf: number;
  estimated_cost?: number;
  floors_consumed?: number;
}

export interface ParkingResult {
  residential_spaces_required: number;
  commercial_spaces_required: number;
  total_spaces_required: number;
  waiver_eligible: boolean;
  parking_options: ParkingOption[];
}

export interface CoreEstimate {
  elevators: number;
  stairs: number;
  elevator_sf_per_floor: number;
  stair_sf_per_floor: number;
  mechanical_sf_per_floor: number;
  corridor_sf_per_floor: number;
  total_core_sf_per_floor: number;
  core_percentage: number;
}

export interface LossFactorResult {
  gross_building_area: number;
  total_common_area: number;
  net_rentable_area: number;
  loss_factor_pct: number;
  efficiency_ratio: number;
}

export interface MassingFloor {
  floor: number;
  use: string;
  gross_sf: number;
  net_sf: number;
  height_ft: number;
}

export interface MassingGeometry {
  vertices: number[][];
  faces: number[][];
  colors: string[];
  floor_plates: FloorPlate[];
  envelope_wireframe: WireframeEdge[];
  origin: { lng: number; lat: number };
  total_height_ft: number;
}

export interface FloorPlate {
  floor: number;
  use: string;
  height: number;
  polygon: Record<string, unknown>;
}

export interface WireframeEdge {
  start: number[];
  end: number[];
}

export interface DevelopmentScenario {
  name: string;
  description: string;
  total_gross_sf: number;
  total_net_sf: number;
  residential_sf: number;
  commercial_sf: number;
  cf_sf: number;
  parking_sf: number;
  total_units: number;
  unit_mix?: UnitMixResult;
  parking?: ParkingResult;
  loss_factor?: LossFactorResult;
  core?: CoreEstimate;
  floors: MassingFloor[];
  max_height_ft: number;
  num_floors: number;
  far_used: number;
  massing_geometry?: MassingGeometry;
}

export interface LotProfile {
  bbl: string;
  address?: string;
  borough: number;
  block: number;
  lot: number;
  latitude?: number;
  longitude?: number;
  pluto?: PlutoData;
  geometry?: Record<string, unknown>;
  zoning_districts: string[];
  overlays: string[];
  special_districts: string[];
  limited_height?: string;
  split_zone: boolean;
  lot_area?: number;
  lot_frontage?: number;
  lot_depth?: number;
  lot_type: string;
  street_width: string;
  is_mih_area: boolean;
  is_historic_district: boolean;
  flood_zone?: string;
  coastal_zone: boolean;
}

export interface CalculationResult {
  lot_profile: LotProfile;
  zoning_envelope: ZoningEnvelope;
  scenarios: DevelopmentScenario[];
}
