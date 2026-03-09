import { useState, useEffect } from "react";
import { Plug, RefreshCw, ToggleLeft, ToggleRight, AlertCircle } from "lucide-react";

interface PluginItem {
  name: string;
  display_name: string;
  version: string;
  description: string;
  score_weight: number;
  score_field: string;
  source: string;
}

interface PluginListData {
  plugins: PluginItem[];
  bundled_enabled: boolean;
}

export function PluginsPage() {
  const [data, setData] = useState<PluginListData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toggling, setToggling] = useState(false);

  const fetchPlugins = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/v1/plugins");
      if (!res.ok) throw new Error(`Failed to load plugins (${res.status})`);
      setData(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load plugins");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlugins();
  }, []);

  const handleToggleBundled = async () => {
    setToggling(true);
    try {
      const res = await fetch("/api/v1/plugins/toggle-bundled", { method: "POST" });
      if (!res.ok) throw new Error("Toggle failed");
      await fetchPlugins();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Toggle failed");
    } finally {
      setToggling(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl text-white" style={{ fontWeight: 700 }}>
            Plugins
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Manage analyzer plugins that extend VisionScore
          </p>
        </div>
        <button
          onClick={fetchPlugins}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm bg-white/[0.05] text-gray-300 border border-white/[0.08] hover:bg-white/[0.08] transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 mb-6">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Bundled plugins toggle */}
      <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-5 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-white text-sm" style={{ fontWeight: 600 }}>
              Bundled Plugins
            </h3>
            <p className="text-xs text-gray-500 mt-1">
              Enable built-in plugins that ship with VisionScore (e.g. Instagram Readiness)
            </p>
          </div>
          <button
            onClick={handleToggleBundled}
            disabled={toggling}
            className="flex items-center gap-2 text-sm transition-colors"
          >
            {data?.bundled_enabled ? (
              <ToggleRight className="w-8 h-8 text-emerald-400" />
            ) : (
              <ToggleLeft className="w-8 h-8 text-gray-500" />
            )}
          </button>
        </div>
      </div>

      {/* Plugin directory info */}
      <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-5 mb-6">
        <h3 className="text-white text-sm mb-2" style={{ fontWeight: 600 }}>
          Custom Plugins
        </h3>
        <p className="text-xs text-gray-500">
          Place <code className="text-gray-400 bg-white/[0.05] px-1 py-0.5 rounded">*.py</code> plugin files in{" "}
          <code className="text-gray-400 bg-white/[0.05] px-1 py-0.5 rounded">~/.visionscore/plugins/</code>{" "}
          to load them automatically. Plugins must extend <code className="text-gray-400 bg-white/[0.05] px-1 py-0.5 rounded">BaseAnalyzer</code> and
          define a <code className="text-gray-400 bg-white/[0.05] px-1 py-0.5 rounded">plugin_info</code> attribute.
        </p>
      </div>

      {/* Plugin list */}
      {loading && !data ? (
        <div className="flex items-center justify-center py-16">
          <div className="w-6 h-6 border-2 border-white/20 border-t-white rounded-full animate-spin" />
        </div>
      ) : data && data.plugins.length > 0 ? (
        <div className="space-y-3">
          <h3 className="text-sm text-gray-400" style={{ fontWeight: 500 }}>
            Registered ({data.plugins.length})
          </h3>
          {data.plugins.map((plugin) => (
            <div
              key={plugin.name}
              className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-5"
            >
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-indigo-500/10">
                  <Plug className="w-5 h-5 text-indigo-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h4 className="text-white text-sm" style={{ fontWeight: 600 }}>
                      {plugin.display_name}
                    </h4>
                    <span className="text-xs text-gray-500 bg-white/[0.05] px-2 py-0.5 rounded-full">
                      v{plugin.version}
                    </span>
                    <span className="text-xs text-gray-500 bg-white/[0.05] px-2 py-0.5 rounded-full">
                      {plugin.source}
                    </span>
                  </div>
                  {plugin.description && (
                    <p className="text-xs text-gray-400 mt-1">{plugin.description}</p>
                  )}
                  <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                    <span>
                      Weight: {plugin.score_weight > 0 ? `${(plugin.score_weight * 100).toFixed(0)}%` : "none"}
                    </span>
                    <span>Score field: {plugin.score_field}</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-16 text-gray-500">
          <Plug className="w-10 h-10 mb-3 text-gray-600" />
          <p className="text-sm">No plugins registered</p>
          <p className="text-xs text-gray-600 mt-1">
            Enable bundled plugins or add custom ones to get started
          </p>
        </div>
      )}
    </div>
  );
}
