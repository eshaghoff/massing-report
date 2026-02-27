"use client";

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
  Compass,
  ClipboardList,
  AlertCircle,
} from "lucide-react";

const BRAND_GOLD = "#D4A843";
const BRAND_NAVY = "#2C5F7C";
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8321";


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
    icon: ClipboardList,
    title: "Analyst's Manifest",
    desc: "Per-scenario digest for pro formas: unit count, gross/net SF, loss factor, avg unit size, commercial area, and parking",
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

  return (
    <div className="min-h-screen bg-white">
      {/* Nav */}
      <nav className="bg-white shadow-sm sticky top-0 z-50">
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
              href="/start"
              className="text-sm px-4 py-2 rounded-lg text-white font-medium"
              style={{ backgroundColor: BRAND_GOLD }}
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section
        className="px-6 pt-20 pb-16 text-center"
        style={{ background: "linear-gradient(135deg, #2C5F7C, #1E4A5F)" }}
      >
        <div className="max-w-4xl mx-auto">
          <h1 className="text-5xl font-bold text-white leading-tight font-heading">
            In-Depth Zoning Analysis
            <br />& Due Diligence
            <br />
            <span style={{ color: BRAND_GOLD }}>
              In Seconds. At a Fraction of the Cost.
            </span>
          </h1>
          <p className="mt-6 text-xl text-white/80 max-w-2xl mx-auto">
            Instant zoning analysis and massing report for any property in New York City.
            Get development scenarios, 3D massing models, and a professional PDF
            report in seconds.
          </p>

          {/* Get Started CTA */}
          <div className="mt-10">
            <Link
              href="/start"
              className="inline-flex items-center gap-3 px-12 py-5 rounded-lg text-white font-semibold text-xl shadow-lg hover:shadow-xl hover:opacity-90 transition"
              style={{ backgroundColor: BRAND_GOLD }}
            >
              Get Started
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </Link>
            <p className="mt-4 text-white/60 text-sm">
              No account required to preview your analysis
            </p>
          </div>
        </div>
      </section>

      {/* Value Props Banner */}
      <section className="bg-white border-b-2" style={{ borderColor: `${BRAND_GOLD}30` }}>
          <div className="max-w-5xl mx-auto px-6 py-10">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
              <div className="flex flex-col items-center gap-2">
                <div className="w-12 h-12 rounded-full flex items-center justify-center" style={{ backgroundColor: `${BRAND_GOLD}15` }}>
                  <Clock className="w-6 h-6" style={{ color: BRAND_GOLD }} />
                </div>
                <span className="font-semibold text-gray-900">
                  Reports in Under 5 Minutes
                </span>
                <span className="text-sm text-gray-500">
                  What used to take days now takes seconds
                </span>
              </div>
              <div className="flex flex-col items-center gap-2">
                <div className="w-12 h-12 rounded-full flex items-center justify-center" style={{ backgroundColor: `${BRAND_GOLD}15` }}>
                  <DollarSign className="w-6 h-6" style={{ color: BRAND_GOLD }} />
                </div>
                <span className="font-semibold text-gray-900">
                  Fraction of Traditional Cost
                </span>
                <span className="text-sm text-gray-500">
                  Save thousands on every deal evaluation
                </span>
              </div>
              <div className="flex flex-col items-center gap-2">
                <div className="w-12 h-12 rounded-full flex items-center justify-center" style={{ backgroundColor: `${BRAND_GOLD}15` }}>
                  <Building2 className="w-6 h-6" style={{ color: BRAND_GOLD }} />
                </div>
                <span className="font-semibold text-gray-900">
                  Every New York City Property Covered
                </span>
                <span className="text-sm text-gray-500">
                  All five boroughs, every zoning district
                </span>
              </div>
            </div>
          </div>
        </section>

      {/* How It Works */}
      <section className="py-20 bg-white">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-4 font-heading">
            How It Works
          </h2>
          <p className="text-center text-gray-500 mb-12">
            Just two steps.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-10 max-w-4xl mx-auto">
            <div className="bg-white rounded-xl p-10 shadow-sm border border-gray-100 text-center" style={{ borderTop: `3px solid ${BRAND_GOLD}` }}>
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
                Enter any New York City address or BBL number. Select one or multiple
                properties to analyze together.
              </p>
            </div>
            <div className="bg-white rounded-xl p-10 shadow-sm border border-gray-100 text-center" style={{ borderTop: `3px solid ${BRAND_GOLD}` }}>
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
      <section className="py-20" style={{ backgroundColor: "#F8F6F1" }}>
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-4 font-heading">
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
                  className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-lg hover:-translate-y-1 transition-all duration-200 group"
                >
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center mb-3 group-hover:scale-110 transition-transform"
                    style={{ backgroundColor: `${BRAND_NAVY}10` }}
                  >
                    <Icon className="w-6 h-6" style={{ color: BRAND_NAVY }} />
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
      <section
        className="py-16"
        style={{ background: "linear-gradient(135deg, #2C5F7C, #1E4A5F)" }}
      >
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold text-white mb-4 font-heading">
            See a Sample Report
          </h2>
          <p className="text-white/70 mb-8 max-w-2xl mx-auto">
            Download a complete zoning feasibility report to see exactly what
            you get &mdash; zoning maps, 3D massing models, development scenarios,
            floor-by-floor breakdowns, and more.
          </p>
          <a
            href="/sample-report.pdf"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-8 py-4 rounded-lg bg-white font-semibold text-lg shadow-lg hover:shadow-xl transition"
            style={{ color: BRAND_NAVY }}
          >
            <Download className="w-5 h-5" />
            Download Sample Report
          </a>
        </div>
      </section>

      {/* Built for... */}
      <section className="py-20 bg-white">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12 font-heading">
            Built for New York City Real Estate Professionals
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
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
              {
                icon: Compass,
                title: "Architects & Design Professionals",
                desc: "Fast-track your design process with instant zoning constraints and massing envelopes for any site.",
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
      <section id="pricing" className="py-20" style={{ backgroundColor: "#F8F6F1" }}>
        <div className="max-w-4xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-4 font-heading">
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
      <footer className="py-10" style={{ backgroundColor: "#1a2a3a" }}>
        <div className="max-w-6xl mx-auto px-6 text-center text-sm text-gray-400">
          &copy; {new Date().getFullYear()} Massing Report by West Egg
          Development. All rights reserved.
        </div>
      </footer>
    </div>
  );
}
