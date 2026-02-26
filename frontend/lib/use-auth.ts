"use client";

const CLERK_KEY = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || "";
const isClerkConfigured = CLERK_KEY && !CLERK_KEY.includes("PLACEHOLDER");

/**
 * Wrapper around Clerk's useAuth that returns a no-op in dev mode.
 */
export function useAuthToken() {
  if (!isClerkConfigured) {
    return {
      getToken: async () => null as string | null,
      isSignedIn: true,
      isLoaded: true,
    };
  }

  // eslint-disable-next-line react-hooks/rules-of-hooks
  const { getToken, isSignedIn, isLoaded } = require("@clerk/nextjs").useAuth();
  return { getToken, isSignedIn, isLoaded };
}
