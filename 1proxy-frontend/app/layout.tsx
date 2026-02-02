import type { Metadata } from "next";
import { AuthProvider } from "@/lib/auth-context";
import { ThemeProvider } from "@/app/theme-provider";
import "./globals.css";

const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || '/1proxy';

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
        {/* Manual Favicon Link to prevent Next.js metadata mangling */}
        <link rel="icon" href={`${BASE_PATH}/favicon.ico`} sizes="any" />
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
