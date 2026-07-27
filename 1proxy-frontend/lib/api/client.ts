/** Shared API utilities and common types. */
import { API_URL } from "../constants";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || API_URL;

export const apiFetch = async (url: string, init: RequestInit = {}) => {
  return fetch(url, {
    ...init,
    credentials: 'include',
  });
};

export const extractApiError = async (res: Response, fallback: string) => {
  try {
    const data = (await res.json()) as { detail?: string | { error?: string; reason?: string } };
    if (typeof data.detail === "string") return data.detail;
    if (data.detail?.reason) return data.detail.reason;
    if (data.detail?.error) return data.detail.error;
  } catch {
    return fallback;
  }
  return fallback;
};

// ── Shared interfaces ──

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
  by_protocol: { http: number; vmess: number; vless: number; trojan: number; shadowsocks: number };
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

export type SourceType = "github_raw" | "subscription_base64" | "generic_text";

export interface User {
  id: number;
  email: string;
  username: string;
  avatar_url?: string;
  role: string;
  created_at: string;
}

export interface SourceCreateRequest {
  url: string;
  type: SourceType;
  name?: string;
  description?: string;
  is_paid: boolean;
}

export interface SourceCreateResponse {
  message: string;
  source_id: number;
  validation: { proxy_count: number; sample_proxies: string[] };
}

export interface UserStats {
  total_sources: number;
  active_sources: number;
  total_proxies_contributed: number;
  avg_success_rate: number;
}

export interface AdminSource {
  id: number;
  url: string;
  type: string;
  name?: string;
  description?: string;
  enabled: boolean;
  validated: boolean;
  total_scraped: number;
  success_rate: number;
  last_scraped: string | null;
  created_at: string | null;
  is_admin_source: boolean;
}

export interface AdminSourcesResponse {
  total: number;
  count: number;
  offset: number;
  limit: number;
  sources: AdminSource[];
}

export interface AdminSourceCreateRequest {
  url: string;
  type: string;
  name?: string;
  description?: string;
  enabled?: boolean;
}

export interface AdminSourceUpdateRequest {
  name?: string;
  description?: string;
  enabled?: boolean;
  url?: string;
  type?: string;
}
