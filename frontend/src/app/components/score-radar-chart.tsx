import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from "recharts";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "./ui/chart";

interface ScoreRadarChartProps {
  technical: number | null;
  aesthetic: number | null;
  composition: number | null;
  aiFeedback: number | null;
  /** Optional second data series for comparison mode */
  compareTechnical?: number | null;
  compareAesthetic?: number | null;
  compareComposition?: number | null;
  compareAiFeedback?: number | null;
  labelA?: string;
  labelB?: string;
}

const chartConfig: ChartConfig = {
  score: { label: "Score", color: "#60a5fa" },
  compare: { label: "Compare", color: "#a78bfa" },
};

export function ScoreRadarChart({
  technical,
  aesthetic,
  composition,
  aiFeedback,
  compareTechnical,
  compareAesthetic,
  compareComposition,
  compareAiFeedback,
  labelA = "Image A",
  labelB = "Image B",
}: ScoreRadarChartProps) {
  const hasCompare = compareTechnical != null || compareAesthetic != null || compareComposition != null || compareAiFeedback != null;

  const data = [
    {
      category: "Technical",
      score: technical ?? 0,
      ...(hasCompare && { compare: compareTechnical ?? 0 }),
    },
    {
      category: "Aesthetic",
      score: aesthetic ?? 0,
      ...(hasCompare && { compare: compareAesthetic ?? 0 }),
    },
    {
      category: "Composition",
      score: composition ?? 0,
      ...(hasCompare && { compare: compareComposition ?? 0 }),
    },
    {
      category: "AI Feedback",
      score: aiFeedback ?? 0,
      ...(hasCompare && { compare: compareAiFeedback ?? 0 }),
    },
  ];

  const config: ChartConfig = hasCompare
    ? { score: { label: labelA, color: "#60a5fa" }, compare: { label: labelB, color: "#a78bfa" } }
    : chartConfig;

  return (
    <ChartContainer config={config} className="mx-auto aspect-square max-h-[280px] w-full">
      <RadarChart data={data}>
        <PolarGrid stroke="rgba(255,255,255,0.1)" />
        <PolarAngleAxis
          dataKey="category"
          tick={{ fill: "#9ca3af", fontSize: 12 }}
        />
        <PolarRadiusAxis
          angle={90}
          domain={[0, 100]}
          tick={{ fill: "#6b7280", fontSize: 10 }}
          tickCount={5}
        />
        <ChartTooltip
          content={
            <ChartTooltipContent
              labelClassName="text-white"
              formatter={(value, name) => (
                <span className="text-gray-200">
                  {name === "score" ? (hasCompare ? labelA : "Score") : labelB}: {typeof value === "number" ? value.toFixed(1) : value}
                </span>
              )}
            />
          }
        />
        <Radar
          name="score"
          dataKey="score"
          stroke="#60a5fa"
          fill="#60a5fa"
          fillOpacity={hasCompare ? 0.2 : 0.3}
          strokeWidth={2}
          animationDuration={1000}
        />
        {hasCompare && (
          <Radar
            name="compare"
            dataKey="compare"
            stroke="#a78bfa"
            fill="#a78bfa"
            fillOpacity={0.2}
            strokeWidth={2}
            animationDuration={1000}
          />
        )}
      </RadarChart>
    </ChartContainer>
  );
}
