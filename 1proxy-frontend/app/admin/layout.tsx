import { ThemeProvider } from "../theme-provider";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <ThemeProvider>{children}</ThemeProvider>;
}
