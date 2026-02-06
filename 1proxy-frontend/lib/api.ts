import { API_URL } from "./constants";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || API_URL;

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
  validation_status?: string;
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

export interface ScrapingConfig {
  global_config: Record<string, any>;
  module_configs: Record<string, any>;
  active_sessions: Array<Record<string, any>>;
  rate_limiter_status: Record<string, any>;
  performance_stats: Record<string, any>;
}

export interface ScrapingSession {
  session_id: string;
  start_time: string;
  end_time: string | null;
  duration: number | null;
  requests_made: number;
  successful_requests: number;
  failed_requests: number;
  success_rate: number;
  total_data_bytes: number;
  avg_response_time: number;
  proxies_used: string[];
  proxies_tested: number;
}

export interface SessionStatsResponse {
  total_sessions: number;
  active_sessions: number;
  total_requests: number;
  successful_requests: number;
  avg_session_duration: number;
  total_data_bytes: number;
  success_rate: number;
}

export interface ProxySourceManagement {
  sources: Array<Record<string, any>>;
  total: number;
  pending_approval: number;
  auto_discovered: number;
}

export interface HunterStats {
  total_discovered: number;
  pending_validation: number;
  approved_sources: number;
  rejected_sources: number;
  discovery_rate: number;
  avg_confidence_score: number;
}

export interface QueueStatus {
  total_queued: number;
  processing: number;
  pending: number;
  failed: number;
  avg_wait_time: number;
}

export interface AdvancedScrapingConfig {
  enable_scheduler: boolean;
  schedule?: Record<string, any>;
  enable_proxy_testing: boolean;
  proxy_rotation_enabled: boolean;
  max_proxies_per_source?: number;
  test_urls?: string[];
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
    validation_status?: string;
  }): Promise<ProxiesResponse> {
    const query = new URLSearchParams();
    if (params?.protocol) query.set("protocol", params.protocol);
    if (params?.limit) query.set("limit", params.limit.toString());
    if (params?.offset) query.set("offset", params.offset.toString());
    if (params?.validation_status) query.set("validation_status", params.validation_status);

    const res = await fetch(`${API_BASE}/api/v1/proxies/advanced?${query}`);
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

  async getScrapingConfig(): Promise<ScrapingConfig> {
    const res = await fetch(`${API_BASE}/api/v1/admin/scraping/scraping/config`);
    if (!res.ok) throw new Error("Failed to fetch scraping config");
    return res.json();
  },

  async updateScrapingConfig(
    moduleName: string,
    settings: Record<string, any>
  ): Promise<{ message: string; updated_config: Record<string, any> }> {
    const res = await fetch(
      `${API_BASE}/api/v1/admin/scraping/scraping/config/${moduleName}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ module_name: moduleName, settings }),
      }
    );
    if (!res.ok) throw new Error("Failed to update scraping config");
    return res.json();
  },

  async startScrapingSession(params?: {
    module_name?: string;
    source_id?: number;
  }): Promise<{ session_id: string; message: string }> {
    const res = await fetch(
      `${API_BASE}/api/v1/admin/scraping/scraping/start-session`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params || {}),
      }
    );
    if (!res.ok) throw new Error("Failed to start scraping session");
    return res.json();
  },

  async getScrapingSession(sessionId: string): Promise<ScrapingSession> {
    const res = await fetch(
      `${API_BASE}/api/v1/admin/scraping/scraping/sessions/${sessionId}`
    );
    if (!res.ok) throw new Error("Failed to fetch scraping session");
    return res.json();
  },

  async stopScrapingSession(
    sessionId: string
  ): Promise<{ message: string; session: ScrapingSession }> {
    const res = await fetch(
      `${API_BASE}/api/v1/admin/scraping/scraping/sessions/${sessionId}/stop`,
      {
        method: "POST",
      }
    );
    if (!res.ok) throw new Error("Failed to stop scraping session");
    return res.json();
  },

  async getScrapingStats(): Promise<SessionStatsResponse> {
    const res = await fetch(
      `${API_BASE}/api/v1/admin/scraping/scraping/stats/overview`
    );
    if (!res.ok) throw new Error("Failed to fetch scraping stats");
    return res.json();
  },

  async getProxySourceManagement(): Promise<ProxySourceManagement> {
    const res = await fetch(
      `${API_BASE}/api/v1/admin/scraping/scraping/proxy-sources`
    );
    if (!res.ok) throw new Error("Failed to fetch proxy source management");
    return res.json();
  },

  async createProxySource(data: {
    url: string;
    name?: string;
    description?: string;
    type?: string;
  }): Promise<{ message: string; source_id: number }> {
    const res = await fetch(
      `${API_BASE}/api/v1/admin/scraping/scraping/proxy-sources`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }
    );
    if (!res.ok) throw new Error("Failed to create proxy source");
    return res.json();
  },

  async updateProxySource(
    sourceId: number,
    data: {
      url?: string;
      name?: string;
      description?: string;
      enabled?: boolean;
    }
  ): Promise<{ message: string }> {
    const res = await fetch(
      `${API_BASE}/api/v1/admin/scraping/scraping/proxy-sources/${sourceId}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }
    );
    if (!res.ok) throw new Error("Failed to update proxy source");
    return res.json();
  },

  async deleteProxySource(sourceId: number): Promise<{ message: string }> {
    const res = await fetch(
      `${API_BASE}/api/v1/admin/scraping/scraping/proxy-sources/${sourceId}`,
      {
        method: "DELETE",
      }
    );
    if (!res.ok) throw new Error("Failed to delete proxy source");
    return res.json();
  },

  async validateProxySource(
    sourceId: number
  ): Promise<{ message: string; validation_result: Record<string, any> }> {
    const res = await fetch(
      `${API_BASE}/api/v1/admin/scraping/scraping/proxy-sources/${sourceId}/validate`,
      {
        method: "POST",
      }
    );
    if (!res.ok) throw new Error("Failed to validate proxy source");
    return res.json();
  },

  async getHunterStats(): Promise<HunterStats> {
    const res = await fetch(
      `${API_BASE}/api/v1/admin/scraping/scraping/hunter`
    );
    if (!res.ok) throw new Error("Failed to fetch hunter stats");
    return res.json();
  },

  async triggerHunterDiscovery(): Promise<{ message: string; task_id: string }> {
    const res = await fetch(
      `${API_BASE}/api/v1/admin/scraping/scraping/hunter/trigger`,
      {
        method: "POST",
      }
    );
    if (!res.ok) throw new Error("Failed to trigger hunter discovery");
    return res.json();
  },

  async getQueueStatus(): Promise<QueueStatus> {
    const res = await fetch(
      `${API_BASE}/api/v1/admin/scraping/scraping/queue`
    );
    if (!res.ok) throw new Error("Failed to fetch queue status");
    return res.json();
  },

  async clearQueue(): Promise<{ message: string; cleared_count: number }> {
    const res = await fetch(
      `${API_BASE}/api/v1/admin/scraping/scraping/queue/clear`,
      {
        method: "POST",
      }
    );
    if (!res.ok) throw new Error("Failed to clear queue");
    return res.json();
  },

  async getAdvancedConfig(): Promise<AdvancedScrapingConfig> {
    const res = await fetch(
      `${API_BASE}/api/v1/admin/scraping/scraping/advanced-config`
    );
    if (!res.ok) throw new Error("Failed to fetch advanced config");
    return res.json();
  },

  async updateAdvancedConfig(
    config: AdvancedScrapingConfig
  ): Promise<{ message: string; config: AdvancedScrapingConfig }> {
    const res = await fetch(
      `${API_BASE}/api/v1/admin/scraping/scraping/advanced-config`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      }
    );
    if (!res.ok) throw new Error("Failed to update advanced config");
    return res.json();
  },

  async getScrapingOperations(): Promise<{
    operations: string[];
    descriptions: Record<string, string>;
  }> {
    const res = await fetch(
      `${API_BASE}/api/v1/admin/scraping/scraping/operations`
    );
    if (!res.ok) throw new Error("Failed to fetch scraping operations");
    return res.json();
  },

  async executeScrapingOperation(
    operation: string
  ): Promise<{ message: string; result: any }> {
    const res = await fetch(
      `${API_BASE}/api/v1/admin/scraping/scraping/operations/${operation}`,
      {
        method: "POST",
      }
    );
    if (!res.ok) throw new Error("Failed to execute scraping operation");
    return res.json();
  },
};

