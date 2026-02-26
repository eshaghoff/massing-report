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
} from "lucide-react";

const BRAND_GOLD = "#D4A843";
const BRAND_NAVY = "#2C5F7C";

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
      <section className="max-w-4xl mx-auto px-6 pt-24 pb-16 text-center">
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
        <div className="mt-10 flex justify-center gap-4">
          <Link
            href="/sign-up"
            className="px-8 py-3 rounded-lg text-white font-semibold text-lg shadow-lg hover:shadow-xl transition"
            style={{ backgroundColor: BRAND_GOLD }}
          >
            Select Property
          </Link>
          <Link
            href="#pricing"
            className="px-8 py-3 rounded-lg border-2 border-gray-300 text-gray-700 font-semibold text-lg hover:border-gray-400 transition"
          >
            View Pricing
          </Link>
        </div>
      </section>

      {/* Value Props Banner */}
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

      {/* How It Works — 2 Steps */}
      <section className="py-20">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-4">
            How It Works
          </h2>
          <p className="text-center text-gray-500 mb-12">
            Two steps. No learning curve. No waiting around.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-10 max-w-4xl mx-auto">
            {/* Step 1 */}
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

            {/* Step 2 */}
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

      {/* What You Get — 12 items */}
      <section className="bg-gray-50 py-20">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-4">
            What You Get
          </h2>
          <p className="text-center text-gray-500 mb-12">
            Everything you need to evaluate a deal — in one report.
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
                    <Icon
                      className="w-5 h-5"
                      style={{ color: BRAND_NAVY }}
                    />
                  </div>
                  <h3 className="font-semibold text-gray-900 mb-1 text-sm">
                    {f.title}
                  </h3>
                  <p className="text-xs text-gray-500 leading-relaxed">
                    {f.desc}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Who It's For */}
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
                    <Icon
                      className="w-7 h-7"
                      style={{ color: BRAND_NAVY }}
                    />
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
                Volume discounts: $0.04/SF above 20K SF, $0.03/SF above 50K SF.
                Minimum $50 per report.
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
