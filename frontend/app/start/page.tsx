"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import {
  MapPin,
  Search,
  Plus,
  X,
  Building2,
  Layers,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Info,
  Ruler,
} from "lucide-react";

const BRAND_GOLD = "#D4A843";
const BRAND_NAVY = "#2C5F7C";
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8321";

// ── Types ──

interface LotCard {
  bbl: string;
  address: string;
  lot_area: number;
  lot_frontage: number;
  lot_depth: number;
  zoning_districts: string[];
  bldgarea: number;
  builtfar: number;
  numfloors: number;
  yearbuilt: number;
  geometry: unknown;
  keepExistingBuilding: boolean;
}

interface AdjacentLot {
  bbl: string;
  address: string;
  lot_area: number;
  zoning_districts: string[];
  bldgarea: number;
  builtfar: number;
  numfloors: number;
  yearbuilt: number;
  shared_boundary_ft: number;
  geometry: unknown;
}

interface Scenario {
  name: string;
  total_zfa: number;
  max_height_ft: number;
  num_floors: number;
  total_units: number;
  residential_sf: number;
  commercial_sf: number;
  far_used: number;
}

interface AirRightsData {
  total_lot_area: number;
  total_allowable_zfa: number;
  existing_kept_area: number;
  developable_zfa: number;
  development_lot_area: number;
}

interface AssemblagePreview {
  preview_id: string;
  is_assemblage: boolean;
  lots: LotCard[];
  address: string;
  bbl: string;
  lot_area: number;
  zoning_districts: string[];
  buildable_sf: number;
  scenarios: Scenario[];
  pricing: {
    buildable_sf: number;
    price_cents: number;
    price_dollars: number;
    breakdown: { range: string; sf: number; rate: number; subtotal: number }[];
    effective_rate: number;
  };
  air_rights: AirRightsData | null;
  assemblage_unlocks: string[];
  warnings: string[];
  zoning_envelope: {
    residential_far: number;
    commercial_far: number;
    cf_far: number;
    max_building_height: number;
    lot_coverage_max: number;
    quality_housing: boolean;
  };
}

type PageStep = "search" | "build" | "preview";

// ── Component ──

export default function StartPage() {
  const [step, setStep] = useState<PageStep>("search");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState("");

  const [lots, setLots] = useState<LotCard[]>([]);
  const [adjacentLots, setAdjacentLots] = useState<AdjacentLot[]>([]);
  const [adjacentLoading, setAdjacentLoading] = useState(false);
  const [adjacentOpen, setAdjacentOpen] = useState(false);

  const [preview, setPreview] = useState<AssemblagePreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");

  // ── Search & Add First Lot ──

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearchLoading(true);
    setSearchError("");
    try {
      const res = await fetch(
        `${API_URL}/api/v1/saas/lots/lookup?address=${encodeURIComponent(searchQuery.trim())}`
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Property not found");
      }
      const data = await res.json();

      // Check for duplicate
      if (lots.some((l) => l.bbl === data.bbl)) {
        setSearchError("This property is already in your development site.");
        return;
      }

      const newLot: LotCard = {
        bbl: data.bbl,
        address: data.address || searchQuery,
        lot_area: data.lot_area || 0,
        lot_frontage: data.lot_frontage || 0,
        lot_depth: data.lot_depth || 0,
        zoning_districts: data.zoning_districts || [],
        bldgarea: data.bldgarea || 0,
        builtfar: data.builtfar || 0,
        numfloors: data.numfloors || 0,
        yearbuilt: data.yearbuilt || 0,
        geometry: data.geometry,
        keepExistingBuilding: false,
      };

      setLots((prev) => [...prev, newLot]);
      setSearchQuery("");
      setStep("build");
    } catch (err: unknown) {
      setSearchError(err instanceof Error ? err.message : "Lookup failed");
    } finally {
      setSearchLoading(false);
    }
  }

  // ── Adjacent Lots ──

  async function loadAdjacentLots() {
    if (lots.length === 0) return;
    setAdjacentLoading(true);
    setAdjacentOpen(true);

    // Get adjacent lots for the most recently added lot
    const targetBbl = lots[lots.length - 1].bbl;
    try {
      const res = await fetch(
        `${API_URL}/api/v1/saas/lots/adjacent/${targetBbl}`
      );
      if (!res.ok) throw new Error("Could not load adjacent lots");
      const data = await res.json();

      // Filter out lots already in the assemblage
      const existingBbls = new Set(lots.map((l) => l.bbl));
      const available = (data.adjacent_lots || []).filter(
        (a: AdjacentLot) => !existingBbls.has(a.bbl)
      );
      setAdjacentLots(available);
    } catch {
      setAdjacentLots([]);
    } finally {
      setAdjacentLoading(false);
    }
  }

  function addAdjacentLot(adj: AdjacentLot) {
    const newLot: LotCard = {
      bbl: adj.bbl,
      address: adj.address || "",
      lot_area: adj.lot_area || 0,
      lot_frontage: 0,
      lot_depth: 0,
      zoning_districts: adj.zoning_districts || [],
      bldgarea: adj.bldgarea || 0,
      builtfar: adj.builtfar || 0,
      numfloors: adj.numfloors || 0,
      yearbuilt: adj.yearbuilt || 0,
      geometry: adj.geometry,
      keepExistingBuilding: false,
    };
    setLots((prev) => [...prev, newLot]);
    setAdjacentLots((prev) => prev.filter((a) => a.bbl !== adj.bbl));
    setAdjacentOpen(false);
  }

  function removeLot(bbl: string) {
    setLots((prev) => prev.filter((l) => l.bbl !== bbl));
    if (lots.length <= 1) {
      setStep("search");
    }
  }

  function toggleKeepBuilding(bbl: string) {
    setLots((prev) =>
      prev.map((l) =>
        l.bbl === bbl
          ? { ...l, keepExistingBuilding: !l.keepExistingBuilding }
          : l
      )
    );
  }

  // ── Analyze / Preview ──

  const hasAtLeastOneDevelopment = lots.some((l) => !l.keepExistingBuilding);

  async function handleAnalyze() {
    if (!hasAtLeastOneDevelopment) return;
    setPreviewLoading(true);
    setPreviewError("");
    try {
      const body = {
        lots: lots.map((l) => ({
          bbl: l.bbl,
          keep_existing_building: l.keepExistingBuilding,
        })),
      };
      const res = await fetch(
        `${API_URL}/api/v1/saas/reports/preview-assemblage`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Analysis failed");
      }
      const data: AssemblagePreview = await res.json();
      setPreview(data);
      setStep("preview");
    } catch (err: unknown) {
      setPreviewError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setPreviewLoading(false);
    }
  }

  function handleGetReport() {
    if (!preview) return;
    localStorage.setItem("massing_preview", JSON.stringify(preview));
    window.location.href = "/sign-up?redirect_url=/checkout";
  }

  // ── Computed ──

  const totalLotArea = lots.reduce((s, l) => s + l.lot_area, 0);
  const totalKeptArea = lots
    .filter((l) => l.keepExistingBuilding)
    .reduce((s, l) => s + l.bldgarea, 0);

  // ── Render ──

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Nav */}
      <nav className="bg-white shadow-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-sm font-bold"
              style={{ backgroundColor: BRAND_NAVY }}
            >
              MR
            </div>
            <span className="font-semibold text-gray-900">Massing Report</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/sign-in" className="text-sm text-gray-600 hover:text-gray-900">
              Sign In
            </Link>
          </div>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-6 py-10">
        {/* Step Indicator */}
        <div className="flex items-center gap-3 mb-8">
          {(["search", "build", "preview"] as PageStep[]).map((s, i) => (
            <div key={s} className="flex items-center gap-2">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition ${
                  step === s
                    ? "text-white"
                    : i < ["search", "build", "preview"].indexOf(step)
                    ? "text-white"
                    : "bg-gray-200 text-gray-500"
                }`}
                style={
                  step === s || i < ["search", "build", "preview"].indexOf(step)
                    ? { backgroundColor: BRAND_GOLD }
                    : {}
                }
              >
                {i + 1}
              </div>
              <span
                className={`text-sm font-medium ${
                  step === s ? "text-gray-900" : "text-gray-400"
                }`}
              >
                {s === "search" ? "Find Property" : s === "build" ? "Build Site" : "Preview"}
              </span>
              {i < 2 && (
                <div className="w-12 h-px bg-gray-300 mx-1" />
              )}
            </div>
          ))}
        </div>

        {/* ── STEP 1: Search ── */}
        {step === "search" && (
          <div className="space-y-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 font-heading">
                Find Your Property
              </h1>
              <p className="mt-2 text-gray-500">
                Enter a New York City address or BBL to begin your zoning analysis.
              </p>
            </div>

            <form onSubmit={handleSearch} className="space-y-4">
              <div className="flex gap-3">
                <div className="flex-1 relative">
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="120 Broadway, New York or 1000477501"
                    className="w-full pl-12 pr-4 py-4 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#D4A843] focus:border-transparent text-lg bg-white"
                  />
                </div>
                <button
                  type="submit"
                  disabled={searchLoading || !searchQuery.trim()}
                  className="px-8 py-4 rounded-lg text-white font-semibold shadow-lg hover:shadow-xl transition disabled:opacity-50"
                  style={{ backgroundColor: BRAND_GOLD }}
                >
                  {searchLoading ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    "Search"
                  )}
                </button>
              </div>
              {searchError && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start gap-2">
                  <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                  <p className="text-red-700 text-sm">{searchError}</p>
                </div>
              )}
            </form>
          </div>
        )}

        {/* ── STEP 2: Build Assemblage ── */}
        {step === "build" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900 font-heading">
                  Your Development Site
                </h1>
                <p className="mt-1 text-gray-500">
                  {lots.length === 1
                    ? "Add adjacent properties to create an assemblage, or analyze this lot."
                    : `${lots.length} lots assembled`}
                </p>
              </div>
              <button
                onClick={() => {
                  setStep("search");
                }}
                className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
              >
                <ArrowLeft className="w-4 h-4" /> Back
              </button>
            </div>

            {/* Lot Cards */}
            <div className="space-y-4">
              {lots.map((lot) => (
                <div
                  key={lot.bbl}
                  className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <Building2 className="w-5 h-5" style={{ color: BRAND_NAVY }} />
                        <h3 className="font-semibold text-gray-900">
                          {lot.address || lot.bbl}
                        </h3>
                      </div>
                      <div className="mt-2 grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                        <div>
                          <span className="text-gray-400 text-xs uppercase">BBL</span>
                          <p className="text-gray-700 font-mono text-xs">{lot.bbl}</p>
                        </div>
                        <div>
                          <span className="text-gray-400 text-xs uppercase">Lot Area</span>
                          <p className="text-gray-700">{lot.lot_area.toLocaleString()} SF</p>
                        </div>
                        <div>
                          <span className="text-gray-400 text-xs uppercase">Zoning</span>
                          <p className="text-gray-700">
                            {lot.zoning_districts.join(", ") || "—"}
                          </p>
                        </div>
                        <div>
                          <span className="text-gray-400 text-xs uppercase">Existing Bldg</span>
                          <p className="text-gray-700">
                            {lot.bldgarea
                              ? `${lot.bldgarea.toLocaleString()} SF (${lot.numfloors} fl, ${lot.yearbuilt})`
                              : "Vacant"}
                          </p>
                        </div>
                      </div>

                      {/* Keep Existing Building Toggle */}
                      {lot.bldgarea > 0 && (
                        <button
                          type="button"
                          onClick={() => toggleKeepBuilding(lot.bbl)}
                          className="mt-3 flex items-center gap-3 cursor-pointer group"
                        >
                          <div
                            className={`w-10 h-6 rounded-full transition relative ${
                              lot.keepExistingBuilding
                                ? ""
                                : "bg-gray-300"
                            }`}
                            style={
                              lot.keepExistingBuilding
                                ? { backgroundColor: BRAND_GOLD }
                                : {}
                            }
                          >
                            <div
                              className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-transform ${
                                lot.keepExistingBuilding
                                  ? "translate-x-5"
                                  : "translate-x-1"
                              }`}
                            />
                          </div>
                          <div className="text-left">
                            <span className="text-sm font-medium text-gray-700">
                              Keep Existing Building
                            </span>
                            <span className="text-xs text-gray-400 ml-1">
                              (air rights transfer)
                            </span>
                          </div>
                        </button>
                      )}
                    </div>

                    {/* Remove button */}
                    <button
                      onClick={() => removeLot(lot.bbl)}
                      className="text-gray-400 hover:text-red-500 p-1 transition"
                      title="Remove from site"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Add adjacent property button */}
            <div className="flex gap-3">
              <button
                onClick={loadAdjacentLots}
                disabled={adjacentLoading}
                className="flex items-center gap-2 px-5 py-3 rounded-lg border-2 border-dashed text-sm font-medium hover:bg-gray-50 transition"
                style={{ borderColor: BRAND_NAVY, color: BRAND_NAVY }}
              >
                {adjacentLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Plus className="w-4 h-4" />
                )}
                Add Adjacent Property
              </button>

              {/* Also allow manual search for adjacent */}
              <button
                onClick={() => setStep("search")}
                className="flex items-center gap-2 px-5 py-3 rounded-lg border border-gray-300 text-sm text-gray-600 hover:bg-gray-50 transition"
              >
                <Search className="w-4 h-4" />
                Search by Address
              </button>
            </div>

            {/* Adjacent lots panel */}
            {adjacentOpen && (
              <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                <h3 className="font-semibold text-gray-900 mb-1 flex items-center gap-2">
                  <Layers className="w-5 h-5" style={{ color: BRAND_GOLD }} />
                  Qualifying Adjacent Properties
                </h3>
                <p className="text-xs text-gray-400 mb-4">
                  Per NYC ZR Section 12-10, lots must share at least 10 ft of common boundary.
                </p>

                {adjacentLoading ? (
                  <div className="flex items-center gap-2 text-gray-500 py-4">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Searching for adjacent lots...
                  </div>
                ) : adjacentLots.length === 0 ? (
                  <p className="text-gray-500 text-sm py-2">
                    No qualifying adjacent lots found.
                  </p>
                ) : (
                  <div className="space-y-2">
                    {adjacentLots.map((adj) => (
                      <div
                        key={adj.bbl}
                        className="flex items-center justify-between bg-gray-50 rounded-lg p-3 hover:bg-gray-100 transition"
                      >
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-gray-900 text-sm">
                              {adj.address || adj.bbl}
                            </span>
                            <span className="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 flex items-center gap-1">
                              <Ruler className="w-3 h-3" />
                              {adj.shared_boundary_ft} ft shared
                            </span>
                          </div>
                          <div className="flex gap-4 mt-1 text-xs text-gray-500">
                            <span>{adj.lot_area.toLocaleString()} SF</span>
                            <span>{adj.zoning_districts.join(", ")}</span>
                            {adj.bldgarea > 0 && (
                              <span>
                                Bldg: {adj.bldgarea.toLocaleString()} SF ({adj.numfloors} fl)
                              </span>
                            )}
                            {adj.bldgarea === 0 && (
                              <span className="text-green-600">Vacant</span>
                            )}
                          </div>
                        </div>
                        <button
                          onClick={() => addAdjacentLot(adj)}
                          className="px-4 py-2 rounded-lg text-white text-sm font-medium hover:opacity-90 transition"
                          style={{ backgroundColor: BRAND_NAVY }}
                        >
                          Add
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                <button
                  onClick={() => setAdjacentOpen(false)}
                  className="mt-3 text-sm text-gray-400 hover:text-gray-600"
                >
                  Close
                </button>
              </div>
            )}

            {/* Combined Site Summary */}
            {lots.length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
                  Combined Site Summary
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <p className="text-2xl font-bold text-gray-900">
                      {lots.length}
                    </p>
                    <p className="text-xs text-gray-500">
                      {lots.length === 1 ? "Property" : "Properties"}
                    </p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-gray-900">
                      {totalLotArea.toLocaleString()}
                    </p>
                    <p className="text-xs text-gray-500">Total Lot Area (SF)</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-gray-900">
                      {lots.filter((l) => l.keepExistingBuilding).length}
                    </p>
                    <p className="text-xs text-gray-500">Keeping Building</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-gray-900">
                      {totalKeptArea > 0
                        ? totalKeptArea.toLocaleString()
                        : "—"}
                    </p>
                    <p className="text-xs text-gray-500">Kept Bldg Area (SF)</p>
                  </div>
                </div>
              </div>
            )}

            {/* Validation & Analyze Button */}
            {!hasAtLeastOneDevelopment && lots.length > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-start gap-2">
                <Info className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
                <p className="text-amber-700 text-sm">
                  At least one lot must be designated for development (not keeping
                  existing building).
                </p>
              </div>
            )}

            {previewError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start gap-2">
                <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                <p className="text-red-700 text-sm">{previewError}</p>
              </div>
            )}

            <button
              onClick={handleAnalyze}
              disabled={!hasAtLeastOneDevelopment || previewLoading}
              className="w-full py-4 rounded-lg text-white font-semibold text-lg shadow-lg hover:shadow-xl transition disabled:opacity-50 flex items-center justify-center gap-2"
              style={{ backgroundColor: BRAND_GOLD }}
            >
              {previewLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Analyzing Development Site...
                </>
              ) : (
                <>
                  Analyze Development Site
                  <ArrowRight className="w-5 h-5" />
                </>
              )}
            </button>
          </div>
        )}

        {/* ── STEP 3: Preview ── */}
        {step === "preview" && preview && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900 font-heading">
                  Analysis Preview
                </h1>
                <p className="mt-1 text-gray-500">
                  {preview.is_assemblage
                    ? `${preview.lots.length} lots assembled | ${preview.lot_area.toLocaleString()} SF combined`
                    : preview.address}
                </p>
              </div>
              <button
                onClick={() => setStep("build")}
                className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
              >
                <ArrowLeft className="w-4 h-4" /> Edit Site
              </button>
            </div>

            {/* Air Rights Summary */}
            {preview.air_rights && (
              <div
                className="rounded-xl p-5 text-white"
                style={{ backgroundColor: BRAND_NAVY }}
              >
                <h3 className="font-semibold mb-3 flex items-center gap-2">
                  <Building2 className="w-5 h-5" />
                  Air Rights Transfer
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <p className="text-white/60 text-xs">Total Allowable ZFA</p>
                    <p className="font-bold text-lg">
                      {preview.air_rights.total_allowable_zfa.toLocaleString()} SF
                    </p>
                  </div>
                  <div>
                    <p className="text-white/60 text-xs">Existing Kept</p>
                    <p className="font-bold text-lg text-red-300">
                      -{preview.air_rights.existing_kept_area.toLocaleString()} SF
                    </p>
                  </div>
                  <div>
                    <p className="text-white/60 text-xs">Developable ZFA</p>
                    <p className="font-bold text-lg" style={{ color: BRAND_GOLD }}>
                      {preview.air_rights.developable_zfa.toLocaleString()} SF
                    </p>
                  </div>
                  <div>
                    <p className="text-white/60 text-xs">Dev Site Area</p>
                    <p className="font-bold text-lg">
                      {preview.air_rights.development_lot_area.toLocaleString()} SF
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Assemblage Unlocks */}
            {preview.assemblage_unlocks && preview.assemblage_unlocks.length > 0 && (
              <div className="bg-green-50 border border-green-200 rounded-xl p-5">
                <h3 className="font-semibold text-green-800 mb-2 flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5" />
                  Assemblage Unlocks
                </h3>
                <ul className="space-y-1">
                  {preview.assemblage_unlocks.map((u, i) => (
                    <li key={i} className="text-green-700 text-sm flex items-start gap-2">
                      <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-green-500 flex-shrink-0" />
                      {u}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Zoning Overview */}
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
              <h3 className="font-semibold text-gray-900 mb-3">Zoning Overview</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <p className="text-gray-400 text-xs uppercase">Total Lot Area</p>
                  <p className="font-bold text-gray-900 text-lg">
                    {preview.lot_area.toLocaleString()} SF
                  </p>
                </div>
                <div>
                  <p className="text-gray-400 text-xs uppercase">Zoning</p>
                  <p className="font-bold text-gray-900">
                    {preview.zoning_districts.join(", ")}
                  </p>
                </div>
                <div>
                  <p className="text-gray-400 text-xs uppercase">Res FAR</p>
                  <p className="font-bold text-gray-900">
                    {preview.zoning_envelope.residential_far || "—"}
                  </p>
                </div>
                <div>
                  <p className="text-gray-400 text-xs uppercase">Comm FAR</p>
                  <p className="font-bold text-gray-900">
                    {preview.zoning_envelope.commercial_far || "—"}
                  </p>
                </div>
              </div>
            </div>

            {/* Scenarios Table */}
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm overflow-x-auto">
              <h3 className="font-semibold text-gray-900 mb-3">
                Development Scenarios
              </h3>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-400 uppercase border-b">
                    <th className="pb-2 pr-4">Scenario</th>
                    <th className="pb-2 pr-4 text-right">ZFA</th>
                    <th className="pb-2 pr-4 text-right">Height</th>
                    <th className="pb-2 pr-4 text-right">Floors</th>
                    <th className="pb-2 pr-4 text-right">Units</th>
                    <th className="pb-2 text-right">FAR</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.scenarios.map((s, i) => (
                    <tr key={i} className="border-b border-gray-100 last:border-0">
                      <td className="py-2 pr-4 font-medium text-gray-900">
                        {s.name}
                      </td>
                      <td className="py-2 pr-4 text-right text-gray-700">
                        {s.total_zfa?.toLocaleString() || "—"}
                      </td>
                      <td className="py-2 pr-4 text-right text-gray-700">
                        {s.max_height_ft ? `${s.max_height_ft} ft` : "—"}
                      </td>
                      <td className="py-2 pr-4 text-right text-gray-700">
                        {s.num_floors || "—"}
                      </td>
                      <td className="py-2 pr-4 text-right text-gray-700">
                        {s.total_units || "—"}
                      </td>
                      <td className="py-2 text-right text-gray-700">
                        {s.far_used?.toFixed(2) || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pricing & Generate */}
            <div
              className="rounded-xl p-6 text-white flex items-center justify-between"
              style={{ backgroundColor: BRAND_NAVY }}
            >
              <div>
                <h3 className="font-semibold text-lg">Full Feasibility Report</h3>
                <p className="text-white/70 text-sm mt-1">
                  Professional PDF with zoning maps, 3D massing, building programs,
                  and detailed calculations.
                </p>
                {preview.pricing?.breakdown && (
                  <div className="mt-2 text-xs text-white/50 space-y-0.5">
                    {preview.pricing.breakdown.map((b, i) => (
                      <p key={i}>
                        {b.range}: {b.sf.toLocaleString()} SF @ ${b.rate.toFixed(2)}/SF = ${b.subtotal.toLocaleString()}
                      </p>
                    ))}
                  </div>
                )}
              </div>
              <div className="text-right flex-shrink-0 ml-6">
                <p className="text-3xl font-bold">
                  ${(preview.pricing.price_cents / 100).toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                  })}
                </p>
                <button
                  onClick={handleGetReport}
                  className="mt-3 px-8 py-3 rounded-lg font-semibold text-sm hover:opacity-90 transition"
                  style={{ backgroundColor: BRAND_GOLD }}
                >
                  Generate Report
                </button>
              </div>
            </div>

            {/* Warnings */}
            {preview.warnings && preview.warnings.length > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                <p className="text-amber-700 text-sm font-medium mb-1">Notes:</p>
                {preview.warnings.map((w, i) => (
                  <p key={i} className="text-amber-600 text-xs">
                    {w}
                  </p>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
