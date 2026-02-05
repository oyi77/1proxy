// The subdirectory where the app is deployed (GitHub Pages uses /1proxy).
// For local / Docker standalone runtime, this should be empty.
export const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "/1proxy";

// The production backend API URL (Railway)
export const API_URL = "https://helpful-alignment-production-2ae5.up.railway.app";

/**
 * Ensures a path is correctly prefixed with the BASE_PATH
 * Examples: 
 *   getFullUrl('/') -> '/1proxy/'
 *   getFullUrl('/login') -> '/1proxy/login'
 */
export const getFullUrl = (path: string) => {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  // Ensure we don't double slash if cleanPath is '/'
  if (cleanPath === "/") return `${BASE_PATH}/`;
  return `${BASE_PATH}${cleanPath}`;
};
