"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type Proxy, type Stats } from "@/lib/api";
import { TabNavigation } from "@/components/TabNavigation";
import { ProxyTable } from "@/components/ProxyTable";
import { useTheme } from "@/app/theme-provider";
import { useAuth } from "@/lib/auth-context";

export function HomeClient() {
  const { theme, toggleTheme } = useTheme();
  const { user, logout } = useAuth();

  const [activeTab, setActiveTab] = useState("home");
  const [stats, setStats] = useState<Stats | null>(null);
  const [proxies, setProxies] = useState<Proxy[]>([]);
  const [totalProxies, setTotalProxies] = useState(0);
  const [loading, setLoading] = useState(true);
  const [tableLoading, setTableLoading] = useState(false);
  const [scraping, setScraping] = useState(false);
  const [filter, setFilter] = useState<string>("");
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

  const handleScrapeDemo = async () => {
    setScraping(true);
    try {
      const result = await api.scrapeDemo();
      alert(
        `Scraped ${result.scraped} proxies!\nAdded: ${result.added}\nTotal: ${result.total_stored}`
      );
      await loadStats();
      await loadProxies();
    } catch (error) {
      console.error("Error scraping:", error);
      alert("Failed to scrape demo proxies");
    } finally {
      setScraping(false);
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
    return `http://localhost:8000/api/v1/proxies/random${query ? `?${query}` : ""}`;
  };

  useEffect(() => {
    loadStats();
    loadProxies();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter, currentPage]);

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
                      href="/dashboard"
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
                      href="/dashboard/add-source"
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
                    href="/login"
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
            href="https://github.com/yourusername/1proxy"
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
            <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div
                className="retro-border rounded-2xl p-6 md:p-8 relative overflow-hidden"
                style={{
                  backgroundColor: "var(--retro-purple)",
                  boxShadow: "6px 6px 0px #000000",
                }}
              >
                <div
                  className="absolute top-4 right-4 w-32 h-32 rounded-full opacity-20"
                  style={{
                    backgroundColor: "var(--retro-pink)",
                  }}
                ></div>
                <div className="relative z-10">
                  <h2
                    className="text-3xl md:text-4xl font-bold mb-4"
                    style={{
                      fontFamily: "'Bangers', cursive",
                      color: "#FFFFFF",
                      textShadow: "4px 4px 0px #000000",
                    }}
                  >
                    Welcome to 1proxy
                  </h2>
                  <p
                    className="text-lg md:text-xl mb-8 leading-relaxed"
                    style={{
                      fontFamily: "'Press Start 2P', 'Courier New', monospace",
                      color: "#FFFFFF",
                    }}
                  >
                    Access thousands of free proxies automatically aggregated from
                    community sources. Use our rotation endpoint to forget about
                    managing proxy lists forever.
                  </p>
                  <div className="flex flex-wrap gap-4">
                    <button
                      onClick={() => setActiveTab("rotation")}
                      className="retro-button px-6 py-3 font-bold rounded-lg text-lg"
                      style={{
                        backgroundColor: "#FFFFFF",
                        color: "var(--retro-purple)",
                        fontFamily: "'Bangers', cursive",
                      }}
                    >
                      Use Proxy Rotator
                    </button>
                    <button
                      onClick={() => setActiveTab("list")}
                      className="retro-button px-6 py-3 font-semibold rounded-lg text-lg"
                      style={{
                        backgroundColor: "rgba(255,255,255,0.3)",
                        color: "#FFFFFF",
                        fontFamily: "'Press Start 2P', 'Courier New', monospace",
                      }}
                    >
                      Browse Proxy List
                    </button>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div
                  className="retro-border rounded-xl p-6"
                  style={{
                    backgroundColor:
                      theme === "dark" ? "var(--dark-card)" : "#FFFFFF",
                    boxShadow: "4px 4px 0px #000000",
                  }}
                >
                  <h3
                    className="text-sm font-bold mb-2 uppercase"
                    style={{
                      fontFamily: "'Press Start 2P', 'Courier New', monospace",
                      color: theme === "dark" ? "var(--dark-text)" : "#6B7280",
                    }}
                  >
                    Total Proxies
                  </h3>
                  <p
                    className="text-4xl font-bold mt-2"
                    style={{
                      fontFamily: "'Bangers', cursive",
                      color: "var(--retro-blue)",
                      textShadow: "2px 2px 0px #000000",
                    }}
                  >
                    {stats?.total_proxies.toLocaleString() || 0}
                  </p>
                </div>
                <div
                  className="retro-border rounded-xl p-6"
                  style={{
                    backgroundColor:
                      theme === "dark" ? "var(--dark-card)" : "#FFFFFF",
                    boxShadow: "4px 4px 0px #000000",
                  }}
                >
                  <h3
                    className="text-sm font-bold mb-2 uppercase"
                    style={{
                      fontFamily: "'Press Start 2P', 'Courier New', monospace",
                      color: theme === "dark" ? "var(--dark-text)" : "#6B7280",
                    }}
                  >
                    HTTP Proxies
                  </h3>
                  <p
                    className="text-4xl font-bold mt-2"
                    style={{
                      fontFamily: "'Bangers', cursive",
                      color: "#10B981",
                      textShadow: "2px 2px 0px #000000",
                    }}
                  >
                    {stats?.by_protocol.http.toLocaleString() || 0}
                  </p>
                </div>
                <div
                  className="retro-border rounded-xl p-6"
                  style={{
                    backgroundColor:
                      theme === "dark" ? "var(--dark-card)" : "#FFFFFF",
                    boxShadow: "4px 4px 0px #000000",
                  }}
                >
                  <h3
                    className="text-sm font-bold mb-2 uppercase"
                    style={{
                      fontFamily: "'Press Start 2P', 'Courier New', monospace",
                      color: theme === "dark" ? "var(--dark-text)" : "#6B7280",
                    }}
                  >
                    SOCKS/VMess
                  </h3>
                  <p
                    className="text-4xl font-bold mt-2"
                    style={{
                      fontFamily: "'Bangers', cursive",
                      color: "var(--retro-orange)",
                      textShadow: "2px 2px 0px #000000",
                    }}
                  >
                    {(
                      (stats?.by_protocol.vmess || 0) +
                      (stats?.by_protocol.shadowsocks || 0)
                    ).toLocaleString()}
                  </p>
                </div>
              </div>
            </div>
          )}

          {activeTab === "list" && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
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
                  onChange={(e) => {
                    setFilter(e.target.value);
                    setCurrentPage(0);
                  }}
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
                  href="/sources"
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
                <button
                  onClick={handleScrapeDemo}
                  disabled={scraping}
                  className="retro-button px-6 py-3 rounded-lg flex items-center justify-center gap-2 font-bold"
                  style={{
                    backgroundColor: "var(--retro-blue)",
                    color: "#FFFFFF",
                    border: "3px solid #000000",
                    fontFamily: "'Press Start 2P', 'Courier New', monospace",
                    boxShadow: "4px 4px 0px #000000",
                    opacity: scraping ? 0.5 : 1,
                    cursor: scraping ? "not-allowed" : "pointer",
                  }}
                >
                  {scraping && (
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  )}
                  {scraping ? "Scraping..." : "Scrape Demo"}
                </button>
              </div>

              <ProxyTable
                proxies={proxies}
                loading={tableLoading}
                total={totalProxies}
                limit={limit}
                currentPage={currentPage}
                onPageChange={setCurrentPage}
              />
            </div>
          )}

          {activeTab === "rotation" && (
            <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
              <div className="grid lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2 space-y-6">
                  <div
                    className="retro-border rounded-2xl p-6"
                    style={{
                      backgroundColor:
                        theme === "dark" ? "var(--dark-card)" : "#FFFFFF",
                      boxShadow: "4px 4px 0px #000000",
                    }}
                  >
                    <h2
                      className="text-2xl font-bold mb-4"
                      style={{
                        fontFamily: "'Bangers', cursive",
                        color: "var(--retro-pink)",
                        textShadow: "4px 4px 0px #000000",
                      }}
                    >
                      Configure Rotation
                    </h2>
                    <div className="grid md:grid-cols-3 gap-4 mb-6">
                      <div>
                        <label
                          className="block text-xs font-bold mb-1 uppercase"
                          style={{
                            fontFamily: "'Press Start 2P', 'Courier New', monospace",
                            color:
                              theme === "dark" ? "var(--dark-text)" : "#6B7280",
                          }}
                        >
                          Country
                        </label>
                        <select
                          className="w-full px-4 py-2 rounded-lg font-bold outline-none"
                          style={{
                            backgroundColor:
                              theme === "dark" ? "var(--dark-bg)" : "#F0F0F0",
                            color:
                              theme === "dark" ? "var(--dark-text)" : "#1a1a1a",
                            border: "3px solid #000000",
                            fontFamily: "'Press Start 2P', 'Courier New', monospace",
                          }}
                          onChange={(e) =>
                            setRotatorFilters({
                              ...rotatorFilters,
                              country: e.target.value,
                            })
                          }
                        >
                          <option value="">Any Country</option>
                          <option value="US">United States</option>
                          <option value="DE">Germany</option>
                          <option value="CN">China</option>
                          <option value="RU">Russia</option>
                        </select>
                      </div>
                      <div>
                        <label
                          className="block text-xs font-bold mb-1 uppercase"
                          style={{
                            fontFamily: "'Press Start 2P', 'Courier New', monospace",
                            color:
                              theme === "dark" ? "var(--dark-text)" : "#6B7280",
                          }}
                        >
                          Protocol
                        </label>
                        <select
                          className="w-full px-4 py-2 rounded-lg font-bold outline-none"
                          style={{
                            backgroundColor:
                              theme === "dark" ? "var(--dark-bg)" : "#F0F0F0",
                            color:
                              theme === "dark" ? "var(--dark-text)" : "#1a1a1a",
                            border: "3px solid #000000",
                            fontFamily: "'Press Start 2P', 'Courier New', monospace",
                          }}
                          onChange={(e) =>
                            setRotatorFilters({
                              ...rotatorFilters,
                              protocol: e.target.value,
                            })
                          }
                        >
                          <option value="">Any Protocol</option>
                          <option value="http">HTTP</option>
                          <option value="socks4">SOCKS4</option>
                          <option value="socks5">SOCKS5</option>
                        </select>
                      </div>
                      <div>
                        <label
                          className="block text-xs font-bold mb-1 uppercase"
                          style={{
                            fontFamily: "'Press Start 2P', 'Courier New', monospace",
                            color:
                              theme === "dark" ? "var(--dark-text)" : "#6B7280",
                          }}
                        >
                          Anonymity
                        </label>
                        <select
                          className="w-full px-4 py-2 rounded-lg font-bold outline-none"
                          style={{
                            backgroundColor:
                              theme === "dark" ? "var(--dark-bg)" : "#F0F0F0",
                            color:
                              theme === "dark" ? "var(--dark-text)" : "#1a1a1a",
                            border: "3px solid #000000",
                            fontFamily: "'Press Start 2P', 'Courier New', monospace",
                          }}
                          onChange={(e) =>
                            setRotatorFilters({
                              ...rotatorFilters,
                              anonymity: e.target.value,
                            })
                          }
                        >
                          <option value="">Any Level</option>
                          <option value="elite">Elite</option>
                          <option value="anonymous">Anonymous</option>
                          <option value="transparent">Transparent</option>
                        </select>
                      </div>
                    </div>

                    <div
                      className="rounded-xl p-6 font-mono text-sm overflow-x-auto"
                      style={{
                        backgroundColor: theme === "dark" ? "#1a1a2e" : "#1a1a1a",
                        border: "3px solid #000000",
                        boxShadow: "4px 4px 0px #000000",
                      }}
                    >
                      <div className="flex justify-between items-center mb-4 border-b-2 border-black pb-2">
                        <span className="font-bold" style={{ color: "#10B981" }}>
                          API Endpoint
                        </span>
                        <span className="text-xs font-bold" style={{ color: "#6B7280" }}>
                          GET
                        </span>
                      </div>
                      <p
                        className="break-all font-bold"
                        style={{
                          color: theme === "dark" ? "#4ADE80" : "#10B981",
                        }}
                      >
                        {getRotationUrl()}
                      </p>
                    </div>
                  </div>

                  <div
                    className="retro-border rounded-2xl p-6"
                    style={{
                      backgroundColor:
                        theme === "dark" ? "var(--dark-card)" : "#FFFFFF",
                      boxShadow: "4px 4px 0px #000000",
                    }}
                  >
                    <h2
                      className="text-xl font-bold mb-4"
                      style={{
                        fontFamily: "'Bangers', cursive",
                        color: "var(--retro-pink)",
                        textShadow: "4px 4px 0px #000000",
                      }}
                    >
                      Connect as a Proxy
                    </h2>
                    <p
                      className="text-base mb-6"
                      style={{
                        fontFamily: "'Press Start 2P', 'Courier New', monospace",
                        color: theme === "dark" ? "var(--dark-text)" : "#6B7280",
                      }}
                    >
                      Download our local rotator script to create a standard HTTP
                      proxy on your machine (localhost:8080) that automatically
                      rotates IP for every request.
                    </p>
                    <div className="flex gap-4">
                      <a
                        href="/rotator.py"
                        download="rotator.py"
                        className="retro-button px-6 py-3 font-bold rounded-lg flex items-center gap-2"
                        style={{
                          backgroundColor: "var(--retro-purple)",
                          color: "#FFFFFF",
                          fontFamily: "'Press Start 2P', 'Courier New', monospace",
                        }}
                      >
                        <svg
                          className="w-5 h-5"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                          />
                        </svg>
                        Download Rotator Script
                      </a>
                    </div>
                    <div
                      className="rounded-lg p-4"
                      style={{
                        backgroundColor: theme === "dark" ? "var(--dark-bg)" : "#F0F0F0",
                        border: "3px solid #000000",
                      }}
                    >
                      <p
                        className="text-sm font-mono font-bold"
                        style={{
                          color: theme === "dark" ? "var(--dark-text)" : "#6B7280",
                        }}
                      >
                        python3 rotator.py --port 8080 --country US --anonymity elite
                      </p>
                    </div>
                  </div>
                </div>

                <div className="space-y-6">
                  <div
                    className="retro-border rounded-xl p-6"
                    style={{
                      backgroundColor:
                        theme === "dark" ? "var(--dark-card)" : "#FFFFFF",
                      boxShadow: "4px 4px 0px #000000",
                    }}
                  >
                    <h3
                      className="font-bold mb-2"
                      style={{
                        fontFamily: "'Bangers', cursive",
                        color: "#FFFFFF",
                        textShadow: "4px 4px 0px #000000",
                      }}
                    >
                      Why use rotation?
                    </h3>
                    <ul
                      className="space-y-2 text-base"
                      style={{
                        fontFamily: "'Press Start 2P', 'Courier New', monospace",
                        color: "#FFFFFF",
                      }}
                    >
                      <li>• Avoid IP bans while scraping</li>
                      <li>• Access geo-restricted content</li>
                      <li>• Distribute traffic across thousands of IPs</li>
                      <li>• High availability via automatic failover</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
