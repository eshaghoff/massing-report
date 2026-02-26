const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8321";

export async function apiRequest(
  path: string,
  options: RequestInit & { token?: string | null } = {}
) {
  const { token, ...fetchOptions } = options;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${path}`, {
    ...fetchOptions,
    headers,
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `API error: ${res.status}`);
  }

  return res.json();
}

// Preview a property (returns summary + price, no PDF)
export async function previewReport(
  token: string | null,
  address: string
) {
  return apiRequest("/api/v1/saas/reports/preview", {
    method: "POST",
    token,
    body: JSON.stringify({ address }),
  });
}

// Generate a full report (returns report_id for polling)
export async function generateReport(
  token: string | null,
  data: { address?: string; bbl?: string; preview_id?: string }
) {
  return apiRequest("/api/v1/saas/reports/generate", {
    method: "POST",
    token,
    body: JSON.stringify(data),
  });
}

// Get user reports list
export async function getReports(token: string | null) {
  return apiRequest("/api/v1/saas/reports/", { token });
}

// Get single report (for polling status)
export async function getReport(token: string | null, reportId: string) {
  return apiRequest(`/api/v1/saas/reports/${reportId}`, { token });
}

// Get PDF download URL (direct link)
export function getReportPdfUrl(reportId: string) {
  return `${API_URL}/api/v1/saas/reports/${reportId}/pdf`;
}

// Get current user billing info
export async function getBillingInfo(token: string | null) {
  return apiRequest("/api/v1/saas/billing/me", { token });
}

// Create checkout session for a la carte purchase
export async function createCheckout(
  token: string | null,
  data: {
    report_preview_id: string;
    price_cents: number;
    bbl: string;
    address?: string;
    buildable_sf?: number;
  }
) {
  return apiRequest("/api/v1/saas/billing/checkout", {
    method: "POST",
    token,
    body: JSON.stringify(data),
  });
}

// Create subscription checkout
export async function createSubscription(token: string | null) {
  return apiRequest("/api/v1/saas/billing/subscribe", {
    method: "POST",
    token,
  });
}

// Get Stripe customer portal URL
export async function getPortalUrl(token: string | null) {
  return apiRequest("/api/v1/saas/billing/portal", {
    method: "POST",
    token,
  });
}
