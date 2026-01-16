"use client";

import { useEffect, useState } from "react";
import { useTheme } from "@/app/theme-provider";
import { api, type ValidationStats, type QualityDistribution } from "@/lib/api";
import { ScrapingSessionTab } from "@/components/tabs/ScrapingSessionTab";
import { ScrapingConfigTab } from "@/components/tabs/ScrapingConfigTab";

type TabType = "overview" | "scraping-sessions" | "scraping-config";

export default function AdminPage() {
  const { theme } = useTheme();
  const [activeTab, setActiveTab] = useState<TabType>("overview");
  const [stats, setStats] = useState<ValidationStats | null>(null);
  const [quality, setQuality] = useState<QualityDistribution | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = async () => {
    try {
      const [statsData, qualityData] = await Promise.all([
        api.getAdminValidationStats(),
        api.getAdminQualityDistribution(),
      ]);

      setStats(statsData);
      setQuality(qualityData);
    } catch (error) {
      console.error("Failed to fetch admin stats:", error);
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);

  const tabs: { id: TabType; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "scraping-sessions", label: "Scraping Sessions" },
    { id: "scraping-config", label: "Scraping Config" },
  ];

  if (loading && activeTab === "overview") {
    return (
      <div className="min-h-screen p-8" style={{
        backgroundColor: theme === 'dark' ? 'var(--dark-bg)' : 'var(--light-bg)'
      }}>
        <div className="max-w-7xl mx-auto">
          <div className="text-center py-20">
            <div
              className="w-12 h-12 border-4 border-current border-t-transparent rounded-full animate-spin mx-auto"
              style={{ color: 'var(--retro-blue)' }}
            />
            <p className="mt-4" style={{
              fontFamily: "'Press Start 2P', 'Courier New', monospace",
              color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a'
            }}>
              Loading stats...
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-8" style={{
      backgroundColor: theme === 'dark' ? 'var(--dark-bg)' : 'var(--light-bg)'
    }}>
      <div className="max-w-7xl mx-auto">
        <h1 className="text-4xl font-bold mb-8 retro-text-shadow" style={{
          fontFamily: "'Bangers', 'Arial Black', sans-serif",
          color: 'var(--retro-pink)',
          textShadow: '4px 4px 0px #000000'
        }}>
          Admin Dashboard
        </h1>

        <div className="mb-8">
          <div className="flex flex-wrap gap-3">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className="px-6 py-3 rounded-lg font-bold transition-all"
                style={{
                  fontFamily: "'Press Start 2P', 'Courier New', monospace",
                  backgroundColor: activeTab === tab.id 
                    ? 'var(--retro-pink)' 
                    : theme === 'dark' ? 'var(--dark-card)' : '#FFFFFF',
                  color: activeTab === tab.id 
                    ? '#FFFFFF' 
                    : theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a',
                  border: '3px solid #000000',
                  boxShadow: activeTab === tab.id 
                    ? '4px 4px 0px #000000' 
                    : '2px 2px 0px #000000',
                  fontSize: '0.75rem',
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {activeTab === "overview" && stats && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              <StatCard
                title="Total Proxies"
                value={stats.total_proxies}
                color="var(--retro-blue)"
                theme={theme}
              />
              <StatCard
                title="Validated"
                value={stats.summary.validated}
                subtitle={`${stats.summary.validation_rate_percent}%`}
                color="var(--retro-green)"
                theme={theme}
              />
              <StatCard
                title="Pending"
                value={stats.summary.pending}
                color="var(--retro-yellow)"
                theme={theme}
              />
              <StatCard
                title="Failed"
                value={stats.summary.failed}
                color="var(--retro-pink)"
                theme={theme}
              />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
              <div className="retro-border rounded-2xl p-6" style={{
                backgroundColor: theme === 'dark' ? 'var(--dark-card)' : '#FFFFFF',
                boxShadow: '6px 6px 0px #000000',
                border: '3px solid #000000'
              }}>
                <h2 className="text-2xl font-bold mb-4" style={{
                  fontFamily: "'Bangers', 'Arial Black', sans-serif",
                  color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a'
                }}>
                  Validation Progress
                </h2>

                <div className="space-y-4">
                  {stats.summary.validated > 0 && (
                    <ProgressBar
                      label="Validated"
                      value={stats.summary.validated}
                      total={stats.total_proxies}
                      color="var(--retro-green)"
                      theme={theme}
                    />
                  )}
                  {stats.summary.pending > 0 && (
                    <ProgressBar
                      label="Pending"
                      value={stats.summary.pending}
                      total={stats.total_proxies}
                      color="var(--retro-yellow)"
                      theme={theme}
                    />
                  )}
                  {stats.summary.failed > 0 && (
                    <ProgressBar
                      label="Failed"
                      value={stats.summary.failed}
                      total={stats.total_proxies}
                      color="var(--retro-pink)"
                      theme={theme}
                    />
                  )}
                </div>
              </div>

              {quality && (
                <div className="retro-border rounded-2xl p-6" style={{
                  backgroundColor: theme === 'dark' ? 'var(--dark-card)' : '#FFFFFF',
                  boxShadow: '6px 6px 0px #000000',
                  border: '3px solid #000000'
                }}>
                  <h2 className="text-2xl font-bold mb-4" style={{
                    fontFamily: "'Bangers', 'Arial Black', sans-serif",
                    color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a'
                  }}>
                    Quality Distribution
                  </h2>

                  <div className="space-y-3">
                    <QualityItem
                      label="Excellent (80-100)"
                      count={quality.excellent}
                      color="var(--retro-purple)"
                      theme={theme}
                    />
                    <QualityItem
                      label="Good (60-79)"
                      count={quality.good}
                      color="var(--retro-blue)"
                      theme={theme}
                    />
                    <QualityItem
                      label="Fair (40-59)"
                      count={quality.fair}
                      color="var(--retro-yellow)"
                      theme={theme}
                    />
                    <QualityItem
                      label="Poor (0-39)"
                      count={quality.poor}
                      color="var(--retro-pink)"
                      theme={theme}
                    />
                  </div>
                </div>
              )}
            </div>

            <div className="retro-border rounded-2xl p-6" style={{
              backgroundColor: theme === 'dark' ? 'var(--dark-card)' : '#FFFFFF',
              boxShadow: '6px 6px 0px #000000',
              border: '3px solid #000000'
            }}>
              <h2 className="text-2xl font-bold mb-4" style={{
                fontFamily: "'Bangers', 'Arial Black', sans-serif",
                color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a'
              }}>
                Detailed Stats
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {Object.entries(stats.by_status).map(([status, data]) => (
                  <div key={status} className="p-4 retro-border rounded-xl" style={{
                    backgroundColor: theme === 'dark' ? 'rgba(255,255,255,0.05)' : '#F9F9F9',
                    border: '2px solid #000000'
                  }}>
                    <div className="text-lg font-bold mb-2 capitalize" style={{
                      fontFamily: "'Press Start 2P', 'Courier New', monospace",
                      color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a',
                      fontSize: '0.875rem'
                    }}>
                      {status}
                    </div>
                    <div className="text-3xl font-bold mb-2" style={{
                      fontFamily: "'Bangers', 'Arial Black', sans-serif",
                      color: 'var(--retro-blue)'
                    }}>
                      {data.count}
                    </div>
                    {data.avg_quality && (
                      <div className="text-sm" style={{
                        fontFamily: "'Press Start 2P', 'Courier New', monospace",
                        color: theme === 'dark' ? 'var(--dark-text-secondary)' : '#6B7280',
                        fontSize: '0.625rem'
                      }}>
                        Quality: {data.avg_quality}/100
                      </div>
                    )}
                    {data.avg_latency && (
                      <div className="text-sm" style={{
                        fontFamily: "'Press Start 2P', 'Courier New', monospace",
                        color: theme === 'dark' ? 'var(--dark-text-secondary)' : '#6B7280',
                        fontSize: '0.625rem'
                      }}>
                        Latency: {Math.round(data.avg_latency)}ms
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-6 text-center">
              <button
                onClick={fetchStats}
                className="px-6 py-3 rounded-xl font-bold retro-button"
                style={{
                  fontFamily: "'Press Start 2P', 'Courier New', monospace",
                  backgroundColor: 'var(--retro-blue)',
                  color: '#FFFFFF',
                  border: '3px solid #000000',
                  boxShadow: '4px 4px 0px #000000',
                  fontSize: '0.75rem'
                }}
              >
                Refresh Stats
              </button>
            </div>
          </>
        )}

        {activeTab === "scraping-sessions" && (
          <ScrapingSessionTab theme={theme} />
        )}

        {activeTab === "scraping-config" && (
          <ScrapingConfigTab theme={theme} />
        )}
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  subtitle,
  color,
  theme,
}: {
  title: string;
  value: number;
  subtitle?: string;
  color: string;
  theme: string;
}) {
  return (
    <div className="retro-border rounded-2xl p-6" style={{
      backgroundColor: theme === 'dark' ? 'var(--dark-card)' : '#FFFFFF',
      boxShadow: '6px 6px 0px #000000',
      border: '3px solid #000000'
    }}>
      <div className="text-sm font-bold mb-2" style={{
        fontFamily: "'Press Start 2P', 'Courier New', monospace",
        color: theme === 'dark' ? 'var(--dark-text-secondary)' : '#6B7280',
        fontSize: '0.625rem'
      }}>
        {title}
      </div>
      <div className="text-4xl font-bold" style={{
        fontFamily: "'Bangers', 'Arial Black', sans-serif",
        color: color
      }}>
        {value.toLocaleString()}
      </div>
      {subtitle && (
        <div className="text-lg font-bold mt-1" style={{
          fontFamily: "'Press Start 2P', 'Courier New', monospace",
          color: color,
          fontSize: '0.75rem'
        }}>
          {subtitle}
        </div>
      )}
    </div>
  );
}

function ProgressBar({
  label,
  value,
  total,
  color,
  theme,
}: {
  label: string;
  value: number;
  total: number;
  color: string;
  theme: string;
}) {
  const percentage = Math.round((value / total) * 100);

  return (
    <div>
      <div className="flex justify-between mb-2">
        <span style={{
          fontFamily: "'Press Start 2P', 'Courier New', monospace",
          color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a',
          fontSize: '0.625rem'
        }}>
          {label}
        </span>
        <span style={{
          fontFamily: "'Press Start 2P', 'Courier New', monospace",
          color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a',
          fontSize: '0.625rem'
        }}>
          {value} ({percentage}%)
        </span>
      </div>
      <div className="w-full h-4 rounded-full retro-border" style={{
        backgroundColor: theme === 'dark' ? 'rgba(255,255,255,0.1)' : '#E5E7EB',
        border: '2px solid #000000'
      }}>
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${percentage}%`,
            backgroundColor: color
          }}
        />
      </div>
    </div>
  );
}

function QualityItem({
  label,
  count,
  color,
  theme,
}: {
  label: string;
  count: number;
  color: string;
  theme: string;
}) {
  return (
    <div className="flex items-center justify-between p-3 retro-border rounded-xl" style={{
      backgroundColor: theme === 'dark' ? 'rgba(255,255,255,0.05)' : '#F9F9F9',
      border: '2px solid #000000'
    }}>
      <span style={{
        fontFamily: "'Press Start 2P', 'Courier New', monospace",
        color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a',
        fontSize: '0.625rem'
      }}>
        {label}
      </span>
      <span className="px-3 py-1 rounded-lg font-bold" style={{
        fontFamily: "'Press Start 2P', 'Courier New', monospace",
        backgroundColor: color,
        color: '#FFFFFF',
        border: '2px solid #000000',
        fontSize: '0.625rem'
      }}>
        {count}
      </span>
    </div>
  );
}
