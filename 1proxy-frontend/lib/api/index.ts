/**
 * API barrel — re-exports all types and composes the flat `api` object.
 *
 * Usage: import { api, type Proxy, type Stats, type Source, ... } from "@/lib/api"
 */

// Re-export all types from every domain module — this ensures
// every import that was using `from "@/lib/api"` keeps working.
export * from "./client";
export * from "./proxy";
export * from "./source";
export * from "./admin";
export * from "./scraping";

// Compose the flat `api` object (same shape as the original monolithic api.ts)
import { proxyApi } from "./proxy";
import { sourceApi } from "./source";
import { adminApi } from "./admin";
import { scrapingApi } from "./scraping";

export const api = {
  ...proxyApi,
  ...sourceApi,
  ...adminApi,
  ...scrapingApi,
};
