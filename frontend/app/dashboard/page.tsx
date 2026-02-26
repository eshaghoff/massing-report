"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuthToken } from "@/lib/use-auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8321";

interface Report {
  id: string;
  bbl: string;
  address: string;
  status: string;
  buildable_sf: number | null;
  price_cents: number | null;
  created_at: string;
  scenarios_count: number | null;
}

export default function DashboardPage() {
  const { getToken } = useAuthToken();
  const router = useRouter();
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchReports() {
      try {
        const token = await getToken();
        const res = await fetch(`${API_URL}/api/v1/saas/reports/`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (res.ok) {
          const data = await res.json();
          setReports(data.reports || []);
        }
      } catch (err) {
        console.error("Failed to fetch reports:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchReports();
  }, [getToken]);

  const totalReports = reports.filter((r) => r.status === "completed").length;
  const totalSpend = reports.reduce(
    (sum, r) => sum + (r.price_cents || 0),
    0
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <Link
          href="/dashboard/new-report"
          className="px-4 py-2 rounded-lg text-white font-medium text-sm bg-[#D4A843] hover:opacity-90 transition"
        >
          + New Report
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-white rounded-lg p-6 border border-gray-200">
          <p className="text-sm text-gray-500">Total Reports</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">
            {totalReports}
          </p>
        </div>
        <div className="bg-white rounded-lg p-6 border border-gray-200">
          <p className="text-sm text-gray-500">Total Spend</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">
            ${(totalSpend / 100).toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </p>
        </div>
        <div className="bg-white rounded-lg p-6 border border-gray-200">
          <p className="text-sm text-gray-500">Plan</p>
          <p className="text-xl font-bold text-gray-900 mt-1">
            Pay Per Report
          </p>
        </div>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
          <div className="animate-spin w-8 h-8 border-4 border-gray-200 border-t-[#D4A843] rounded-full mx-auto mb-4" />
          <p className="text-gray-500">Loading reports...</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && reports.length === 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
          <div className="text-4xl mb-4">🏗️</div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            No reports yet
          </h3>
          <p className="text-gray-500 mb-6">
            Analyze your first property to get started.
          </p>
          <Link
            href="/dashboard/new-report"
            className="inline-block px-6 py-3 rounded-lg text-white font-medium bg-[#D4A843] hover:opacity-90 transition"
          >
            Analyze a Property
          </Link>
        </div>
      )}

      {/* Reports list */}
      {!loading && reports.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b bg-gray-50">
                <th className="px-6 py-3 font-medium">Address</th>
                <th className="px-6 py-3 font-medium">BBL</th>
                <th className="px-6 py-3 font-medium text-right">
                  Buildable SF
                </th>
                <th className="px-6 py-3 font-medium text-right">Price</th>
                <th className="px-6 py-3 font-medium text-center">Status</th>
                <th className="px-6 py-3 font-medium">Date</th>
                <th className="px-6 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {reports.map((report) => (
                <tr
                  key={report.id}
                  className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
                  onClick={() =>
                    router.push(`/dashboard/reports/${report.id}`)
                  }
                >
                  <td className="px-6 py-4 font-medium text-gray-900">
                    {report.address || "—"}
                  </td>
                  <td className="px-6 py-4 text-gray-600 font-mono text-xs">
                    {report.bbl}
                  </td>
                  <td className="px-6 py-4 text-right text-gray-700">
                    {report.buildable_sf
                      ? report.buildable_sf.toLocaleString()
                      : "—"}
                  </td>
                  <td className="px-6 py-4 text-right text-gray-700">
                    {report.price_cents
                      ? `$${(report.price_cents / 100).toLocaleString(undefined, { minimumFractionDigits: 2 })}`
                      : "—"}
                  </td>
                  <td className="px-6 py-4 text-center">
                    <span
                      className={`inline-block px-2.5 py-1 rounded-full text-xs font-medium ${
                        report.status === "completed"
                          ? "bg-green-100 text-green-700"
                          : report.status === "processing"
                          ? "bg-yellow-100 text-yellow-700"
                          : report.status === "failed"
                          ? "bg-red-100 text-red-700"
                          : "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {report.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-gray-500 text-xs">
                    {new Date(report.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4">
                    {report.status === "completed" && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          window.open(
                            `${API_URL}/api/v1/saas/reports/${report.id}/pdf`,
                            "_blank"
                          );
                        }}
                        className="text-xs text-[#D4A843] hover:underline font-medium"
                      >
                        Download PDF
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
