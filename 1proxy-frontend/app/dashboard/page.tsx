"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useTheme } from "@/app/theme-provider";
import { useAuth, ProtectedRoute } from "@/lib/auth-context";
import { getFullUrl, API_URL } from "@/lib/constants";

interface Source {
  id: number;
  url: string;
  type: string;
  name: string;
  enabled: boolean;
  validated: boolean;
  validation_error: string | null;
  total_scraped: number;
  success_rate: number;
  is_admin_source: boolean;
}

interface UserStats {
  total_sources: number;
  active_sources: number;
  total_proxies_contributed: number;
  avg_success_rate: number;
}

function DashboardContent() {
  const { theme } = useTheme();
  const { user, logout } = useAuth();
  const [sources, setSources] = useState<Source[]>([]);
  const [stats, setStats] = useState<UserStats | null>(null);
  const [loading, setLoading] = useState(true);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || API_URL;

  useEffect(() => {
    loadUserData();
  }, []);

  const loadUserData = async () => {
    try {
      const [sourcesRes, statsRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/my-sources`, { credentials: "include" }),
        fetch(`${API_BASE}/api/v1/my-stats`, { credentials: "include" })
      ]);

      if (sourcesRes.ok) {
        const sourcesData = await sourcesRes.json();
        setSources(sourcesData.sources || []);
      }

      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }
    } catch (error) {
      console.error("Error loading dashboard:", error);
    } finally {
      setLoading(false);
    }
  };

  const deleteSource = async (id: number) => {
    if (!confirm("Are you sure you want to delete this source?")) return;

    try {
      const res = await fetch(`${API_BASE}/api/v1/my-sources/${id}`, {
        method: "DELETE",
        credentials: "include"
      });

      if (res.ok) {
        setSources(sources.filter(s => s.id !== id));
      } else {
        alert("Failed to delete source");
      }
    } catch (error) {
      console.error("Error deleting source:", error);
      alert("Error deleting source");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{
        backgroundColor: theme === 'dark' ? 'var(--dark-bg)' : 'var(--light-bg)'
      }}>
        <div className="text-xl animate-pulse" style={{
          fontFamily: "'Press Start 2P', 'Courier New', monospace",
          color: theme === 'dark' ? 'var(--dark-text)' : 'var(--light-text)'
        }}>
          Loading dashboard...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-4 md:p-8" style={{
      backgroundColor: theme === 'dark' ? 'var(--dark-bg)' : 'var(--light-bg)'
    }}>
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row md:justify-between md:items-start gap-4 mb-8">
          <div>
            <h1 className="text-4xl md:text-5xl font-bold mb-2" style={{
              fontFamily: "'Bangers', cursive",
              color: 'var(--retro-pink)',
              textShadow: '4px 4px 0px #000000'
            }}>
              My Dashboard
            </h1>
            <p className="text-base md:text-lg" style={{
              fontFamily: "'Press Start 2P', 'Courier New', monospace",
              color: theme === 'dark' ? 'var(--dark-text)' : 'var(--light-text)'
            }}>
              Welcome, {user?.username}! Manage your proxy sources and track contributions
            </p>
          </div>
          <div className="flex gap-3">
            {user?.role === 'admin' && (
              <Link
                href={getFullUrl("/admin")}
                className="retro-button px-6 py-3 rounded-lg font-bold"
                style={{
                  backgroundColor: 'var(--retro-purple)',
                  color: '#FFFFFF',
                  fontFamily: "'Press Start 2P', 'Courier New', monospace",
                  border: '3px solid #000000',
                  boxShadow: '4px 4px 0px #000000'
                }}
              >
                Admin Panel
              </Link>
            )}
            <button
              onClick={logout}
              className="retro-button px-6 py-3 rounded-lg font-bold"
              style={{
                backgroundColor: theme === 'dark' ? 'var(--dark-bg)' : '#F0F0F0',
                color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a',
                fontFamily: "'Press Start 2P', 'Courier New', monospace",
                border: '3px solid #000000',
                boxShadow: '4px 4px 0px #000000'
              }}
            >
              Logout
            </button>
          </div>
        </div>

        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div className="retro-border rounded-xl p-6" style={{
              backgroundColor: theme === 'dark' ? 'var(--dark-card)' : '#FFFFFF',
              boxShadow: '4px 4px 0px #000000'
            }}>
              <h3 className="text-sm font-bold mb-2 uppercase" style={{
                fontFamily: "'Press Start 2P', 'Courier New', monospace",
                color: theme === 'dark' ? 'var(--dark-text)' : '#6B7280'
              }}>
                Total Sources
              </h3>
              <p className="text-4xl font-bold" style={{
                fontFamily: "'Bangers', cursive",
                color: 'var(--retro-blue)',
                textShadow: '2px 2px 0px #000000'
              }}>
                {stats.total_sources}
              </p>
            </div>
            <div className="retro-border rounded-xl p-6" style={{
              backgroundColor: theme === 'dark' ? 'var(--dark-card)' : '#FFFFFF',
              boxShadow: '4px 4px 0px #000000'
            }}>
              <h3 className="text-sm font-bold mb-2 uppercase" style={{
                fontFamily: "'Press Start 2P', 'Courier New', monospace",
                color: theme === 'dark' ? 'var(--dark-text)' : '#6B7280'
              }}>
                Active Sources
              </h3>
              <p className="text-4xl font-bold" style={{
                fontFamily: "'Bangers', cursive",
                color: 'var(--retro-blue)',
                textShadow: '2px 2px 0px #000000'
              }}>
                {stats.active_sources}
              </p>
            </div>
            <div className="retro-border rounded-xl p-6" style={{
              backgroundColor: theme === 'dark' ? 'var(--dark-card)' : '#FFFFFF',
              boxShadow: '4px 4px 0px #000000'
            }}>
              <h3 className="text-sm font-bold mb-2 uppercase" style={{
                fontFamily: "'Press Start 2P', 'Courier New', monospace",
                color: theme === 'dark' ? 'var(--dark-text)' : '#6B7280'
              }}>
                Proxies Contributed
              </h3>
              <p className="text-4xl font-bold" style={{
                fontFamily: "'Bangers', cursive",
                color: 'var(--retro-blue)',
                textShadow: '2px 2px 0px #000000'
              }}>
                {stats.total_proxies_contributed}
              </p>
            </div>
            <div className="retro-border rounded-xl p-6" style={{
              backgroundColor: theme === 'dark' ? 'var(--dark-card)' : '#FFFFFF',
              boxShadow: '4px 4px 0px #000000'
            }}>
              <h3 className="text-sm font-bold mb-2 uppercase" style={{
                fontFamily: "'Press Start 2P', 'Courier New', monospace",
                color: theme === 'dark' ? 'var(--dark-text)' : '#6B7280'
              }}>
                Success Rate
              </h3>
              <p className="text-4xl font-bold" style={{
                fontFamily: "'Bangers', cursive",
                color: 'var(--retro-blue)',
                textShadow: '2px 2px 0px #000000'
              }}>
                {(stats.avg_success_rate * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        )}

        <div className="retro-border rounded-2xl p-6 md:p-8" style={{
          backgroundColor: theme === 'dark' ? 'var(--dark-card)' : '#FFFFFF',
          boxShadow: '6px 6px 0px #000000'
        }}>
          <div className="flex flex-col md:flex-row md:justify-between md:items-center gap-4 mb-6">
            <h2 className="text-2xl font-bold" style={{
              fontFamily: "'Bangers', cursive",
              color: 'var(--retro-pink)',
              textShadow: '2px 2px 0px #000000'
            }}>
              My Sources
            </h2>
            <Link
              href={getFullUrl("/dashboard/add-source")}
              className="retro-button px-6 py-3 rounded-lg font-bold"
              style={{
                backgroundColor: 'var(--retro-blue)',
                color: '#FFFFFF',
                fontFamily: "'Press Start 2P', 'Courier New', monospace",
                border: '3px solid #000000',
                boxShadow: '4px 4px 0px #000000'
              }}
            >
              ➕ Add New Source
            </Link>
          </div>

          {sources.length === 0 ? (
            <div className="text-center py-12" style={{
              color: theme === 'dark' ? 'var(--dark-text)' : '#6B7280'
            }}>
              <p style={{
                fontFamily: "'Press Start 2P', 'Courier New', monospace",
                marginBottom: '1rem'
              }}>
                You haven&apos;t added any sources yet.
              </p>
              <Link
                href={getFullUrl("/dashboard/add-source")}
                className="inline-block"
                style={{
                  color: 'var(--retro-pink)',
                  fontFamily: "'Press Start 2P', 'Courier New', monospace",
                  textDecoration: 'underline'
                }}
              >
                Add your first source →
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead style={{
                  borderBottom: '3px solid #000000'
                }}>
                  <tr>
                    <th className="text-left py-4 px-4 font-bold" style={{
                      fontFamily: "'Press Start 2P', 'Courier New', monospace",
                      color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a'
                    }}>
                      Name
                    </th>
                    <th className="text-left py-4 px-4 font-bold" style={{
                      fontFamily: "'Press Start 2P', 'Courier New', monospace",
                      color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a'
                    }}>
                      Status
                    </th>
                    <th className="text-left py-4 px-4 font-bold" style={{
                      fontFamily: "'Press Start 2P', 'Courier New', monospace",
                      color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a'
                    }}>
                      Type
                    </th>
                    <th className="text-left py-4 px-4 font-bold" style={{
                      fontFamily: "'Press Start 2P', 'Courier New', monospace",
                      color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a'
                    }}>
                      Proxies
                    </th>
                    <th className="text-left py-4 px-4 font-bold" style={{
                      fontFamily: "'Press Start 2P', 'Courier New', monospace",
                      color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a'
                    }}>
                      Success Rate
                    </th>
                    <th className="text-left py-4 px-4 font-bold" style={{
                      fontFamily: "'Press Start 2P', 'Courier New', monospace",
                      color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a'
                    }}>
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {sources.map((source, idx) => (
                    <tr
                      key={source.id}
                      style={{
                        borderBottom: '2px solid #000000',
                        backgroundColor: idx % 2 === 0 ? (theme === 'dark' ? 'var(--dark-card)' : '#FFFFFF') : (theme === 'dark' ? 'rgba(255,255,255,0.05)' : '#F9F9F9')
                      }}
                    >
                      <td className="py-4 px-4 font-medium" style={{
                        color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a',
                        fontFamily: "'Press Start 2P', 'Courier New', monospace"
                      }}>
                        {source.name}
                      </td>
                      <td className="py-4 px-4">
                        {source.validated ? (
                          <span className="px-3 py-1 rounded font-bold text-sm" style={{
                            backgroundColor: 'var(--retro-blue)',
                            color: '#FFFFFF',
                            fontFamily: "'Press Start 2P', 'Courier New', monospace",
                            border: '2px solid #000000'
                          }}>
                            ✓ Valid
                          </span>
                        ) : (
                          <span className="px-3 py-1 rounded font-bold text-sm" style={{
                            backgroundColor: '#EF4444',
                            color: '#FFFFFF',
                            fontFamily: "'Press Start 2P', 'Courier New', monospace",
                            border: '2px solid #000000'
                          }}>
                            {source.validation_error || "Pending"}
                          </span>
                        )}
                      </td>
                      <td className="py-4 px-4">
                        <span className="px-3 py-1 rounded font-bold text-sm" style={{
                          backgroundColor: 'var(--retro-purple)',
                          color: '#FFFFFF',
                          fontFamily: "'Press Start 2P', 'Courier New', monospace",
                          border: '2px solid #000000'
                        }}>
                          {source.type}
                        </span>
                      </td>
                      <td className="py-4 px-4" style={{
                        color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a',
                        fontFamily: "'Press Start 2P', 'Courier New', monospace"
                      }}>
                        {source.total_scraped}
                      </td>
                      <td className="py-4 px-4" style={{
                        color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a',
                        fontFamily: "'Press Start 2P', 'Courier New', monospace"
                      }}>
                        {(source.success_rate * 100).toFixed(1)}%
                      </td>
                      <td className="py-4 px-4">
                        <div className="flex gap-3 flex-wrap">
                          <Link
                            href={getFullUrl(`/dashboard/sources/${source.id}/edit`)}
                            className="font-bold text-sm"
                            style={{
                              color: 'var(--retro-pink)',
                              fontFamily: "'Press Start 2P', 'Courier New', monospace",
                              textDecoration: 'underline'
                            }}
                          >
                            Edit
                          </Link>
                          {!source.is_admin_source && (
                            <button
                              onClick={() => deleteSource(source.id)}
                              className="font-bold text-sm"
                              style={{
                                color: '#EF4444',
                                fontFamily: "'Press Start 2P', 'Courier New', monospace",
                                textDecoration: 'underline',
                                cursor: 'pointer'
                              }}
                            >
                              Delete
                            </button>
                          )}
                          {source.is_admin_source && (
                            <span className="text-sm" style={{
                              color: '#9CA3AF',
                              fontFamily: "'Press Start 2P', 'Courier New', monospace"
                            }}>
                              Protected
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="mt-6">
          <Link
            href={getFullUrl("/")}
            className="retro-button px-6 py-3 rounded-lg font-bold inline-block"
            style={{
              backgroundColor: theme === 'dark' ? 'var(--dark-bg)' : '#F0F0F0',
              color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a',
              fontFamily: "'Press Start 2P', 'Courier New', monospace",
              border: '3px solid #000000',
              boxShadow: '4px 4px 0px #000000'
            }}
          >
            ← Back to Public Proxies
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}
