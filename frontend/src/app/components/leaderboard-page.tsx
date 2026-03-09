import { useState, useEffect } from "react";
import { useNavigate } from "react-router";
import {
  Trophy,
  Crown,
  LayoutGrid,
  List,
  ArrowUp,
  ArrowDown,
  Loader2,
  Image as ImageIcon,
  BarChart3,
} from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Cell } from "recharts";
import { ScoreBadge } from "./score-badge";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "./ui/chart";
import { getGradeColor, getGradeBg, getScoreBarClass } from "./mock-data";

interface LeaderboardEntry {
  id: string;
  image_url: string | null;
  overall_score: number;
  grade: string;
  created_at: string;
  filename: string;
  genre: string | null;
}

interface LeaderboardData {
  entries: LeaderboardEntry[];
  total: number;
  potd: LeaderboardEntry | null;
  average_score: number;
  grade_distribution: Record<string, number>;
}

const GRADES = ["S", "A", "B", "C", "D", "F"];

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

const gradeChartConfig: ChartConfig = {
  count: { label: "Count", color: "#60a5fa" },
};

const PAGE_SIZE = 20;

export function LeaderboardPage() {
  const navigate = useNavigate();

  const [data, setData] = useState<LeaderboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [viewMode, setViewMode] = useState<"grid" | "table">("table");
  const [sortBy, setSortBy] = useState("overall_score");
  const [sortOrder, setSortOrder] = useState("desc");
  const [gradeFilter, setGradeFilter] = useState<string>("");
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    fetchLeaderboard();
  }, [sortBy, sortOrder, gradeFilter, offset]);

  const fetchLeaderboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        limit: String(PAGE_SIZE),
        offset: String(offset),
        sort_by: sortBy,
        sort_order: sortOrder,
      });
      if (gradeFilter) params.set("grade", gradeFilter);

      const res = await fetch(`/api/v1/leaderboard?${params}`);
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Failed to load leaderboard (${res.status})`);
      }
      setData(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load leaderboard");
    } finally {
      setLoading(false);
    }
  };

  const toggleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder((prev) => (prev === "desc" ? "asc" : "desc"));
    } else {
      setSortBy(field);
      setSortOrder("desc");
    }
    setOffset(0);
  };

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  if (loading && !data) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-gray-500 animate-spin mb-4" />
        <p className="text-sm text-gray-500">Loading leaderboard...</p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          {error}
        </div>
      </div>
    );
  }

  if (!data || data.total === 0) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-12">
        <div className="text-center space-y-4">
          <Trophy className="w-12 h-12 text-gray-600 mx-auto" />
          <h2 className="text-xl text-white">No images ranked yet</h2>
          <p className="text-sm text-gray-500">Analyze some images to see them on the leaderboard.</p>
          <button
            onClick={() => navigate("/")}
            className="px-4 py-2 rounded-lg bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 text-sm transition-colors"
          >
            Upload an Image
          </button>
        </div>
      </div>
    );
  }

  const gradeChartData = GRADES.map((g) => ({
    grade: g,
    count: data.grade_distribution[g] || 0,
  })).filter((d) => d.count > 0);

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-amber-500/10">
          <Trophy className="w-5 h-5 text-amber-400" />
        </div>
        <div>
          <h1 className="text-xl text-white" style={{ fontWeight: 700 }}>Leaderboard</h1>
          <p className="text-xs text-gray-500">{data.total} images ranked</p>
        </div>
      </div>

      {/* POTD Hero */}
      {data.potd && (
        <button
          onClick={() => navigate(`/report/${data.potd!.id}`)}
          className="w-full text-left"
        >
          <div className="relative rounded-xl overflow-hidden border border-amber-500/20 bg-gradient-to-br from-amber-500/[0.06] to-purple-500/[0.04] hover:border-amber-500/40 transition-colors group">
            <div className="flex items-center gap-6 p-5">
              {data.potd.image_url ? (
                <img
                  src={data.potd.image_url}
                  alt={data.potd.filename}
                  className="w-40 h-28 object-cover rounded-lg flex-shrink-0"
                />
              ) : (
                <div className="w-40 h-28 bg-white/[0.03] rounded-lg flex items-center justify-center flex-shrink-0">
                  <ImageIcon className="w-8 h-8 text-gray-600" />
                </div>
              )}
              <div className="flex-1 min-w-0 space-y-2">
                <div className="flex items-center gap-2">
                  <Crown className="w-4 h-4 text-amber-400" />
                  <span className="text-xs text-amber-400 uppercase tracking-wider" style={{ fontWeight: 600 }}>
                    Photo of the Day
                  </span>
                </div>
                <p className="text-white text-lg truncate" style={{ fontWeight: 600 }}>
                  {data.potd.filename || "Untitled"}
                </p>
                <div className="flex items-center gap-3">
                  <span className={`text-2xl ${getGradeColor(data.potd.grade)}`} style={{ fontWeight: 700 }}>
                    {data.potd.overall_score.toFixed(1)}
                  </span>
                  <span className={`px-2 py-0.5 rounded text-xs border ${getGradeBg(data.potd.grade)} ${getGradeColor(data.potd.grade)}`} style={{ fontWeight: 700 }}>
                    {data.potd.grade}
                  </span>
                  {data.potd.genre && (
                    <span className="px-2 py-0.5 rounded text-xs bg-indigo-500/15 text-indigo-300 border border-indigo-500/20">
                      {data.potd.genre}
                    </span>
                  )}
                </div>
              </div>
              <div className="hidden sm:block flex-shrink-0">
                <ScoreBadge score={data.potd.overall_score} grade={data.potd.grade} size="sm" />
              </div>
            </div>
          </div>
        </button>
      )}

      {/* Stats Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "Total Images", value: String(data.total) },
          { label: "Average Score", value: data.average_score.toFixed(1) },
          { label: "Top Score", value: data.potd ? data.potd.overall_score.toFixed(1) : "—" },
          { label: "Top Grade", value: data.potd?.grade || "—" },
        ].map((stat) => (
          <div
            key={stat.label}
            className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4 text-center"
          >
            <div className="text-xl text-white" style={{ fontWeight: 700 }}>{stat.value}</div>
            <div className="text-xs text-gray-500 mt-1">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Grade Distribution Chart */}
      {gradeChartData.length > 0 && (
        <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-400">Grade Distribution</span>
          </div>
          <ChartContainer config={gradeChartConfig} className="h-[140px] w-full">
            <BarChart data={gradeChartData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
              <XAxis dataKey="grade" tick={{ fill: "#9ca3af", fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis hide allowDecimals={false} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {gradeChartData.map((entry) => (
                  <Cell key={entry.grade} fill={gradeBarColor(entry.grade)} />
                ))}
              </Bar>
            </BarChart>
          </ChartContainer>
        </div>
      )}

      {/* Controls */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        {/* Grade filter */}
        <div className="flex items-center gap-1 flex-wrap">
          <button
            onClick={() => { setGradeFilter(""); setOffset(0); }}
            className={`px-3 py-1.5 rounded-lg text-xs transition-colors ${
              !gradeFilter
                ? "bg-white/10 text-white"
                : "bg-white/[0.03] text-gray-500 hover:text-gray-300"
            }`}
          >
            All
          </button>
          {GRADES.map((g) => (
            <button
              key={g}
              onClick={() => { setGradeFilter(gradeFilter === g ? "" : g); setOffset(0); }}
              className={`px-3 py-1.5 rounded-lg text-xs transition-colors ${
                gradeFilter === g
                  ? `${getGradeBg(g)} ${getGradeColor(g)}`
                  : "bg-white/[0.03] text-gray-500 hover:text-gray-300"
              }`}
            >
              {g}
            </button>
          ))}
        </div>

        {/* View toggle + Sort */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => toggleSort("overall_score")}
            className={`px-3 py-1.5 rounded-lg text-xs flex items-center gap-1 transition-colors ${
              sortBy === "overall_score" ? "bg-white/10 text-white" : "bg-white/[0.03] text-gray-500 hover:text-gray-300"
            }`}
          >
            Score
            {sortBy === "overall_score" && (sortOrder === "desc" ? <ArrowDown className="w-3 h-3" /> : <ArrowUp className="w-3 h-3" />)}
          </button>
          <button
            onClick={() => toggleSort("created_at")}
            className={`px-3 py-1.5 rounded-lg text-xs flex items-center gap-1 transition-colors ${
              sortBy === "created_at" ? "bg-white/10 text-white" : "bg-white/[0.03] text-gray-500 hover:text-gray-300"
            }`}
          >
            Date
            {sortBy === "created_at" && (sortOrder === "desc" ? <ArrowDown className="w-3 h-3" /> : <ArrowUp className="w-3 h-3" />)}
          </button>
          <div className="w-px h-5 bg-white/[0.08]" />
          <button
            onClick={() => setViewMode("table")}
            className={`p-1.5 rounded-lg transition-colors ${viewMode === "table" ? "bg-white/10 text-white" : "text-gray-500 hover:text-gray-300"}`}
          >
            <List className="w-4 h-4" />
          </button>
          <button
            onClick={() => setViewMode("grid")}
            className={`p-1.5 rounded-lg transition-colors ${viewMode === "grid" ? "bg-white/10 text-white" : "text-gray-500 hover:text-gray-300"}`}
          >
            <LayoutGrid className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Table View */}
      {viewMode === "table" && (
        <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/[0.06] text-gray-500 text-xs">
                <th className="px-4 py-3 text-left w-12">#</th>
                <th className="px-4 py-3 text-left w-12"></th>
                <th className="px-4 py-3 text-left">Image</th>
                <th className="px-4 py-3 text-right">Score</th>
                <th className="px-4 py-3 text-center">Grade</th>
                <th className="px-4 py-3 text-left hidden sm:table-cell">Genre</th>
                <th className="px-4 py-3 text-right hidden sm:table-cell">Date</th>
              </tr>
            </thead>
            <tbody>
              {data.entries.map((entry, i) => {
                const rank = offset + i + 1;
                return (
                  <tr
                    key={entry.id}
                    onClick={() => navigate(`/report/${entry.id}`)}
                    className="border-b border-white/[0.04] hover:bg-white/[0.04] cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3 text-gray-500 tabular-nums">
                      {rank <= 3 ? (
                        <span className={`text-xs font-bold ${rank === 1 ? "text-amber-400" : rank === 2 ? "text-gray-300" : "text-orange-400"}`}>
                          {rank}
                        </span>
                      ) : (
                        rank
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {entry.image_url ? (
                        <img
                          src={entry.image_url}
                          alt=""
                          className="w-8 h-8 rounded object-cover"
                        />
                      ) : (
                        <div className="w-8 h-8 rounded bg-white/[0.05] flex items-center justify-center">
                          <ImageIcon className="w-3.5 h-3.5 text-gray-600" />
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-white truncate max-w-[200px]">
                      {entry.filename || "Untitled"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-16 h-1.5 rounded-full bg-white/[0.06] hidden md:block">
                          <div
                            className={`h-full rounded-full ${getScoreBarClass(entry.overall_score)}`}
                            style={{ width: `${entry.overall_score}%` }}
                          />
                        </div>
                        <span className="text-white tabular-nums" style={{ fontWeight: 600 }}>
                          {entry.overall_score.toFixed(1)}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-0.5 rounded text-xs border ${getGradeBg(entry.grade)} ${getGradeColor(entry.grade)}`} style={{ fontWeight: 700 }}>
                        {entry.grade}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500 hidden sm:table-cell">
                      {entry.genre || "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-right hidden sm:table-cell">
                      {new Date(entry.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Grid View */}
      {viewMode === "grid" && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {data.entries.map((entry, i) => {
            const rank = offset + i + 1;
            return (
              <button
                key={entry.id}
                onClick={() => navigate(`/report/${entry.id}`)}
                className="text-left bg-white/[0.03] border border-white/[0.06] rounded-xl overflow-hidden hover:border-white/[0.12] transition-colors group relative"
              >
                <div className="absolute top-2 left-2 z-10 px-1.5 py-0.5 rounded bg-black/60 text-white text-[10px]" style={{ fontWeight: 700 }}>
                  #{rank}
                </div>
                {entry.image_url ? (
                  <img
                    src={entry.image_url}
                    alt={entry.filename}
                    className="w-full h-32 object-cover"
                  />
                ) : (
                  <div className="w-full h-32 bg-white/[0.02] flex items-center justify-center">
                    <ImageIcon className="w-8 h-8 text-gray-700" />
                  </div>
                )}
                <div className="p-3 space-y-1.5">
                  <p className="text-xs text-gray-300 truncate">{entry.filename || "Untitled"}</p>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-white" style={{ fontWeight: 700 }}>
                      {entry.overall_score.toFixed(1)}
                    </span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] border ${getGradeBg(entry.grade)} ${getGradeColor(entry.grade)}`} style={{ fontWeight: 700 }}>
                      {entry.grade}
                    </span>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            disabled={offset === 0}
            className="px-3 py-1.5 rounded-lg text-xs bg-white/[0.03] text-gray-400 hover:text-white disabled:opacity-30 disabled:hover:text-gray-400 transition-colors"
          >
            Previous
          </button>
          <span className="text-xs text-gray-500">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => setOffset(offset + PAGE_SIZE)}
            disabled={currentPage >= totalPages}
            className="px-3 py-1.5 rounded-lg text-xs bg-white/[0.03] text-gray-400 hover:text-white disabled:opacity-30 disabled:hover:text-gray-400 transition-colors"
          >
            Next
          </button>
        </div>
      )}

      {loading && data && (
        <div className="flex justify-center py-4">
          <Loader2 className="w-5 h-5 text-gray-500 animate-spin" />
        </div>
      )}
    </div>
  );
}
