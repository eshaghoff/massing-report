"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuthToken } from "@/lib/use-auth";
import { CheckCircle2, FileText, Loader2, AlertCircle, ArrowLeft, Layers, ArrowRightLeft } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8321";
const BRAND_GOLD = "#D4A843";
const BRAND_NAVY = "#2C5F7C";

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

interface LotSummary {
  bbl: string;
  address: string;
  lot_area: number;
  zoning_districts: string[];
  bldgarea: number;
  builtfar: number;
  keep_existing_building: boolean;
}

interface AirRightsData {
  total_lot_area: number;
  total_allowable_zfa: number;
  existing_kept_area: number;
  developable_zfa: number;
  development_lot_area: number;
}

interface PreviewData {
  preview_id: string;
  address: string;
  bbl: string;
  borough?: number;
  lot_area: number;
  lot_frontage?: number;
  lot_depth?: number;
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
  zoning_envelope?: {
    residential_far: number;
    commercial_far: number;
    cf_far: number;
    max_building_height: number;
    lot_coverage_max: number;
    quality_housing: boolean;
  };
  is_assemblage?: boolean;
  lots?: LotSummary[];
  air_rights?: AirRightsData | null;
  assemblage_unlocks?: string[];
}

type CheckoutStep = "confirm" | "generating" | "complete" | "error";

export default function CheckoutPage() {
  const { getToken, isLoaded } = useAuthToken();
  const router = useRouter();

  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [step, setStep] = useState<CheckoutStep>("confirm");
  const [error, setError] = useState("");
  const [reportId, setReportId] = useState<string | null>(null);
  const [reportStatus, setReportStatus] = useState("");

  // Load preview from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem("massing_preview");
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        setPreview(parsed);
      } catch {
        setError("Could not load your analysis. Please try again from the home page.");
      }
    } else {
      setError("No analysis found. Please start from the home page.");
    }
  }, []);

  // Auto-trigger generation when preview is loaded and auth is ready
  useEffect(() => {
    if (preview && isLoaded && step === "confirm" && !reportId) {
      handleGenerate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preview, isLoaded]);

  // Poll for report completion
  const pollStatus = useCallback(
    async (id: string) => {
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
          localStorage.removeItem("massing_preview");
        } else if (data.status === "failed") {
          setStep("error");
          setError(data.error || "Report generation failed. Please try again.");
        } else {
          // Still generating — poll again
          setTimeout(() => pollStatus(id), 3000);
        }
      } catch {
        setTimeout(() => pollStatus(id), 5000);
      }
    },
    [getToken]
  );

  async function handleGenerate() {
    if (!preview) return;
    setStep("generating");
    setError("");
    setReportStatus("Initializing...");

    try {
      const token = await getToken();
      const res = await fetch(`${API_URL}/api/v1/saas/reports/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ preview_id: preview.preview_id }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to start report generation.");
      }

      const data = await res.json();
      setReportId(data.report_id);
      setReportStatus("Generating zoning analysis...");
      pollStatus(data.report_id);
    } catch (err: unknown) {
      setStep("error");
      setError(err instanceof Error ? err.message : "Something went wrong.");
    }
  }

  async function handleDownload() {
    if (!reportId) return;
    try {
      const token = await getToken();
      const res = await fetch(`${API_URL}/api/v1/saas/reports/${reportId}/pdf`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error("Download failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `massing-report-${preview?.bbl || "report"}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      setError("Failed to download PDF. Please try again.");
    }
  }

  // Helper: display name for the property/assemblage
  const displayName = preview?.is_assemblage && preview.lots && preview.lots.length > 1
    ? `${preview.lots.length}-Lot Assemblage`
    : preview?.address || "";

  if (!isLoaded) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (error && !preview) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h1 className="text-xl font-semibold text-gray-900 mb-2">Something Went Wrong</h1>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={() => router.push("/")}
            className="px-6 py-3 rounded-lg text-white font-semibold"
            style={{ backgroundColor: BRAND_GOLD }}
          >
            Back to Home
          </button>
        </div>
      </div>
    );
  }

  if (!preview) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Nav */}
      <nav className="border-b border-gray-100 bg-white">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <button
            onClick={() => router.push("/")}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 text-sm"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
          <div className="flex items-center gap-2">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-sm font-bold"
              style={{ backgroundColor: BRAND_NAVY }}
            >
              MR
            </div>
            <span className="font-semibold text-gray-900">Massing Report</span>
          </div>
          <div className="w-16" /> {/* Spacer */}
        </div>
      </nav>

      <div className="max-w-3xl mx-auto px-6 py-12">
        {/* Confirm Step */}
        {step === "confirm" && (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                Generate Your Report
              </h1>
              <p className="text-gray-600">
                Review your {preview.is_assemblage ? "development site" : "property"} details and confirm to generate the full report.
              </p>
            </div>

            {/* Property / Assemblage Summary Card */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-center gap-2 mb-4">
                {preview.is_assemblage ? (
                  <Layers className="w-5 h-5" style={{ color: BRAND_GOLD }} />
                ) : null}
                <h2 className="text-lg font-semibold text-gray-900">
                  {preview.is_assemblage ? "Development Site Summary" : "Property Summary"}
                </h2>
              </div>

              {/* Assemblage badge */}
              {preview.is_assemblage && preview.lots && (
                <div className="mb-4 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium text-white" style={{ backgroundColor: BRAND_NAVY }}>
                  <Layers className="w-3 h-3" />
                  {preview.lots.length} Lots Assembled &bull; {preview.lot_area?.toLocaleString()} SF Combined
                </div>
              )}

              {/* Individual lots for assemblage */}
              {preview.is_assemblage && preview.lots && preview.lots.length > 1 && (
                <div className="mb-4 space-y-2">
                  {preview.lots.map((lot, i) => (
                    <div key={lot.bbl} className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded-lg text-sm">
                      <div>
                        <span className="font-medium text-gray-900">{lot.address || lot.bbl}</span>
                        <span className="ml-2 text-gray-400 text-xs">{lot.bbl}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-gray-500 text-xs">{lot.lot_area?.toLocaleString()} SF</span>
                        {lot.keep_existing_building && (
                          <span className="text-xs px-2 py-0.5 rounded bg-amber-100 text-amber-700 font-medium">Keep Building</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                {!preview.is_assemblage && (
                  <>
                    <div>
                      <p className="text-xs text-gray-500 uppercase tracking-wide">Address</p>
                      <p className="font-medium text-gray-900">{preview.address}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 uppercase tracking-wide">BBL</p>
                      <p className="font-medium text-gray-900">{preview.bbl}</p>
                    </div>
                  </>
                )}
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Zoning</p>
                  <p className="font-medium text-gray-900">
                    {preview.zoning_districts?.join(", ") || "\u2014"}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wide">{preview.is_assemblage ? "Combined Area" : "Lot Area"}</p>
                  <p className="font-medium text-gray-900">
                    {preview.lot_area?.toLocaleString()} SF
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Max Buildable SF</p>
                  <p className="font-medium text-gray-900">
                    {preview.buildable_sf?.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Scenarios</p>
                  <p className="font-medium text-gray-900">
                    {preview.scenarios?.length || 0} development scenarios
                  </p>
                </div>
              </div>
            </div>

            {/* Air Rights Card (only for assemblage with air rights) */}
            {preview.air_rights && (
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <div className="flex items-center gap-2 mb-4">
                  <ArrowRightLeft className="w-5 h-5" style={{ color: BRAND_GOLD }} />
                  <h2 className="text-lg font-semibold text-gray-900">Air Rights Transfer</h2>
                </div>
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">Total Allowable</p>
                    <p className="text-xl font-bold text-gray-900">{preview.air_rights.total_allowable_zfa?.toLocaleString()}</p>
                    <p className="text-xs text-gray-400">SF</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">Kept Buildings</p>
                    <p className="text-xl font-bold text-red-600">-{preview.air_rights.existing_kept_area?.toLocaleString()}</p>
                    <p className="text-xs text-gray-400">SF</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">Developable</p>
                    <p className="text-xl font-bold" style={{ color: BRAND_NAVY }}>{preview.air_rights.developable_zfa?.toLocaleString()}</p>
                    <p className="text-xs text-gray-400">SF</p>
                  </div>
                </div>
              </div>
            )}

            {/* Pricing Card */}
            <div
              className="rounded-xl p-6 text-white"
              style={{ backgroundColor: BRAND_NAVY }}
            >
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold mb-1">Report Price</h2>
                  {preview.pricing?.breakdown && (
                    <div className="text-xs text-white/60 space-y-0.5 mt-2">
                      {preview.pricing.breakdown.map((b: PricingBreakdown, i: number) => (
                        <p key={i}>
                          {b.range}: {b.sf.toLocaleString()} SF @ ${b.rate.toFixed(2)}/SF = ${b.subtotal.toLocaleString()}
                        </p>
                      ))}
                      <p className="mt-1 text-white/50">
                        Effective rate: ${preview.pricing.effective_rate.toFixed(4)}/SF
                      </p>
                    </div>
                  )}
                </div>
                <div className="text-right">
                  <p className="text-4xl font-bold">
                    ${(preview.pricing?.price_cents / 100).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </p>
                </div>
              </div>
            </div>

            {/* What You Get */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wide">
                What&apos;s Included
              </h2>
              <div className="grid grid-cols-2 gap-2">
                {[
                  "Complete zoning analysis",
                  "All development scenarios",
                  "3D massing models",
                  "Floor-by-floor breakdown",
                  "Parking requirements",
                  "Professional PDF report",
                ].map((item) => (
                  <div key={item} className="flex items-center gap-2 text-sm text-gray-700">
                    <CheckCircle2 className="w-4 h-4 flex-shrink-0" style={{ color: BRAND_GOLD }} />
                    {item}
                  </div>
                ))}
              </div>
            </div>

            {/* Generate Button */}
            <button
              onClick={handleGenerate}
              className="w-full py-4 rounded-xl text-white font-semibold text-lg shadow-lg hover:shadow-xl transition"
              style={{ backgroundColor: BRAND_GOLD }}
            >
              Generate Report — ${(preview.pricing?.price_cents / 100).toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </button>

            {error && (
              <p className="text-red-600 text-sm text-center">{error}</p>
            )}
          </div>
        )}

        {/* Generating Step */}
        {step === "generating" && (
          <div className="text-center py-20">
            <div className="relative w-20 h-20 mx-auto mb-6">
              <div
                className="absolute inset-0 rounded-full animate-ping opacity-20"
                style={{ backgroundColor: BRAND_GOLD }}
              />
              <div
                className="relative w-20 h-20 rounded-full flex items-center justify-center"
                style={{ backgroundColor: `${BRAND_NAVY}15` }}
              >
                <Loader2 className="w-10 h-10 animate-spin" style={{ color: BRAND_NAVY }} />
              </div>
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              Generating Your Report
            </h1>
            <p className="text-gray-500 mb-4">{displayName}</p>
            {preview.is_assemblage && preview.lots && (
              <p className="text-xs text-gray-400 mb-2">
                {preview.lots.length} lots &bull; {preview.lot_area?.toLocaleString()} SF combined
                {preview.air_rights ? ` \u2022 Air rights transfer` : ""}
              </p>
            )}
            <p className="text-sm text-gray-400">{reportStatus}</p>
            <div className="mt-8 max-w-sm mx-auto space-y-3">
              {[
                { label: "Zoning analysis", done: true },
                { label: "Development scenarios", done: reportStatus.includes("massing") || reportStatus.includes("Generating") },
                { label: "3D massing models", done: reportStatus.includes("PDF") || reportStatus.includes("final") },
                { label: "PDF compilation", done: reportStatus.includes("final") || reportStatus.includes("complete") },
              ].map((item) => (
                <div key={item.label} className="flex items-center gap-3 text-sm">
                  {item.done ? (
                    <CheckCircle2 className="w-5 h-5" style={{ color: BRAND_GOLD }} />
                  ) : (
                    <div className="w-5 h-5 rounded-full border-2 border-gray-200" />
                  )}
                  <span className={item.done ? "text-gray-900" : "text-gray-400"}>
                    {item.label}
                  </span>
                </div>
              ))}
            </div>
            <p className="mt-8 text-xs text-gray-400">
              This usually takes 2\u20135 minutes. You can leave this page \u2014 we&apos;ll save your report.
            </p>
          </div>
        )}

        {/* Complete Step */}
        {step === "complete" && (
          <div className="text-center py-20">
            <div
              className="w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6"
              style={{ backgroundColor: `${BRAND_GOLD}15` }}
            >
              <CheckCircle2 className="w-12 h-12" style={{ color: BRAND_GOLD }} />
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Your Report Is Ready!
            </h1>
            <p className="text-gray-600 mb-8">{displayName}</p>
            <div className="flex flex-col items-center gap-4">
              <button
                onClick={handleDownload}
                className="inline-flex items-center gap-2 px-8 py-4 rounded-lg text-white font-semibold text-lg shadow-lg hover:shadow-xl transition"
                style={{ backgroundColor: BRAND_GOLD }}
              >
                <FileText className="w-5 h-5" />
                Download PDF Report
              </button>
              <button
                onClick={() => router.push("/dashboard")}
                className="text-sm text-gray-500 hover:text-gray-700 underline"
              >
                Go to Dashboard
              </button>
            </div>
          </div>
        )}

        {/* Error Step */}
        {step === "error" && (
          <div className="text-center py-20">
            <AlertCircle className="w-16 h-16 text-red-400 mx-auto mb-6" />
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              Generation Failed
            </h1>
            <p className="text-gray-600 mb-8">{error}</p>
            <div className="flex flex-col items-center gap-4">
              <button
                onClick={handleGenerate}
                className="px-8 py-3 rounded-lg text-white font-semibold"
                style={{ backgroundColor: BRAND_GOLD }}
              >
                Try Again
              </button>
              <button
                onClick={() => router.push("/")}
                className="text-sm text-gray-500 hover:text-gray-700 underline"
              >
                Start Over
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
