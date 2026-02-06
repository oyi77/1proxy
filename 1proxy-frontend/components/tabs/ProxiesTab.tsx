import { useState } from "react";
import Link from "next/link";
import { ProxyTable } from "@/components/ProxyTable";
import { type Proxy } from "@/lib/api";
import { getFullUrl } from "@/lib/constants";

interface ProxiesTabProps {
  proxies: Proxy[];
  loading: boolean;
  total: number;
  limit: number;
  currentPage: number;
  onPageChange: (page: number) => void;
  filter: string;
  onFilterChange: (filter: string) => void;
  statusFilter: string;
  onStatusFilterChange: (status: string) => void;
  theme: string;
}

export function ProxiesTab({
  proxies,
  loading,
  total,
  limit,
  currentPage,
  onPageChange,
  filter,
  onFilterChange,
  statusFilter,
  onStatusFilterChange,
  theme,
}: ProxiesTabProps) {
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
      {/* Status Filter Toggle */}
      <div
        className="retro-border rounded-lg p-6"
        style={{
          backgroundColor: theme === "dark" ? "var(--dark-card)" : "#FFFFFF",
          boxShadow: "4px 4px 0px #000000",
        }}
      >
        <label
          className="block text-xs font-bold mb-3 uppercase"
          style={{
            fontFamily: "'Press Start 2P', 'Courier New', monospace",
            color: theme === "dark" ? "var(--dark-text)" : "#6B7280",
          }}
        >
          Proxy Type
        </label>
        <div className="flex gap-2">
          <button
            onClick={() => onStatusFilterChange("validated")}
            className={`px-4 py-2 rounded-lg font-bold transition-all ${
              statusFilter === "validated"
                ? "ring-4 ring-offset-2"
                : "opacity-70 hover:opacity-100"
            }`}
            style={{
              backgroundColor:
                statusFilter === "validated"
                  ? "#4ade80"
                  : theme === "dark"
                  ? "var(--dark-bg)"
                  : "#F0F0F0",
              color: statusFilter === "validated" ? "#000000" : theme === "dark" ? "var(--dark-text)" : "#1a1a1a",
              border: "3px solid #000000",
              fontFamily: "'Press Start 2P', 'Courier New', monospace",
              boxShadow: statusFilter === "validated" ? "4px 4px 0px #000000" : "2px 2px 0px #000000",
            }}
          >
            ✓ Validated
          </button>
          <button
            onClick={() => onStatusFilterChange("pending")}
            className={`px-4 py-2 rounded-lg font-bold transition-all ${
              statusFilter === "pending"
                ? "ring-4 ring-offset-2"
                : "opacity-70 hover:opacity-100"
            }`}
            style={{
              backgroundColor:
                statusFilter === "pending"
                  ? "#fbbf24"
                  : theme === "dark"
                  ? "var(--dark-bg)"
                  : "#F0F0F0",
              color: statusFilter === "pending" ? "#000000" : theme === "dark" ? "var(--dark-text)" : "#1a1a1a",
              border: "3px solid #000000",
              fontFamily: "'Press Start 2P', 'Courier New', monospace",
              boxShadow: statusFilter === "pending" ? "4px 4px 0px #000000" : "2px 2px 0px #000000",
            }}
          >
            ○ Raw/Pending
          </button>
        </div>
      </div>

      {/* Protocol Filter */}
      <div
        className="retro-border rounded-lg p-6"
        style={{
          backgroundColor: theme === "dark" ? "var(--dark-card)" : "#FFFFFF",
          boxShadow: "4px 4px 0px #000000",
        }}
      >
        <label
          className="block text-xs font-bold mb-3 uppercase"
          style={{
            fontFamily: "'Press Start 2P', 'Courier New', monospace",
            color: theme === "dark" ? "var(--dark-text)" : "#6B7280",
          }}
        >
          Filter Protocol
        </label>
        <select
          value={filter}
          onChange={(e) => onFilterChange(e.target.value)}
          className="w-full px-4 py-2 rounded-lg font-bold outline-none"
          style={{
            backgroundColor: theme === "dark" ? "var(--dark-bg)" : "#F0F0F0",
            color: theme === "dark" ? "var(--dark-text)" : "#1a1a1a",
            border: "3px solid #000000",
            fontFamily: "'Press Start 2P', 'Courier New', monospace",
          }}
        >
          <option value="">All Protocols</option>
          <option value="http">HTTP</option>
          <option value="vmess">VMess</option>
          <option value="vless">VLESS</option>
          <option value="trojan">Trojan</option>
          <option value="shadowsocks">Shadowsocks</option>
        </select>
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <Link
          href={getFullUrl("/sources")}
          className="retro-button px-6 py-3 rounded-lg text-center font-bold"
          style={{
            backgroundColor: theme === "dark" ? "var(--dark-bg)" : "#F0F0F0",
            color: theme === "dark" ? "var(--dark-text)" : "#1a1a1a",
            border: "3px solid #000000",
            fontFamily: "'Press Start 2P', 'Courier New', monospace",
            boxShadow: "4px 4px 0px #000000",
          }}
        >
          View Sources
        </Link>
      </div>

      <ProxyTable
        proxies={proxies}
        loading={loading}
        total={total}
        limit={limit}
        currentPage={currentPage}
        onPageChange={onPageChange}
      />
    </div>
  );
}
