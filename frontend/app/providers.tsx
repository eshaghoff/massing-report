"use client";

import { ClerkProvider } from "@clerk/nextjs";

const CLERK_KEY = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || "";
const isClerkConfigured = CLERK_KEY && !CLERK_KEY.includes("PLACEHOLDER");

export default function Providers({ children }: { children: React.ReactNode }) {
  if (!isClerkConfigured) {
    // Dev mode: skip Clerk
    return <>{children}</>;
  }

  return <ClerkProvider>{children}</ClerkProvider>;
}
