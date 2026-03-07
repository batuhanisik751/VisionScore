import { getGradeColor, getScoreColor } from "./mock-data";

interface ScoreBadgeProps {
  score: number;
  grade: string;
  size?: "sm" | "md" | "lg";
}

export function ScoreBadge({ score, grade, size = "md" }: ScoreBadgeProps) {
  const dimensions = size === "lg" ? 180 : size === "md" ? 120 : 80;
  const strokeWidth = size === "lg" ? 8 : size === "md" ? 6 : 4;
  const radius = (dimensions - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;
  const color = getScoreColor(score);

  return (
    <div className="relative flex items-center justify-center" style={{ width: dimensions, height: dimensions }}>
      <svg width={dimensions} height={dimensions} className="-rotate-90">
        <circle
          cx={dimensions / 2}
          cy={dimensions / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={dimensions / 2}
          cy={dimensions / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={circumference - progress}
          strokeLinecap="round"
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className={`${size === "lg" ? "text-4xl" : size === "md" ? "text-2xl" : "text-lg"} tabular-nums`}
          style={{ color, fontWeight: 700 }}
        >
          {Math.round(score)}
        </span>
        <span
          className={`${getGradeColor(grade)} ${size === "lg" ? "text-lg" : size === "md" ? "text-sm" : "text-xs"} font-mono`}
          style={{ fontWeight: 700 }}
        >
          {grade}
        </span>
      </div>
    </div>
  );
}

interface CircularScoreProps {
  score: number;
  label: string;
  size?: number;
}

export function CircularScore({ score, label, size = 80 }: CircularScoreProps) {
  const strokeWidth = 4;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;
  const color = getScoreColor(score);

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={strokeWidth} />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={circumference - progress}
            strokeLinecap="round"
            className="transition-all duration-1000 ease-out"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-sm tabular-nums" style={{ color, fontWeight: 600 }}>{Math.round(score)}</span>
        </div>
      </div>
      <span className="text-xs text-gray-400">{label}</span>
    </div>
  );
}
