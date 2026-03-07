import { CheckCircle, AlertTriangle, Sparkles, Quote } from "lucide-react";

interface FeedbackSectionProps {
  feedback: {
    description: string;
    genre: string;
    strengths: string[];
    improvements: string[];
    mood: string;
    score: number;
    reasoning: string;
  };
}

export function FeedbackSection({ feedback }: FeedbackSectionProps) {
  return (
    <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-6 space-y-5">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-purple-500/10">
          <Sparkles className="w-5 h-5 text-purple-400" />
        </div>
        <h3 className="text-white">AI Feedback</h3>
      </div>

      <div className="flex flex-wrap gap-2">
        <span className="px-3 py-1 rounded-full text-xs bg-indigo-500/15 text-indigo-300 border border-indigo-500/20">
          {feedback.genre}
        </span>
        <span className="px-3 py-1 rounded-full text-xs bg-violet-500/15 text-violet-300 border border-violet-500/20">
          {feedback.mood}
        </span>
      </div>

      <p className="text-gray-300 text-sm">{feedback.description}</p>

      <div className="space-y-2">
        <h4 className="text-emerald-400 text-sm flex items-center gap-2">
          <CheckCircle className="w-4 h-4" /> Strengths
        </h4>
        {feedback.strengths.map((s, i) => (
          <div key={i} className="flex items-start gap-2 text-sm text-gray-300 pl-6">
            <span className="text-emerald-400/60 mt-0.5">•</span>
            <span>{s}</span>
          </div>
        ))}
      </div>

      <div className="space-y-2">
        <h4 className="text-amber-400 text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" /> Improvements
        </h4>
        {feedback.improvements.map((s, i) => (
          <div key={i} className="flex items-start gap-2 text-sm text-gray-300 pl-6">
            <span className="text-amber-400/60 mt-0.5">•</span>
            <span>{s}</span>
          </div>
        ))}
      </div>

      <div className="bg-white/[0.03] rounded-lg p-4 border border-white/[0.04]">
        <div className="flex items-start gap-2">
          <Quote className="w-4 h-4 text-gray-500 mt-0.5 shrink-0" />
          <p className="text-sm text-gray-400 italic">{feedback.reasoning}</p>
        </div>
      </div>
    </div>
  );
}
