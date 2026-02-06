// The subdirectory where the app is deployed.
// - GitHub Pages with static export: set NEXT_PUBLIC_BASE_PATH=/1proxy at build time
// - Docker standalone: defaults to empty (let Next.js basePath handle it)
// - GitHub Pages standalone: empty (basePath already configured in next.config.js)
export const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

// The production backend API URL (Railway)
export const API_URL = "https://helpful-alignment-production-2ae5.up.railway.app";

/**
 * Ensures a path is correctly prefixed with BASE_PATH for EXTERNAL URLs only.
 * For INTERNAL app navigation (Links), use the path directly - Next.js basePath handles prefixing.
 */
export const getFullUrl = (path: string) => {
  // For external/full URLs that need the BASE_PATH prefix (e.g., API calls to same origin)
  // But NOT for internal Link navigation which Next.js handles automatically
  if (path.startsWith("http") || path.startsWith("//")) {
    return path;
  }
  // For internal app routes, return as-is - Next.js basePath will prefix automatically
  return path.startsWith("/") ? path : `/${path}`;
};
