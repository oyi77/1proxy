// The subdirectory where the app is deployed.
// - GitHub Pages with static export: set NEXT_PUBLIC_BASE_PATH=/1proxy at build time
// - Docker standalone: defaults to empty (let Next.js basePath handle it)
// - GitHub Pages standalone: empty (basePath already configured in next.config.js)
export const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

// The production backend API URL (Railway)
export const API_URL = "https://helpful-alignment-production-2ae5.up.railway.app";

/**
 * Ensures a path is correctly prefixed with BASE_PATH.
 * Only prepends BASE_PATH if it's not already present.
 */
export const getFullUrl = (path: string) => {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  // Don't double-prefix if BASE_PATH is already in the path
  if (cleanPath.startsWith(BASE_PATH)) {
    return cleanPath;
  }
  if (cleanPath === "/") return BASE_PATH || "/";
  return `${BASE_PATH}${cleanPath}`;
};
