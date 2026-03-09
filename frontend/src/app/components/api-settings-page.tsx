import { useState, useEffect, useCallback } from "react";
import {
  Key,
  Webhook,
  Copy,
  Trash2,
  AlertCircle,
  CheckCircle2,
  Send,
  Plus,
  Shield,
} from "lucide-react";

interface ApiKeyInfo {
  id: string;
  name: string;
  key_prefix: string;
  is_active: boolean;
  rate_limit_per_minute: number;
  created_at: string;
  last_used_at: string | null;
}

interface WebhookInfo {
  id: string;
  url: string;
  events: string[];
  is_active: boolean;
  created_at: string;
  last_triggered_at: string | null;
  failure_count: number;
}

type Tab = "keys" | "webhooks";

export function ApiSettingsPage() {
  const [tab, setTab] = useState<Tab>("keys");
  const [error, setError] = useState("");

  // API Keys state
  const [keys, setKeys] = useState<ApiKeyInfo[]>([]);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyRpm, setNewKeyRpm] = useState(60);
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [loadingKeys, setLoadingKeys] = useState(true);

  // Webhooks state
  const [webhooks, setWebhooks] = useState<WebhookInfo[]>([]);
  const [newWebhookUrl, setNewWebhookUrl] = useState("");
  const [newWebhookEvents, setNewWebhookEvents] = useState<string[]>([
    "analysis.completed",
    "batch.completed",
  ]);
  const [newWebhookSecret, setNewWebhookSecret] = useState("");
  const [loadingWebhooks, setLoadingWebhooks] = useState(true);

  const fetchKeys = useCallback(async () => {
    setLoadingKeys(true);
    try {
      const res = await fetch("/api/v1/api-keys");
      if (res.ok) {
        const data = await res.json();
        setKeys(data.keys);
      }
    } catch {
      // Supabase may not be configured
    } finally {
      setLoadingKeys(false);
    }
  }, []);

  const fetchWebhooks = useCallback(async () => {
    setLoadingWebhooks(true);
    try {
      const res = await fetch("/api/v1/webhooks");
      if (res.ok) {
        const data = await res.json();
        setWebhooks(data.webhooks);
      }
    } catch {
      // Supabase may not be configured
    } finally {
      setLoadingWebhooks(false);
    }
  }, []);

  useEffect(() => {
    fetchKeys();
    fetchWebhooks();
  }, [fetchKeys, fetchWebhooks]);

  const createKey = async () => {
    if (!newKeyName.trim()) return;
    setError("");
    try {
      const res = await fetch("/api/v1/api-keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newKeyName,
          rate_limit_per_minute: newKeyRpm,
        }),
      });
      if (!res.ok) {
        const data = await res.json();
        setError(data.detail || "Failed to create API key");
        return;
      }
      const data = await res.json();
      setCreatedKey(data.key);
      setNewKeyName("");
      fetchKeys();
    } catch {
      setError("Failed to create API key");
    }
  };

  const revokeKey = async (keyId: string) => {
    setError("");
    try {
      const res = await fetch(`/api/v1/api-keys/${keyId}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const data = await res.json();
        setError(data.detail || "Failed to revoke key");
        return;
      }
      fetchKeys();
    } catch {
      setError("Failed to revoke key");
    }
  };

  const copyKey = async () => {
    if (createdKey) {
      await navigator.clipboard.writeText(createdKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const createWebhook = async () => {
    if (!newWebhookUrl.trim()) return;
    setError("");
    try {
      const body: Record<string, unknown> = {
        url: newWebhookUrl,
        events: newWebhookEvents,
      };
      if (newWebhookSecret) body.secret = newWebhookSecret;

      const res = await fetch("/api/v1/webhooks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const data = await res.json();
        setError(data.detail || "Failed to create webhook");
        return;
      }
      setNewWebhookUrl("");
      setNewWebhookSecret("");
      fetchWebhooks();
    } catch {
      setError("Failed to create webhook");
    }
  };

  const deleteWebhook = async (webhookId: string) => {
    setError("");
    try {
      const res = await fetch(`/api/v1/webhooks/${webhookId}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const data = await res.json();
        setError(data.detail || "Failed to delete webhook");
        return;
      }
      fetchWebhooks();
    } catch {
      setError("Failed to delete webhook");
    }
  };

  const testWebhook = async (webhookId: string) => {
    setError("");
    try {
      const res = await fetch(`/api/v1/webhooks/${webhookId}/test`, {
        method: "POST",
      });
      if (!res.ok) {
        const data = await res.json();
        setError(data.detail || "Test ping failed");
      }
    } catch {
      setError("Test ping failed");
    }
  };

  const toggleEvent = (event: string) => {
    setNewWebhookEvents((prev) =>
      prev.includes(event)
        ? prev.filter((e) => e !== event)
        : [...prev, event]
    );
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2.5 bg-indigo-500/10 rounded-xl">
          <Shield className="w-6 h-6 text-indigo-400" />
        </div>
        <div>
          <h1 className="text-2xl text-white" style={{ fontWeight: 700 }}>
            API Settings
          </h1>
          <p className="text-sm text-gray-500">
            Manage API keys, webhooks, and rate limits
          </p>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex items-center gap-2 text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 mb-6">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span className="text-sm">{error}</span>
        </div>
      )}

      {/* Created key banner */}
      {createdKey && (
        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg px-4 py-3 mb-6">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span className="text-sm text-emerald-400" style={{ fontWeight: 600 }}>
              API Key Created
            </span>
          </div>
          <p className="text-xs text-gray-400 mb-2">
            Copy this key now. It won't be shown again.
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 text-sm text-gray-200 bg-white/[0.05] px-3 py-2 rounded font-mono">
              {createdKey}
            </code>
            <button
              onClick={copyKey}
              className="px-3 py-2 rounded-lg text-sm bg-white/[0.05] text-gray-300 border border-white/[0.08] hover:bg-white/[0.08] transition-colors flex items-center gap-1.5"
            >
              {copied ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
          <button
            onClick={() => setCreatedKey(null)}
            className="text-xs text-gray-500 hover:text-gray-400 mt-2"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Tab switcher */}
      <div className="flex gap-1 bg-white/[0.03] border border-white/[0.06] rounded-lg p-1 mb-6">
        <button
          onClick={() => setTab("keys")}
          className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-md text-sm transition-colors ${
            tab === "keys"
              ? "bg-white/[0.08] text-white"
              : "text-gray-500 hover:text-gray-300"
          }`}
          style={{ fontWeight: tab === "keys" ? 600 : 400 }}
        >
          <Key className="w-4 h-4" />
          API Keys
        </button>
        <button
          onClick={() => setTab("webhooks")}
          className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-md text-sm transition-colors ${
            tab === "webhooks"
              ? "bg-white/[0.08] text-white"
              : "text-gray-500 hover:text-gray-300"
          }`}
          style={{ fontWeight: tab === "webhooks" ? 600 : 400 }}
        >
          <Webhook className="w-4 h-4" />
          Webhooks
        </button>
      </div>

      {/* API Keys Tab */}
      {tab === "keys" && (
        <div className="space-y-4">
          {/* Create form */}
          <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-5">
            <h3 className="text-white text-sm mb-4" style={{ fontWeight: 600 }}>
              Generate New API Key
            </h3>
            <div className="flex gap-3">
              <input
                type="text"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                placeholder="Key name (e.g. Mobile App)"
                className="flex-1 bg-white/[0.05] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-white/[0.15]"
              />
              <input
                type="number"
                value={newKeyRpm}
                onChange={(e) =>
                  setNewKeyRpm(Math.max(1, parseInt(e.target.value) || 60))
                }
                className="w-24 bg-white/[0.05] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-white/[0.15]"
                title="Rate limit (req/min)"
              />
              <button
                onClick={createKey}
                disabled={!newKeyName.trim()}
                className="px-4 py-2 rounded-lg text-sm bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-500/30 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5"
              >
                <Plus className="w-3.5 h-3.5" />
                Generate
              </button>
            </div>
            <p className="text-xs text-gray-600 mt-2">
              Rate limit: requests per minute per key
            </p>
          </div>

          {/* Keys list */}
          {loadingKeys ? (
            <div className="flex justify-center py-12">
              <div className="w-6 h-6 border-2 border-white/20 border-t-white rounded-full animate-spin" />
            </div>
          ) : keys.length === 0 ? (
            <div className="flex flex-col items-center py-12 text-gray-600">
              <Key className="w-10 h-10 mb-3" />
              <p className="text-sm">No API keys yet</p>
            </div>
          ) : (
            <div className="space-y-2">
              {keys.map((k) => (
                <div
                  key={k.id}
                  className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4 flex items-center gap-4"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className="text-sm text-white truncate"
                        style={{ fontWeight: 500 }}
                      >
                        {k.name}
                      </span>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full ${
                          k.is_active
                            ? "text-emerald-400 bg-emerald-500/10"
                            : "text-red-400 bg-red-500/10"
                        }`}
                      >
                        {k.is_active ? "Active" : "Revoked"}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-gray-500">
                      <code className="bg-white/[0.05] px-1.5 py-0.5 rounded">
                        {k.key_prefix}...
                      </code>
                      <span>{k.rate_limit_per_minute} req/min</span>
                      <span>
                        Created{" "}
                        {new Date(k.created_at).toLocaleDateString()}
                      </span>
                      {k.last_used_at && (
                        <span>
                          Last used{" "}
                          {new Date(k.last_used_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>
                  {k.is_active && (
                    <button
                      onClick={() => revokeKey(k.id)}
                      className="px-3 py-1.5 rounded-lg text-xs text-red-400 bg-red-500/10 border border-red-500/20 hover:bg-red-500/20 transition-colors flex items-center gap-1.5"
                    >
                      <Trash2 className="w-3 h-3" />
                      Revoke
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Webhooks Tab */}
      {tab === "webhooks" && (
        <div className="space-y-4">
          {/* Create form */}
          <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-5">
            <h3 className="text-white text-sm mb-4" style={{ fontWeight: 600 }}>
              Register New Webhook
            </h3>
            <div className="space-y-3">
              <input
                type="url"
                value={newWebhookUrl}
                onChange={(e) => setNewWebhookUrl(e.target.value)}
                placeholder="https://example.com/webhook"
                className="w-full bg-white/[0.05] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-white/[0.15]"
              />
              <div className="flex gap-3">
                <div className="flex-1">
                  <p className="text-xs text-gray-500 mb-2">Events</p>
                  <div className="flex gap-2">
                    {["analysis.completed", "batch.completed"].map((event) => (
                      <button
                        key={event}
                        onClick={() => toggleEvent(event)}
                        className={`px-3 py-1.5 rounded-lg text-xs border transition-colors ${
                          newWebhookEvents.includes(event)
                            ? "bg-indigo-500/20 text-indigo-300 border-indigo-500/30"
                            : "bg-white/[0.03] text-gray-500 border-white/[0.08] hover:text-gray-400"
                        }`}
                      >
                        {event}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="flex-1">
                  <p className="text-xs text-gray-500 mb-2">
                    Secret (optional, for HMAC)
                  </p>
                  <input
                    type="text"
                    value={newWebhookSecret}
                    onChange={(e) => setNewWebhookSecret(e.target.value)}
                    placeholder="HMAC signing secret"
                    className="w-full bg-white/[0.05] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-white/[0.15]"
                  />
                </div>
              </div>
              <button
                onClick={createWebhook}
                disabled={!newWebhookUrl.trim() || newWebhookEvents.length === 0}
                className="px-4 py-2 rounded-lg text-sm bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-500/30 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5"
              >
                <Plus className="w-3.5 h-3.5" />
                Register
              </button>
            </div>
          </div>

          {/* Webhooks list */}
          {loadingWebhooks ? (
            <div className="flex justify-center py-12">
              <div className="w-6 h-6 border-2 border-white/20 border-t-white rounded-full animate-spin" />
            </div>
          ) : webhooks.length === 0 ? (
            <div className="flex flex-col items-center py-12 text-gray-600">
              <Webhook className="w-10 h-10 mb-3" />
              <p className="text-sm">No webhooks registered</p>
            </div>
          ) : (
            <div className="space-y-2">
              {webhooks.map((wh) => (
                <div
                  key={wh.id}
                  className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4"
                >
                  <div className="flex items-start gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <code
                          className="text-sm text-gray-200 truncate block"
                          style={{ fontWeight: 500 }}
                        >
                          {wh.url}
                        </code>
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${
                            wh.is_active
                              ? "text-emerald-400 bg-emerald-500/10"
                              : "text-red-400 bg-red-500/10"
                          }`}
                        >
                          {wh.is_active ? "Active" : "Inactive"}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mt-2 flex-wrap">
                        {wh.events.map((ev) => (
                          <span
                            key={ev}
                            className="text-xs text-gray-500 bg-white/[0.05] px-2 py-0.5 rounded-full"
                          >
                            {ev}
                          </span>
                        ))}
                        {wh.failure_count > 0 && (
                          <span className="text-xs text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full">
                            {wh.failure_count} failures
                          </span>
                        )}
                        <span className="text-xs text-gray-600">
                          Created{" "}
                          {new Date(wh.created_at).toLocaleDateString()}
                        </span>
                        {wh.last_triggered_at && (
                          <span className="text-xs text-gray-600">
                            Last fired{" "}
                            {new Date(
                              wh.last_triggered_at
                            ).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-2 shrink-0">
                      <button
                        onClick={() => testWebhook(wh.id)}
                        className="px-3 py-1.5 rounded-lg text-xs text-gray-300 bg-white/[0.05] border border-white/[0.08] hover:bg-white/[0.08] transition-colors flex items-center gap-1.5"
                      >
                        <Send className="w-3 h-3" />
                        Test
                      </button>
                      <button
                        onClick={() => deleteWebhook(wh.id)}
                        className="px-3 py-1.5 rounded-lg text-xs text-red-400 bg-red-500/10 border border-red-500/20 hover:bg-red-500/20 transition-colors flex items-center gap-1.5"
                      >
                        <Trash2 className="w-3 h-3" />
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
