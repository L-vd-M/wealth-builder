import { ClerkProvider } from "@clerk/nextjs";
import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "../components/nav";

export const metadata: Metadata = {
  title: "MarketCommand",
  description: "Bloomberg-style analysis and trading workspace",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body>
          <main className="grid min-h-screen grid-cols-1 gap-4 p-4 lg:grid-cols-[240px_1fr]">
            <Nav />
            <section className="panel p-4">{children}</section>
          </main>
        </body>
      </html>
    </ClerkProvider>
  );
}
