import { type Stats } from "@/lib/api";

interface HomeTabProps {
  stats: Stats | null;
  theme: string;
  onNavigate: (tab: string) => void;
}

export function HomeTab({ stats, theme, onNavigate }: HomeTabProps) {
  return (
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
              onClick={() => onNavigate("rotation")}
              className="retro-button px-4 py-2 font-bold rounded-lg text-xs"
              style={{
                backgroundColor: "#FFFFFF",
                color: "var(--retro-purple)",
                fontFamily: "'Press Start 2P', 'Courier New', monospace",
              }}
            >
              Use Proxy Rotator
            </button>
            <button
              onClick={() => onNavigate("list")}
              className="retro-button px-4 py-2 font-semibold rounded-lg text-xs"
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
        <StatCard
          title="Total Proxies"
          value={stats?.total_proxies || 0}
          color="var(--retro-blue)"
          theme={theme}
        />
        <StatCard
          title="HTTP Proxies"
          value={stats?.by_protocol.http || 0}
          color="#10B981"
          theme={theme}
        />
        <StatCard
          title="SOCKS/VMess"
          value={(stats?.by_protocol.vmess || 0) + (stats?.by_protocol.shadowsocks || 0)}
          color="var(--retro-orange)"
          theme={theme}
        />
      </div>
    </div>
  );
}

function StatCard({ title, value, color, theme }: { title: string; value: number; color: string; theme: string }) {
  return (
    <div
      className="retro-border rounded-xl p-6"
      style={{
        backgroundColor: theme === "dark" ? "var(--dark-card)" : "#FFFFFF",
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
        {title}
      </h3>
      <p
        className="text-4xl font-bold mt-2"
        style={{
          fontFamily: "'Bangers', cursive",
          color: color,
          textShadow: "2px 2px 0px #000000",
        }}
      >
        {value.toLocaleString()}
      </p>
    </div>
  );
}
