"use client";

import { useAuth } from "@clerk/nextjs";
import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8321";

export default function BillingPage() {
  const { getToken } = useAuth();
  const [loading, setLoading] = useState(false);

  async function openPortal() {
    setLoading(true);
    try {
      const token = await getToken();
      const res = await fetch(`${API_URL}/api/v1/saas/billing/portal`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });
      const { portal_url } = await res.json();
      window.location.href = portal_url;
    } catch {
      alert("Failed to open billing portal");
    } finally {
      setLoading(false);
    }
  }

  async function handleSubscribe() {
    setLoading(true);
    try {
      const token = await getToken();
      const res = await fetch(`${API_URL}/api/v1/saas/billing/subscribe`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });
      const { checkout_url } = await res.json();
      window.location.href = checkout_url;
    } catch {
      alert("Failed to start subscription");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-8">Billing</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Current Plan */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="font-semibold text-gray-900 mb-4">Current Plan</h2>
          <p className="text-2xl font-bold text-gray-900 mb-1">
            Pay Per Report
          </p>
          <p className="text-sm text-gray-500 mb-6">
            $0.05 per buildable square foot, with volume discounts.
          </p>
          <button
            onClick={openPortal}
            disabled={loading}
            className="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 font-medium text-sm hover:bg-gray-50 disabled:opacity-50 transition"
          >
            Manage Payments
          </button>
        </div>

        {/* Upgrade */}
        <div className="bg-[#2C5F7C] rounded-lg p-6 text-white">
          <h2 className="font-semibold mb-4">Upgrade to Annual</h2>
          <p className="text-2xl font-bold mb-1">$10,000 / year</p>
          <p className="text-sm text-white/70 mb-6">
            Unlimited reports for one seat. Best for active developers.
          </p>
          <button
            onClick={handleSubscribe}
            disabled={loading}
            className="px-4 py-2 rounded-lg font-medium text-sm bg-[#D4A843] hover:opacity-90 disabled:opacity-50 transition"
          >
            {loading ? "Loading..." : "Upgrade Now"}
          </button>
        </div>
      </div>
    </div>
  );
}
