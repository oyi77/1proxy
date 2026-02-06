"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type Proxy, type Stats } from "@/lib/api";
import { getFullUrl, API_URL } from '@/lib/constants';
import { TabNavigation } from "@/components/TabNavigation";
import { useTheme } from "@/app/theme-provider";
import { useAuth } from "@/lib/auth-context";
import { HomeTab } from "@/components/tabs/HomeTab";
import { ProxiesTab } from "@/components/tabs/ProxiesTab";
import { RotationTab } from "@/components/tabs/RotationTab";

export function HomeClient() {

  const { theme, toggleTheme } = useTheme();
  const { user, logout } = useAuth();

  const [activeTab, setActiveTab] = useState("home");
  const [stats, setStats] = useState<Stats | null>(null);
  const [proxies, setProxies] = useState<Proxy[]>([]);
  const [totalProxies, setTotalProxies] = useState(0);
  const [loading, setLoading] = useState(true);
  const [tableLoading, setTableLoading] = useState(false);
  const [filter, setFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("validated");
  const [currentPage, setCurrentPage] = useState(0);
  const limit = 15;

  const [rotatorFilters, setRotatorFilters] = useState({
    protocol: "",
    country: "",
    anonymity: "",
  });

  const loadStats = async () => {
    try {
      const data = await api.getStats();
      setStats(data);
    } catch (error) {
      console.error("Error loading stats:", error);
    }
  };

  const loadProxies = async () => {
    setTableLoading(true);
    try {
      const data = await api.getProxies({
        protocol: filter || undefined,
        limit,
        offset: currentPage * limit,
        validation_status: statusFilter === "all" ? undefined : statusFilter,
      });
      setProxies(data.proxies);
      setTotalProxies(data.total);
    } catch (error) {
      console.error("Error loading proxies:", error);
    } finally {
      setTableLoading(false);
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await logout();
  };

  const getRotationUrl = () => {
    const params = new URLSearchParams();
    if (rotatorFilters.protocol) params.set("protocol", rotatorFilters.protocol);
    if (rotatorFilters.country)
      params.set("country_code", rotatorFilters.country);
    if (rotatorFilters.anonymity)
      params.set("anonymity", rotatorFilters.anonymity);

    const query = params.toString();
    return `${API_URL}/api/v1/proxies/random${query ? `?${query}` : ""}`;
  };

  useEffect(() => {
    loadStats();
    loadProxies();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter, statusFilter, currentPage]);

  if (loading && !stats) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{
          backgroundColor: theme === "dark" ? "var(--dark-bg)" : "var(--light-bg)",
        }}
      >
        <div
          className="text-xl animate-pulse"
          style={{
            fontFamily: "'Press Start 2P', 'Courier New', monospace",
            color: theme === "dark" ? "var(--dark-text)" : "var(--light-text)",
          }}
        >
          Loading 1proxy...
        </div>
      </div>
    );
  }

  return (
    <div
      className="min-h-screen p-4 md:p-8"
      style={{
        backgroundColor: theme === "dark" ? "var(--dark-bg)" : "var(--light-bg)",
      }}
    >
      <div className="max-w-7xl mx-auto relative">
        <header className="mb-6">
          <div className="flex flex-col gap-4">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div>
                <h1
                  className="text-4xl md:text-5xl font-bold mb-2"
                  style={{
                    fontFamily: "'Bangers', cursive",
                    color: "var(--retro-pink)",
                    textShadow: "4px 4px 0px #000000",
                  }}
                >
                  1proxy
                </h1>
                <p
                  className="text-base md:text-lg"
                  style={{
                    fontFamily: "'Press Start 2P', 'Courier New', monospace",
                    color:
                      theme === "dark" ? "var(--dark-text)" : "var(--light-text)",
                  }}
                >
                  Robust, Free, Fast Proxy Aggregation Platform
                </p>
              </div>

              <div className="flex flex-wrap items-center justify-end gap-3">
                <button
                  onClick={toggleTheme}
                  className="retro-button px-6 py-3 font-bold rounded-lg"
                  style={{
                    backgroundColor: "var(--retro-yellow)",
                    color: "#000000",
                    fontFamily: "'Press Start 2P', 'Courier New', monospace",
                    border: "3px solid #000000",
                    boxShadow: "4px 4px 0px #000000",
                    width: "fit-content",
                  }}
                  aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
                  title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
                >
                  {theme === "dark" ? "🌙 Dark" : "☀️ Light"}
                </button>

                {user ? (
                  <>
                    <Link
                      href={getFullUrl('/dashboard')}
                      className="retro-button px-4 py-3 rounded-lg flex items-center justify-center font-bold"
                      style={{
                        backgroundColor: "var(--retro-purple)",
                        color: "#FFFFFF",
                        fontFamily: "'Press Start 2P', 'Courier New', monospace",
                        border: "3px solid #000000",
                        boxShadow: "4px 4px 0px #000000",
                      }}
                    >
                      Dashboard
                    </Link>

                    <Link
                      href={getFullUrl('/dashboard/add-source')}
                      className="retro-button px-4 py-3 rounded-lg flex items-center justify-center font-bold"
                      style={{
                        backgroundColor: "var(--retro-blue)",
                        color: "#FFFFFF",
                        fontFamily: "'Press Start 2P', 'Courier New', monospace",
                        border: "3px solid #000000",
                        boxShadow: "4px 4px 0px #000000",
                      }}
                    >
                      + Add
                    </Link>

                    <button
                      onClick={handleLogout}
                      className="retro-button px-4 py-3 rounded-lg flex items-center justify-center font-bold"
                      style={{
                        backgroundColor: "var(--retro-pink)",
                        color: "#FFFFFF",
                        fontFamily: "'Press Start 2P', 'Courier New', monospace",
                        border: "3px solid #000000",
                        boxShadow: "4px 4px 0px #000000",
                      }}
                    >
                      Logout
                    </button>
                  </>
                ) : (
                  <Link
                    href={getFullUrl('/login')}
                    className="retro-button px-4 py-3 rounded-lg flex items-center justify-center font-bold"
                    style={{
                      backgroundColor: "var(--retro-purple)",
                      color: "#FFFFFF",
                      fontFamily: "'Press Start 2P', 'Courier New', monospace",
                      border: "3px solid #000000",
                      boxShadow: "4px 4px 0px #000000",
                    }}
                  >
                    Login
                  </Link>
                )}
              </div>
            </div>

            <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />
          </div>
        </header>

        <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-3">
          <a
            href="https://github.com/oyi77/1proxy"
            target="_blank"
            rel="noopener noreferrer"
            className="retro-button px-4 py-3 rounded-lg flex items-center justify-center gap-2 font-bold"
            style={{
              backgroundColor: "#000000",
              color: "#FFFFFF",
              fontFamily: "'Press Start 2P', 'Courier New', monospace",
              border: "3px solid #000000",
              boxShadow: "4px 4px 0px #000000",
            }}
          >
            <svg
              className="w-5 h-5"
              fill="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747 1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848 2.339 4.695-4.566 4.943.359.309 6.78.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                clipRule="evenodd"
              />
            </svg>
            <span className="hidden sm:inline">GitHub</span>
          </a>

          <a
            href="#"
            className="retro-button px-4 py-3 rounded-lg flex items-center justify-center gap-2 font-bold"
            style={{
              backgroundColor: "var(--retro-pink)",
              color: "#FFFFFF",
              fontFamily: "'Press Start 2P', 'Courier New', monospace",
              border: "3px solid #000000",
              boxShadow: "4px 4px 0px #000000",
            }}
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
              />
            </svg>
            <span className="hidden sm:inline">Support</span>
          </a>
        </div>

        <div className="mt-6">
          {activeTab === "home" && (
            <HomeTab stats={stats} theme={theme} onNavigate={setActiveTab} />
          )}

          {activeTab === "list" && (
            <ProxiesTab
              proxies={proxies}
              loading={tableLoading}
              total={totalProxies}
              limit={limit}
              currentPage={currentPage}
              onPageChange={setCurrentPage}
              filter={filter}
              onFilterChange={(newFilter) => {
                setFilter(newFilter);
                setCurrentPage(0);
              }}
              statusFilter={statusFilter}
              onStatusFilterChange={(newStatus) => {
                setStatusFilter(newStatus);
                setCurrentPage(0);
              }}
              theme={theme}
            />
          )}

          {activeTab === "rotation" && (
            <RotationTab
              filters={rotatorFilters}
              onFilterChange={setRotatorFilters}
              theme={theme}
              rotationUrl={getRotationUrl()}
            />
          )}
        </div>

      </div>
    </div>
  );
}
