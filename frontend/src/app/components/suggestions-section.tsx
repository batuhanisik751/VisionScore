import { useState } from "react";
import {
  Lightbulb,
  Crop,
  Sun,
  Palette,
  Contrast,
  Focus,
  RotateCcw,
  LayoutGrid,
  Image as ImageIcon,
  Wand2,
  Loader2,
  Check,
  X,
  Download,
} from "lucide-react";
import type { AnalysisReport } from "./mock-data";

type SuggestionsData = NonNullable<AnalysisReport["suggestions"]>;
type Suggestion = SuggestionsData["suggestions"][number];

const TYPE_CONFIG: Record<
  Suggestion["type"],
  { icon: React.ReactNode; color: string; bg: string; border: string }
> = {
  crop: {
    icon: <Crop className="w-4 h-4" />,
    color: "text-blue-400",
    bg: "bg-blue-500/10",
    border: "border-blue-500/20",
  },
  exposure: {
    icon: <Sun className="w-4 h-4" />,
    color: "text-yellow-400",
    bg: "bg-yellow-500/10",
    border: "border-yellow-500/20",
  },
  color: {
    icon: <Palette className="w-4 h-4" />,
    color: "text-violet-400",
    bg: "bg-violet-500/10",
    border: "border-violet-500/20",
  },
  contrast: {
    icon: <Contrast className="w-4 h-4" />,
    color: "text-orange-400",
    bg: "bg-orange-500/10",
    border: "border-orange-500/20",
  },
  sharpness: {
    icon: <Focus className="w-4 h-4" />,
    color: "text-cyan-400",
    bg: "bg-cyan-500/10",
    border: "border-cyan-500/20",
  },
  horizon: {
    icon: <RotateCcw className="w-4 h-4" />,
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/20",
  },
  composition: {
    icon: <LayoutGrid className="w-4 h-4" />,
    color: "text-pink-400",
    bg: "bg-pink-500/10",
    border: "border-pink-500/20",
  },
};

function PriorityBadge({ priority }: { priority: number }) {
  const color =
    priority <= 2
      ? "bg-red-500/15 text-red-400 border-red-500/25"
      : priority <= 3
      ? "bg-amber-500/15 text-amber-400 border-amber-500/25"
      : "bg-gray-500/15 text-gray-400 border-gray-500/25";
  const label = priority <= 2 ? "High" : priority <= 3 ? "Medium" : "Low";
  return (
    <span className={`px-2 py-0.5 rounded text-[10px] uppercase tracking-wider border ${color}`}>
      {label}
    </span>
  );
}

interface AutoFixResult {
  downloadUrl: string;
  originalUrl: string;
  appliedEdits: { type: string; instruction: string }[];
  skipped: string[];
  editTime: number;
}

interface SuggestionsSectionProps {
  suggestions: SuggestionsData;
  cropPreviewUrl?: string | null;
  imageFile?: File | null;
  originalImageUrl?: string;
}

export function SuggestionsSection({
  suggestions,
  cropPreviewUrl,
  imageFile,
  originalImageUrl,
}: SuggestionsSectionProps) {
  const [autoFixLoading, setAutoFixLoading] = useState(false);
  const [autoFixResult, setAutoFixResult] = useState<AutoFixResult | null>(null);
  const [autoFixError, setAutoFixError] = useState<string | null>(null);

  if (!suggestions.suggestions.length) return null;

  const handleAutoFix = async () => {
    setAutoFixLoading(true);
    setAutoFixError(null);
    setAutoFixResult(null);

    try {
      let fileToSend: File | Blob | null = imageFile || null;

      // If no File object but we have an image URL, fetch it as a blob.
      if (!fileToSend && originalImageUrl) {
        const imgRes = await fetch(originalImageUrl);
        if (!imgRes.ok) throw new Error("Could not fetch original image");
        fileToSend = await imgRes.blob();
      }

      if (!fileToSend) {
        throw new Error("No image available for auto-fix");
      }

      const formData = new FormData();
      const filename = imageFile?.name || originalImageUrl?.split("/").pop() || "image.jpg";
      formData.append("file", fileToSend, filename);

      const res = await fetch("/api/v1/auto-fix?skip_ai=true", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Auto-fix failed (${res.status})`);
      }

      const data = await res.json();
      setAutoFixResult({
        downloadUrl: data.download_url,
        originalUrl: data.original_url,
        appliedEdits: data.applied_edits || [],
        skipped: data.skipped || [],
        editTime: data.edit_time_seconds || 0,
      });
    } catch (err) {
      setAutoFixError(err instanceof Error ? err.message : "Auto-fix failed");
    } finally {
      setAutoFixLoading(false);
    }
  };

  return (
    <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-6 space-y-5">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-amber-500/10">
          <Lightbulb className="w-5 h-5 text-amber-400" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-white">Improvement Suggestions</h3>
          {suggestions.summary && (
            <p className="text-xs text-gray-500 mt-0.5">{suggestions.summary}</p>
          )}
        </div>
        <button
          onClick={handleAutoFix}
          disabled={autoFixLoading || (!imageFile && !originalImageUrl) || !!autoFixResult}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm border transition-colors shrink-0 ${
            autoFixResult
              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
              : "bg-gradient-to-r from-blue-500/20 to-purple-500/20 text-white border-white/10 hover:from-blue-500/30 hover:to-purple-500/30 disabled:opacity-40 disabled:cursor-not-allowed"
          }`}
        >
          {autoFixLoading ? (
            <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Fixing...</>
          ) : autoFixResult ? (
            <><Check className="w-3.5 h-3.5" /> Fixed</>
          ) : (
            <><Wand2 className="w-3.5 h-3.5" /> Auto-Fix</>
          )}
        </button>
      </div>

      {autoFixError && (
        <div className="px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20 text-sm text-red-400">
          {autoFixError}
        </div>
      )}

      <div className="space-y-3">
        {suggestions.suggestions.map((s, i) => {
          const cfg = TYPE_CONFIG[s.type];
          return (
            <div
              key={i}
              className="flex items-start gap-3 p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.04] transition-colors"
            >
              <div className={`p-1.5 rounded-md shrink-0 ${cfg.bg} ${cfg.color}`}>
                {cfg.icon}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-xs font-medium ${cfg.color}`}>
                    {s.type.charAt(0).toUpperCase() + s.type.slice(1)}
                  </span>
                  <PriorityBadge priority={s.priority} />
                </div>
                <p className="text-sm text-gray-300">{s.instruction}</p>
              </div>
              <span className="text-xs text-gray-600 shrink-0">#{i + 1}</span>
            </div>
          );
        })}
      </div>

      {/* Crop preview */}
      {cropPreviewUrl && (
        <div className="space-y-2 pt-2 border-t border-white/[0.06]">
          <div className="flex items-center gap-2">
            <ImageIcon className="w-4 h-4 text-blue-400" />
            <span className="text-sm text-gray-400">Suggested Crop Preview</span>
          </div>
          <div className="rounded-lg overflow-hidden border border-white/[0.06]">
            <img
              src={cropPreviewUrl}
              alt="Suggested crop preview"
              className="w-full h-auto max-h-64 object-contain bg-black/20"
            />
          </div>
        </div>
      )}

      {/* Auto-Fix Result: Before/After */}
      {autoFixResult && autoFixResult.downloadUrl && (
        <div className="space-y-4 pt-4 border-t border-white/[0.06]">
          <h4 className="text-white text-sm font-medium">Auto-Fix Result</h4>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-500 mb-1.5">Before</p>
              <div className="rounded-lg overflow-hidden border border-white/[0.06]">
                <img
                  src={originalImageUrl || autoFixResult.originalUrl}
                  alt="Original"
                  className="w-full h-auto max-h-64 object-contain bg-black/20"
                />
              </div>
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1.5">After</p>
              <div className="rounded-lg overflow-hidden border border-white/[0.06]">
                <img
                  src={autoFixResult.downloadUrl}
                  alt="Auto-fixed"
                  className="w-full h-auto max-h-64 object-contain bg-black/20"
                />
              </div>
            </div>
          </div>

          {/* Applied edits list */}
          <div className="space-y-1.5">
            {autoFixResult.appliedEdits.map((edit, i) => (
              <div key={i} className="flex items-center gap-2 text-xs text-gray-400">
                <Check className="w-3 h-3 text-emerald-400 shrink-0" />
                <span className="text-emerald-400 capitalize">{edit.type}</span>
                <span className="truncate">{edit.instruction}</span>
              </div>
            ))}
            {autoFixResult.skipped.map((s, i) => (
              <div key={i} className="flex items-center gap-2 text-xs text-gray-600">
                <X className="w-3 h-3 shrink-0" />
                <span>{s}</span>
              </div>
            ))}
          </div>

          <div className="flex items-center gap-3">
            <a
              href={autoFixResult.downloadUrl}
              download
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 transition-colors"
            >
              <Download className="w-3.5 h-3.5" /> Download Fixed Image
            </a>
            <span className="text-xs text-gray-600">
              Applied in {autoFixResult.editTime.toFixed(1)}s
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
