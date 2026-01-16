'use client';

import { useState, useEffect } from 'react';
import { api, type ScrapingConfig } from '@/lib/api';

interface ScrapingConfigTabProps {
  theme: string;
}

export function ScrapingConfigTab({ theme }: ScrapingConfigTabProps) {
  const [config, setConfig] = useState<ScrapingConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [expandedModule, setExpandedModule] = useState<string | null>(null);
  const [editingModule, setEditingModule] = useState<string | null>(null);
  const [editValues, setEditValues] = useState<Record<string, any>>({});

  const fetchConfig = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getScrapingConfig();
      setConfig(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch config');
      console.error('Error fetching scraping config:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  const handleEditModule = (moduleName: string, currentConfig: Record<string, any>) => {
    setEditingModule(moduleName);
    setEditValues(currentConfig);
  };

  const handleSaveModule = async (moduleName: string) => {
    try {
      setSaving(true);
      await api.updateScrapingConfig(moduleName, editValues);
      alert('Configuration updated successfully');
      setEditingModule(null);
      fetchConfig();
    } catch (err) {
      alert(`Failed to update config: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setSaving(false);
    }
  };

  const handleCancelEdit = () => {
    setEditingModule(null);
    setEditValues({});
  };

  const renderConfigValue = (key: string, value: any) => {
    if (typeof value === 'boolean') {
      return value ? 'Enabled' : 'Disabled';
    }
    if (typeof value === 'number') {
      return value.toString();
    }
    if (typeof value === 'string') {
      return value;
    }
    if (Array.isArray(value)) {
      return `[${value.length} items]`;
    }
    if (typeof value === 'object' && value !== null) {
      return `{${Object.keys(value).length} keys}`;
    }
    return String(value);
  };

  const renderEditInput = (key: string, value: any) => {
    const inputStyle = {
      backgroundColor: theme === 'dark' ? 'var(--dark-bg)' : '#F9FAFB',
      color: theme === 'dark' ? 'var(--dark-text)' : '#1a1a1a',
      border: '2px solid #000000',
      fontFamily: "'Courier New', monospace",
      fontSize: '12px',
    };

    if (typeof value === 'boolean') {
      return (
        <select
          value={editValues[key] ? 'true' : 'false'}
          onChange={(e) => setEditValues({ ...editValues, [key]: e.target.value === 'true' })}
          className="px-3 py-2 rounded outline-none w-full"
          style={inputStyle}
        >
          <option value="true">Enabled</option>
          <option value="false">Disabled</option>
        </select>
      );
    }

    if (typeof value === 'number') {
      return (
        <input
          type="number"
          value={editValues[key] || value}
          onChange={(e) => setEditValues({ ...editValues, [key]: parseFloat(e.target.value) })}
          className="px-3 py-2 rounded outline-none w-full"
          style={inputStyle}
        />
      );
    }

    return (
      <input
        type="text"
        value={editValues[key] || value}
        onChange={(e) => setEditValues({ ...editValues, [key]: e.target.value })}
        className="px-3 py-2 rounded outline-none w-full"
        style={inputStyle}
      />
    );
  };

  if (loading) {
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

  if (error || !config) {
    return (
      <div
        className="retro-border rounded-lg p-6"
        style={{
          backgroundColor: '#FFE5E5',
          border: '3px solid #FF0000',
          boxShadow: '4px 4px 0px #000000',
        }}
      >
        <p className="font-bold text-red-600" style={{ fontFamily: "'Press Start 2P', monospace" }}>
          ERROR: {error || 'No config data'}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div
        className="retro-border rounded-lg p-6"
        style={{
          backgroundColor: theme === 'dark' ? 'var(--dark-card)' : '#FFFFFF',
          boxShadow: '4px 4px 0px #000000',
        }}
      >
        <h2 className="text-xl font-bold mb-4" style={{ fontFamily: "'Press Start 2P', monospace" }}>
          Global Configuration
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(config.global_config).map(([key, value]) => (
            <div
              key={key}
              className="p-4 rounded"
              style={{
                backgroundColor: theme === 'dark' ? 'var(--dark-bg)' : '#F9FAFB',
                border: '2px solid #000000',
              }}
            >
              <div className="text-xs text-gray-500 mb-1 uppercase" style={{ fontFamily: "'Press Start 2P', monospace" }}>
                {key.replace(/_/g, ' ')}
              </div>
              <div className="font-bold" style={{ fontFamily: "'Courier New', monospace" }}>
                {renderConfigValue(key, value)}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div
        className="retro-border rounded-lg p-6"
        style={{
          backgroundColor: theme === 'dark' ? 'var(--dark-card)' : '#FFFFFF',
          boxShadow: '4px 4px 0px #000000',
        }}
      >
        <h2 className="text-xl font-bold mb-4" style={{ fontFamily: "'Press Start 2P', monospace" }}>
          Rate Limiter Status
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(config.rate_limiter_status).map(([key, value]) => (
            <div
              key={key}
              className="p-4 rounded"
              style={{
                backgroundColor: theme === 'dark' ? 'var(--dark-bg)' : '#F9FAFB',
                border: '2px solid #000000',
              }}
            >
              <div className="text-xs text-gray-500 mb-1 uppercase" style={{ fontFamily: "'Press Start 2P', monospace" }}>
                {key.replace(/_/g, ' ')}
              </div>
              <div className="font-bold text-lg" style={{ fontFamily: "'Press Start 2P', monospace", color: '#FF69B4' }}>
                {renderConfigValue(key, value)}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div
        className="retro-border rounded-lg p-6"
        style={{
          backgroundColor: theme === 'dark' ? 'var(--dark-card)' : '#FFFFFF',
          boxShadow: '4px 4px 0px #000000',
        }}
      >
        <h2 className="text-xl font-bold mb-4" style={{ fontFamily: "'Press Start 2P', monospace" }}>
          Performance Statistics
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(config.performance_stats).map(([key, value]) => (
            <div
              key={key}
              className="p-4 rounded"
              style={{
                backgroundColor: theme === 'dark' ? 'var(--dark-bg)' : '#F9FAFB',
                border: '2px solid #000000',
              }}
            >
              <div className="text-xs text-gray-500 mb-1 uppercase" style={{ fontFamily: "'Press Start 2P', monospace" }}>
                {key.replace(/_/g, ' ')}
              </div>
              <div className="font-bold text-lg" style={{ fontFamily: "'Press Start 2P', monospace", color: '#6BCB77' }}>
                {renderConfigValue(key, value)}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div
        className="retro-border rounded-lg p-6"
        style={{
          backgroundColor: theme === 'dark' ? 'var(--dark-card)' : '#FFFFFF',
          boxShadow: '4px 4px 0px #000000',
        }}
      >
        <h2 className="text-xl font-bold mb-6" style={{ fontFamily: "'Press Start 2P', monospace" }}>
          Module Configurations
        </h2>
        <div className="space-y-4">
          {Object.entries(config.module_configs).map(([moduleName, moduleConfig]) => (
            <div
              key={moduleName}
              className="retro-border rounded-lg overflow-hidden"
              style={{
                backgroundColor: theme === 'dark' ? 'var(--dark-bg)' : '#F9FAFB',
                border: '2px solid #000000',
              }}
            >
              <div
                className="p-4 cursor-pointer hover:bg-opacity-80 transition-all flex justify-between items-center"
                onClick={() => setExpandedModule(expandedModule === moduleName ? null : moduleName)}
                style={{
                  backgroundColor: theme === 'dark' ? 'var(--dark-card)' : '#FFFFFF',
                }}
              >
                <h3 className="font-bold" style={{ fontFamily: "'Press Start 2P', monospace", fontSize: '14px' }}>
                  {moduleName.replace(/_/g, ' ').toUpperCase()}
                </h3>
                <div className="flex items-center gap-3">
                  {editingModule !== moduleName && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleEditModule(moduleName, moduleConfig as Record<string, any>);
                      }}
                      className="px-4 py-2 rounded font-bold text-xs"
                      style={{
                        backgroundColor: '#FFD93D',
                        color: '#000000',
                        border: '2px solid #000000',
                        fontFamily: "'Press Start 2P', monospace",
                      }}
                    >
                      Edit
                    </button>
                  )}
                  <span className="text-xl font-bold">
                    {expandedModule === moduleName ? '▼' : '▶'}
                  </span>
                </div>
              </div>

              {expandedModule === moduleName && (
                <div className="p-4 border-t-2 border-black">
                  {editingModule === moduleName ? (
                    <div className="space-y-4">
                      {Object.entries(editValues).map(([key, value]) => (
                        <div key={key}>
                          <label className="block text-xs font-bold mb-2 uppercase" style={{ fontFamily: "'Press Start 2P', monospace" }}>
                            {key.replace(/_/g, ' ')}
                          </label>
                          {renderEditInput(key, value)}
                        </div>
                      ))}
                      <div className="flex gap-3 mt-6">
                        <button
                          onClick={() => handleSaveModule(moduleName)}
                          disabled={saving}
                          className="px-6 py-3 rounded font-bold"
                          style={{
                            backgroundColor: '#6BCB77',
                            color: '#000000',
                            border: '3px solid #000000',
                            fontFamily: "'Press Start 2P', monospace",
                            boxShadow: '4px 4px 0px #000000',
                            opacity: saving ? 0.5 : 1,
                          }}
                        >
                          {saving ? 'Saving...' : 'Save'}
                        </button>
                        <button
                          onClick={handleCancelEdit}
                          disabled={saving}
                          className="px-6 py-3 rounded font-bold"
                          style={{
                            backgroundColor: '#FF6B6B',
                            color: '#000000',
                            border: '3px solid #000000',
                            fontFamily: "'Press Start 2P', monospace",
                            boxShadow: '4px 4px 0px #000000',
                          }}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {Object.entries(moduleConfig as Record<string, any>).map(([key, value]) => (
                        <div key={key} className="flex justify-between items-center p-2">
                          <span className="text-xs text-gray-500" style={{ fontFamily: "'Press Start 2P', monospace" }}>
                            {key.replace(/_/g, ' ')}:
                          </span>
                          <span className="font-bold ml-2" style={{ fontFamily: "'Courier New', monospace" }}>
                            {renderConfigValue(key, value)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <div
        className="retro-border rounded-lg p-6"
        style={{
          backgroundColor: theme === 'dark' ? 'var(--dark-card)' : '#FFFFFF',
          boxShadow: '4px 4px 0px #000000',
        }}
      >
        <h2 className="text-xl font-bold mb-4" style={{ fontFamily: "'Press Start 2P', monospace" }}>
          Active Sessions
        </h2>
        {config.active_sessions.length === 0 ? (
          <p className="text-gray-500 text-center py-4" style={{ fontFamily: "'Press Start 2P', monospace", fontSize: '12px' }}>
            No active sessions
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {config.active_sessions.map((session, idx) => (
              <div
                key={idx}
                className="p-4 rounded"
                style={{
                  backgroundColor: theme === 'dark' ? 'var(--dark-bg)' : '#F9FAFB',
                  border: '2px solid #000000',
                }}
              >
                <div className="font-bold mb-2" style={{ fontFamily: "'Press Start 2P', monospace", fontSize: '10px' }}>
                  {typeof session === 'string' ? session : JSON.stringify(session)}
                </div>
                <div
                  className="px-2 py-1 rounded text-xs font-bold inline-block"
                  style={{
                    backgroundColor: '#6BCB77',
                    color: '#000000',
                  }}
                >
                  ACTIVE
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
