import { CircularScore } from "./score-badge";
import { getScoreBarClass } from "./mock-data";

interface SubScore {
  label: string;
  value: number;
}

interface CategoryCardProps {
  title: string;
  weight: number;
  overall: number;
  subScores: SubScore[];
  icon: React.ReactNode;
}

export function CategoryCard({ title, weight, overall, subScores, icon }: CategoryCardProps) {
  return (
    <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-5 hover:bg-white/[0.05] transition-colors">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-white/[0.06]">{icon}</div>
          <div>
            <h3 className="text-white">{title}</h3>
            <span className="text-xs text-gray-500">{weight}% weight</span>
          </div>
        </div>
        <CircularScore score={overall} label="Overall" size={64} />
      </div>
      <div className="space-y-3">
        {subScores.map((sub) => (
          <div key={sub.label}>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-gray-400">{sub.label}</span>
              <span className="text-gray-300 tabular-nums" style={{ fontWeight: 500 }}>{sub.value.toFixed(1)}</span>
            </div>
            <div className="h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-1000 ease-out ${getScoreBarClass(sub.value)}`}
                style={{ width: `${sub.value}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
