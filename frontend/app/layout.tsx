export const dynamic = "force-dynamic";
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Providers from "./providers";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Massing Report | NYC Zoning Feasibility Analysis",
  description:
    "Instant zoning feasibility analysis for any NYC property. Get development scenarios, 3D massing models, and professional PDF reports in seconds.",
  openGraph: {
    title: "Massing Report | Know What You Can Build Before You Buy",
    description:
      "Instant zoning feasibility analysis for any NYC property.",
    url: "https://massingreport.com",
    siteName: "Massing Report",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <Providers>
      <html lang="en">
        <body
          className={`${geistSans.variable} ${geistMono.variable} antialiased`}
        >
          {children}
        </body>
      </html>
    </Providers>
  );
}
