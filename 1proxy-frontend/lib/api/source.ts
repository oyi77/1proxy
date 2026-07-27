/** Source-related API calls. */
import { API_BASE, apiFetch, extractApiError, type AdminSourceCreateRequest, type AdminSourcesResponse, type AdminSourceUpdateRequest, type Source, type SourceCreateRequest, type SourceCreateResponse, type UserStats } from "./client";

// ── Interfaces ──

export interface SourcesResponse {
  total: number;
  enabled: number;
  sources: Source[];
}

// ── API Methods ──

export const sourceApi = {
  async getSources(): Promise<SourcesResponse> {
    const res = await apiFetch(`${API_BASE}/api/v1/sources`);
    if (!res.ok) throw new Error("Failed to fetch sources");
    return res.json();
  },

  async getMySources(): Promise<Source[]> {
    const res = await apiFetch(`${API_BASE}/api/v1/my-sources`);
    if (!res.ok) throw new Error(await extractApiError(res, "Failed to fetch your sources"));
    return res.json();
  },

  async getMyStats(): Promise<UserStats> {
    const res = await apiFetch(`${API_BASE}/api/v1/my-stats`);
    if (!res.ok) throw new Error(await extractApiError(res, "Failed to fetch your stats"));
    return res.json();
  },

  async createMySource(data: SourceCreateRequest): Promise<SourceCreateResponse> {
    const res = await apiFetch(`${API_BASE}/api/v1/my-sources`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await extractApiError(res, "Failed to add source"));
    return res.json();
  },

  async deleteMySource(id: number): Promise<void> {
    const res = await apiFetch(`${API_BASE}/api/v1/my-sources/${id}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error(await extractApiError(res, "Failed to delete source"));
  },

  // ── Admin Sources (DB-driven) ──

  async getAdminSources(params?: {
    limit?: number;
    offset?: number;
  }): Promise<AdminSourcesResponse> {
    const query = new URLSearchParams();
    if (params?.limit) query.set("limit", params.limit.toString());
    if (params?.offset) query.set("offset", params.offset.toString());
    const res = await apiFetch(`${API_BASE}/api/v1/admin/sources?${query}`);
    if (!res.ok) throw new Error("Failed to fetch admin sources");
    return res.json();
  },

  async createAdminSource(
    data: AdminSourceCreateRequest
  ): Promise<{ message: string; source_id: number; url: string; type: string; name: string }> {
    const res = await apiFetch(`${API_BASE}/api/v1/admin/sources`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await extractApiError(res, "Failed to create admin source"));
    return res.json();
  },

  async updateAdminSource(
    sourceId: number,
    data: AdminSourceUpdateRequest
  ): Promise<{ message: string }> {
    const res = await apiFetch(`${API_BASE}/api/v1/admin/sources/${sourceId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await extractApiError(res, "Failed to update admin source"));
    return res.json();
  },

  async deleteAdminSource(sourceId: number): Promise<{ message: string }> {
    const res = await apiFetch(`${API_BASE}/api/v1/admin/sources/${sourceId}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error(await extractApiError(res, "Failed to delete admin source"));
    return res.json();
  },

  async seedAdminSources(): Promise<{ message: string; count: number }> {
    const res = await apiFetch(`${API_BASE}/api/v1/admin/seed-sources`, {
      method: "POST",
    });
    if (!res.ok) throw new Error(await extractApiError(res, "Failed to seed admin sources"));
    return res.json();
  },
};
