"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuthToken } from "@/lib/use-auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8321";

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

interface PricingBreakdown {
  range: string;
  sf: number;
  rate: number;
  subtotal: number;
}

interface PreviewData {
  preview_id: string;
  address: string;
  bbl: string;
  borough: number;
  lot_area: number;
  lot_frontage: number;
  lot_depth: number;
  zoning_districts: string[];
  buildable_sf: number;
  scenarios: Scenario[];
  pricing: {
    buildable_sf: number;
    price_cents: number;
    price_dollars: number;
    breakdown: PricingBreakdown[];
    effective_rate: number;
  };
  zoning_envelope: {
    residential_far: number;
    commercial_far: number;
    cf_far: number;
    max_building_height: number;
    lot_coverage_max: number;
    quality_housing: boolean;
  };
}

type Step = "input" | "preview" | "generating" | "complete";

export default function NewReportPage() {
  const { getToken } = useAuthToken();
  const router = useRouter();
  const [address, setAddress] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [step, setStep] = useState<Step>("input");
  const [reportId, setReportId] = useState<string | null>(null);
  const [reportStatus, setReportStatus] = useState<string>("");

  async function handleAnalyze(e: React.FormEvent) {
    e.preventDefault();
    if (!address.trim()) return;

    setLoading(true);
    setError("");
    setPreview(null);
    setStep("input");

    try {
      const token = await getToken();
      const res = await fetch(`${API_URL}/api/v1/saas/reports/preview`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ address: address.trim() }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Analysis failed. Please try again.");
      }

      const data: PreviewData = await res.json();
      setPreview(data);
      setStep("preview");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  // Poll for report status
  const pollReport = useCallback(async (id: string) => {
    try {
      const token = await getToken();
      const res = await fetch(`${API_URL}/api/v1/saas/reports/${id}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) return;
      const data = await res.json();
      setReportStatus(data.status);

      if (data.status === "completed") {
        setStep("complete");
      } else if (data.status === "failed") {
        setError(data.error || "Report generation failed");
        setStep("preview");
      } else {
        // Keep polling
        setTimeout(() => pollReport(id), 3000);
      }
    } catch {
      setTimeout(() => pollReport(id), 5000);
    }
  }, [getToken]);

  async function handleGenerate() {
    if (!preview) return;
    setError("");
    setStep("generating");
    setReportStatus("processing");

    try {
      const token = await getToken();
      const res = await fetch(`${API_URL}/api/v1/saas/reports/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          address: preview.address,
          bbl: preview.bbl,
          preview_id: preview.preview_id,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to start report generation");
      }

      const { report_id } = await res.json();
      setReportId(report_id);
      pollReport(report_id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Generation failed");
      setStep("preview");
    }
  }

  function handleDownload() {
    if (!reportId) return;
    window.open(`${API_URL}/api/v1/saas/reports/${reportId}/pdf`, "_blank");
  }

  // Compute max values from scenarios
  const maxBuildable = preview?.buildable_sf || 0;
  const maxHeight = preview
    ? Math.max(...preview.scenarios.map((s) => s.max_height_ft))
    : 0;
  const maxUnits = preview
    ? Math.max(...preview.scenarios.map((s) => s.total_units))
    : 0;

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-2">New Report</h1>
      <p className="text-gray-500 mb-8">
        Enter a NYC address or BBL to analyze zoning feasibility.
      </p>

      {/* Search */}
      <form onSubmit={handleAnalyze} className="mb-8">
        <div className="flex gap-3">
          <input
            type="text"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="e.g. 351 Pleasant Avenue, Manhattan or 3-04622-0022"
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#D4A843] focus:border-transparent"
          />
          <button
            type="submit"
            disabled={loading || !address.trim()}
            className="px-6 py-3 rounded-lg text-white font-medium bg-[#D4A843] hover:opacity-90 disabled:opacity-50 transition whitespace-nowrap"
          >
            {loading ? "Analyzing..." : "Analyze"}
          </button>
        </div>
      </form>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-red-700 text-sm">
          {error}
        </div>
      )}

      {loading && (
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
          <div className="animate-spin w-8 h-8 border-4 border-gray-200 border-t-[#D4A843] rounded-full mx-auto mb-4" />
          <p className="text-gray-600">
            Running zoning analysis... This takes a few seconds.
          </p>
        </div>
      )}

      {/* Preview Results */}
      {preview && step !== "input" && !loading && (
        <div className="space-y-6">
          {/* Property Summary */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Property Summary
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wide">
                  Address
                </p>
                <p className="font-medium text-gray-900">{preview.address}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wide">
                  BBL
                </p>
                <p className="font-medium text-gray-900">{preview.bbl}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wide">
                  Zoning
                </p>
                <p className="font-medium text-gray-900">
                  {preview.zoning_districts?.join(", ") || "—"}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wide">
                  Lot Area
                </p>
                <p className="font-medium text-gray-900">
                  {preview.lot_area?.toLocaleString()} SF
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wide">
                  Frontage
                </p>
                <p className="font-medium text-gray-900">
                  {preview.lot_frontage?.toFixed(1)}&#39;
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wide">
                  Depth
                </p>
                <p className="font-medium text-gray-900">
                  {preview.lot_depth?.toFixed(1)}&#39;
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wide">
                  Max FAR
                </p>
                <p className="font-medium text-gray-900">
                  {preview.zoning_envelope?.residential_far || "—"}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wide">
                  Coverage
                </p>
                <p className="font-medium text-gray-900">
                  {preview.zoning_envelope?.lot_coverage_max
                    ? `${preview.zoning_envelope.lot_coverage_max}%`
                    : "—"}
                </p>
              </div>
            </div>
          </div>

          {/* Key Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white rounded-lg border border-gray-200 p-6 text-center">
              <p className="text-sm text-gray-500">Max Buildable SF</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">
                {maxBuildable.toLocaleString()}
              </p>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-6 text-center">
              <p className="text-sm text-gray-500">Max Height</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">
                {maxHeight} ft
              </p>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-6 text-center">
              <p className="text-sm text-gray-500">Max Units</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">
                {maxUnits}
              </p>
            </div>
          </div>

          {/* Scenarios */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Development Scenarios
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b">
                    <th className="pb-2 font-medium">Scenario</th>
                    <th className="pb-2 font-medium text-right">ZFA</th>
                    <th className="pb-2 font-medium text-right">Height</th>
                    <th className="pb-2 font-medium text-right">Floors</th>
                    <th className="pb-2 font-medium text-right">Units</th>
                    <th className="pb-2 font-medium text-right">FAR</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.scenarios.map((s) => (
                    <tr key={s.name} className="border-b border-gray-100">
                      <td className="py-2.5 text-gray-900 font-medium">
                        {s.name}
                      </td>
                      <td className="py-2.5 text-right text-gray-700">
                        {s.total_zfa?.toLocaleString()}
                      </td>
                      <td className="py-2.5 text-right text-gray-700">
                        {s.max_height_ft}&#39;
                      </td>
                      <td className="py-2.5 text-right text-gray-700">
                        {s.num_floors}
                      </td>
                      <td className="py-2.5 text-right text-gray-700">
                        {s.total_units}
                      </td>
                      <td className="py-2.5 text-right text-gray-700">
                        {s.far_used?.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Generating / Complete State */}
          {step === "generating" && (
            <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
              <div className="animate-spin w-10 h-10 border-4 border-gray-200 border-t-[#D4A843] rounded-full mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Generating Your Report
              </h3>
              <p className="text-gray-500 text-sm">
                Building zoning maps, 3D massing models, and detailed
                calculations... This typically takes 15-30 seconds.
              </p>
              <p className="text-xs text-gray-400 mt-2">
                Status: {reportStatus}
              </p>
            </div>
          )}

          {step === "complete" && reportId && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-8 text-center">
              <div className="text-4xl mb-3">✅</div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Report Ready!
              </h3>
              <p className="text-gray-600 text-sm mb-6">
                Your zoning feasibility report has been generated.
              </p>
              <div className="flex gap-3 justify-center">
                <button
                  onClick={handleDownload}
                  className="px-6 py-3 rounded-lg text-white font-semibold bg-[#D4A843] hover:opacity-90 transition"
                >
                  Download PDF
                </button>
                <button
                  onClick={() => router.push(`/dashboard/reports/${reportId}`)}
                  className="px-6 py-3 rounded-lg text-gray-700 font-semibold bg-white border border-gray-300 hover:bg-gray-50 transition"
                >
                  View Report
                </button>
              </div>
            </div>
          )}

          {/* Price + Generate Button (only in preview step) */}
          {step === "preview" && (
            <div className="bg-[#2C5F7C] rounded-lg p-6 text-white">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold mb-1">
                    Full Feasibility Report
                  </h2>
                  <p className="text-white/70 text-sm">
                    Professional PDF with zoning maps, 3D massing, building
                    programs, and detailed calculations.
                  </p>
                  {preview.pricing?.breakdown && (
                    <div className="mt-3 text-xs text-white/60 space-y-0.5">
                      {preview.pricing.breakdown.map(
                        (b: PricingBreakdown, i: number) => (
                          <p key={i}>
                            {b.range}: {b.sf.toLocaleString()} SF @ $
                            {b.rate.toFixed(2)}/SF = $
                            {b.subtotal.toLocaleString()}
                          </p>
                        )
                      )}
                    </div>
                  )}
                </div>
                <div className="text-right ml-6 flex-shrink-0">
                  <p className="text-3xl font-bold">
                    ${(preview.pricing?.price_cents / 100).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </p>
                  <button
                    onClick={handleGenerate}
                    className="mt-3 px-6 py-3 rounded-lg font-semibold text-sm bg-[#D4A843] hover:opacity-90 transition"
                  >
                    Generate Report
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
