import { useState, useCallback, useEffect } from "react";
import { Upload, ArrowUp, ArrowDown, Minus, Loader2, X, ChevronDown, Eye, EyeOff, Settings2 } from "lucide-react";
import { ScoreRadarChart } from "./score-radar-chart";
import { ImageOverlay } from "./image-overlay";
import { ScoreBadge } from "./score-badge";
import { getGradeColor, getGradeBg, type AnalysisReport } from "./mock-data";
import { ACCEPT_ATTR } from "./image-utils";

interface CompareSlot {
  report: AnalysisReport | null;
  imageUrl: string | null;
  file: File | null;
  loading: boolean;
  error: string | null;
}

interface SavedRow {
  id: string;
  image_url: string | null;
  overall_score: number;
  grade: string;
  full_report: AnalysisReport;
  created_at: string;
}

const emptySlot: CompareSlot = { report: null, imageUrl: null, file: null, loading: false, error: null };

const ACCEPTED = ACCEPT_ATTR;

export function ComparePage() {
  const [slotA, setSlotA] = useState<CompareSlot>(emptySlot);
  const [slotB, setSlotB] = useState<CompareSlot>(emptySlot);
  const [savedReports, setSavedReports] = useState<SavedRow[]>([]);
  const [showSavedPicker, setShowSavedPicker] = useState<"A" | "B" | null>(null);
  const [skipAI, setSkipAI] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [weights, setWeights] = useState({ technical: 25, aesthetic: 30, composition: 25, ai: 20 });

  const updateWeight = (key: keyof typeof weights, value: number) => {
    const others = Object.keys(weights).filter((k) => k !== key) as (keyof typeof weights)[];
    const remaining = 100 - value;
    const currentOthersSum = others.reduce((s, k) => s + weights[k], 0);
    const newWeights = { ...weights, [key]: value };
    others.forEach((k) => {
      newWeights[k] = currentOthersSum > 0 ? Math.round((weights[k] / currentOthersSum) * remaining) : Math.round(remaining / 3);
    });
    const sum = Object.values(newWeights).reduce((a, b) => a + b, 0);
    if (sum !== 100) newWeights[others[0]] += 100 - sum;
    setWeights(newWeights);
  };

  // Fetch saved reports for the picker
  useEffect(() => {
    fetch("/api/v1/reports?limit=50")
      .then(async (res) => {
        if (!res.ok) return;
        const data = await res.json();
        setSavedReports(data.reports || []);
      })
      .catch(() => {});
  }, []);

  const analyzeFile = useCallback(async (file: File, setSlot: (s: CompareSlot) => void) => {
    const imageUrl = URL.createObjectURL(file);
    setSlot({ report: null, imageUrl, file, loading: true, error: null });

    try {
      const formData = new FormData();
      formData.append("file", file);

      const params = new URLSearchParams();
      if (skipAI) params.set("skip_ai", "true");
      params.set("weights", `${weights.technical}:${weights.aesthetic}:${weights.composition}:${weights.ai}`);

      const res = await fetch(`/api/v1/analyze?${params}`, { method: "POST", body: formData });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Analysis failed (${res.status})`);
      }
      const data = await res.json();
      setSlot({ report: { ...data.report, image_url: imageUrl }, imageUrl, file, loading: false, error: null });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Analysis failed";
      setSlot({ report: null, imageUrl, file, loading: false, error: msg });
    }
  }, [skipAI, weights]);

  const handleDrop = useCallback((e: React.DragEvent, setSlot: (s: CompareSlot) => void) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) analyzeFile(file, setSlot);
  }, [analyzeFile]);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>, setSlot: (s: CompareSlot) => void) => {
    const file = e.target.files?.[0];
    if (file) analyzeFile(file, setSlot);
    e.target.value = "";
  }, [analyzeFile]);

  const selectSavedReport = useCallback((row: SavedRow, slot: "A" | "B") => {
    const report: AnalysisReport = {
      ...row.full_report,
      id: row.id,
      image_url: row.image_url || "",
    };
    const slotData: CompareSlot = { report, imageUrl: row.image_url, file: null, loading: false, error: null };
    if (slot === "A") setSlotA(slotData);
    else setSlotB(slotData);
    setShowSavedPicker(null);
  }, []);

  const bothReady = slotA.report && slotB.report;

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <h1 className="text-xl text-white mb-6" style={{ fontWeight: 700 }}>Compare Images</h1>

      {/* Analysis settings */}
      <div className="mb-6 max-w-xl space-y-3">
        <div className="flex items-center justify-between">
          <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
            <button
              onClick={() => setSkipAI(!skipAI)}
              className={`w-9 h-5 rounded-full transition-colors relative ${skipAI ? "bg-blue-500" : "bg-white/10"}`}
            >
              <div
                className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${skipAI ? "left-[18px]" : "left-0.5"}`}
              />
            </button>
            {skipAI ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            Skip AI Feedback
          </label>
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-300 transition-colors"
          >
            <Settings2 className="w-3.5 h-3.5" />
            Weights
          </button>
        </div>

        {showAdvanced && (
          <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4 space-y-3">
            {(
              [
                { key: "technical" as const, label: "Technical" },
                { key: "aesthetic" as const, label: "Aesthetic" },
                { key: "composition" as const, label: "Composition" },
                { key: "ai" as const, label: "AI Feedback" },
              ] as const
            ).map(({ key, label }) => (
              <div key={key}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-400">{label}</span>
                  <span className="text-gray-300 tabular-nums">{weights[key]}%</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={weights[key]}
                  onChange={(e) => updateWeight(key, Number(e.target.value))}
                  className="w-full accent-blue-500 h-1"
                />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Upload zones */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <UploadSlot
          label="Image A"
          slot={slotA}
          setSlot={setSlotA}
          onDrop={(e) => handleDrop(e, setSlotA)}
          onFileChange={(e) => handleFileChange(e, setSlotA)}
          onPickSaved={() => setShowSavedPicker("A")}
          onClear={() => setSlotA(emptySlot)}
          accentColor="blue"
        />
        <UploadSlot
          label="Image B"
          slot={slotB}
          setSlot={setSlotB}
          onDrop={(e) => handleDrop(e, setSlotB)}
          onFileChange={(e) => handleFileChange(e, setSlotB)}
          onPickSaved={() => setShowSavedPicker("B")}
          onClear={() => setSlotB(emptySlot)}
          accentColor="purple"
        />
      </div>

      {/* Comparison results */}
      {bothReady && (
        <div className="space-y-6">
          {/* Dual radar chart */}
          <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-6">
            <h3 className="text-white text-sm mb-2">Score Comparison</h3>
            <ScoreRadarChart
              technical={slotA.report!.technical?.overall ?? null}
              aesthetic={slotA.report!.aesthetic?.overall ?? null}
              composition={slotA.report!.composition?.overall ?? null}
              aiFeedback={slotA.report!.ai_feedback?.score ?? null}
              compareTechnical={slotB.report!.technical?.overall ?? null}
              compareAesthetic={slotB.report!.aesthetic?.overall ?? null}
              compareComposition={slotB.report!.composition?.overall ?? null}
              compareAiFeedback={slotB.report!.ai_feedback?.score ?? null}
              labelA="Image A"
              labelB="Image B"
            />
          </div>

          {/* Score comparison table */}
          <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  <th className="text-left text-xs text-gray-500 px-4 py-3">Category</th>
                  <th className="text-center text-xs text-blue-400 px-4 py-3">Image A</th>
                  <th className="text-center text-xs text-purple-400 px-4 py-3">Image B</th>
                  <th className="text-center text-xs text-gray-500 px-4 py-3">Diff</th>
                </tr>
              </thead>
              <tbody>
                <CompareRow label="Overall" a={slotA.report!.overall_score} b={slotB.report!.overall_score} bold />
                <CompareRow label="Technical" a={slotA.report!.technical?.overall} b={slotB.report!.technical?.overall} />
                <CompareRow label="  Sharpness" a={slotA.report!.technical?.sharpness} b={slotB.report!.technical?.sharpness} sub />
                <CompareRow label="  Exposure" a={slotA.report!.technical?.exposure} b={slotB.report!.technical?.exposure} sub />
                <CompareRow label="  Noise" a={slotA.report!.technical?.noise} b={slotB.report!.technical?.noise} sub />
                <CompareRow label="  Dynamic Range" a={slotA.report!.technical?.dynamic_range} b={slotB.report!.technical?.dynamic_range} sub />
                <CompareRow label="Aesthetic" a={slotA.report!.aesthetic?.overall} b={slotB.report!.aesthetic?.overall} />
                <CompareRow label="Composition" a={slotA.report!.composition?.overall} b={slotB.report!.composition?.overall} />
                <CompareRow label="  Rule of Thirds" a={slotA.report!.composition?.rule_of_thirds} b={slotB.report!.composition?.rule_of_thirds} sub />
                <CompareRow label="  Subject Position" a={slotA.report!.composition?.subject_position} b={slotB.report!.composition?.subject_position} sub />
                <CompareRow label="  Horizon" a={slotA.report!.composition?.horizon} b={slotB.report!.composition?.horizon} sub />
                <CompareRow label="  Balance" a={slotA.report!.composition?.balance} b={slotB.report!.composition?.balance} sub />
                <CompareRow label="AI Feedback" a={slotA.report!.ai_feedback?.score} b={slotB.report!.ai_feedback?.score} />
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Saved report picker modal */}
      {showSavedPicker && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 px-4">
          <div className="bg-gray-900 border border-white/10 rounded-2xl p-6 max-w-md w-full max-h-[70vh] flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-white text-sm" style={{ fontWeight: 600 }}>Select a saved report</h3>
              <button onClick={() => setShowSavedPicker(null)} className="text-gray-500 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="overflow-y-auto space-y-2 flex-1">
              {savedReports.length === 0 && (
                <p className="text-sm text-gray-500 text-center py-8">No saved reports found</p>
              )}
              {savedReports.map((row) => (
                <button
                  key={row.id}
                  onClick={() => selectSavedReport(row, showSavedPicker)}
                  className="w-full flex items-center gap-3 p-3 rounded-lg bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.06] transition-colors text-left"
                >
                  {row.image_url && (
                    <img src={row.image_url} alt="" className="w-10 h-10 rounded object-cover shrink-0" />
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-gray-300 truncate">{row.full_report.image_meta.path}</p>
                    <p className="text-xs text-gray-500">{new Date(row.created_at).toLocaleDateString()}</p>
                  </div>
                  <span className={`text-sm font-mono px-2 py-0.5 rounded border ${getGradeBg(row.grade)} ${getGradeColor(row.grade)}`}>
                    {row.overall_score.toFixed(1)}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// --- Sub-components ---

interface UploadSlotProps {
  label: string;
  slot: CompareSlot;
  setSlot: (s: CompareSlot) => void;
  onDrop: (e: React.DragEvent) => void;
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onPickSaved: () => void;
  onClear: () => void;
  accentColor: "blue" | "purple";
}

function UploadSlot({ label, slot, onDrop, onFileChange, onPickSaved, onClear, accentColor }: UploadSlotProps) {
  const [dragging, setDragging] = useState(false);
  const borderColor = accentColor === "blue" ? "border-blue-500/30" : "border-purple-500/30";
  const textColor = accentColor === "blue" ? "text-blue-400" : "text-purple-400";

  if (slot.loading) {
    return (
      <div className={`rounded-xl border ${borderColor} bg-white/[0.03] p-8 flex flex-col items-center justify-center min-h-[220px]`}>
        <Loader2 className={`w-8 h-8 ${textColor} animate-spin mb-3`} />
        <p className="text-sm text-gray-400">Analyzing {label}...</p>
      </div>
    );
  }

  if (slot.error) {
    return (
      <div className="rounded-xl border border-red-500/20 bg-red-500/[0.03] p-6 min-h-[220px]">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs text-red-400">{label}</span>
          <button onClick={onClear} className="text-gray-500 hover:text-white"><X className="w-4 h-4" /></button>
        </div>
        <p className="text-sm text-red-400">{slot.error}</p>
      </div>
    );
  }

  if (slot.report) {
    return (
      <div className={`rounded-xl border ${borderColor} bg-white/[0.03] overflow-hidden`}>
        <div className="flex items-center justify-between px-4 py-2 border-b border-white/[0.06]">
          <span className={`text-xs ${textColor}`} style={{ fontWeight: 600 }}>{label}</span>
          <button onClick={onClear} className="text-gray-500 hover:text-white"><X className="w-3.5 h-3.5" /></button>
        </div>
        <ImageOverlay
          src={slot.report.image_url}
          alt={slot.report.image_meta.path}
          composition={slot.report.composition}
        />
        <div className="p-4 flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-300 truncate">{slot.report.image_meta.path}</p>
            <span className={`inline-block mt-1 text-xs px-2 py-0.5 rounded border ${getGradeBg(slot.report.grade)} ${getGradeColor(slot.report.grade)}`}>
              Grade {slot.report.grade}
            </span>
          </div>
          <ScoreBadge score={slot.report.overall_score} grade={slot.report.grade} size="sm" />
        </div>
      </div>
    );
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => { setDragging(false); onDrop(e); }}
      className={`rounded-xl border-2 border-dashed p-8 flex flex-col items-center justify-center min-h-[220px] transition-all ${
        dragging
          ? `${borderColor} bg-white/[0.04]`
          : "border-white/[0.08] bg-white/[0.02] hover:border-white/[0.15]"
      }`}
    >
      <Upload className={`w-8 h-8 ${dragging ? textColor : "text-gray-600"} mb-3`} />
      <p className="text-sm text-gray-400 mb-1">{label}</p>
      <p className="text-xs text-gray-600 mb-4">Drag & drop or click to upload</p>
      <div className="flex gap-2">
        <label className={`px-4 py-2 rounded-lg text-sm cursor-pointer border transition-colors ${
          accentColor === "blue"
            ? "bg-blue-500/10 text-blue-400 border-blue-500/20 hover:bg-blue-500/20"
            : "bg-purple-500/10 text-purple-400 border-purple-500/20 hover:bg-purple-500/20"
        }`}>
          Browse
          <input type="file" accept={ACCEPTED} className="hidden" onChange={(e) => onFileChange(e)} />
        </label>
        <button
          onClick={onPickSaved}
          className="flex items-center gap-1 px-4 py-2 rounded-lg text-sm bg-white/[0.05] text-gray-400 border border-white/[0.08] hover:bg-white/[0.08] transition-colors"
        >
          <ChevronDown className="w-3 h-3" /> Saved
        </button>
      </div>
    </div>
  );
}

interface CompareRowProps {
  label: string;
  a: number | undefined | null;
  b: number | undefined | null;
  bold?: boolean;
  sub?: boolean;
}

function CompareRow({ label, a, b, bold, sub }: CompareRowProps) {
  const aVal = a ?? null;
  const bVal = b ?? null;
  const diff = aVal != null && bVal != null ? bVal - aVal : null;

  return (
    <tr className={`border-b border-white/[0.03] ${bold ? "bg-white/[0.02]" : ""}`}>
      <td className={`px-4 py-2.5 text-sm ${sub ? "text-gray-500 pl-8" : bold ? "text-white font-semibold" : "text-gray-300"}`}>
        {label}
      </td>
      <td className="px-4 py-2.5 text-center text-sm tabular-nums text-blue-400">
        {aVal != null ? aVal.toFixed(1) : "—"}
      </td>
      <td className="px-4 py-2.5 text-center text-sm tabular-nums text-purple-400">
        {bVal != null ? bVal.toFixed(1) : "—"}
      </td>
      <td className="px-4 py-2.5 text-center">
        {diff != null ? (
          <span className={`inline-flex items-center gap-0.5 text-xs tabular-nums ${
            Math.abs(diff) < 0.5 ? "text-gray-500" : diff > 0 ? "text-emerald-400" : "text-red-400"
          }`}>
            {Math.abs(diff) < 0.5 ? (
              <Minus className="w-3 h-3" />
            ) : diff > 0 ? (
              <ArrowUp className="w-3 h-3" />
            ) : (
              <ArrowDown className="w-3 h-3" />
            )}
            {Math.abs(diff).toFixed(1)}
          </span>
        ) : (
          <span className="text-xs text-gray-600">—</span>
        )}
      </td>
    </tr>
  );
}
