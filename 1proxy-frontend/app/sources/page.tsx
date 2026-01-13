"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useTheme } from "@/app/theme-provider";
import { api, type Source, type ScrapeAllResult } from "@/lib/api";

export default function SourcesPage() {
  const { theme } = useTheme();
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [scraping, setScraping] = useState(false);
  const [results, setResults] = useState<ScrapeAllResult[]>([]);

  useEffect(() => {
    loadSources();
  }, []);

  const loadSources = async () => {
    try {
      const data = await api.getSources();
      setSources(data.sources);
    } catch (error) {
      console.error("Error loading sources:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleScrapeAll = async () => {
    setScraping(true);
    setResults([]);
    try {
      const result = await api.scrapeAllSources();
      setResults(result.results);
      alert(
        `Scrape completed!\n\nTotal scraped: ${result.total_scraped}\nTotal added: ${result.total_added}\nTotal stored: ${result.total_stored}`
      );
    } catch (error) {
      console.error("Error scraping:", error);
      alert("Failed to scrape sources");
    } finally {
      setScraping(false);
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
          Loading sources...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-4 md:p-8" style={{
      backgroundColor: theme === 'dark' ? 'var(--dark-bg)' : 'var(--light-bg)'
    }}>
      <div className="max-w-7xl mx-auto">
        <header className="mb-8">
          <h1 className="text-4xl md:text-5xl font-bold mb-2" style={{
            fontFamily: "'Bangers', cursive",
            color: 'var(--retro-pink)',
            textShadow: '4px 4px 0px #000000'
          }}>
            Proxy Sources
          </h1>
          <p className="text-lg" style={{
            fontFamily: "'Press Start 2P', 'Courier New', monospace",
            color: theme === 'dark' ? 'var(--dark-text)' : 'var(--light-text)'
          }}>
            Auto-updated GitHub repositories with fresh proxies
          </p>
        </header>

        <div className="retro-border rounded-2xl p-6 md:p-8 mb-8" style={{
          backgroundColor: theme === 'dark' ? 'var(--dark-card)' : '#FFFFFF',
          boxShadow: '6px 6px 0px #000000'
        }}>
          <div className="flex flex-col md:flex-row md:justify-between md:items-center gap-4 mb-6">
            <div>
              <h2 className="text-2xl font-bold mb-2" style={{
                fontFamily: "'Bangers', cursive",
                color: 'var(--retro-blue)',
                textShadow: '2px 2px 0px #000000'
              }}>
                {sources.filter((s) => s.enabled).length} Active Sources
              </h2>
              <p className="text-sm" style={{
                fontFamily: "'Press Start 2P', 'Courier New', monospace",
                color: theme === 'dark' ? 'var(--dark-text)' : '#6B7280'
              }}>
                {sources.length} total sources configured
              </p>
            </div>
            <button
              onClick={handleScrapeAll}
              disabled={scraping}
              className="retro-button px-6 py-3 rounded-lg font-bold"
              style={{
                backgroundColor: 'var(--retro-blue)',
                color: '#FFFFFF',
                fontFamily: "'Press Start 2P', 'Courier New', monospace",
                border: '3px solid #000000',
                boxShadow: '4px 4px 0px #000000',
                opacity: scraping ? 0.5 : 1,
                cursor: scraping ? 'not-allowed' : 'pointer'
              }}
            >
              {scraping ? "Scraping..." : "Scrape All"}
            </button>
          </div>

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
                    Status
                  </th>
                  <th className="text-left py-4 px-4 font-bold" style={{
                    fontFamily: "'Press Start 2P', 'Courier New', monospace",
                    color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a'
                  }}>
                    Repository
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
                    Last Result
                  </th>
                </tr>
              </thead>
              <tbody>
                {sources.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-8 text-center" style={{
                      fontFamily: "'Press Start 2P', 'Courier New', monospace",
                      color: theme === 'dark' ? 'var(--dark-text)' : '#6B7280'
                    }}>
                      No sources found
                    </td>
                  </tr>
                ) : (
                  sources.map((source, idx) => {
                    const repoMatch = source.url.match(
                      /github\.com\/([^/]+\/[^/]+)/
                    );
                    const repoName = repoMatch ? repoMatch[1] : source.url;
                    const result = results.find((r) => r.url === source.url);

                    return (
                      <tr
                        key={idx}
                        style={{
                          borderBottom: '2px solid #000000',
                          backgroundColor: idx % 2 === 0 ? (theme === 'dark' ? 'var(--dark-card)' : '#FFFFFF') : (theme === 'dark' ? 'rgba(255,255,255,0.05)' : '#F9F9F9')
                        }}
                      >
                        <td className="py-4 px-4">
                          {source.enabled ? (
                            <span className="px-3 py-1 rounded font-bold text-sm" style={{
                              backgroundColor: 'var(--retro-blue)',
                              color: '#FFFFFF',
                              fontFamily: "'Press Start 2P', 'Courier New', monospace",
                              border: '2px solid #000000'
                            }}>
                              Active
                            </span>
                          ) : (
                            <span className="px-3 py-1 rounded font-bold text-sm" style={{
                              backgroundColor: theme === 'dark' ? '#4B5563' : '#D1D5DB',
                              color: theme === 'dark' ? '#FFFFFF' : '#1a1a1a',
                              fontFamily: "'Press Start 2P', 'Courier New', monospace",
                              border: '2px solid #000000'
                            }}>
                              Off
                            </span>
                          )}
                        </td>
                        <td className="py-4 px-4">
                          <a
                            href={`https://github.com/${repoName.split("/raw/")[0]}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="font-mono text-sm hover:underline"
                            style={{
                              color: 'var(--retro-pink)',
                              fontFamily: "'Press Start 2P', 'Courier New', monospace"
                            }}
                          >
                            {repoName.split("/raw/")[0]}
                          </a>
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
                        <td className="py-4 px-4">
                          {result ? (
                            result.status === "success" ? (
                              <span style={{ color: '#10B981', fontFamily: "'Press Start 2P', 'Courier New', monospace" }}>
                                ✓ {result.scraped} scraped, {result.added} added
                              </span>
                            ) : (
                              <span style={{ color: '#EF4444', fontFamily: "'Press Start 2P', 'Courier New', monospace" }}>
                                ✗ {result.error}
                              </span>
                            )
                          ) : (
                            <span style={{ color: '#9CA3AF', fontFamily: "'Press Start 2P', 'Courier New', monospace" }}>—</span>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <Link
            href="/"
            className="retro-button px-6 py-3 rounded-lg font-bold inline-block"
            style={{
              backgroundColor: theme === 'dark' ? 'var(--dark-bg)' : '#F0F0F0',
              color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a',
              fontFamily: "'Press Start 2P', 'Courier New', monospace",
              border: '3px solid #000000',
              boxShadow: '4px 4px 0px #000000'
            }}
          >
            ← Back to Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
