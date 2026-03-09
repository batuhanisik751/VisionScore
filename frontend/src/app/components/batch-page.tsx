import { useState, useCallback, useRef } from "react";
import { useNavigate } from "react-router";
import {
  FolderOpen,
  Play,
  Download,
  X,
  Image,
  Trophy,
  AlertCircle,
  Eye,
  EyeOff,
  Settings2,
  Loader2,
  ArrowDown,
  ArrowUp,
  Save,
  Check,
} from "lucide-react";
import { ScoreBadge } from "./score-badge";
import { getGradeColor, getGradeBg, getScoreBarClass, type AnalysisReport } from "./mock-data";
import { isAcceptedImage, createPreviewUrl, ACCEPT_ATTR } from "./image-utils";

interface BatchImageResult {
  filename: string;
  report: AnalysisReport | null;
  error: string | null;
  imageUrl: string | null;
}

interface BatchResult {
  total: number;
  successful: number;
  failed: number;
  averageScore: number;
  bestImage: string;
  bestScore: number;
  worstImage: string;
  worstScore: number;
  gradeDistribution: Record<string, number>;
  totalTime: number;
  results: BatchImageResult[];
}

const GRADES = ["S", "A", "B", "C", "D", "F"];

export function BatchPage() {
  const navigate = useNavigate();
  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<Map<string, string>>(new Map());
  const [dragging, setDragging] = useState(false);
  const [skipAI, setSkipAI] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [weights, setWeights] = useState({ technical: 25, aesthetic: 30, composition: 25, ai: 20 });

  const [analyzing, setAnalyzing] = useState(false);
  const [progress, setProgress] = useState({ current: 0, total: 0, filename: "" });
  const [error, setError] = useState<string | null>(null);
  const [batch, setBatch] = useState<BatchResult | null>(null);

  const [sortField, setSortField] = useState<"score" | "name">("score");
  const [sortAsc, setSortAsc] = useState(false);

  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(async (newFiles: FileList | File[]) => {
    const valid = Array.from(newFiles).filter((f) => isAcceptedImage(f));
    if (valid.length === 0) return;

    setFiles((prev) => {
      const existing = new Set(prev.map((f) => f.name));
      const toAdd = valid.filter((f) => !existing.has(f.name));
      return [...prev, ...toAdd];
    });

    const newPreviews = new Map(previews);
    for (const f of valid) {
      if (!newPreviews.has(f.name)) {
        newPreviews.set(f.name, await createPreviewUrl(f));
      }
    }
    setPreviews(newPreviews);
  }, [previews]);

  const removeFile = (name: string) => {
    setFiles((prev) => prev.filter((f) => f.name !== name));
    setPreviews((prev) => {
      const next = new Map(prev);
      const url = next.get(name);
      if (url) URL.revokeObjectURL(url);
      next.delete(name);
      return next;
    });
  };

  const clearAll = () => {
    previews.forEach((url) => URL.revokeObjectURL(url));
    setFiles([]);
    setPreviews(new Map());
    setBatch(null);
    setError(null);
  };

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      if (e.dataTransfer.files.length > 0) handleFiles(e.dataTransfer.files);
    },
    [handleFiles]
  );

  const updateWeight = (key: keyof typeof weights, value: number) => {
    const others = Object.keys(weights).filter((k) => k !== key) as (keyof typeof weights)[];
    const remaining = 100 - value;
    const currentOthersSum = others.reduce((s, k) => s + weights[k], 0);
    const newWeights = { ...weights, [key]: value };
    others.forEach((k) => {
      newWeights[k] =
        currentOthersSum > 0
          ? Math.round((weights[k] / currentOthersSum) * remaining)
          : Math.round(remaining / 3);
    });
    const sum = Object.values(newWeights).reduce((a, b) => a + b, 0);
    if (sum !== 100) newWeights[others[0]] += 100 - sum;
    setWeights(newWeights);
  };

  const handleAnalyze = async () => {
    if (files.length === 0) return;
    setAnalyzing(true);
    setError(null);
    setBatch(null);

    const results: BatchImageResult[] = [];
    const scores: number[] = [];
    const gradeCounts: Record<string, number> = {};
    let bestImage = "",
      bestScore = 0,
      worstImage = "",
      worstScore = 100;
    const startTime = performance.now();

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      setProgress({ current: i + 1, total: files.length, filename: file.name });

      try {
        const formData = new FormData();
        formData.append("file", file);

        const params = new URLSearchParams();
        if (skipAI) params.set("skip_ai", "true");
        params.set(
          "weights",
          `${weights.technical}:${weights.aesthetic}:${weights.composition}:${weights.ai}`
        );

        const res = await fetch(`/api/v1/analyze?${params}`, {
          method: "POST",
          body: formData,
        });

        if (!res.ok) {
          const body = await res.json().catch(() => null);
          throw new Error(body?.detail || `Failed (${res.status})`);
        }

        const data = await res.json();
        const report = data.report as AnalysisReport;
        results.push({
          filename: file.name,
          report,
          error: null,
          imageUrl: previews.get(file.name) || null,
        });

        scores.push(report.overall_score);
        const grade = report.grade;
        gradeCounts[grade] = (gradeCounts[grade] || 0) + 1;

        if (report.overall_score >= bestScore) {
          bestScore = report.overall_score;
          bestImage = file.name;
        }
        if (report.overall_score < worstScore) {
          worstScore = report.overall_score;
          worstImage = file.name;
        }
      } catch (err) {
        results.push({
          filename: file.name,
          report: null,
          error: err instanceof Error ? err.message : "Analysis failed",
          imageUrl: previews.get(file.name) || null,
        });
      }
    }

    const totalTime = (performance.now() - startTime) / 1000;
    const avg = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;

    setBatch({
      total: files.length,
      successful: scores.length,
      failed: results.length - scores.length,
      averageScore: Math.round(avg * 10) / 10,
      bestImage,
      bestScore,
      worstImage,
      worstScore,
      gradeDistribution: gradeCounts,
      totalTime: Math.round(totalTime * 10) / 10,
      results,
    });

    setAnalyzing(false);
  };

  const exportCSV = () => {
    if (!batch) return;

    const headers = [
      "filename",
      "overall_score",
      "grade",
      "technical",
      "aesthetic",
      "composition",
      "ai_feedback",
      "sharpness",
      "exposure",
      "noise",
      "dynamic_range",
      "error",
    ];

    const rows = batch.results.map((r) => {
      if (r.error) return [r.filename, ...Array(headers.length - 2).fill(""), r.error];
      const rp = r.report!;
      return [
        r.filename,
        rp.overall_score,
        rp.grade,
        rp.technical?.overall ?? "",
        rp.aesthetic?.overall ?? "",
        rp.composition?.overall ?? "",
        rp.ai_feedback?.score ?? "",
        rp.technical?.sharpness ?? "",
        rp.technical?.exposure ?? "",
        rp.technical?.noise ?? "",
        rp.technical?.dynamic_range ?? "",
        "",
      ];
    });

    const csv = [headers, ...rows].map((row) => row.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "visionscore-batch.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleSave = async () => {
    if (!batch) return;
    setSaving(true);

    try {
      const reportsMap: Record<string, AnalysisReport> = {};
      batch.results.forEach((r) => {
        if (r.report) reportsMap[r.filename] = r.report;
      });

      const formData = new FormData();
      for (const file of files) {
        if (reportsMap[file.name]) {
          formData.append("files", file);
        }
      }
      formData.append("reports_json", JSON.stringify(reportsMap));

      const res = await fetch("/api/v1/reports/batch", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Save failed (${res.status})`);
      }

      const data = await res.json();
      setSaveSuccess(true);
      setTimeout(() => navigate(`/batch-report/${data.batch_id}`), 600);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
      setSaving(false);
    }
  };

  const sortedResults = batch
    ? [...batch.results].sort((a, b) => {
        if (sortField === "name") {
          return sortAsc
            ? a.filename.localeCompare(b.filename)
            : b.filename.localeCompare(a.filename);
        }
        const sa = a.report?.overall_score ?? -1;
        const sb = b.report?.overall_score ?? -1;
        return sortAsc ? sa - sb : sb - sa;
      })
    : [];

  const toggleSort = (field: "score" | "name") => {
    if (sortField === field) setSortAsc(!sortAsc);
    else {
      setSortField(field);
      setSortAsc(field === "name");
    }
  };

  const SortIcon = sortAsc ? ArrowUp : ArrowDown;

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.05] border border-white/[0.08] text-xs text-gray-400 mb-4">
          <FolderOpen className="w-3 h-3" /> Batch Analysis
        </div>
        <h1 className="text-3xl text-white mb-2" style={{ fontWeight: 700 }}>
          Analyze{" "}
          <span className="bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            multiple images
          </span>
        </h1>
        <p className="text-gray-400 text-sm">
          Upload a set of images for comparative scoring, ranking, and CSV export.
        </p>
      </div>

      {/* Upload + Controls (hidden once results are in) */}
      {!batch && (
        <>
          {/* Drop zone */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all mb-6 ${
              dragging
                ? "border-blue-400 bg-blue-400/[0.05]"
                : "border-white/10 hover:border-white/20 bg-white/[0.02]"
            }`}
          >
            <input
              ref={inputRef}
              type="file"
              accept={ACCEPT_ATTR}
              multiple
              className="hidden"
              onChange={(e) => e.target.files && handleFiles(e.target.files)}
            />
            <div className="flex flex-col items-center gap-3">
              <div className="p-3 rounded-full bg-white/[0.05]">
                <FolderOpen className="w-6 h-6 text-gray-400" />
              </div>
              <div>
                <p className="text-white mb-1">Drop images here or click to browse</p>
                <p className="text-xs text-gray-500">JPEG, PNG, WebP, or HEIC • Max 20MB each • Select multiple</p>
              </div>
            </div>
          </div>

          {/* File list */}
          {files.length > 0 && (
            <div className="mb-6">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm text-gray-400">
                  {files.length} image{files.length !== 1 && "s"} selected
                </span>
                <button
                  onClick={clearAll}
                  className="text-xs text-gray-500 hover:text-red-400 transition-colors"
                >
                  Clear all
                </button>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
                {files.map((f) => (
                  <div
                    key={f.name}
                    className="relative group rounded-xl overflow-hidden border border-white/[0.06] bg-white/[0.02]"
                  >
                    <img
                      src={previews.get(f.name)}
                      alt={f.name}
                      className="w-full h-24 object-cover"
                    />
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        removeFile(f.name);
                      }}
                      className="absolute top-1.5 right-1.5 p-1 rounded-full bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <X className="w-3 h-3 text-white" />
                    </button>
                    <div className="px-2 py-1.5">
                      <p className="text-xs text-gray-400 truncate">{f.name}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Options */}
          <div className="space-y-4 max-w-xl mx-auto">
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
                <button
                  onClick={() => setSkipAI(!skipAI)}
                  className={`w-9 h-5 rounded-full transition-colors relative ${
                    skipAI ? "bg-blue-500" : "bg-white/10"
                  }`}
                >
                  <div
                    className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
                      skipAI ? "left-[18px]" : "left-0.5"
                    }`}
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

            {error && (
              <div className="flex items-center gap-2 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                {error}
              </div>
            )}

            <button
              onClick={handleAnalyze}
              disabled={files.length === 0 || analyzing}
              className={`w-full py-3 rounded-xl transition-all flex items-center justify-center gap-2 ${
                files.length > 0 && !analyzing
                  ? "bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white"
                  : "bg-white/[0.05] text-gray-600 cursor-not-allowed"
              }`}
            >
              {analyzing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Analyzing {progress.current}/{progress.total}...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Analyze {files.length} Image{files.length !== 1 && "s"}
                </>
              )}
            </button>
          </div>

          {/* Progress bar */}
          {analyzing && (
            <div className="max-w-xl mx-auto mt-6">
              <div className="flex items-center justify-between text-sm mb-2">
                <span className="text-gray-400 truncate mr-2">
                  <Image className="w-3.5 h-3.5 inline mr-1" />
                  {progress.filename}
                </span>
                <span className="text-gray-500 tabular-nums shrink-0">
                  {progress.current}/{progress.total}
                </span>
              </div>
              <div className="w-full h-2 bg-white/[0.06] rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full transition-all duration-300"
                  style={{ width: `${(progress.current / progress.total) * 100}%` }}
                />
              </div>
            </div>
          )}
        </>
      )}

      {/* Results */}
      {batch && (
        <div className="space-y-8">
          {/* Summary cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: "Images", value: batch.total, color: "text-white" },
              { label: "Successful", value: batch.successful, color: "text-emerald-400" },
              { label: "Failed", value: batch.failed, color: batch.failed > 0 ? "text-red-400" : "text-gray-500" },
              { label: "Avg Score", value: batch.averageScore.toFixed(1), color: "text-blue-400" },
            ].map((stat) => (
              <div
                key={stat.label}
                className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4 text-center"
              >
                <p className="text-xs text-gray-500 mb-1">{stat.label}</p>
                <p className={`text-2xl tabular-nums ${stat.color}`} style={{ fontWeight: 700 }}>
                  {stat.value}
                </p>
              </div>
            ))}
          </div>

          {/* Best & Worst + Grade Distribution */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Best */}
            {batch.bestImage && (
              <div className="bg-white/[0.03] border border-emerald-500/20 rounded-xl p-4 flex items-center gap-4">
                <div className="shrink-0">
                  <Trophy className="w-8 h-8 text-emerald-400" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs text-emerald-400 mb-0.5">Best Image</p>
                  <p className="text-white text-sm truncate" style={{ fontWeight: 600 }}>
                    {batch.bestImage}
                  </p>
                  <p className="text-emerald-400 text-lg tabular-nums" style={{ fontWeight: 700 }}>
                    {batch.bestScore.toFixed(1)}
                  </p>
                </div>
              </div>
            )}

            {/* Worst */}
            {batch.worstImage && (
              <div className="bg-white/[0.03] border border-red-500/20 rounded-xl p-4 flex items-center gap-4">
                <div className="shrink-0">
                  <AlertCircle className="w-8 h-8 text-red-400" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs text-red-400 mb-0.5">Lowest Score</p>
                  <p className="text-white text-sm truncate" style={{ fontWeight: 600 }}>
                    {batch.worstImage}
                  </p>
                  <p className="text-red-400 text-lg tabular-nums" style={{ fontWeight: 700 }}>
                    {batch.worstScore.toFixed(1)}
                  </p>
                </div>
              </div>
            )}

            {/* Grade distribution */}
            <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4">
              <p className="text-xs text-gray-500 mb-3">Grade Distribution</p>
              <div className="flex items-end justify-between gap-1 h-16">
                {GRADES.map((g) => {
                  const count = batch.gradeDistribution[g] || 0;
                  const max = Math.max(...Object.values(batch.gradeDistribution), 1);
                  const height = count > 0 ? Math.max((count / max) * 100, 15) : 0;
                  return (
                    <div key={g} className="flex flex-col items-center gap-1 flex-1">
                      <span className="text-xs text-gray-400 tabular-nums">{count || ""}</span>
                      <div
                        className={`w-full rounded-t ${getGradeBg(g).split(" ")[0]} transition-all`}
                        style={{ height: `${height}%` }}
                      />
                      <span className={`text-xs font-mono ${getGradeColor(g)}`}>{g}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">
              Completed in {batch.totalTime}s
            </span>
            <div className="flex gap-3">
              <button
                onClick={clearAll}
                className="flex items-center gap-2 px-4 py-2 text-sm text-gray-400 hover:text-white bg-white/[0.03] border border-white/[0.06] rounded-lg transition-colors"
              >
                <FolderOpen className="w-3.5 h-3.5" />
                New Batch
              </button>
              <button
                onClick={handleSave}
                disabled={saving || saveSuccess}
                className={`flex items-center gap-2 px-4 py-2 text-sm rounded-lg transition-all ${
                  saveSuccess
                    ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                    : "text-white bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600"
                }`}
              >
                {saving ? (
                  <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Saving...</>
                ) : saveSuccess ? (
                  <><Check className="w-3.5 h-3.5" /> Saved</>
                ) : (
                  <><Save className="w-3.5 h-3.5" /> Save All</>
                )}
              </button>
              <button
                onClick={exportCSV}
                className="flex items-center gap-2 px-4 py-2 text-sm text-gray-300 bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.06] rounded-lg transition-all"
              >
                <Download className="w-3.5 h-3.5" />
                Export CSV
              </button>
            </div>
          </div>

          {/* Ranking table */}
          <div className="bg-white/[0.02] border border-white/[0.06] rounded-xl overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  <th className="text-left text-xs text-gray-500 px-4 py-3 w-12">#</th>
                  <th className="text-left text-xs text-gray-500 px-4 py-3">
                    <button onClick={() => toggleSort("name")} className="flex items-center gap-1 hover:text-gray-300 transition-colors">
                      Image
                      {sortField === "name" && <SortIcon className="w-3 h-3" />}
                    </button>
                  </th>
                  <th className="text-center text-xs text-gray-500 px-4 py-3">
                    <button onClick={() => toggleSort("score")} className="flex items-center gap-1 hover:text-gray-300 transition-colors mx-auto">
                      Score
                      {sortField === "score" && <SortIcon className="w-3 h-3" />}
                    </button>
                  </th>
                  <th className="text-center text-xs text-gray-500 px-4 py-3">Grade</th>
                  <th className="text-left text-xs text-gray-500 px-4 py-3 hidden sm:table-cell">Bar</th>
                  <th className="text-right text-xs text-gray-500 px-4 py-3 hidden md:table-cell">Technical</th>
                  <th className="text-right text-xs text-gray-500 px-4 py-3 hidden md:table-cell">Aesthetic</th>
                  <th className="text-right text-xs text-gray-500 px-4 py-3 hidden lg:table-cell">Composition</th>
                </tr>
              </thead>
              <tbody>
                {sortedResults.map((item, i) => {
                  if (item.error) {
                    return (
                      <tr key={item.filename} className="border-b border-white/[0.03]">
                        <td className="px-4 py-3 text-sm text-gray-500">{i + 1}</td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-3">
                            {item.imageUrl && (
                              <img
                                src={item.imageUrl}
                                alt=""
                                className="w-10 h-10 rounded object-cover opacity-50"
                              />
                            )}
                            <span className="text-sm text-gray-500">{item.filename}</span>
                          </div>
                        </td>
                        <td colSpan={6} className="px-4 py-3 text-sm text-red-400">
                          <AlertCircle className="w-3.5 h-3.5 inline mr-1" />
                          {item.error}
                        </td>
                      </tr>
                    );
                  }

                  const rp = item.report!;
                  const isBest = item.filename === batch.bestImage;
                  const isWorst = item.filename === batch.worstImage;

                  return (
                    <tr
                      key={item.filename}
                      className={`border-b border-white/[0.03] transition-colors hover:bg-white/[0.02] ${
                        isBest ? "bg-emerald-500/[0.03]" : isWorst ? "bg-red-500/[0.03]" : ""
                      }`}
                    >
                      <td className="px-4 py-3 text-sm text-gray-500 tabular-nums">{i + 1}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          {item.imageUrl && (
                            <img
                              src={item.imageUrl}
                              alt=""
                              className="w-10 h-10 rounded object-cover"
                            />
                          )}
                          <span
                            className={`text-sm truncate ${
                              isBest
                                ? "text-emerald-400 font-semibold"
                                : isWorst
                                ? "text-red-400 font-semibold"
                                : "text-gray-300"
                            }`}
                          >
                            {item.filename}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <ScoreBadge score={rp.overall_score} grade={rp.grade} size="sm" />
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-xs font-mono border ${getGradeBg(
                            rp.grade
                          )} ${getGradeColor(rp.grade)}`}
                        >
                          {rp.grade}
                        </span>
                      </td>
                      <td className="px-4 py-3 hidden sm:table-cell">
                        <div className="w-full h-2 bg-white/[0.06] rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${getScoreBarClass(rp.overall_score)}`}
                            style={{ width: `${rp.overall_score}%` }}
                          />
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right text-sm tabular-nums text-gray-400 hidden md:table-cell">
                        {rp.technical?.overall.toFixed(1) ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-right text-sm tabular-nums text-gray-400 hidden md:table-cell">
                        {rp.aesthetic?.overall.toFixed(1) ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-right text-sm tabular-nums text-gray-400 hidden lg:table-cell">
                        {rp.composition?.overall.toFixed(1) ?? "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
