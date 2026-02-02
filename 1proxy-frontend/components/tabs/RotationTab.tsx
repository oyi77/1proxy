import { getFullUrl } from "@/lib/constants";

interface RotationFilters {
  protocol: string;
  country: string;
  anonymity: string;
}

interface RotationTabProps {
  filters: RotationFilters;
  onFilterChange: (filters: RotationFilters) => void;
  theme: string;
  rotationUrl: string;
}

export function RotationTab({
  filters,
  onFilterChange,
  theme,
  rotationUrl,
}: RotationTabProps) {
  return (
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div
            className="retro-border rounded-2xl p-6"
            style={{
              backgroundColor: theme === "dark" ? "var(--dark-card)" : "#FFFFFF",
              boxShadow: "6px 6px 0px #000000",
              border: "3px solid #000000",
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
                    color: theme === "dark" ? "var(--dark-text)" : "#6B7280",
                    fontSize: "0.625rem"
                  }}
                >
                  Country
                </label>
                <select
                  className="w-full px-4 py-2 rounded-lg font-bold outline-none"
                  style={{
                    backgroundColor: theme === "dark" ? "var(--dark-bg)" : "#F0F0F0",
                    color: theme === "dark" ? "var(--dark-text)" : "#1a1a1a",
                    border: "3px solid #000000",
                    fontFamily: "'Press Start 2P', 'Courier New', monospace",
                    fontSize: "0.75rem"
                  }}
                  value={filters.country}
                  onChange={(e) =>
                    onFilterChange({ ...filters, country: e.target.value })
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
                    color: theme === "dark" ? "var(--dark-text)" : "#6B7280",
                    fontSize: "0.625rem"
                  }}
                >
                  Protocol
                </label>
                <select
                  className="w-full px-4 py-2 rounded-lg font-bold outline-none"
                  style={{
                    backgroundColor: theme === "dark" ? "var(--dark-bg)" : "#F0F0F0",
                    color: theme === "dark" ? "var(--dark-text)" : "#1a1a1a",
                    border: "3px solid #000000",
                    fontFamily: "'Press Start 2P', 'Courier New', monospace",
                    fontSize: "0.75rem"
                  }}
                  value={filters.protocol}
                  onChange={(e) =>
                    onFilterChange({ ...filters, protocol: e.target.value })
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
                    color: theme === "dark" ? "var(--dark-text)" : "#6B7280",
                    fontSize: "0.625rem"
                  }}
                >
                  Anonymity
                </label>
                <select
                  className="w-full px-4 py-2 rounded-lg font-bold outline-none"
                  style={{
                    backgroundColor: theme === "dark" ? "var(--dark-bg)" : "#F0F0F0",
                    color: theme === "dark" ? "var(--dark-text)" : "#1a1a1a",
                    border: "3px solid #000000",
                    fontFamily: "'Press Start 2P', 'Courier New', monospace",
                    fontSize: "0.75rem"
                  }}
                  value={filters.anonymity}
                  onChange={(e) =>
                    onFilterChange({ ...filters, anonymity: e.target.value })
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
                {rotationUrl}
              </p>
            </div>
          </div>

          <div
            className="retro-border rounded-2xl p-6"
            style={{
              backgroundColor: theme === "dark" ? "var(--dark-card)" : "#FFFFFF",
              boxShadow: "6px 6px 0px #000000",
              border: "3px solid #000000",
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
                fontSize: "0.75rem",
                lineHeight: "1.5"
              }}
            >
              Download our local rotator script to create a standard HTTP
              proxy on your machine (localhost:8080) that automatically
              rotates IP for every request.
            </p>
            <div className="flex gap-4 mb-4">
              <a
                href={getFullUrl("/rotator.js")}
                download="rotator.js"
                className="retro-button px-6 py-3 font-bold rounded-lg flex items-center gap-2"
                style={{
                  backgroundColor: "var(--retro-purple)",
                  color: "#FFFFFF",
                  fontFamily: "'Press Start 2P', 'Courier New', monospace",
                  border: "3px solid #000000",
                  fontSize: "0.625rem"
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
                Download Rotator Script (Node.js)
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
                node rotator.js --port 8080 --country US
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div
            className="retro-border rounded-xl p-6"
            style={{
              backgroundColor: theme === "dark" ? "var(--dark-card)" : "#FFFFFF",
              boxShadow: "6px 6px 0px #000000",
              border: "3px solid #000000",
            }}
          >
            <h3
              className="font-bold mb-4"
              style={{
                fontFamily: "'Bangers', cursive",
                color: "var(--retro-pink)",
                textShadow: "2px 2px 0px #000000",
                fontSize: "1.5rem"
              }}
            >
              Why use rotation?
            </h3>
            <ul
              className="space-y-4 text-sm"
              style={{
                fontFamily: "'Press Start 2P', 'Courier New', monospace",
                color: theme === "dark" ? "var(--dark-text)" : "#1a1a1a",
                fontSize: "0.625rem",
                lineHeight: "1.6"
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
  );
}
