import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const CLERK_KEY = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || "";
const isClerkConfigured = CLERK_KEY && !CLERK_KEY.includes("PLACEHOLDER");

export default async function middleware(req: NextRequest) {
  if (!isClerkConfigured) {
    // Dev mode: allow all routes without auth
    return NextResponse.next();
  }

  // Production: use Clerk middleware
  const { clerkMiddleware, createRouteMatcher } = await import(
    "@clerk/nextjs/server"
  );
  const isProtectedRoute = createRouteMatcher(["/dashboard(.*)"]);
  const handler = clerkMiddleware(async (auth, request) => {
    if (isProtectedRoute(request)) {
      await auth.protect();
    }
  });
  return handler(req, {} as any);
}

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
