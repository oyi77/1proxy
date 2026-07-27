/** Proxy-related API calls. */
import { API_BASE, apiFetch, type Proxy } from "./client";

export interface ProxiesResponse {
  total: number;
  count: number;
  offset: number;
  limit: number;
  proxies: Proxy[];
}

export interface ScrapeAllResult {
  url: string;
  status: "success" | "failed";
  scraped: number;
  added: number;
  error?: string;
}

export interface ScrapeAllResponse {
  message: string;
  total_scraped: number;
  total_added: number;
  total_stored: number;
  results: ScrapeAllResult[];
}

export const proxyApi = {
  async getProxies(params?: {
    protocol?: string;
    limit?: number;
    offset?: number;
    validation_status?: string;
  }): Promise<ProxiesResponse> {
    const query = new URLSearchParams();
    if (params?.protocol) query.set("protocol", params.protocol);
    if (params?.limit) query.set("limit", params.limit.toString());
    if (params?.offset) query.set("offset", params.offset.toString());
    if (params?.validation_status) query.set("validation_status", params.validation_status);
    const res = await apiFetch(`${API_BASE}/api/v1/proxies/advanced?${query}`);
    if (!res.ok) throw new Error("Failed to fetch proxies");
    return res.json();
  },

  async getRandomProxy(exclude?: string[]): Promise<import("./client").Proxy> {
    const query = new URLSearchParams();
    if (exclude && exclude.length > 0) query.set("exclude", exclude.join(","));
    const res = await apiFetch(`${API_BASE}/api/v1/proxies/random?${query}`);
    if (!res.ok) throw new Error("Failed to fetch random proxy");
    return res.json();
  },

  async deleteProxy(id: number): Promise<void> {
    const res = await apiFetch(`${API_BASE}/api/v1/proxies/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete proxy");
  },

  async scrapeDemo(): Promise<{ message: string; source: string; scraped: number; added: number; total_stored: number; sample: import("./client").Proxy[] }> {
    const res = await apiFetch(`${API_BASE}/api/v1/proxies/demo`);
    if (!res.ok) throw new Error("Failed to scrape demo");
    return res.json();
  },

  async scrapeAllSources(): Promise<ScrapeAllResponse> {
    const res = await apiFetch(`${API_BASE}/api/v1/proxies/scrape-all`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to scrape all sources");
    return res.json();
  },
};
