import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router";
import {
  ArrowLeft,
  Download,
  FileText,
  Trash2,
  Trophy,
  AlertCircle,
  Loader2,
  ArrowDown,
  ArrowUp,
  FolderOpen,
} from "lucide-react";
import { jsPDF } from "jspdf";
import { BarChart, Bar, XAxis, YAxis, Cell } from "recharts";
import { ScoreBadge } from "./score-badge";
import { ScoreRadarChart } from "./score-radar-chart";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "./ui/chart";
import { getGradeColor, getGradeBg, getScoreBarClass, type AnalysisReport } from "./mock-data";

interface DbRow {
  id: string;
  created_at: string;
  image_url: string | null;
  overall_score: number;
  grade: string;
  full_report: AnalysisReport;
}

const GRADES = ["S", "A", "B", "C", "D", "F"];

const gradeChartConfig: ChartConfig = {
  count: { label: "Count", color: "#60a5fa" },
};

function gradeBarColor(grade: string): string {
  switch (grade) {
    case "S": return "#fbbf24";
    case "A": return "#34d399";
    case "B": return "#60a5fa";
    case "C": return "#facc15";
    case "D": return "#fb923c";
    case "F": return "#f87171";
    default: return "#6b7280";
  }
}

export function BatchDetailPage() {
  const { batchId } = useParams();
  const navigate = useNavigate();

  const [reports, setReports] = useState<DbRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const [sortField, setSortField] = useState<"score" | "name">("score");
  const [sortAsc, setSortAsc] = useState(false);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    if (!batchId) return;
    setLoading(true);
    fetch(`/api/v1/reports/batch/${batchId}`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`Failed to load batch (${res.status})`);
        const data = await res.json();
        setReports(data.reports);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load batch"))
      .finally(() => setLoading(false));
  }, [batchId]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-gray-500 animate-spin mb-4" />
        <p className="text-sm text-gray-500">Loading batch...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          {error}
        </div>
      </div>
    );
  }

  const successful = reports.filter((r) => r.full_report);
  const scores = successful.map((r) => r.overall_score);
  const avgScore = scores.length > 0 ? Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 10) / 10 : 0;
  const bestRow = successful.length > 0 ? successful.reduce((a, b) => (a.overall_score >= b.overall_score ? a : b)) : null;
  const worstRow = successful.length > 0 ? successful.reduce((a, b) => (a.overall_score < b.overall_score ? a : b)) : null;

  const gradeDistribution: Record<string, number> = {};
  successful.forEach((r) => {
    gradeDistribution[r.grade] = (gradeDistribution[r.grade] || 0) + 1;
  });

  const avgCategory = (key: "technical" | "aesthetic" | "composition" | "ai_feedback") => {
    const vals = successful
      .map((r) => {
        const cat = r.full_report[key];
        if (!cat) return null;
        return key === "ai_feedback" ? (cat as { score: number }).score : (cat as { overall: number }).overall;
      })
      .filter((v): v is number => v != null);
    return vals.length > 0 ? Math.round((vals.reduce((a, b) => a + b, 0) / vals.length) * 10) / 10 : null;
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await fetch(`/api/v1/reports/batch/${batchId}`, { method: "DELETE" });
      navigate("/history");
    } catch {
      setDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  const exportCSV = () => {
    const headers = [
      "filename", "overall_score", "grade", "technical", "aesthetic",
      "composition", "ai_feedback", "sharpness", "exposure", "noise", "dynamic_range",
    ];
    const rows = successful.map((r) => {
      const rp = r.full_report;
      return [
        rp.image_meta.path, r.overall_score, r.grade,
        rp.technical?.overall ?? "", rp.aesthetic?.overall ?? "",
        rp.composition?.overall ?? "", rp.ai_feedback?.score ?? "",
        rp.technical?.sharpness ?? "", rp.technical?.exposure ?? "",
        rp.technical?.noise ?? "", rp.technical?.dynamic_range ?? "",
      ];
    });
    const csv = [headers, ...rows].map((row) => row.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `visionscore-batch-${batchId?.slice(0, 8)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const loadImageAsDataUrl = (src: string): Promise<string | null> => {
    return new Promise((resolve) => {
      const img = new window.Image();
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

  const exportPDF = async () => {
    setExporting(true);
    try {
      const doc = new jsPDF();
      const margin = 20;

      const addLine = (y: number, text: string, size = 10, style: "normal" | "bold" = "normal"): number => {
        doc.setFontSize(size);
        doc.setFont("helvetica", style);
        const lines = doc.splitTextToSize(text, 170);
        if (y + lines.length * size * 0.4 > 280) {
          doc.addPage();
          y = margin;
        }
        doc.text(lines, margin, y);
        return y + lines.length * size * 0.45 + 2;
      };

      const addScoreRow = (y: number, label: string, value: number): number => {
        doc.setFontSize(10);
        doc.setFont("helvetica", "normal");
        if (y > 275) { doc.addPage(); y = margin; }
        doc.text(label, margin + 4, y);
        doc.text(`${value.toFixed(1)}`, 170, y, { align: "right" });
        const barWidth = 60;
        const barX = 100;
        doc.setFillColor(230, 230, 230);
        doc.roundedRect(barX, y - 3.5, barWidth, 4, 1, 1, "F");
        const fill = (value / 100) * barWidth;
        const [r, g, b] = value >= 80 ? [52, 211, 153] : value >= 60 ? [96, 165, 250] : value >= 40 ? [251, 191, 36] : [248, 113, 113];
        doc.setFillColor(r, g, b);
        doc.roundedRect(barX, y - 3.5, fill, 4, 1, 1, "F");
        return y + 7;
      };

      // --- Summary page ---
      let y = margin;
      y = addLine(y, "VisionScore Batch Report", 20, "bold");
      y = addLine(y, `Batch ID: ${batchId?.slice(0, 8)}`, 10);
      y = addLine(y, `${successful.length} images analyzed  |  Average: ${avgScore.toFixed(1)}  |  Best: ${bestRow?.grade || "—"}`, 10);
      y += 6;

      // Grade distribution table
      y = addLine(y, "Grade Distribution", 12, "bold");
      GRADES.forEach((g) => {
        const count = gradeDistribution[g] || 0;
        if (count > 0) y = addLine(y, `  ${g}: ${count} image${count > 1 ? "s" : ""}`);
      });
      y += 4;

      // Ranking table
      y = addLine(y, "Ranking", 12, "bold");
      y += 2;
      const ranked = [...successful].sort((a, b) => b.overall_score - a.overall_score);
      ranked.forEach((row, i) => {
        const name = row.full_report.image_meta.path.split("/").pop() || row.full_report.image_meta.path;
        y = addLine(y, `${i + 1}. ${name}  —  ${row.overall_score.toFixed(1)} (${row.grade})`);
      });

      // --- One page per report ---
      for (const row of ranked) {
        doc.addPage();
        y = margin;
        const rp = row.full_report;

        y = addLine(y, "VisionScore Analysis Report", 20, "bold");

        // Embed photo
        if (row.image_url) {
          const dataUrl = await loadImageAsDataUrl(row.image_url);
          if (dataUrl) {
            const pageWidth = 170;
            const aspect = rp.image_meta.height / rp.image_meta.width;
            const imgHeight = Math.min(pageWidth * aspect, 100);
            doc.addImage(dataUrl, "JPEG", margin, y, pageWidth, imgHeight);
            y += imgHeight + 4;
          }
        }

        y = addLine(y, `${rp.image_meta.width} × ${rp.image_meta.height} | ${rp.image_meta.format}`, 9);
        y += 4;
        y = addLine(y, `Overall Score: ${row.overall_score.toFixed(1)} / 100  —  Grade ${row.grade}`, 14, "bold");
        y += 4;

        if (rp.technical) {
          y = addLine(y, "Technical Quality (25%)", 12, "bold");
          y = addScoreRow(y, "Sharpness", rp.technical.sharpness);
          y = addScoreRow(y, "Exposure", rp.technical.exposure);
          y = addScoreRow(y, "Noise", rp.technical.noise);
          y = addScoreRow(y, "Dynamic Range", rp.technical.dynamic_range);
          y = addScoreRow(y, "Overall", rp.technical.overall);
          y += 3;
        }

        if (rp.aesthetic) {
          y = addLine(y, "Aesthetic Quality (30%)", 12, "bold");
          y = addScoreRow(y, "NIMA Score", rp.aesthetic.nima_score);
          y = addScoreRow(y, "Confidence", rp.aesthetic.confidence * 100);
          y = addScoreRow(y, "Overall", rp.aesthetic.overall);
          y += 3;
        }

        if (rp.composition) {
          y = addLine(y, "Composition (25%)", 12, "bold");
          y = addScoreRow(y, "Rule of Thirds", rp.composition.rule_of_thirds);
          y = addScoreRow(y, "Subject Position", rp.composition.subject_position);
          y = addScoreRow(y, "Horizon", rp.composition.horizon);
          y = addScoreRow(y, "Balance", rp.composition.balance);
          y = addScoreRow(y, "Overall", rp.composition.overall);
          y += 3;
        }

        if (rp.ai_feedback) {
          y = addLine(y, "AI Feedback (20%)", 12, "bold");
          y = addScoreRow(y, "AI Score", rp.ai_feedback.score);
          y += 2;
          y = addLine(y, `Genre: ${rp.ai_feedback.genre}  |  Mood: ${rp.ai_feedback.mood}`, 10);
          y = addLine(y, rp.ai_feedback.description, 10);
          y += 2;
          y = addLine(y, "Strengths:", 10, "bold");
          rp.ai_feedback.strengths.forEach((s) => { y = addLine(y, `  + ${s}`); });
          y += 1;
          y = addLine(y, "Improvements:", 10, "bold");
          rp.ai_feedback.improvements.forEach((s) => { y = addLine(y, `  ~ ${s}`); });
          y += 2;
          y = addLine(y, rp.ai_feedback.reasoning, 9);
        }

        const exif = rp.image_meta?.exif;
        if (exif) {
          y += 4;
          y = addLine(y, "Image Metadata", 12, "bold");
          if (exif.camera) y = addLine(y, `Camera: ${exif.camera}  |  ISO: ${exif.iso}  |  Aperture: ${exif.aperture}`);
          if (exif.shutter_speed) y = addLine(y, `Shutter: ${exif.shutter_speed}  |  Focal Length: ${exif.focal_length}${exif.lens ? `  |  Lens: ${exif.lens}` : ""}`);
        }
      }

      doc.save(`visionscore-batch-${batchId?.slice(0, 8)}.pdf`);
    } finally {
      setExporting(false);
    }
  };

  const sortedReports = [...successful].sort((a, b) => {
    if (sortField === "name") {
      return sortAsc
        ? a.full_report.image_meta.path.localeCompare(b.full_report.image_meta.path)
        : b.full_report.image_meta.path.localeCompare(a.full_report.image_meta.path);
    }
    return sortAsc ? a.overall_score - b.overall_score : b.overall_score - a.overall_score;
  });

  const toggleSort = (field: "score" | "name") => {
    if (sortField === field) setSortAsc(!sortAsc);
    else { setSortField(field); setSortAsc(field === "name"); }
  };

  const SortIcon = sortAsc ? ArrowUp : ArrowDown;

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Top bar */}
      <div className="flex items-center justify-between mb-6">
        <button
          onClick={() => navigate("/history")}
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Reports
        </button>
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <FolderOpen className="w-3 h-3" />
          Batch {batchId?.slice(0, 8)}
        </div>
      </div>

      <div className="space-y-8">
        {/* Summary cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "Images", value: reports.length, color: "text-white" },
            { label: "Successful", value: successful.length, color: "text-emerald-400" },
            { label: "Failed", value: reports.length - successful.length, color: reports.length - successful.length > 0 ? "text-red-400" : "text-gray-500" },
            { label: "Avg Score", value: avgScore.toFixed(1), color: "text-blue-400" },
          ].map((stat) => (
            <div key={stat.label} className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4 text-center">
              <p className="text-xs text-gray-500 mb-1">{stat.label}</p>
              <p className={`text-2xl tabular-nums ${stat.color}`} style={{ fontWeight: 700 }}>{stat.value}</p>
            </div>
          ))}
        </div>

        {/* Best & Worst */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {bestRow && (
            <div className="bg-white/[0.03] border border-emerald-500/20 rounded-xl p-4 flex items-center gap-4">
              <Trophy className="w-8 h-8 text-emerald-400 shrink-0" />
              <div className="min-w-0">
                <p className="text-xs text-emerald-400 mb-0.5">Best Image</p>
                <p className="text-white text-sm truncate" style={{ fontWeight: 600 }}>{bestRow.full_report.image_meta.path}</p>
                <p className="text-emerald-400 text-lg tabular-nums" style={{ fontWeight: 700 }}>{bestRow.overall_score.toFixed(1)}</p>
              </div>
            </div>
          )}
          {worstRow && (
            <div className="bg-white/[0.03] border border-red-500/20 rounded-xl p-4 flex items-center gap-4">
              <AlertCircle className="w-8 h-8 text-red-400 shrink-0" />
              <div className="min-w-0">
                <p className="text-xs text-red-400 mb-0.5">Lowest Score</p>
                <p className="text-white text-sm truncate" style={{ fontWeight: 600 }}>{worstRow.full_report.image_meta.path}</p>
                <p className="text-red-400 text-lg tabular-nums" style={{ fontWeight: 700 }}>{worstRow.overall_score.toFixed(1)}</p>
              </div>
            </div>
          )}
        </div>

        {/* Charts: Grade Distribution + Avg Scores Radar */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4">
            <p className="text-xs text-gray-500 mb-3">Grade Distribution</p>
            <ChartContainer config={gradeChartConfig} className="h-[160px] w-full aspect-auto">
              <BarChart data={GRADES.map((g) => ({ grade: g, count: gradeDistribution[g] || 0 }))} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
                <XAxis dataKey="grade" tick={{ fill: "#9ca3af", fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fill: "#6b7280", fontSize: 10 }} axisLine={false} tickLine={false} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]} animationDuration={800}>
                  {GRADES.map((g) => (
                    <Cell key={g} fill={gradeBarColor(g)} />
                  ))}
                </Bar>
              </BarChart>
            </ChartContainer>
          </div>
          <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4">
            <p className="text-xs text-gray-500 mb-1">Average Score Profile</p>
            <ScoreRadarChart
              technical={avgCategory("technical")}
              aesthetic={avgCategory("aesthetic")}
              composition={avgCategory("composition")}
              aiFeedback={avgCategory("ai_feedback")}
            />
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-500">{reports.length} images in batch</span>
          <div className="flex gap-3">
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="flex items-center gap-2 px-4 py-2 text-sm text-red-400 bg-red-500/10 border border-red-500/20 hover:bg-red-500/20 rounded-lg transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" /> Delete Batch
            </button>
            <button
              onClick={exportPDF}
              disabled={exporting}
              className="flex items-center gap-2 px-4 py-2 text-sm text-gray-300 bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.06] rounded-lg transition-all"
            >
              {exporting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileText className="w-3.5 h-3.5" />}
              {exporting ? "Exporting..." : "Export PDF"}
            </button>
            <button
              onClick={exportCSV}
              className="flex items-center gap-2 px-4 py-2 text-sm text-gray-300 bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.06] rounded-lg transition-all"
            >
              <Download className="w-3.5 h-3.5" /> Export CSV
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
                    Image {sortField === "name" && <SortIcon className="w-3 h-3" />}
                  </button>
                </th>
                <th className="text-center text-xs text-gray-500 px-4 py-3">
                  <button onClick={() => toggleSort("score")} className="flex items-center gap-1 hover:text-gray-300 transition-colors mx-auto">
                    Score {sortField === "score" && <SortIcon className="w-3 h-3" />}
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
              {sortedReports.map((row, i) => {
                const rp = row.full_report;
                const isBest = bestRow && row.id === bestRow.id;
                const isWorst = worstRow && row.id === worstRow.id;
                return (
                  <tr
                    key={row.id}
                    onClick={() => navigate(`/report/${row.id}`, { state: { batchId } })}
                    className={`border-b border-white/[0.03] transition-colors hover:bg-white/[0.02] cursor-pointer ${
                      isBest ? "bg-emerald-500/[0.03]" : isWorst ? "bg-red-500/[0.03]" : ""
                    }`}
                  >
                    <td className="px-4 py-3 text-sm text-gray-500 tabular-nums">{i + 1}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        {row.image_url && (
                          <img src={row.image_url} alt="" className="w-10 h-10 rounded object-cover" />
                        )}
                        <span className={`text-sm truncate ${
                          isBest ? "text-emerald-400 font-semibold" : isWorst ? "text-red-400 font-semibold" : "text-gray-300"
                        }`}>
                          {rp.image_meta.path}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <ScoreBadge score={row.overall_score} grade={row.grade} size="sm" />
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs font-mono border ${getGradeBg(row.grade)} ${getGradeColor(row.grade)}`}>
                        {row.grade}
                      </span>
                    </td>
                    <td className="px-4 py-3 hidden sm:table-cell">
                      <div className="w-full h-2 bg-white/[0.06] rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${getScoreBarClass(row.overall_score)}`} style={{ width: `${row.overall_score}%` }} />
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

      {/* Delete Confirmation */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 px-4">
          <div className="bg-gray-900 border border-white/10 rounded-2xl p-6 max-w-sm w-full">
            <h3 className="text-white mb-2">Delete Batch?</h3>
            <p className="text-sm text-gray-400 mb-6">This will delete all {reports.length} reports in this batch. This action cannot be undone.</p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="flex-1 py-2 rounded-lg text-sm bg-white/[0.05] text-gray-300 border border-white/[0.08]"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="flex-1 py-2 rounded-lg text-sm bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30 transition-colors"
              >
                {deleting ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
