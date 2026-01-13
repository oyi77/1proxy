"use client";

import { useState } from "react";
import Image from "next/image";
import { type Proxy } from "@/lib/api";
import { useTheme } from "@/app/theme-provider";

interface ProxyTableProps {
  proxies: Proxy[];
  loading: boolean;
  total: number;
  limit: number;
  currentPage: number;
  onPageChange: (page: number) => void;
}

export function ProxyTable({
  proxies,
  loading,
  total,
  limit,
  currentPage,
  onPageChange,
}: ProxyTableProps) {
  const { theme } = useTheme();
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const copyToClipboard = async (text: string, id: number) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  const getLatencyColor = (ms?: number) => {
    if (!ms) return "#9CA3AF";
    if (ms < 100) return "#10B981";
    if (ms < 300) return "#FBBF24";
    return "#EF4444";
  };

  const getAnonymityColor = (anonymity?: string) => {
    if (!anonymity) return "var(--retro-gray)";
    const lower = anonymity.toLowerCase();
    if (lower === "elite") return "var(--retro-purple)";
    if (lower === "anonymous") return "var(--retro-blue)";
    return "var(--retro-orange)";
  };

  if (loading) {
    return (
      <div className="retro-border rounded-2xl p-12 flex items-center justify-center" style={{
        backgroundColor: theme === 'dark' ? 'var(--dark-card)' : '#FFFFFF',
        boxShadow: '6px 6px 0px #000000'
      }}>
        <div className="text-center">
          <div className="w-8 h-8 border-3 border-current border-t-transparent rounded-full animate-spin mx-auto mb-4" style={{
            color: 'var(--retro-blue)'
          }}></div>
          <p style={{
            fontFamily: "'Press Start 2P', 'Courier New', monospace",
            color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a'
          }}>
            Loading proxies...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="retro-border rounded-2xl overflow-hidden" style={{
      backgroundColor: theme === 'dark' ? 'var(--dark-card)' : '#FFFFFF',
      boxShadow: '6px 6px 0px #000000',
      border: '3px solid #000000'
    }}>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead style={{
            backgroundColor: theme === 'dark' ? 'rgba(255,255,255,0.1)' : '#F0F0F0',
            borderBottom: '3px solid #000000'
          }}>
            <tr>
              <th className="px-4 py-3 text-left font-bold" style={{
                fontFamily: "'Press Start 2P', 'Courier New', monospace",
                color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a'
              }}>
                IP:Port
              </th>
              <th className="px-4 py-3 text-left font-bold" style={{
                fontFamily: "'Press Start 2P', 'Courier New', monospace",
                color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a'
              }}>
                Protocol
              </th>
              <th className="px-4 py-3 text-left font-bold" style={{
                fontFamily: "'Press Start 2P', 'Courier New', monospace",
                color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a'
              }}>
                Country
              </th>
              <th className="px-4 py-3 text-left font-bold" style={{
                fontFamily: "'Press Start 2P', 'Courier New', monospace",
                color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a'
              }}>
                Anonymity
              </th>
              <th className="px-4 py-3 text-left font-bold" style={{
                fontFamily: "'Press Start 2P', 'Courier New', monospace",
                color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a'
              }}>
                Latency
              </th>
              <th className="px-4 py-3 text-left font-bold" style={{
                fontFamily: "'Press Start 2P', 'Courier New', monospace",
                color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a'
              }}>
                Quality
              </th>
              <th className="px-4 py-3 text-right font-bold" style={{
                fontFamily: "'Press Start 2P', 'Courier New', monospace",
                color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a'
              }}>
                Action
              </th>
            </tr>
          </thead>
          <tbody>
            {proxies.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-12 text-center" style={{
                  color: theme === 'dark' ? 'var(--dark-text)' : '#6B7280',
                  fontFamily: "'Press Start 2P', 'Courier New', monospace"
                }}>
                  No proxies found matching your criteria.
                </td>
              </tr>
            ) : (
              proxies.map((proxy, idx) => (
                <tr
                  key={proxy.id}
                  style={{
                    borderBottom: '2px solid #000000',
                    backgroundColor: idx % 2 === 0 ? 'transparent' : (theme === 'dark' ? 'rgba(255,255,255,0.05)' : '#F9F9F9')
                  }}
                >
                  <td className="px-4 py-3 font-mono" style={{
                    color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a',
                    fontFamily: "'Press Start 2P', 'Courier New', monospace"
                  }}>
                    {proxy.ip && proxy.port ? `${proxy.ip}:${proxy.port}` : proxy.url}
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-1 rounded font-bold text-xs" style={{
                      backgroundColor: 'var(--retro-blue)',
                      color: '#FFFFFF',
                      fontFamily: "'Press Start 2P', 'Courier New', monospace",
                      border: '2px solid #000000'
                    }}>
                      {proxy.protocol.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {proxy.country_code ? (
                      <div className="flex items-center gap-2">
                        <Image
                          src={`https://flagcdn.com/20x15/${proxy.country_code.toLowerCase()}.png`}
                          alt={proxy.country_name || proxy.country_code}
                          width={20}
                          height={15}
                          className="w-5 h-auto shadow-sm"
                        />
                        <span className="truncate max-w-[100px]" title={proxy.country_name} style={{
                          color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a',
                          fontFamily: "'Press Start 2P', 'Courier New', monospace"
                        }}>
                          {proxy.country_code}
                        </span>
                      </div>
                    ) : (
                      <span style={{
                        color: '#9CA3AF',
                        fontFamily: "'Press Start 2P', 'Courier New', monospace"
                      }}>
                        -
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {proxy.anonymity ? (
                      <span className="px-2 py-1 rounded font-bold text-xs" style={{
                        backgroundColor: getAnonymityColor(proxy.anonymity),
                        color: '#FFFFFF',
                        fontFamily: "'Press Start 2P', 'Courier New', monospace",
                        border: '2px solid #000000'
                      }}>
                        {proxy.anonymity}
                      </span>
                    ) : (
                      <span style={{
                        color: '#9CA3AF',
                        fontFamily: "'Press Start 2P', 'Courier New', monospace"
                      }}>
                        -
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono font-bold" style={{
                    color: getLatencyColor(proxy.latency_ms),
                    fontFamily: "'Press Start 2P', 'Courier New', monospace"
                  }}>
                    {proxy.latency_ms ? `${proxy.latency_ms}ms` : "-"}
                  </td>
                  <td className="px-4 py-3">
                    {proxy.quality_score !== undefined ? (
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-2 rounded-full border-2 border-black overflow-hidden" style={{
                          backgroundColor: theme === 'dark' ? 'rgba(255,255,255,0.1)' : '#D1D5DB'
                        }}>
                          <div
                            style={{
                              height: '100%',
                              width: `${proxy.quality_score}%`,
                              backgroundColor: proxy.quality_score >= 80
                                ? '#10B981'
                                : proxy.quality_score >= 50
                                ? '#FBBF24'
                                : '#EF4444'
                            }}
                          />
                        </div>
                        <span className="text-xs font-bold" style={{
                          color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a',
                          fontFamily: "'Press Start 2P', 'Courier New', monospace"
                        }}>
                          {proxy.quality_score}%
                        </span>
                      </div>
                    ) : (
                      <span style={{
                        color: '#9CA3AF',
                        fontFamily: "'Press Start 2P', 'Courier New', monospace"
                      }}>
                        -
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => copyToClipboard(proxy.url, proxy.id)}
                      className="px-3 py-1.5 rounded font-bold text-xs transition-all"
                      style={{
                        backgroundColor: copiedId === proxy.id ? '#10B981' : 'var(--retro-pink)',
                        color: '#FFFFFF',
                        fontFamily: "'Press Start 2P', 'Courier New', monospace",
                        border: '2px solid #000000'
                      }}
                    >
                      {copiedId === proxy.id ? "✓" : "Copy"}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="px-4 py-3" style={{
        backgroundColor: theme === 'dark' ? 'rgba(255,255,255,0.05)' : '#F9F9F9',
        borderTop: '3px solid #000000',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        <span style={{
          fontFamily: "'Press Start 2P', 'Courier New', monospace",
          color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a',
          fontSize: '0.75rem'
        }}>
          Showing <span className="font-bold">{Math.min(currentPage * limit + 1, total)}</span>-<span className="font-bold">{Math.min((currentPage + 1) * limit, total)}</span> of <span className="font-bold">{total}</span>
        </span>
        <div className="flex gap-2">
          <button
            onClick={() => onPageChange(Math.max(0, currentPage - 1))}
            disabled={currentPage === 0}
            className="px-3 py-1.5 rounded font-bold text-sm transition-all"
            style={{
              backgroundColor: currentPage === 0 ? '#D1D5DB' : 'var(--retro-blue)',
              color: '#FFFFFF',
              fontFamily: "'Press Start 2P', 'Courier New', monospace",
              border: '2px solid #000000',
              cursor: currentPage === 0 ? 'not-allowed' : 'pointer',
              opacity: currentPage === 0 ? 0.5 : 1
            }}
          >
            ← Prev
          </button>
          <button
            onClick={() => onPageChange(currentPage + 1)}
            disabled={(currentPage + 1) * limit >= total}
            className="px-3 py-1.5 rounded font-bold text-sm transition-all"
            style={{
              backgroundColor: (currentPage + 1) * limit >= total ? '#D1D5DB' : 'var(--retro-blue)',
              color: '#FFFFFF',
              fontFamily: "'Press Start 2P', 'Courier New', monospace",
              border: '2px solid #000000',
              cursor: (currentPage + 1) * limit >= total ? 'not-allowed' : 'pointer',
              opacity: (currentPage + 1) * limit >= total ? 0.5 : 1
            }}
          >
            Next →
          </button>
        </div>
      </div>
    </div>
  );
}
