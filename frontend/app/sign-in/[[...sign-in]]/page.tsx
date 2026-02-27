"use client";

import { SignIn, SignUp } from "@clerk/nextjs";
import { useState, useEffect } from "react";
import Link from "next/link";
import { CheckCircle2, MapPin, FileText, Layers, ArrowRightLeft } from "lucide-react";

export const dynamic = "force-dynamic";

const BRAND_GOLD = "#D4A843";
const BRAND_NAVY = "#2C5F7C";

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
  zoning_districts: string[];
  buildable_sf: number;
  scenarios: { name: string; total_zfa: number; max_height_ft: number; num_floors: number; total_units: number; far_used: number }[];
  pricing: {
    buildable_sf: number;
    price_cents: number;
    price_dollars: number;
    breakdown: { range: string; sf: number; rate: number; subtotal: number }[];
    effective_rate: number;
  };
  is_assemblage?: boolean;
  lots?: LotSummary[];
  air_rights?: AirRightsData | null;
  assemblage_unlocks?: string[];
}

const CLERK_APPEARANCE = {
  elements: {
    rootBox: "w-full max-w-md",
    card: "shadow-lg border border-gray-200 rounded-xl",
    headerTitle: "text-xl font-bold",
    headerSubtitle: "text-gray-500 text-sm",
    socialButtonsBlockButton:
      "py-3 text-base font-medium border-2 border-gray-200 hover:border-gray-300 transition",
    socialButtonsBlockButtonText: "text-sm font-semibold",
    formFieldInput:
      "py-2.5 text-sm border-gray-200 focus:ring-2 focus:ring-[#D4A843] focus:border-transparent",
    formFieldLabel: "text-xs font-medium text-gray-600",
    formButtonPrimary:
      "py-3 text-base font-semibold shadow-md hover:shadow-lg transition",
    footerAction: "text-sm",
    dividerLine: "bg-gray-200",
    dividerText: "text-gray-400 text-xs",
  },
  variables: {
    colorPrimary: BRAND_GOLD,
    borderRadius: "0.75rem",
  },
};

const FEATURES_LIST = [
  "Complete zoning feasibility analysis",
  "All development scenarios with massing",
  "3D massing models & floor breakdowns",
  "Analyst\u2019s Manifest for pro formas",
  "Parking analysis & waiver eligibility",
  "Professional PDF report download",
];

export default function SignInPage() {
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [preview, setPreview] = useState<PreviewData | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem("massing_preview");
    if (stored) {
      try {
        setPreview(JSON.parse(stored));
      } catch {
        // ignore parse errors
      }
    }
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Nav */}
      <nav className="border-b border-gray-100 bg-white">
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
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-6 py-10">
        <div className={`grid gap-8 items-start ${preview ? "grid-cols-1 lg:grid-cols-2" : "grid-cols-1 max-w-xl mx-auto"}`}>
          {/* LEFT: Auth */}
          <div>
            <div className={`mb-6 ${preview ? "text-left" : "text-center"}`}>
              <h1 className="text-2xl font-bold text-gray-900 mb-2">
                {preview ? "Sign in to get your report" : "Welcome Back"}
              </h1>
              <p className="text-gray-600 text-sm">
                {preview
                  ? "Sign in to generate your full zoning feasibility report."
                  : "Sign in to access your account and reports."}
              </p>
            </div>

            {/* Tab Switcher */}
            <div className={`mb-6 ${preview ? "" : "flex justify-center"}`}>
              <div className="inline-flex bg-white rounded-lg border border-gray-200 p-1">
                <button
                  onClick={() => setMode("signin")}
                  className={`px-5 py-2 rounded-md text-sm font-medium transition ${
                    mode === "signin"
                      ? "text-white shadow-sm"
                      : "text-gray-600 hover:text-gray-900"
                  }`}
                  style={mode === "signin" ? { backgroundColor: BRAND_NAVY } : {}}
                >
                  Sign In
                </button>
                <button
                  onClick={() => setMode("signup")}
                  className={`px-5 py-2 rounded-md text-sm font-medium transition ${
                    mode === "signup"
                      ? "text-white shadow-sm"
                      : "text-gray-600 hover:text-gray-900"
                  }`}
                  style={mode === "signup" ? { backgroundColor: BRAND_NAVY } : {}}
                >
                  Sign Up
                </button>
              </div>
            </div>

            {/* Auth Component */}
            <div className={preview ? "" : "flex justify-center"}>
              {mode === "signin" ? (
                <SignIn
                  appearance={CLERK_APPEARANCE}
                  forceRedirectUrl="/checkout"
                />
              ) : (
                <SignUp
                  appearance={CLERK_APPEARANCE}
                  forceRedirectUrl="/checkout"
                />
              )}
            </div>
          </div>

          {/* RIGHT: Checkout Preview (only if preview data exists) */}
          {preview && (
            <div className="lg:sticky lg:top-24 space-y-5">
              {/* Property / Assemblage Summary */}
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <div className="flex items-center gap-2 mb-3">
                  {preview.is_assemblage ? (
                    <Layers className="w-4 h-4" style={{ color: BRAND_GOLD }} />
                  ) : (
                    <MapPin className="w-4 h-4" style={{ color: BRAND_GOLD }} />
                  )}
                  <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
                    {preview.is_assemblage ? "Your Development Site" : "Your Property"}
                  </h2>
                </div>

                {/* Assemblage badge */}
                {preview.is_assemblage && preview.lots && (
                  <div className="mb-3 inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium text-white" style={{ backgroundColor: BRAND_NAVY }}>
                    <Layers className="w-3 h-3" />
                    {preview.lots.length} Lots Assembled
                  </div>
                )}

                <div className="space-y-2 text-sm">
                  {/* Show individual lots for assemblage */}
                  {preview.is_assemblage && preview.lots && preview.lots.length > 1 ? (
                    <>
                      {preview.lots.map((lot, i) => (
                        <div key={lot.bbl} className="flex justify-between items-start">
                          <span className="text-gray-500">Lot {i + 1}</span>
                          <span className="font-medium text-gray-900 text-right text-xs">
                            {lot.address || lot.bbl}
                            {lot.keep_existing_building && (
                              <span className="ml-1 text-xs px-1.5 py-0.5 rounded bg-amber-100 text-amber-700">Keep Bldg</span>
                            )}
                          </span>
                        </div>
                      ))}
                      <div className="border-t border-gray-100 pt-2 mt-2" />
                    </>
                  ) : (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Address</span>
                      <span className="font-medium text-gray-900">{preview.address}</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-gray-500">{preview.is_assemblage ? "Combined Area" : "Lot Area"}</span>
                    <span className="font-medium text-gray-900">
                      {preview.lot_area?.toLocaleString()} SF
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Zoning</span>
                    <span className="font-medium text-gray-900">
                      {preview.zoning_districts?.join(", ") || "\u2014"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Max Buildable</span>
                    <span className="font-medium text-gray-900">
                      {preview.buildable_sf?.toLocaleString()} SF
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Scenarios</span>
                    <span className="font-medium text-gray-900">
                      {preview.scenarios?.length || 0}
                    </span>
                  </div>
                </div>
              </div>

              {/* Air Rights Summary (only for assemblage with air rights) */}
              {preview.air_rights && (
                <div className="bg-white rounded-xl border border-gray-200 p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <ArrowRightLeft className="w-4 h-4" style={{ color: BRAND_GOLD }} />
                    <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
                      Air Rights Transfer
                    </h2>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Total Allowable ZFA</span>
                      <span className="font-medium text-gray-900">
                        {preview.air_rights.total_allowable_zfa?.toLocaleString()} SF
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Existing Kept Area</span>
                      <span className="font-medium text-red-600">
                        -{preview.air_rights.existing_kept_area?.toLocaleString()} SF
                      </span>
                    </div>
                    <div className="flex justify-between border-t border-gray-100 pt-2">
                      <span className="text-gray-500 font-medium">Developable ZFA</span>
                      <span className="font-bold" style={{ color: BRAND_NAVY }}>
                        {preview.air_rights.developable_zfa?.toLocaleString()} SF
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* What You Get */}
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <div className="flex items-center gap-2 mb-3">
                  <FileText className="w-4 h-4" style={{ color: BRAND_GOLD }} />
                  <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
                    What You Get
                  </h2>
                </div>
                <ul className="space-y-2">
                  {FEATURES_LIST.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-gray-700">
                      <CheckCircle2
                        className="w-4 h-4 flex-shrink-0 mt-0.5"
                        style={{ color: BRAND_GOLD }}
                      />
                      {f}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Price Card */}
              <div
                className="rounded-xl p-5 text-white"
                style={{ backgroundColor: BRAND_NAVY }}
              >
                <p className="text-white/70 text-xs uppercase tracking-wide mb-1">
                  Report Price
                </p>
                <p className="text-3xl font-bold">
                  $
                  {(preview.pricing?.price_cents / 100).toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                  })}
                </p>
                {preview.pricing?.breakdown && (
                  <div className="mt-2 text-xs text-white/50 space-y-0.5">
                    {preview.pricing.breakdown.map((b, i) => (
                      <p key={i}>
                        {b.range}: {b.sf.toLocaleString()} SF @ ${b.rate.toFixed(2)}/SF
                      </p>
                    ))}
                  </div>
                )}
              </div>

              {/* CTA Message */}
              <div
                className="text-center p-4 rounded-xl border-2"
                style={{ borderColor: `${BRAND_GOLD}40`, backgroundColor: `${BRAND_GOLD}08` }}
              >
                <p className="text-sm font-semibold" style={{ color: BRAND_NAVY }}>
                  You&apos;re one step away from your report
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  Sign in to generate your full zoning feasibility analysis
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
