"use client";

import { SignIn, SignUp } from "@clerk/nextjs";
import { useState } from "react";
import Link from "next/link";

export const dynamic = "force-dynamic";

const BRAND_GOLD = "#D4A843";
const BRAND_NAVY = "#2C5F7C";

export default function SignInPage() {
  const [mode, setMode] = useState<"signin" | "signup">("signin");

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

      <div className="max-w-5xl mx-auto px-6 py-12">
        <div className="text-center mb-10">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Sign In to Save Your Reports
          </h1>
          <p className="text-gray-600">
            Sign in to access your account or create a new one to get started.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex justify-center mb-8">
          <div className="inline-flex bg-white rounded-lg border border-gray-200 p-1">
            <button
              onClick={() => setMode("signin")}
              className={`px-6 py-2.5 rounded-md text-sm font-medium transition ${
                mode === "signin"
                  ? "text-white shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              }`}
              style={mode === "signin" ? { backgroundColor: BRAND_NAVY } : {}}
            >
              Already have an account? Sign In
            </button>
            <button
              onClick={() => setMode("signup")}
              className={`px-6 py-2.5 rounded-md text-sm font-medium transition ${
                mode === "signup"
                  ? "text-white shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              }`}
              style={mode === "signup" ? { backgroundColor: BRAND_NAVY } : {}}
            >
              New here? Sign Up
            </button>
          </div>
        </div>

        {/* Auth Component */}
        <div className="flex justify-center">
          {mode === "signin" ? (
            <SignIn
              appearance={{
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
              }}
              forceRedirectUrl="/checkout"
            />
          ) : (
            <SignUp
              appearance={{
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
              }}
              forceRedirectUrl="/checkout"
            />
          )}
        </div>
      </div>
    </div>
  );
}
