// The subdirectory where the app is deployed on GitHub Pages
export const BASE_PATH = "/1proxy";

// The production backend API URL (HuggingFace)
export const API_URL = "https://paijo77-1proxy.hf.space";

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
