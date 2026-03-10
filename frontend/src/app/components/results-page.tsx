import { useParams, useNavigate, useLocation } from "react-router";
import { ScoreBadge } from "./score-badge";
import { CategoryCard } from "./category-card";
import { FeedbackSection } from "./feedback-section";
import { SuggestionsSection } from "./suggestions-section";
import { MetadataPanel } from "./metadata-panel";
import { MOCK_REPORTS, getGradeBg, getGradeColor, type AnalysisReport } from "./mock-data";
import {
  Aperture,
  Palette,
  Grid3x3,
  Sparkles,
  Download,
  Save,
  ArrowLeft,
  Clock,
  Trash2,
  Plug,
  AlertTriangle,
} from "lucide-react";
import { useState, useEffect } from "react";
import { jsPDF } from "jspdf";
import { Loader2, Check, X } from "lucide-react";
import { ScoreRadarChart } from "./score-radar-chart";
import { ImageOverlay } from "./image-overlay";

interface ResultsPageProps {
  saved?: boolean;
}

export function ResultsPage({ saved }: ResultsPageProps) {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  const state = location.state as { report?: AnalysisReport; warnings?: string[]; imageUrl?: string; file?: File; batchId?: string } | null;

  const [fetchedReport, setFetchedReport] = useState<AnalysisReport | null>(null);
  const [fetchLoading, setFetchLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    if (saved && id && !state?.report) {
      setFetchLoading(true);
      fetch(`/api/v1/reports/${id}`)
        .then(async (res) => {
          if (!res.ok) throw new Error(`Failed to load report (${res.status})`);
          const row = await res.json();
          setFetchedReport({
            ...row.full_report,
            id: row.id,
            image_url: row.image_url || row.full_report.image_url || "",
            timestamp: row.created_at,
          });
        })
        .catch((err) => setFetchError(err instanceof Error ? err.message : "Failed to load report"))
        .finally(() => setFetchLoading(false));
    }
  }, [saved, id, state?.report]);

  const report: AnalysisReport | undefined = state?.report
    ? { ...state.report, id: "live", image_url: state.imageUrl || "" }
    : fetchedReport || MOCK_REPORTS.find((r) => r.id === id) || undefined;

  const warnings = state?.warnings ?? [];
  const [showWarnings, setShowWarnings] = useState(true);

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  if (fetchLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-gray-500 animate-spin mb-4" />
        <p className="text-sm text-gray-500">Loading report...</p>
      </div>
    );
  }

  if (fetchError) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          {fetchError}
        </div>
      </div>
    );
  }

  if (!report) return null;

  const handleDelete = async () => {
    if (saved && report.id) {
      try {
        await fetch(`/api/v1/reports/${report.id}`, { method: "DELETE" });
      } catch {
        // best-effort delete
      }
    }
    setShowDeleteConfirm(false);
    navigate(state?.batchId ? `/batch-report/${state.batchId}` : "/history");
  };

  const handleSave = async () => {
    const originalFile = state?.file;
    if (!originalFile || !state?.report) {
      setSaveError("Original file not available for saving");
      return;
    }
    setSaving(true);
    setSaveError(null);

    try {
      const formData = new FormData();
      formData.append("file", originalFile);
      formData.append("report_json", JSON.stringify(state.report));

      const res = await fetch("/api/v1/reports", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Save failed (${res.status})`);
      }

      setSaveSuccess(true);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const loadImageAsDataUrl = (src: string): Promise<string | null> => {
    return new Promise((resolve) => {
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = () => {
        const canvas = document.createElement("canvas");
        canvas.width = img.naturalWidth;
        canvas.height = img.naturalHeight;
        canvas.getContext("2d")!.drawImage(img, 0, 0);
        resolve(canvas.toDataURL("image/jpeg", 0.85));
      };
      img.onerror = () => resolve(null);
      img.src = src;
    });
  };

  const handleExport = async () => {
    const doc = new jsPDF();
    const margin = 20;
    let y = margin;

    const addLine = (text: string, size = 10, style: "normal" | "bold" = "normal") => {
      doc.setFontSize(size);
      doc.setFont("helvetica", style);
      const lines = doc.splitTextToSize(text, 170);
      if (y + lines.length * size * 0.4 > 280) {
        doc.addPage();
        y = margin;
      }
      doc.text(lines, margin, y);
      y += lines.length * size * 0.45 + 2;
    };

    const addScoreRow = (label: string, value: number) => {
      doc.setFontSize(10);
      doc.setFont("helvetica", "normal");
      if (y > 275) { doc.addPage(); y = margin; }
      doc.text(label, margin + 4, y);
      doc.text(`${value.toFixed(1)}`, 170, y, { align: "right" });
      // score bar
      const barWidth = 60;
      const barX = 100;
      doc.setDrawColor(200, 200, 200);
      doc.setFillColor(230, 230, 230);
      doc.roundedRect(barX, y - 3.5, barWidth, 4, 1, 1, "F");
      const fill = (value / 100) * barWidth;
      const [r, g, b] = value >= 80 ? [52, 211, 153] : value >= 60 ? [96, 165, 250] : value >= 40 ? [251, 191, 36] : [248, 113, 113];
      doc.setFillColor(r, g, b);
      doc.roundedRect(barX, y - 3.5, fill, 4, 1, 1, "F");
      y += 7;
    };

    // Header
    addLine("VisionScore Analysis Report", 20, "bold");

    // Embed the photo
    if (report.image_url) {
      const dataUrl = await loadImageAsDataUrl(report.image_url);
      if (dataUrl) {
        const pageWidth = 170;
        const aspect = report.image_meta.height / report.image_meta.width;
        const imgHeight = Math.min(pageWidth * aspect, 100);
        doc.addImage(dataUrl, "JPEG", margin, y, pageWidth, imgHeight);
        y += imgHeight + 4;
      }
    }

    addLine(`${report.image_meta.width} × ${report.image_meta.height} | ${report.image_meta.format} | ${new Date(report.timestamp).toLocaleDateString()}`, 9);
    y += 4;

    // Overall score
    addLine(`Overall Score: ${report.overall_score.toFixed(1)} / 100  —  Grade ${report.grade}`, 14, "bold");
    y += 4;

    // Technical
    if (report.technical) {
      addLine("Technical Quality (25%)", 12, "bold");
      addScoreRow("Sharpness", report.technical.sharpness);
      addScoreRow("Exposure", report.technical.exposure);
      addScoreRow("Noise", report.technical.noise);
      addScoreRow("Dynamic Range", report.technical.dynamic_range);
      addScoreRow("Overall", report.technical.overall);
      y += 3;
    }

    // Aesthetic
    if (report.aesthetic) {
      addLine("Aesthetic Quality (30%)", 12, "bold");
      addScoreRow("NIMA Score", report.aesthetic.nima_score);
      addScoreRow("Confidence", report.aesthetic.confidence * 100);
      addScoreRow("Overall", report.aesthetic.overall);
      y += 3;
    }

    // Composition
    if (report.composition) {
      addLine("Composition (25%)", 12, "bold");
      addScoreRow("Rule of Thirds", report.composition.rule_of_thirds);
      addScoreRow("Subject Position", report.composition.subject_position);
      addScoreRow("Horizon", report.composition.horizon);
      addScoreRow("Balance", report.composition.balance);
      addScoreRow("Overall", report.composition.overall);
      y += 3;
    }

    // AI Feedback
    if (report.ai_feedback) {
      addLine("AI Feedback (20%)", 12, "bold");
      addScoreRow("AI Score", report.ai_feedback.score);
      y += 2;
      addLine(`Genre: ${report.ai_feedback.genre}  |  Mood: ${report.ai_feedback.mood}`, 10);
      addLine(report.ai_feedback.description, 10);
      y += 2;

      addLine("Strengths:", 10, "bold");
      report.ai_feedback.strengths.forEach((s) => addLine(`  + ${s}`));
      y += 1;
      addLine("Improvements:", 10, "bold");
      report.ai_feedback.improvements.forEach((s) => addLine(`  ~ ${s}`));
      y += 2;
      addLine(report.ai_feedback.reasoning, 9);
    }

    // Improvement Suggestions
    if (report.suggestions && report.suggestions.suggestions.length > 0) {
      y += 4;
      addLine("Improvement Suggestions", 12, "bold");
      if (report.suggestions.summary) {
        addLine(report.suggestions.summary, 9);
        y += 1;
      }
      report.suggestions.suggestions.forEach((s, i) => {
        const priority = s.priority <= 2 ? "[HIGH]" : s.priority <= 3 ? "[MED]" : "[LOW]";
        const type = s.type.charAt(0).toUpperCase() + s.type.slice(1);
        addLine(`  ${i + 1}. ${priority} ${type}: ${s.instruction}`);
      });
    }

    // EXIF
    const exif = report.image_meta?.exif;
    if (exif) {
      y += 4;
      addLine("Image Metadata", 12, "bold");
      if (exif.camera) addLine(`Camera: ${exif.camera}  |  ISO: ${exif.iso}  |  Aperture: ${exif.aperture}`);
      if (exif.shutter_speed) addLine(`Shutter: ${exif.shutter_speed}  |  Focal Length: ${exif.focal_length}${exif.lens ? `  |  Lens: ${exif.lens}` : ""}`);
    }

    const safeName = report.image_meta.path.split("/").pop()?.replace(/\.[^.]+$/, "") || "report";
    doc.save(`visionscore-${safeName}.pdf`);
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Top bar */}
      <div className="flex items-center justify-between mb-6">
        <button
          onClick={() => navigate(state?.batchId ? `/batch-report/${state.batchId}` : saved ? "/history" : "/")}
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          {state?.batchId ? "Back to Batch" : saved ? "Back to Reports" : "Analyze Another"}
        </button>
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <Clock className="w-3 h-3" />
          Analyzed in {report.analysis_time_seconds}s
        </div>
      </div>

      {/* Warnings banner */}
      {warnings.length > 0 && showWarnings && (
        <div className="mb-6 rounded-lg bg-yellow-500/10 border border-yellow-500/20 px-4 py-3">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-yellow-400 mt-0.5 shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <span className="text-sm text-yellow-400" style={{ fontWeight: 500 }}>
                  {warnings.length} warning{warnings.length !== 1 && "s"} during analysis
                </span>
                <button
                  onClick={() => setShowWarnings(false)}
                  className="text-yellow-400/60 hover:text-yellow-400 transition-colors ml-2"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
              <ul className="mt-1.5 space-y-0.5">
                {warnings.map((w, i) => (
                  <li key={i} className="text-xs text-yellow-400/80">{w}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Hero section with image and overall score */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2 rounded-2xl overflow-hidden border border-white/[0.06] bg-white/[0.02]">
          <ImageOverlay
            src={report.image_url}
            alt={report.image_meta.path}
            composition={report.composition}
          />
        </div>
        <div className="flex flex-col items-center justify-center bg-white/[0.03] border border-white/[0.06] rounded-2xl p-8">
          <span className="text-xs text-gray-500 uppercase tracking-wider mb-4">Overall Score</span>
          <ScoreBadge score={report.overall_score} grade={report.grade} size="lg" />
          <div className={`mt-4 px-4 py-1.5 rounded-full border text-sm ${getGradeBg(report.grade)} ${getGradeColor(report.grade)}`}>
            Grade {report.grade}
          </div>
          <p className="text-xs text-gray-500 mt-3 text-center">
            {report.grade === "S"
              ? "Exceptional"
              : report.grade === "A"
              ? "Excellent"
              : report.grade === "B"
              ? "Good"
              : report.grade === "C"
              ? "Average"
              : report.grade === "D"
              ? "Below Average"
              : "Poor"}
          </p>

          {/* Actions */}
          <div className="flex gap-2 mt-6 w-full">
            {saved ? (
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-sm bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5" /> Delete
              </button>
            ) : (
              <>
                <button
                  onClick={handleSave}
                  disabled={saving || saveSuccess}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-sm border transition-colors ${
                    saveSuccess
                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                      : "bg-white/[0.05] text-gray-300 border-white/[0.08] hover:bg-white/[0.08]"
                  }`}
                >
                  {saving ? (
                    <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Saving...</>
                  ) : saveSuccess ? (
                    <><Check className="w-3.5 h-3.5" /> Saved</>
                  ) : (
                    <><Save className="w-3.5 h-3.5" /> Save</>
                  )}
                </button>
                {saveError && (
                  <p className="text-xs text-red-400 mt-1">{saveError}</p>
                )}
              </>
            )}
            <button
              onClick={handleExport}
              className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-sm bg-white/[0.05] text-gray-300 border border-white/[0.08] hover:bg-white/[0.08] transition-colors"
            >
              <Download className="w-3.5 h-3.5" /> Export
            </button>
          </div>
        </div>
      </div>

      {/* Score Profile Radar Chart */}
      <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-6 mb-6">
        <h3 className="text-white text-sm mb-2">Score Profile</h3>
        <ScoreRadarChart
          technical={report.technical?.overall ?? null}
          aesthetic={report.aesthetic?.overall ?? null}
          composition={report.composition?.overall ?? null}
          aiFeedback={report.ai_feedback?.score ?? null}
        />
      </div>

      {/* Category Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {report.technical && (
          <CategoryCard
            title="Technical"
            weight={25}
            overall={report.technical.overall}
            icon={<Aperture className="w-5 h-5 text-cyan-400" />}
            subScores={[
              { label: "Sharpness", value: report.technical.sharpness },
              { label: "Exposure", value: report.technical.exposure },
              { label: "Noise", value: report.technical.noise },
              { label: "Dynamic Range", value: report.technical.dynamic_range },
            ]}
          />
        )}
        {report.aesthetic && (
          <CategoryCard
            title="Aesthetic"
            weight={30}
            overall={report.aesthetic.overall}
            icon={<Palette className="w-5 h-5 text-pink-400" />}
            subScores={[
              { label: "NIMA Score", value: report.aesthetic.nima_score },
              { label: "Confidence", value: report.aesthetic.confidence * 100 },
              { label: "Std Dev", value: report.aesthetic.std_dev },
            ]}
          />
        )}
        {report.composition && (
          <CategoryCard
            title="Composition"
            weight={25}
            overall={report.composition.overall}
            icon={<Grid3x3 className="w-5 h-5 text-amber-400" />}
            subScores={[
              { label: "Rule of Thirds", value: report.composition.rule_of_thirds },
              { label: "Subject Position", value: report.composition.subject_position },
              { label: "Horizon", value: report.composition.horizon },
              { label: "Balance", value: report.composition.balance },
            ]}
          />
        )}
        {report.ai_feedback && (
          <CategoryCard
            title="AI Feedback"
            weight={20}
            overall={report.ai_feedback.score}
            icon={<Sparkles className="w-5 h-5 text-purple-400" />}
            subScores={[{ label: "AI Score", value: report.ai_feedback.score }]}
          />
        )}
        {report.plugin_results && Object.entries(report.plugin_results).map(([name, data]) => {
          const overall = typeof data.overall === "number" ? data.overall : typeof data.score === "number" ? data.score : null;
          const subScores = Object.entries(data)
            .filter(([k, v]) => typeof v === "number" && k !== "overall")
            .map(([k, v]) => ({ label: k.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()), value: v as number }));
          const issues = Array.isArray(data.issues) ? data.issues as string[] : [];
          const stringFields = Object.entries(data)
            .filter(([, v]) => typeof v === "string" && v !== "")
            .map(([k, v]) => [k.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()), v as string] as const);
          const displayName = name.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
          const hasExtra = issues.length > 0 || stringFields.length > 0;
          return (
            <CategoryCard
              key={name}
              title={displayName}
              overall={overall}
              icon={<Plug className="w-5 h-5 text-indigo-400" />}
              subScores={subScores}
              extra={hasExtra ? (
                <div className="mt-3 space-y-1.5 border-t border-white/[0.06] pt-3">
                  {stringFields.map(([label, val]) => (
                    <div key={label} className="flex justify-between text-xs">
                      <span className="text-gray-500">{label}</span>
                      <span className="text-gray-300">{val}</span>
                    </div>
                  ))}
                  {issues.map((issue, i) => (
                    <p key={i} className="text-xs text-yellow-400/80">- {issue}</p>
                  ))}
                </div>
              ) : undefined}
            />
          );
        })}
      </div>

      {/* Improvement Suggestions */}
      {report.suggestions && report.suggestions.suggestions.length > 0 && (
        <div className="mb-6">
          <SuggestionsSection
            suggestions={report.suggestions}
            cropPreviewUrl={
              report.suggestions.crop_preview_path
                ? report.suggestions.crop_preview_path
                : undefined
            }
            imageFile={state?.file || null}
            originalImageUrl={report.image_url}
          />
        </div>
      )}

      {/* AI Feedback & Metadata */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {report.ai_feedback ? (
          <div className="lg:col-span-2">
            <FeedbackSection feedback={report.ai_feedback} />
          </div>
        ) : (
          <div className="lg:col-span-2 flex items-center justify-center bg-white/[0.03] border border-white/[0.06] rounded-2xl p-8 text-gray-500 text-sm">
            AI feedback not available for this analysis
          </div>
        )}
        <div className="space-y-4">
          <MetadataPanel meta={report.image_meta} />
          <button
            onClick={() => navigate("/")}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white transition-all flex items-center justify-center gap-2 text-sm"
          >
            Analyze Another Image
          </button>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 px-4">
          <div className="bg-gray-900 border border-white/10 rounded-2xl p-6 max-w-sm w-full">
            <h3 className="text-white mb-2">Delete Report?</h3>
            <p className="text-sm text-gray-400 mb-6">This action cannot be undone. The report will be permanently removed.</p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="flex-1 py-2 rounded-lg text-sm bg-white/[0.05] text-gray-300 border border-white/[0.08] hover:bg-white/[0.08] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                className="flex-1 py-2 rounded-lg text-sm bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30 transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
