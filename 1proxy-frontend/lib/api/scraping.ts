/** Scraping configuration and session management API calls. */
import { API_BASE, apiFetch } from "./client";

// ── Interfaces ──

export interface ScrapingConfig {
  global_config: Record<string, unknown>;
  module_configs: Record<string, unknown>;
  active_sessions: Array<Record<string, unknown>>;
  rate_limiter_status: Record<string, unknown>;
  performance_stats: Record<string, unknown>;
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

export interface AdvancedScrapingConfig {
  enable_scheduler: boolean;
  schedule?: Record<string, unknown>;
  enable_proxy_testing: boolean;
  proxy_rotation_enabled: boolean;
  max_proxies_per_source?: number;
  test_urls?: string[];
}

// ── API Methods ──

export const scrapingApi = {
  async getScrapingConfig(): Promise<ScrapingConfig> {
    const res = await apiFetch(`${API_BASE}/api/v1/admin/scraping/scraping/config`);
    if (!res.ok) throw new Error("Failed to fetch scraping config");
    return res.json();
  },

  async updateScrapingConfig(
    moduleName: string,
    settings: Record<string, unknown>
  ): Promise<{ message: string; updated_config: Record<string, unknown> }> {
    const res = await apiFetch(
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
    const res = await apiFetch(
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
    const res = await apiFetch(
      `${API_BASE}/api/v1/admin/scraping/scraping/sessions/${sessionId}`
    );
    if (!res.ok) throw new Error("Failed to fetch scraping session");
    return res.json();
  },

  async stopScrapingSession(
    sessionId: string
  ): Promise<{ message: string; session: ScrapingSession }> {
    const res = await apiFetch(
      `${API_BASE}/api/v1/admin/scraping/scraping/sessions/${sessionId}/stop`,
      {
        method: "POST",
      }
    );
    if (!res.ok) throw new Error("Failed to stop scraping session");
    return res.json();
  },

  async getScrapingStats(): Promise<SessionStatsResponse> {
    const res = await apiFetch(
      `${API_BASE}/api/v1/admin/scraping/scraping/stats/overview`
    );
    if (!res.ok) throw new Error("Failed to fetch scraping stats");
    return res.json();
  },

  async getScrapingOperations(): Promise<{
    operations: string[];
    descriptions: Record<string, string>;
  }> {
    const res = await apiFetch(
      `${API_BASE}/api/v1/admin/scraping/scraping/operations`
    );
    if (!res.ok) throw new Error("Failed to fetch scraping operations");
    return res.json();
  },

  async executeScrapingOperation(
    operation: string
  ): Promise<{ message: string; result: unknown }> {
    const res = await apiFetch(
      `${API_BASE}/api/v1/admin/scraping/scraping/operations/${operation}`,
      {
        method: "POST",
      }
    );
    if (!res.ok) throw new Error("Failed to execute scraping operation");
    return res.json();
  },

  async getAdvancedConfig(): Promise<AdvancedScrapingConfig> {
    const res = await apiFetch(
      `${API_BASE}/api/v1/admin/scraping/scraping/advanced-config`
    );
    if (!res.ok) throw new Error("Failed to fetch advanced config");
    return res.json();
  },

  async updateAdvancedConfig(
    config: AdvancedScrapingConfig
  ): Promise<{ message: string; config: AdvancedScrapingConfig }> {
    const res = await apiFetch(
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
};
