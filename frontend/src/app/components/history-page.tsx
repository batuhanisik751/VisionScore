import { useState } from "react";
import { useNavigate } from "react-router";
import { MOCK_REPORTS, getGradeColor, getGradeBg, type AnalysisReport } from "./mock-data";
import { ScoreBadge } from "./score-badge";
import { Search, LayoutGrid, List, Calendar, Trash2, ImagePlus, Filter } from "lucide-react";

export function HistoryPage() {
  const navigate = useNavigate();
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [searchQuery, setSearchQuery] = useState("");
  const [gradeFilter, setGradeFilter] = useState<string>("");
  const [reports, setReports] = useState(MOCK_REPORTS);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const filtered = reports.filter((r) => {
    if (gradeFilter && r.grade !== gradeFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        r.ai_feedback.genre.toLowerCase().includes(q) ||
        r.ai_feedback.mood.toLowerCase().includes(q) ||
        r.image_meta.path.toLowerCase().includes(q) ||
        r.grade.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const handleDelete = (id: string) => {
    setReports((prev) => prev.filter((r) => r.id !== id));
    setDeleteId(null);
  };

  const formatDate = (ts: string) => {
    const d = new Date(ts);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl text-white" style={{ fontWeight: 700 }}>Reports</h1>
          <p className="text-sm text-gray-500">{reports.length} saved analyses</p>
        </div>
        <button
          onClick={() => navigate("/")}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-blue-500 to-purple-500 text-white text-sm hover:from-blue-600 hover:to-purple-600 transition-all"
        >
          <ImagePlus className="w-4 h-4" /> New Analysis
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search by genre, mood, filename..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2.5 rounded-lg bg-white/[0.04] border border-white/[0.08] text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500/50"
          />
        </div>
        <div className="flex gap-2">
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500" />
            <select
              value={gradeFilter}
              onChange={(e) => setGradeFilter(e.target.value)}
              className="pl-8 pr-8 py-2.5 rounded-lg bg-white/[0.04] border border-white/[0.08] text-sm text-gray-300 appearance-none focus:outline-none focus:border-blue-500/50"
            >
              <option value="">All Grades</option>
              {["S", "A", "B", "C", "D", "F"].map((g) => (
                <option key={g} value={g}>
                  Grade {g}
                </option>
              ))}
            </select>
          </div>
          <div className="flex rounded-lg border border-white/[0.08] overflow-hidden">
            <button
              onClick={() => setViewMode("grid")}
              className={`p-2.5 transition-colors ${viewMode === "grid" ? "bg-white/[0.08] text-white" : "text-gray-500 hover:text-gray-300"}`}
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode("list")}
              className={`p-2.5 transition-colors ${viewMode === "list" ? "bg-white/[0.08] text-white" : "text-gray-500 hover:text-gray-300"}`}
            >
              <List className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Empty State */}
      {filtered.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="p-4 rounded-full bg-white/[0.04] mb-4">
            <ImagePlus className="w-8 h-8 text-gray-600" />
          </div>
          <h3 className="text-gray-300 mb-1">No reports found</h3>
          <p className="text-sm text-gray-500 mb-6">
            {searchQuery || gradeFilter ? "Try adjusting your filters" : "Upload an image to get started"}
          </p>
          <button
            onClick={() => navigate("/")}
            className="px-6 py-2 rounded-lg bg-gradient-to-r from-blue-500 to-purple-500 text-white text-sm"
          >
            Analyze an Image
          </button>
        </div>
      )}

      {/* Grid View */}
      {viewMode === "grid" && filtered.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((report) => (
            <ReportGridCard
              key={report.id}
              report={report}
              onView={() => navigate(`/report/${report.id}`)}
              onDelete={() => setDeleteId(report.id)}
              formatDate={formatDate}
            />
          ))}
        </div>
      )}

      {/* List View */}
      {viewMode === "list" && filtered.length > 0 && (
        <div className="space-y-2">
          {filtered.map((report) => (
            <ReportListRow
              key={report.id}
              report={report}
              onView={() => navigate(`/report/${report.id}`)}
              onDelete={() => setDeleteId(report.id)}
              formatDate={formatDate}
            />
          ))}
        </div>
      )}

      {/* Delete Confirmation */}
      {deleteId && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 px-4">
          <div className="bg-gray-900 border border-white/10 rounded-2xl p-6 max-w-sm w-full">
            <h3 className="text-white mb-2">Delete Report?</h3>
            <p className="text-sm text-gray-400 mb-6">This action cannot be undone.</p>
            <div className="flex gap-3">
              <button
                onClick={() => setDeleteId(null)}
                className="flex-1 py-2 rounded-lg text-sm bg-white/[0.05] text-gray-300 border border-white/[0.08]"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(deleteId)}
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

function ReportGridCard({
  report,
  onView,
  onDelete,
  formatDate,
}: {
  report: AnalysisReport;
  onView: () => void;
  onDelete: () => void;
  formatDate: (ts: string) => string;
}) {
  return (
    <div
      onClick={onView}
      className="bg-white/[0.03] border border-white/[0.06] rounded-xl overflow-hidden cursor-pointer hover:bg-white/[0.05] hover:border-white/[0.1] transition-all group"
    >
      <div className="relative h-44 overflow-hidden">
        <img src={report.image_url} alt={report.image_meta.path} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
        <div className="absolute top-3 right-3">
          <ScoreBadge score={report.overall_score} grade={report.grade} size="sm" />
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="absolute top-3 left-3 p-1.5 rounded-full bg-black/50 text-gray-400 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>
      <div className="p-4">
        <div className="flex items-center gap-2 mb-2">
          <span className={`px-2 py-0.5 rounded-full text-xs border ${getGradeBg(report.grade)} ${getGradeColor(report.grade)}`}>
            {report.grade}
          </span>
          <span className="px-2 py-0.5 rounded-full text-xs bg-white/[0.05] text-gray-400 border border-white/[0.08]">
            {report.ai_feedback.genre}
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-gray-500">
          <Calendar className="w-3 h-3" />
          {formatDate(report.timestamp)}
        </div>
      </div>
    </div>
  );
}

function ReportListRow({
  report,
  onView,
  onDelete,
  formatDate,
}: {
  report: AnalysisReport;
  onView: () => void;
  onDelete: () => void;
  formatDate: (ts: string) => string;
}) {
  return (
    <div
      onClick={onView}
      className="flex items-center gap-4 bg-white/[0.03] border border-white/[0.06] rounded-xl p-3 cursor-pointer hover:bg-white/[0.05] transition-all group"
    >
      <img src={report.image_url} alt="" className="w-16 h-12 rounded-lg object-cover" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-300 truncate">{report.image_meta.path}</span>
          <span className={`px-2 py-0.5 rounded-full text-xs border ${getGradeBg(report.grade)} ${getGradeColor(report.grade)}`}>
            {report.grade}
          </span>
          <span className="px-2 py-0.5 rounded-full text-xs bg-white/[0.05] text-gray-400 border border-white/[0.08]">
            {report.ai_feedback.genre}
          </span>
        </div>
        <span className="text-xs text-gray-500">{formatDate(report.timestamp)}</span>
      </div>
      <div className="flex items-center gap-3">
        <ScoreBadge score={report.overall_score} grade={report.grade} size="sm" />
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="p-1.5 rounded-full text-gray-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
