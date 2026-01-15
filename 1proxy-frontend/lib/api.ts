const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Proxy {
  id: number;
  url: string;
  protocol: string;
  ip?: string;
  port?: number;
  country_code?: string;
  country_name?: string;
  city?: string;
  latency_ms?: number;
  speed_mbps?: number;
  anonymity?: string;
  quality_score?: number;
  is_working: boolean;
  last_validated?: string;
  source?: string;
}

export interface Stats {
  total_proxies: number;
  by_protocol: {
    http: number;
    vmess: number;
    vless: number;
    trojan: number;
    shadowsocks: number;
  };
}

export interface ProxiesResponse {
  total: number;
  count: number;
  offset: number;
  limit: number;
  proxies: Proxy[];
}

export interface Source {
  id: number;
  url: string;
  type: string;
  name?: string;
  description?: string;
  is_paid: boolean;
  enabled: boolean;
  validated: boolean;
  validation_error?: string;
  total_scraped: number;
  success_rate: number;
  is_admin_source: boolean;
}

export interface SourcesResponse {
  total: number;
  enabled: number;
  sources: Source[];
}

export interface User {
  id: number;
  email: string;
  username: string;
  avatar_url?: string;
  role: string;
  created_at: string;
}

export interface UsersResponse {
  total: number;
  users: User[];
}

export interface ValidationStats {
  total_proxies: number;
  by_status: {
    [key: string]: {
      count: number;
      avg_quality: number | null;
      avg_latency: number | null;
    };
  };
  summary: {
    validated: number;
    pending: number;
    failed: number;
    validation_rate_percent: number;
  };
}

export interface QualityDistribution {
  excellent: number;
  good: number;
  fair: number;
  poor: number;
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

export const api = {
  async getStats(): Promise<Stats> {
    const res = await fetch(`${API_BASE}/api/v1/stats`);
    if (!res.ok) throw new Error("Failed to fetch stats");
    return res.json();
  },

  async getProxies(params?: {
    protocol?: string;
    limit?: number;
    offset?: number;
  }): Promise<ProxiesResponse> {
    const query = new URLSearchParams();
    if (params?.protocol) query.set("protocol", params.protocol);
    if (params?.limit) query.set("limit", params.limit.toString());
    if (params?.offset) query.set("offset", params.offset.toString());

    const res = await fetch(`${API_BASE}/api/v1/proxies?${query}`);
    if (!res.ok) throw new Error("Failed to fetch proxies");
    return res.json();
  },

  async getRandomProxy(exclude?: string[]): Promise<Proxy> {
    const query = new URLSearchParams();
    if (exclude && exclude.length > 0) query.set("exclude", exclude.join(","));
    const res = await fetch(`${API_BASE}/api/v1/proxies/random?${query}`);
    if (!res.ok) throw new Error("Failed to fetch random proxy");
    return res.json();
  },

  async deleteProxy(id: number): Promise<void> {
    const res = await fetch(`${API_BASE}/api/v1/proxies/${id}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Failed to delete proxy");
  },

  async scrapeDemo(): Promise<{
    message: string;
    source: string;
    scraped: number;
    added: number;
    total_stored: number;
    sample: Proxy[];
  }> {
    const res = await fetch(`${API_BASE}/api/v1/proxies/demo`);
    if (!res.ok) throw new Error("Failed to scrape demo");
    return res.json();
  },

  async getSources(): Promise<SourcesResponse> {
    const res = await fetch(`${API_BASE}/api/v1/sources`);
    if (!res.ok) throw new Error("Failed to fetch sources");
    return res.json();
  },

  async scrapeAllSources(): Promise<ScrapeAllResponse> {
    const res = await fetch(`${API_BASE}/api/v1/proxies/scrape-all`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to scrape all sources");
    return res.json();
  },

  async getAdminUsers(params?: { limit?: number; offset?: number }): Promise<UsersResponse> {
    const query = new URLSearchParams();
    if (params?.limit) query.set("limit", params.limit.toString());
    if (params?.offset) query.set("offset", params.offset.toString());
    const res = await fetch(`${API_BASE}/api/v1/admin/users?${query}`);
    if (!res.ok) throw new Error("Failed to fetch admin users");
    return res.json();
  },

  async triggerValidation(sourceId: number): Promise<{ message: string }> {
    const res = await fetch(`${API_BASE}/api/v1/validation/trigger`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source_id: sourceId }),
    });
    if (!res.ok) throw new Error("Failed to trigger validation");
    return res.json();
  },

  async getAdminValidationStats(): Promise<ValidationStats> {
    const res = await fetch(`${API_BASE}/api/v1/admin/validation-stats`);
    if (!res.ok) throw new Error("Failed to fetch validation stats");
    return res.json();
  },

  async getAdminQualityDistribution(): Promise<QualityDistribution> {
    const res = await fetch(`${API_BASE}/api/v1/admin/quality-distribution`);
    if (!res.ok) throw new Error("Failed to fetch quality distribution");
    return res.json();
  },
};

