import Link from "next/link";

const BRAND_GOLD = "#D4A843";
const BRAND_NAVY = "#2C5F7C";

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
            <span className="font-semibold text-gray-900">
              Massing Report
            </span>
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
          Know What You Can Build
          <br />
          <span style={{ color: BRAND_GOLD }}>Before You Buy</span>
        </h1>
        <p className="mt-6 text-xl text-gray-600 max-w-2xl mx-auto">
          Instant zoning feasibility analysis for any NYC property. Get
          development scenarios, 3D massing models, and a professional PDF
          report in seconds.
        </p>
        <div className="mt-10 flex justify-center gap-4">
          <Link
            href="/sign-up"
            className="px-8 py-3 rounded-lg text-white font-semibold text-lg shadow-lg hover:shadow-xl transition"
            style={{ backgroundColor: BRAND_GOLD }}
          >
            Analyze a Property
          </Link>
          <Link
            href="#pricing"
            className="px-8 py-3 rounded-lg border-2 border-gray-300 text-gray-700 font-semibold text-lg hover:border-gray-400 transition"
          >
            View Pricing
          </Link>
        </div>
      </section>

      {/* How It Works */}
      <section className="bg-gray-50 py-20">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
            How It Works
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                step: "1",
                title: "Enter an Address",
                desc: "Type any NYC address or BBL number to start your analysis.",
              },
              {
                step: "2",
                title: "Review the Analysis",
                desc: "See FAR, lot coverage, height limits, and multiple development scenarios instantly.",
              },
              {
                step: "3",
                title: "Download Your Report",
                desc: "Get a professional PDF with 3D massing models, zoning maps, and detailed calculations.",
              },
            ].map((item) => (
              <div
                key={item.step}
                className="bg-white rounded-xl p-8 shadow-sm text-center"
              >
                <div
                  className="w-12 h-12 rounded-full flex items-center justify-center text-white text-xl font-bold mx-auto mb-4"
                  style={{ backgroundColor: BRAND_GOLD }}
                >
                  {item.step}
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {item.title}
                </h3>
                <p className="text-gray-600">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
            What You Get
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              { title: "Zoning Analysis", desc: "FAR, height, setbacks, lot coverage, yard requirements" },
              { title: "Development Scenarios", desc: "Max residential, max units, community facility, mixed-use, and more" },
              { title: "3D Massing Models", desc: "Perspective and plan views with dimensions for each scenario" },
              { title: "Building Programs", desc: "Floor-by-floor breakdown, core estimates, unit mixes" },
              { title: "Parking Analysis", desc: "Required spaces, waiver eligibility, layout options" },
              { title: "City of Yes", desc: "UAP bonus FAR, parking reform, and other recent zoning changes" },
            ].map((f) => (
              <div
                key={f.title}
                className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition"
              >
                <h3 className="font-semibold text-gray-900 mb-2">
                  {f.title}
                </h3>
                <p className="text-sm text-gray-600">{f.desc}</p>
              </div>
            ))}
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
                <li>&#10003; Full zoning feasibility report</li>
                <li>&#10003; All development scenarios</li>
                <li>&#10003; 3D massing models</li>
                <li>&#10003; Professional PDF download</li>
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
                <li>&#10003; Unlimited zoning reports</li>
                <li>&#10003; Priority support</li>
                <li>&#10003; Team seat management</li>
                <li>&#10003; API access (coming soon)</li>
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
