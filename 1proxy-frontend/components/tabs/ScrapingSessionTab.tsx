'use client';

import { useState, useEffect } from 'react';
import { api, type ScrapingSession, type SessionStatsResponse } from '@/lib/api';

interface ScrapingSessionTabProps {
  theme: string;
}

export function ScrapingSessionTab({ theme }: ScrapingSessionTabProps) {
  const [sessions, setSessions] = useState<ScrapingSession[]>([]);
  const [stats, setStats] = useState<SessionStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedSession, setExpandedSession] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'completed'>('all');

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [statsData] = await Promise.all([
        api.getScrapingStats(),
      ]);
      
      setStats(statsData);
      
      setSessions([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
      console.error('Error fetching scraping data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleStartSession = async () => {
    try {
      const result = await api.startScrapingSession();
      alert(`Session started: ${result.session_id}`);
      fetchData();
    } catch (err) {
      alert(`Failed to start session: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  const handleStopSession = async (sessionId: string) => {
    try {
      await api.stopScrapingSession(sessionId);
      alert('Session stopped');
      fetchData();
    } catch (err) {
      alert(`Failed to stop session: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
  };

  const formatDuration = (seconds: number | null): string => {
    if (seconds === null) return 'N/A';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hours}h ${minutes}m ${secs}s`;
  };

  const filteredSessions = sessions.filter(session => {
    if (statusFilter === 'all') return true;
    if (statusFilter === 'active') return session.end_time === null;
    if (statusFilter === 'completed') return session.end_time !== null;
    return true;
  });

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="text-2xl font-bold" style={{ fontFamily: "'Press Start 2P', monospace" }}>
            LOADING...
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
      {error && (
        <div
          className="retro-border rounded-lg p-4"
          style={{
            backgroundColor: '#FFE5E5',
            border: '3px solid #FF0000',
            boxShadow: '4px 4px 0px #000000',
          }}
        >
          <p className="font-bold text-red-600" style={{ fontFamily: "'Press Start 2P', monospace" }}>
            ERROR: {error}
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats && (
          <>
            <div
              className="retro-border rounded-lg p-6"
              style={{
                backgroundColor: theme === 'dark' ? 'var(--dark-card)' : '#FFFFFF',
                border: '3px solid #000000',
                boxShadow: '4px 4px 0px #000000',
              }}
            >
              <div className="text-xs font-bold uppercase mb-2" style={{ fontFamily: "'Press Start 2P', monospace", color: '#6B7280' }}>
                Total Sessions
              </div>
              <div className="text-3xl font-bold" style={{ fontFamily: "'Press Start 2P', monospace", color: '#FF69B4' }}>
                {stats.total_sessions}
              </div>
            </div>

            <div
              className="retro-border rounded-lg p-6"
              style={{
                backgroundColor: theme === 'dark' ? 'var(--dark-card)' : '#FFFFFF',
                border: '3px solid #000000',
                boxShadow: '4px 4px 0px #000000',
              }}
            >
              <div className="text-xs font-bold uppercase mb-2" style={{ fontFamily: "'Press Start 2P', monospace", color: '#6B7280' }}>
                Active Sessions
              </div>
              <div className="text-3xl font-bold" style={{ fontFamily: "'Press Start 2P', monospace", color: '#6BCB77' }}>
                {stats.active_sessions}
              </div>
            </div>

            <div
              className="retro-border rounded-lg p-6"
              style={{
                backgroundColor: theme === 'dark' ? 'var(--dark-card)' : '#FFFFFF',
                border: '3px solid #000000',
                boxShadow: '4px 4px 0px #000000',
              }}
            >
              <div className="text-xs font-bold uppercase mb-2" style={{ fontFamily: "'Press Start 2P', monospace", color: '#6B7280' }}>
                Success Rate
              </div>
              <div className="text-3xl font-bold" style={{ fontFamily: "'Press Start 2P', monospace", color: '#FFD93D' }}>
                {(stats.success_rate * 100).toFixed(1)}%
              </div>
            </div>

            <div
              className="retro-border rounded-lg p-6"
              style={{
                backgroundColor: theme === 'dark' ? 'var(--dark-card)' : '#FFFFFF',
                border: '3px solid #000000',
                boxShadow: '4px 4px 0px #000000',
              }}
            >
              <div className="text-xs font-bold uppercase mb-2" style={{ fontFamily: "'Press Start 2P', monospace", color: '#6B7280' }}>
                Data Transferred
              </div>
              <div className="text-2xl font-bold" style={{ fontFamily: "'Press Start 2P', monospace", color: '#FF69B4' }}>
                {formatBytes(stats.total_data_bytes)}
              </div>
            </div>
          </>
        )}
      </div>

      <div
        className="retro-border rounded-lg p-6"
        style={{
          backgroundColor: theme === 'dark' ? 'var(--dark-card)' : '#FFFFFF',
          boxShadow: '4px 4px 0px #000000',
        }}
      >
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
          <h2 className="text-xl font-bold" style={{ fontFamily: "'Press Start 2P', monospace" }}>
            Scraping Sessions
          </h2>
          <div className="flex gap-3">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as any)}
              className="px-4 py-2 rounded-lg font-bold outline-none"
              style={{
                backgroundColor: theme === 'dark' ? 'var(--dark-bg)' : '#F0F0F0',
                color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a',
                border: '3px solid #000000',
                fontFamily: "'Press Start 2P', monospace",
                fontSize: '10px',
              }}
            >
              <option value="all">All</option>
              <option value="active">Active</option>
              <option value="completed">Completed</option>
            </select>
            <button
              onClick={handleStartSession}
              className="px-6 py-2 rounded-lg font-bold"
              style={{
                backgroundColor: '#6BCB77',
                color: '#000000',
                border: '3px solid #000000',
                fontFamily: "'Press Start 2P', monospace",
                boxShadow: '4px 4px 0px #000000',
                fontSize: '10px',
              }}
            >
              Start New
            </button>
          </div>
        </div>

        <div className="space-y-3">
          {filteredSessions.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-500" style={{ fontFamily: "'Press Start 2P', monospace", fontSize: '12px' }}>
                No sessions found
              </p>
            </div>
          ) : (
            filteredSessions.map((session) => (
              <div
                key={session.session_id}
                className="retro-border rounded-lg p-4 cursor-pointer hover:bg-opacity-80 transition-all"
                style={{
                  backgroundColor: theme === 'dark' ? 'var(--dark-bg)' : '#F9FAFB',
                  border: '2px solid #000000',
                }}
                onClick={() => setExpandedSession(expandedSession === session.session_id ? null : session.session_id)}
              >
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="font-bold" style={{ fontFamily: "'Press Start 2P', monospace", fontSize: '12px' }}>
                        {session.session_id}
                      </span>
                      <span
                        className="px-2 py-1 rounded text-xs font-bold"
                        style={{
                          backgroundColor: session.end_time === null ? '#6BCB77' : '#6B7280',
                          color: '#000000',
                        }}
                      >
                        {session.end_time === null ? 'ACTIVE' : 'COMPLETED'}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                      <div>
                        <span className="text-gray-500">Requests:</span>{' '}
                        <span className="font-bold">{session.requests_made}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Success:</span>{' '}
                        <span className="font-bold" style={{ color: '#6BCB77' }}>
                          {(session.success_rate * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500">Duration:</span>{' '}
                        <span className="font-bold">{formatDuration(session.duration)}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Proxies:</span>{' '}
                        <span className="font-bold">{session.proxies_tested}</span>
                      </div>
                    </div>
                  </div>
                  {session.end_time === null && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleStopSession(session.session_id);
                      }}
                      className="px-4 py-2 rounded font-bold text-xs"
                      style={{
                        backgroundColor: '#FF6B6B',
                        color: '#000000',
                        border: '2px solid #000000',
                        fontFamily: "'Press Start 2P', monospace",
                      }}
                    >
                      Stop
                    </button>
                  )}
                </div>

                {expandedSession === session.session_id && (
                  <div className="mt-4 pt-4 border-t-2 border-black">
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
                      <div>
                        <div className="text-gray-500 mb-1">Start Time</div>
                        <div className="font-bold">{new Date(session.start_time).toLocaleString()}</div>
                      </div>
                      {session.end_time && (
                        <div>
                          <div className="text-gray-500 mb-1">End Time</div>
                          <div className="font-bold">{new Date(session.end_time).toLocaleString()}</div>
                        </div>
                      )}
                      <div>
                        <div className="text-gray-500 mb-1">Avg Response Time</div>
                        <div className="font-bold">{session.avg_response_time.toFixed(2)}ms</div>
                      </div>
                      <div>
                        <div className="text-gray-500 mb-1">Data Transferred</div>
                        <div className="font-bold">{formatBytes(session.total_data_bytes)}</div>
                      </div>
                      <div>
                        <div className="text-gray-500 mb-1">Successful Requests</div>
                        <div className="font-bold" style={{ color: '#6BCB77' }}>{session.successful_requests}</div>
                      </div>
                      <div>
                        <div className="text-gray-500 mb-1">Failed Requests</div>
                        <div className="font-bold" style={{ color: '#FF6B6B' }}>{session.failed_requests}</div>
                      </div>
                    </div>
                    {session.proxies_used.length > 0 && (
                      <div className="mt-3">
                        <div className="text-gray-500 text-xs mb-2">Proxies Used</div>
                        <div className="flex flex-wrap gap-2">
                          {session.proxies_used.slice(0, 5).map((proxy, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-1 rounded text-xs font-mono"
                              style={{
                                backgroundColor: theme === 'dark' ? 'var(--dark-card)' : '#E5E7EB',
                                border: '1px solid #000000',
                              }}
                            >
                              {proxy}
                            </span>
                          ))}
                          {session.proxies_used.length > 5 && (
                            <span className="text-gray-500 text-xs">
                              +{session.proxies_used.length - 5} more
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
