"use client";

import { useState, useEffect, useCallback } from "react";
import { api, AdminSource, AdminSourceCreateRequest } from "@/lib/api";

/* ── helpers ── */

const isDark = (t: string) => t === "dark";

const card = (theme: string) =>
  ({
    background: isDark(theme) ? "var(--dark-card)" : "#FFFFFF",
    border: "3px solid #000000",
    boxShadow: "6px 6px 0px #000000",
  } as React.CSSProperties);

const btn = (bg: string) =>
  ({
    fontFamily: "'Press Start 2P','Courier New',monospace",
    fontSize: "0.65rem",
    backgroundColor: bg,
    color: "#FFFFFF",
    border: "3px solid #000000",
    boxShadow: "4px 4px 0px #000000",
    padding: "8px 16px",
    borderRadius: "12px",
    cursor: "pointer",
  } as React.CSSProperties);

const input = (theme: string) =>
  ({
    width: "100%",
    padding: "10px 12px",
    borderRadius: "10px",
    border: "2px solid #000000",
    background: isDark(theme) ? "#2a2a3e" : "#F9F9F9",
    color: isDark(theme) ? "var(--dark-text)" : "#1a1a1a",
    fontFamily: "'Courier New',monospace",
    fontSize: "0.85rem",
    outline: "none",
  } as React.CSSProperties);

/* ── helper components ── */

function Badge({ label, color }: { label: string; color: string }) {
  return (
    <span
      className="inline-block px-2 py-0.5 rounded text-xs font-bold"
      style={{
        fontFamily: "'Press Start 2P','Courier New',monospace",
        fontSize: "0.5rem",
        backgroundColor: color + "22",
        color,
        border: "1px solid " + color,
      }}
    >
      {label}
    </span>
  );
}

/* ── main component ── */

export default function AdminSourcesTab({ theme }: { theme: string }) {
  const [sources, setSources] = useState<AdminSource[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<AdminSourceCreateRequest>({
    url: "",
    type: "github_raw",
    name: "",
    description: "",
    enabled: true,
  });
  const [seeding, setSeeding] = useState(false);
  const [seedMsg, setSeedMsg] = useState("");
  const [scrapeMsg, setScrapeMsg] = useState("");
  const LIMIT = 20;

  const fetchSources = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.getAdminSources({ limit: LIMIT, offset });
      setSources(res.sources);
      setTotal(res.total);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to fetch sources");
    } finally {
      setLoading(false);
    }
  }, [offset]);

  useEffect(() => {
    fetchSources();
  }, [fetchSources]);

  const resetForm = () => {
    setForm({ url: "", type: "github_raw", name: "", description: "", enabled: true });
    setEditId(null);
    setShowForm(false);
  };

  const handleSubmit = async () => {
    if (!form.url.trim()) return;
    setError("");
    try {
      if (editId !== null) {
        await api.updateAdminSource(editId, form);
      } else {
        await api.createAdminSource(form);
      }
      resetForm();
      fetchSources();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Operation failed");
    }
  };

  const handleEdit = (s: AdminSource) => {
    setForm({
      url: s.url,
      type: s.type,
      name: s.name || "",
      description: s.description || "",
      enabled: s.enabled,
    });
    setEditId(s.id);
    setShowForm(true);
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this admin source?")) return;
    setError("");
    try {
      await api.deleteAdminSource(id);
      fetchSources();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  };

  const handleToggleEnabled = async (s: AdminSource) => {
    try {
      await api.updateAdminSource(s.id, { enabled: !s.enabled });
      fetchSources();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Toggle failed");
    }
  };

  const handleScrape = async (s: AdminSource) => {
    setScrapeMsg("");
    try {
      const res = await api.scrapeAdminSource(s.id);
      setScrapeMsg(`🔍 ${res.scraped} proxies from ${res.url.split("/").slice(-2).join("/")}${res.re_enabled ? " (re-enabled ✅)" : ""}${res.error ? ` — ${res.error}` : ""}`);
      fetchSources();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Scrape failed");
    }
  };

  const handleRevive = async (id: number) => {
    try {
      await api.reviveAdminSource(id);
      fetchSources();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Revive failed");
    }
  };

  const handleSeed = async () => {
    setSeeding(true);
    setSeedMsg("");
    try {
      const res = await api.seedAdminSources();
      setSeedMsg(`✅ ${res.message} (${res.count} sources)`);
      fetchSources();
    } catch (e: unknown) {
      setSeedMsg(`❌ ${e instanceof Error ? e.message : "Seed failed"}`);
    } finally {
      setSeeding(false);
    }
  };

  const totalPages = Math.ceil(total / LIMIT);
  const currentPage = Math.floor(offset / LIMIT) + 1;

  return (
    <div className="space-y-6">
      {/* ── header + actions ── */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2
          className="text-2xl font-bold"
          style={{
            fontFamily: "'Bangers','Arial Black',sans-serif",
            color: isDark(theme) ? "var(--dark-text)" : "#1a1a1a",
          }}
        >
          Admin Sources ({total})
        </h2>
        <div className="flex gap-3">
          <button style={btn("var(--retro-purple)")} onClick={() => { resetForm(); setShowForm(!showForm); }}>
            {showForm ? "✕ Close" : "+ Add Source"}
          </button>
          <button style={btn("var(--retro-blue)")} onClick={handleSeed} disabled={seeding}>
            {seeding ? "Seeding..." : "📥 Seed from JSON"}
          </button>
        </div>
      </div>

      {seedMsg && (
        <div
          className="p-3 rounded-xl text-sm font-bold mb-3"
          style={{
            background: isDark(theme) ? "#1a2e1a" : "#e8f5e9",
            border: "2px solid #4caf50",
            color: isDark(theme) ? "#81c784" : "#2e7d32",
            fontFamily: "'Courier New',monospace",
          }}
        >
          {seedMsg}
        </div>
      )}

      {scrapeMsg && (
        <div
          className="p-3 rounded-xl text-sm font-bold mb-3"
          style={{
            background: isDark(theme) ? "#1a2a3e" : "#e3f2fd",
            border: "2px solid #2196f3",
            color: isDark(theme) ? "#90caf9" : "#1565c0",
            fontFamily: "'Courier New',monospace",
          }}
        >
          {scrapeMsg}
        </div>
      )}

      {error && (
        <div
          className="p-3 rounded-xl text-sm font-bold"
          style={{
            background: isDark(theme) ? "#2e1a1a" : "#ffebee",
            border: "2px solid #f44336",
            color: isDark(theme) ? "#ef9a9a" : "#c62828",
            fontFamily: "'Courier New',monospace",
          }}
        >
          ⚠ {error}
        </div>
      )}

      {/* ── add/edit form ── */}
      {showForm && (
        <div className="retro-border rounded-2xl p-6 space-y-4" style={card(theme)}>
          <h3
            className="text-lg font-bold"
            style={{
              fontFamily: "'Press Start 2P','Courier New',monospace",
              fontSize: "0.75rem",
              color: isDark(theme) ? "var(--dark-text)" : "#1a1a1a",
            }}
          >
            {editId !== null ? "✏️ Edit Source" : "➕ New Admin Source"}
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold mb-1" style={{ fontFamily: "'Press Start 2P','Courier New',monospace", fontSize: "0.5rem", color: isDark(theme) ? "var(--dark-text-secondary)" : "#666" }}>
                URL *
              </label>
              <input
                style={input(theme)}
                placeholder="https://raw.githubusercontent.com/..."
                value={form.url}
                onChange={(e) => setForm({ ...form, url: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs font-bold mb-1" style={{ fontFamily: "'Press Start 2P','Courier New',monospace", fontSize: "0.5rem", color: isDark(theme) ? "var(--dark-text-secondary)" : "#666" }}>
                Type
              </label>
              <select
                style={input(theme)}
                value={form.type}
                onChange={(e) => setForm({ ...form, type: e.target.value })}
              >
                <option value="github_raw">github_raw</option>
                <option value="generic_text">generic_text</option>
                <option value="subscription_base64">subscription_base64</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-bold mb-1" style={{ fontFamily: "'Press Start 2P','Courier New',monospace", fontSize: "0.5rem", color: isDark(theme) ? "var(--dark-text-secondary)" : "#666" }}>
                Name
              </label>
              <input
                style={input(theme)}
                placeholder="my-proxy-source"
                value={form.name || ""}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs font-bold mb-1" style={{ fontFamily: "'Press Start 2P','Courier New',monospace", fontSize: "0.5rem", color: isDark(theme) ? "var(--dark-text-secondary)" : "#666" }}>
                Description
              </label>
              <input
                style={input(theme)}
                placeholder="Optional description"
                value={form.description || ""}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </div>
          </div>

          <div className="flex items-center gap-6">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={form.enabled}
                onChange={(e) => setForm({ ...form, enabled: e.target.checked })}
                className="w-4 h-4"
              />
              <span
                className="text-xs font-bold"
                style={{ fontFamily: "'Press Start 2P','Courier New',monospace", fontSize: "0.5rem", color: isDark(theme) ? "var(--dark-text-secondary)" : "#666" }}
              >
                Enabled
              </span>
            </label>
            <button style={btn("var(--retro-green)")} onClick={handleSubmit}>
              {editId !== null ? "💾 Update" : "➕ Create"}
            </button>
            {editId !== null && (
              <button style={btn("#888")} onClick={resetForm}>
                Cancel
              </button>
            )}
          </div>
        </div>
      )}

      {/* ── source list ── */}
      {loading ? (
        <div
          className="text-center py-12 font-bold"
          style={{
            fontFamily: "'Press Start 2P','Courier New',monospace",
            fontSize: "0.75rem",
            color: isDark(theme) ? "var(--dark-text-secondary)" : "#999",
          }}
        >
          Loading sources...
        </div>
      ) : sources.length === 0 ? (
        <div
          className="retro-border rounded-2xl p-8 text-center"
          style={card(theme)}
        >
          <div
            className="font-bold mb-2"
            style={{
              fontFamily: "'Press Start 2P','Courier New',monospace",
              fontSize: "0.75rem",
              color: isDark(theme) ? "var(--dark-text-secondary)" : "#999",
            }}
          >
            No admin sources yet
          </div>
          <p
            className="text-sm"
            style={{
              fontFamily: "'Courier New',monospace",
              color: isDark(theme) ? "var(--dark-text-secondary)" : "#666",
            }}
          >
            Click &quot;Seed from JSON&quot; to load the default 83+ sources, or add one manually.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {sources.map((s) => (
            <div
              key={s.id}
              className="retro-border rounded-xl p-4 flex flex-wrap items-start justify-between gap-4"
              style={card(theme)}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-1">
                  <span
                    className="font-bold truncate max-w-md"
                    style={{
                      fontFamily: "'Courier New',monospace",
                      fontSize: "0.85rem",
                      color: isDark(theme) ? "var(--dark-text)" : "#1a1a1a",
                    }}
                  >
                    {s.name || s.url.split("/").slice(-2).join("/")}
                  </span>
                  <Badge label={s.type} color="var(--retro-blue)" />
                  {!s.enabled && s.validation_error ? (
                    <Badge label="dead" color="var(--retro-pink)" />
                  ) : !s.validated ? (
                    <Badge label="unvalidated" color="var(--retro-yellow)" />
                  ) : null}
                  {s.enabled ? (
                    <Badge label="enabled" color="var(--retro-green)" />
                  ) : (
                    <Badge label="disabled" color="#888" />
                  )}
                </div>
                <div
                  className="text-xs truncate max-w-xl mb-1"
                  style={{
                    fontFamily: "'Courier New',monospace",
                    color: isDark(theme) ? "var(--dark-text-secondary)" : "#666",
                  }}
                >
                  {s.url}
                </div>
                <div
                  className="text-xs flex gap-4"
                  style={{
                    fontFamily: "'Courier New',monospace",
                    color: isDark(theme) ? "var(--dark-text-secondary)" : "#888",
                  }}
                >
                  <span>📊 {s.total_scraped} scraped</span>
                  <span>✅ {s.validated ? "validated" : "pending"}</span>
                  {s.success_rate !== undefined && s.success_rate !== null && (
                    <span>📈 {s.success_rate.toFixed(1)}% success</span>
                  )}
                </div>
              </div>
              <div className="flex gap-2 shrink-0">
                <button
                  style={btn("var(--retro-blue)")}
                  onClick={() => handleScrape(s)}
                  title="Scrape now"
                >
                  🔍
                </button>
                {!s.enabled && s.validation_error ? (
                  <button
                    style={btn("var(--retro-green)")}
                    onClick={() => handleRevive(s.id)}
                    title="Revive (re-enable)"
                  >
                    💀 Revive
                  </button>
                ) : null}
                <button
                  style={btn(s.enabled ? "#888" : "var(--retro-green)")}
                  onClick={() => handleToggleEnabled(s)}
                >
                  {s.enabled ? "Disable" : "Enable"}
                </button>
                <button style={btn("var(--retro-yellow)")} onClick={() => handleEdit(s)}>
                  Edit
                </button>
                <button style={btn("var(--retro-pink)")} onClick={() => handleDelete(s.id)}>
                  Del
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── pagination ── */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 pt-4">
          <button
            style={btn("var(--retro-blue)")}
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - LIMIT))}
          >
            ◀ Prev
          </button>
          <span
            className="text-sm font-bold"
            style={{
              fontFamily: "'Press Start 2P','Courier New',monospace",
              fontSize: "0.6rem",
              color: isDark(theme) ? "var(--dark-text)" : "#1a1a1a",
            }}
          >
            Page {currentPage} / {totalPages}
          </span>
          <button
            style={btn("var(--retro-blue)")}
            disabled={offset + LIMIT >= total}
            onClick={() => setOffset(offset + LIMIT)}
          >
            Next ▶
          </button>
        </div>
      )}
    </div>
  );
}
