"use client";

export const dynamic = "force-dynamic";
import Link from "next/link";
import { usePathname } from "next/navigation";

const CLERK_KEY = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || "";
const isClerkConfigured = CLERK_KEY && !CLERK_KEY.includes("PLACEHOLDER");

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: "📊" },
  { href: "/dashboard/new-report", label: "New Report", icon: "➕" },
  { href: "/dashboard/billing", label: "Billing", icon: "💳" },
  { href: "/dashboard/settings", label: "Settings", icon: "⚙️" },
];

function UserButtonWrapper() {
  if (!isClerkConfigured) {
    return (
      <div className="flex items-center gap-2 px-3 py-2">
        <div className="w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center text-xs font-bold text-gray-600">
          DU
        </div>
        <span className="text-sm text-gray-600">Dev User</span>
      </div>
    );
  }

  // Dynamic import to avoid Clerk errors when not configured
  const { UserButton } = require("@clerk/nextjs");
  return <UserButton afterSignOutUrl="/" />;
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen flex bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-6 border-b border-gray-100">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold bg-[#D4A843]">
              WE
            </div>
            <span className="font-semibold text-gray-900 text-sm">
              West Egg Dev
            </span>
          </Link>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {NAV_ITEMS.map((item) => {
            const isActive =
              item.href === "/dashboard"
                ? pathname === "/dashboard"
                : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition ${
                  isActive
                    ? "bg-[#D4A843]/10 text-[#D4A843] font-medium"
                    : "text-gray-700 hover:bg-gray-100"
                }`}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="p-4 border-t border-gray-100">
          <UserButtonWrapper />
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="max-w-5xl mx-auto p-8">{children}</div>
      </main>
    </div>
  );
}
