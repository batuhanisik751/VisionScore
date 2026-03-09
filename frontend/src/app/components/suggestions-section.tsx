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

interface SuggestionsSectionProps {
  suggestions: SuggestionsData;
  cropPreviewUrl?: string | null;
}

export function SuggestionsSection({ suggestions, cropPreviewUrl }: SuggestionsSectionProps) {
  if (!suggestions.suggestions.length) return null;

  return (
    <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-6 space-y-5">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-amber-500/10">
          <Lightbulb className="w-5 h-5 text-amber-400" />
        </div>
        <div>
          <h3 className="text-white">Improvement Suggestions</h3>
          {suggestions.summary && (
            <p className="text-xs text-gray-500 mt-0.5">{suggestions.summary}</p>
          )}
        </div>
      </div>

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
    </div>
  );
}
