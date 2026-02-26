"use client";

import { useState } from "react";
import Link from "next/link";
import {
  MapPin,
  Calculator,
  ArrowUpFromLine,
  Maximize,
  Layers,
  TableProperties,
  Box,
  Home,
  Car,
  TrendingUp,
  FileText,
  Users,
  Clock,
  DollarSign,
  Building2,
  CheckCircle2,
  Zap,
  Shield,
  Search,
  Download,
} from "lucide-react";

const BRAND_GOLD = "#D4A843";
const BRAND_NAVY = "#2C5F7C";
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

const FEATURES = [
  {
    icon: MapPin,
    title: "Zoning District Analysis",
    desc: "Full zoning district breakdown with overlays and special districts",
  },
  {
    icon: Calculator,
    title: "FAR Calculations",
    desc: "Residential, commercial, and community facility FAR with bonuses",
  },
  {
    icon: ArrowUpFromLine,
    title: "Height & Setback Rules",
    desc: "Base height, max height, sky exposure plane, and setback requirements",
  },
  {
    icon: Maximize,
    title: "Lot Coverage & Yards",
    desc: "Front, rear, and side yard requirements with coverage limits",
  },
  {
    icon: Layers,
    title: "Development Scenarios",
    desc: "Multiple building programs: max residential, commercial, and mixed-use",
  },
  {
    icon: TableProperties,
    title: "Floor-by-Floor Breakdown",
    desc: "Detailed floor plans with use type, area, and dimensions per level",
  },
  {
    icon: Box,
    title: "3D Massing Models",
    desc: "Perspective and plan views with dimensions for each scenario",
  },
  {
    icon: Home,
    title: "Unit Mix Analysis",
    desc: "Dwelling unit counts, bedroom configurations, and density calculations",
  },
  {
    icon: Car,
    title: "Parking Requirements",
    desc: "Required spaces, waiver eligibility, and City of Yes parking reform",
  },
  {
    icon: TrendingUp,
    title: "City of Yes Bonuses",
    desc: "UAP bonus FAR, transit-oriented development, and recent zoning changes",
  },
  {
    icon: FileText,
    title: "Professional PDF Report",
    desc: "Downloadable report with maps, diagrams, tables, and full analysis",
  },
  {
    icon: Users,
    title: "Inclusionary Housing",
    desc: "Affordable housing bonus FAR and MIH requirements when applicable",
  },
];

export default function LandingPage() {
  const [address, setAddress] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<PreviewData | null>(null);

  async function handleAnalyze(e: React.FormEvent) {
    e.preventDefault();
    if (!address.trim()) return;

    setLoading(true);
    setError("");
    setPreview(null);

    try {
      const res = await fetch(`${API_URL}/api/v1/saas/reports/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ address: address.trim() }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Analysis failed. Please try again.");
      }

      const data: PreviewData = await res.json();
      setPreview(data);

      // Scroll to results
      setTimeout(() => {
        document.getElementById("results")?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  function handleGetReport() {
    if (!preview) return;
    // Store preview in localStorage for checkout page to resume
    localStorage.setItem("massing_preview", JSON.stringify(preview));
    // Redirect to sign-up which will redirect to checkout after auth
    window.location.href = "/sign-up?redirect_url=/checkout";
  }

  const maxHeight = preview
    ? Math.max(...preview.scenarios.map((s) => s.max_height_ft))
    : 0;
  const maxUnits = preview
    ? Math.max(...preview.scenarios.map((s) => s.total_units))
    : 0;

  return (
    <div className="min-h-screen bg-white">
      {/* Nav */}
      <nav className="border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-sm font-bold"
              style={{ backgroundColor: BRAND_NAVY }}
            >
              MR
            </div>
            <span className="font-semibold text-gray-900">Massing Report</span>
          </div>
          <div className="flex items-center gap-4">
            <Link
              href="/sign-in"
              className="text-sm text-gray-600 hover:text-gray-900"
            >
              Sign In
            </Link>
            <Link
              href="/sign-up"
              className="text-sm px-4 py-2 rounded-lg text-white font-medium"
              style={{ backgroundColor: BRAND_GOLD }}
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-6 pt-20 pb-12 text-center">
        <h1 className="text-5xl font-bold text-gray-900 leading-tight">
          In-Depth Zoning Analysis
          <br />& Due Diligence
          <br />
          <span style={{ color: BRAND_GOLD }}>
            In Seconds. At a Fraction of the Cost.
          </span>
        </h1>
        <p className="mt-6 text-xl text-gray-600 max-w-2xl mx-auto">
          Instant zoning analysis and massing report for any property in NYC.
          Get development scenarios, 3D massing models, and a professional PDF
          report in seconds.
        </p>

        {/* Inline Address Search */}
        <form onSubmit={handleAnalyze} className="mt-10 max-w-2xl mx-auto">
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="Enter any NYC address or BBL..."
                className="w-full pl-12 pr-4 py-4 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#D4A843] focus:border-transparent text-lg"
              />
            </div>
            <button
              type="submit"
              disabled={loading || !address.trim()}
              className="px-8 py-4 rounded-lg text-white font-semibold text-lg shadow-lg hover:shadow-xl transition whitespace-nowrap disabled:opacity-50"
              style={{ backgroundColor: BRAND_GOLD }}
            >
              {loading ? "Analyzing..." : "Select Property"}
            </button>
          </div>
          {error && (
            <p className="mt-3 text-red-600 text-sm">{error}</p>
          )}
        </form>

        {/* Loading State */}
        {loading && (
          <div className="mt-8 py-12">
            <div className="animate-spin w-8 h-8 border-4 border-gray-200 border-t-[#D4A843] rounded-full mx-auto mb-4" />
            <p className="text-gray-500">
              Running zoning analysis... This takes a few seconds.
            </p>
          </div>
        )}
      </section>

      {/* Analysis Results (shown after search) */}
      {preview && !loading && (
        <section id="results" className="bg-gray-50 border-y border-gray-200 py-12">
          <div className="max-w-5xl mx-auto px-6 space-y-6">
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
                  <p className="font-medium text-gray-900 text-sm">{preview.address}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wide">BBL</p>
                  <p className="font-medium text-gray-900 text-sm">{preview.bbl}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Zoning</p>
                  <p className="font-medium text-gray-900 text-sm">
                    {preview.zoning_districts?.join(", ") || "\u2014"}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Lot Area</p>
                  <p className="font-medium text-gray-900 text-sm">
                    {preview.lot_area?.toLocaleString()} SF
                  </p>
                </div>
              </div>
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-white rounded-lg border border-gray-200 p-5 text-center">
                <p className="text-sm text-gray-500">Max Buildable SF</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {preview.buildable_sf.toLocaleString()}
                </p>
              </div>
              <div className="bg-white rounded-lg border border-gray-200 p-5 text-center">
                <p className="text-sm text-gray-500">Max Height</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{maxHeight} ft</p>
              </div>
              <div className="bg-white rounded-lg border border-gray-200 p-5 text-center">
                <p className="text-sm text-gray-500">Max Units</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{maxUnits}</p>
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
                        <td className="py-2.5 text-gray-900 font-medium">{s.name}</td>
                        <td className="py-2.5 text-right text-gray-700">
                          {s.total_zfa?.toLocaleString()}
                        </td>
                        <td className="py-2.5 text-right text-gray-700">
                          {s.max_height_ft}&apos;
                        </td>
                        <td className="py-2.5 text-right text-gray-700">{s.num_floors}</td>
                        <td className="py-2.5 text-right text-gray-700">{s.total_units}</td>
                        <td className="py-2.5 text-right text-gray-700">
                          {s.far_used?.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Price + CTA */}
            <div className="rounded-lg p-6 text-white" style={{ backgroundColor: BRAND_NAVY }}>
              <div className="flex items-center justify-between flex-wrap gap-4">
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
                            {b.rate.toFixed(2)}/SF = ${b.subtotal.toLocaleString()}
                          </p>
                        )
                      )}
                      <p className="mt-1 text-white/50">
                        Effective rate: ${preview.pricing.effective_rate.toFixed(4)}/SF
                      </p>
                    </div>
                  )}
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-3xl font-bold">
                    $
                    {(preview.pricing?.price_cents / 100).toLocaleString(
                      undefined,
                      { minimumFractionDigits: 2 }
                    )}
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
            </div>
          </div>
        </section>
      )}

      {/* Value Props Banner */}
      {!preview && (
        <section className="border-y border-gray-100 bg-gray-50/50">
          <div className="max-w-5xl mx-auto px-6 py-8">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-center">
              <div className="flex flex-col items-center gap-2">
                <Clock className="w-6 h-6" style={{ color: BRAND_GOLD }} />
                <span className="font-semibold text-gray-900">
                  Reports in Under 5 Minutes
                </span>
                <span className="text-sm text-gray-500">
                  What used to take days now takes seconds
                </span>
              </div>
              <div className="flex flex-col items-center gap-2">
                <DollarSign className="w-6 h-6" style={{ color: BRAND_GOLD }} />
                <span className="font-semibold text-gray-900">
                  Fraction of Traditional Cost
                </span>
                <span className="text-sm text-gray-500">
                  Save thousands on every deal evaluation
                </span>
              </div>
              <div className="flex flex-col items-center gap-2">
                <Building2 className="w-6 h-6" style={{ color: BRAND_GOLD }} />
                <span className="font-semibold text-gray-900">
                  Every NYC Property Covered
                </span>
                <span className="text-sm text-gray-500">
                  All five boroughs, every zoning district
                </span>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* How It Works */}
      <section className="py-20">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-4">
            How It Works
          </h2>
          <p className="text-center text-gray-500 mb-12">
            Two steps. No learning curve. No waiting around.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-10 max-w-4xl mx-auto">
            <div className="bg-white rounded-xl p-10 shadow-sm border border-gray-100 text-center">
              <div
                className="w-14 h-14 rounded-full flex items-center justify-center text-white text-2xl font-bold mx-auto mb-5"
                style={{ backgroundColor: BRAND_GOLD }}
              >
                1
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">
                Select Property
              </h3>
              <p className="text-gray-600 leading-relaxed">
                Enter any NYC address or BBL number. Select one or multiple
                properties to analyze together.
              </p>
            </div>
            <div className="bg-white rounded-xl p-10 shadow-sm border border-gray-100 text-center">
              <div
                className="w-14 h-14 rounded-full flex items-center justify-center text-white text-2xl font-bold mx-auto mb-5"
                style={{ backgroundColor: BRAND_GOLD }}
              >
                2
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">
                Receive Your Report
              </h3>
              <p className="text-gray-600 leading-relaxed">
                Your report will be ready within 5 minutes. See FAR, lot
                coverage, height limits, and multiple development scenarios
                instantly. Get a professional PDF with 3D massing models, zoning
                maps, and detailed calculations.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* What You Get */}
      <section className="bg-gray-50 py-20">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-4">
            What You Get
          </h2>
          <p className="text-center text-gray-500 mb-12">
            Everything you need to evaluate a deal &mdash; in one report.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {FEATURES.map((f) => {
              const Icon = f.icon;
              return (
                <div
                  key={f.title}
                  className="bg-white border border-gray-200 rounded-lg p-5 hover:shadow-md transition group"
                >
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center mb-3 group-hover:scale-110 transition-transform"
                    style={{ backgroundColor: `${BRAND_NAVY}10` }}
                  >
                    <Icon className="w-5 h-5" style={{ color: BRAND_NAVY }} />
                  </div>
                  <h3 className="font-semibold text-gray-900 mb-1 text-sm">
                    {f.title}
                  </h3>
                  <p className="text-xs text-gray-500 leading-relaxed">{f.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Sample Report */}
      <section className="py-16 border-b border-gray-100">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">
            See a Sample Report
          </h2>
          <p className="text-gray-600 mb-8 max-w-2xl mx-auto">
            Download a complete zoning feasibility report to see exactly what
            you get &mdash; zoning maps, 3D massing models, development scenarios,
            floor-by-floor breakdowns, and more.
          </p>
          <a
            href="/sample-report.pdf"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-8 py-4 rounded-lg text-white font-semibold text-lg shadow-lg hover:shadow-xl transition"
            style={{ backgroundColor: BRAND_NAVY }}
          >
            <Download className="w-5 h-5" />
            Download Sample Report
          </a>
        </div>
      </section>

      {/* Built for... */}
      <section className="py-20">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
            Built for NYC Real Estate Professionals
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                icon: Building2,
                title: "Developers",
                desc: "Screen sites faster. Know what you can build before you spend on architects and attorneys.",
              },
              {
                icon: Shield,
                title: "Brokers & Advisors",
                desc: "Add real value to every pitch. Share professional zoning reports with clients instantly.",
              },
              {
                icon: Zap,
                title: "Investors & Lenders",
                desc: "Due diligence in minutes, not weeks. Evaluate more deals with less overhead.",
              },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.title} className="text-center">
                  <div
                    className="w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-4"
                    style={{ backgroundColor: `${BRAND_NAVY}12` }}
                  >
                    <Icon className="w-7 h-7" style={{ color: BRAND_NAVY }} />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    {item.title}
                  </h3>
                  <p className="text-gray-600">{item.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="bg-gray-50 py-20">
        <div className="max-w-4xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-4">
            Pricing
          </h2>
          <p className="text-center text-gray-600 mb-12">
            Pay per report or save with an annual license.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* A La Carte */}
            <div className="bg-white rounded-xl p-8 shadow-sm border border-gray-200">
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Pay Per Report
              </h3>
              <div className="mb-4">
                <span className="text-4xl font-bold text-gray-900">$0.05</span>
                <span className="text-gray-500 ml-1">/ buildable SF</span>
              </div>
              <p className="text-sm text-gray-600 mb-6">
                Volume discounts: $0.04/SF over 5K SF, $0.03/SF over 10K SF,
                $0.02/SF over 25K SF. Capped at $2,500 per report.
              </p>
              <ul className="space-y-2 text-sm text-gray-700 mb-8">
                <li className="flex items-center gap-2">
                  <CheckCircle2
                    className="w-4 h-4 flex-shrink-0"
                    style={{ color: BRAND_GOLD }}
                  />
                  Full zoning feasibility report
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2
                    className="w-4 h-4 flex-shrink-0"
                    style={{ color: BRAND_GOLD }}
                  />
                  All development scenarios
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2
                    className="w-4 h-4 flex-shrink-0"
                    style={{ color: BRAND_GOLD }}
                  />
                  3D massing models
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2
                    className="w-4 h-4 flex-shrink-0"
                    style={{ color: BRAND_GOLD }}
                  />
                  Professional PDF download
                </li>
              </ul>
              <Link
                href="/sign-up"
                className="block text-center px-6 py-3 rounded-lg border-2 font-semibold transition"
                style={{ borderColor: BRAND_GOLD, color: BRAND_GOLD }}
              >
                Get Started
              </Link>
            </div>

            {/* Annual */}
            <div
              className="rounded-xl p-8 shadow-lg text-white relative"
              style={{ backgroundColor: BRAND_NAVY }}
            >
              <div
                className="absolute -top-3 right-6 px-3 py-1 rounded-full text-xs font-bold text-white"
                style={{ backgroundColor: BRAND_GOLD }}
              >
                BEST VALUE
              </div>
              <h3 className="text-xl font-semibold mb-2">Annual License</h3>
              <div className="mb-4">
                <span className="text-4xl font-bold">$10,000</span>
                <span className="text-white/70 ml-1">/ seat / year</span>
              </div>
              <p className="text-sm text-white/80 mb-6">
                Unlimited reports for your entire team. Perfect for active
                developers and brokers.
              </p>
              <ul className="space-y-2 text-sm text-white/90 mb-8">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 flex-shrink-0 text-white/80" />
                  Unlimited zoning reports
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 flex-shrink-0 text-white/80" />
                  Priority support
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 flex-shrink-0 text-white/80" />
                  Team seat management
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 flex-shrink-0 text-white/80" />
                  API access (coming soon)
                </li>
              </ul>
              <Link
                href="/sign-up"
                className="block text-center px-6 py-3 rounded-lg font-semibold transition hover:opacity-90"
                style={{ backgroundColor: BRAND_GOLD }}
              >
                Start Free Trial
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-100 py-8">
        <div className="max-w-6xl mx-auto px-6 text-center text-sm text-gray-500">
          &copy; {new Date().getFullYear()} Massing Report by West Egg
          Development. All rights reserved.
        </div>
      </footer>
    </div>
  );
}
