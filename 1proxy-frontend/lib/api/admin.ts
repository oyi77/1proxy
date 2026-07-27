/** Admin / validation / proxy source management API calls. */
import { API_BASE, apiFetch, extractApiError, type Stats, type User } from "./client";

// ── Interfaces ──

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

export interface ProxySourceManagement {
  sources: Array<Record<string, unknown>>;
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

// ── API Methods ──

export const adminApi = {
  async getStats(): Promise<Stats> {
    const res = await apiFetch(`${API_BASE}/api/v1/stats`);
    if (!res.ok) throw new Error("Failed to fetch stats");
    return res.json();
  },

  async getAdminUsers(params?: { limit?: number; offset?: number }): Promise<UsersResponse> {
    const query = new URLSearchParams();
    if (params?.limit) query.set("limit", params.limit.toString());
    if (params?.offset) query.set("offset", params.offset.toString());
    const res = await apiFetch(`${API_BASE}/api/v1/admin/users?${query}`);
    if (!res.ok) throw new Error("Failed to fetch admin users");
    return res.json();
  },

  async triggerValidation(sourceId: number): Promise<{ message: string }> {
    const res = await apiFetch(`${API_BASE}/api/v1/validation/trigger`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source_id: sourceId }),
    });
    if (!res.ok) throw new Error("Failed to trigger validation");
    return res.json();
  },

  async getAdminValidationStats(): Promise<ValidationStats> {
    const res = await apiFetch(`${API_BASE}/api/v1/admin/validation-stats`);
    if (!res.ok) throw new Error("Failed to fetch validation stats");
    return res.json();
  },

  async getAdminQualityDistribution(): Promise<QualityDistribution> {
    const res = await apiFetch(`${API_BASE}/api/v1/admin/quality-distribution`);
    if (!res.ok) throw new Error("Failed to fetch quality distribution");
    return res.json();
  },

  async getProxySourceManagement(): Promise<ProxySourceManagement> {
    const res = await apiFetch(`${API_BASE}/api/v1/admin/scraping/scraping/proxy-sources`);
    if (!res.ok) throw new Error("Failed to fetch proxy source management");
    return res.json();
  },

  async createProxySource(data: {
    url: string;
    name?: string;
    description?: string;
    type?: string;
  }): Promise<{ message: string; source_id: number }> {
    const res = await apiFetch(`${API_BASE}/api/v1/admin/scraping/scraping/proxy-sources`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
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
    const res = await apiFetch(
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
    const res = await apiFetch(
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
  ): Promise<{ message: string; validation_result: Record<string, unknown> }> {
    const res = await apiFetch(
      `${API_BASE}/api/v1/admin/scraping/scraping/proxy-sources/${sourceId}/validate`,
      {
        method: "POST",
      }
    );
    if (!res.ok) throw new Error("Failed to validate proxy source");
    return res.json();
  },

  async getHunterStats(): Promise<HunterStats> {
    const res = await apiFetch(`${API_BASE}/api/v1/admin/scraping/scraping/hunter`);
    if (!res.ok) throw new Error("Failed to fetch hunter stats");
    return res.json();
  },

  async triggerHunterDiscovery(): Promise<{ message: string; task_id: string }> {
    const res = await apiFetch(`${API_BASE}/api/v1/admin/scraping/scraping/hunter/trigger`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to trigger hunter discovery");
    return res.json();
  },

  async getQueueStatus(): Promise<QueueStatus> {
    const res = await apiFetch(`${API_BASE}/api/v1/admin/scraping/scraping/queue`);
    if (!res.ok) throw new Error("Failed to fetch queue status");
    return res.json();
  },

  async clearQueue(): Promise<{ message: string; cleared_count: number }> {
    const res = await apiFetch(`${API_BASE}/api/v1/admin/scraping/scraping/queue/clear`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to clear queue");
    return res.json();
  },
};
