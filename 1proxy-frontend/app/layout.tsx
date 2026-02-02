import type { Metadata } from "next";
import { AuthProvider } from "@/lib/auth-context";
import { ThemeProvider } from "@/app/theme-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "1proxy - Free Proxy Aggregation Platform",
  description: "Robust, Free, Fast Proxy Aggregation Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Force absolute favicon path to prevent redirection issues */}
        <link rel="icon" href="/1proxy/favicon.ico" sizes="any" />
      </head>
      <body className="antialiased" suppressHydrationWarning>
        <AuthProvider>
          <ThemeProvider>
            {children}
          </ThemeProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
