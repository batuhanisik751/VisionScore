import { useState, useCallback, useRef } from "react";
import { useNavigate } from "react-router";
import { Upload, Image, X, Settings2, Eye, EyeOff, AlertCircle } from "lucide-react";
import { isAcceptedImage, createPreviewUrl, ACCEPT_ATTR } from "./image-utils";

export function UploadPage() {
  const navigate = useNavigate();
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [skipAI, setSkipAI] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [weights, setWeights] = useState({ technical: 25, aesthetic: 30, composition: 25, ai: 20 });
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(async (f: File) => {
    if (!isAcceptedImage(f)) return;
    setFile(f);
    const url = await createPreviewUrl(f);
    setPreview(url);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
    },
    [handleFile]
  );

  const handleAnalyze = async () => {
    if (!file) return;
    setAnalyzing(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const params = new URLSearchParams();
      if (skipAI) params.set("skip_ai", "true");
      const w = `${weights.technical}:${weights.aesthetic}:${weights.composition}:${weights.ai}`;
      params.set("weights", w);

      const res = await fetch(`/api/v1/analyze?${params}`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Analysis failed (${res.status})`);
      }

      const data = await res.json();
      navigate("/results/new", {
        state: { report: data.report, warnings: data.warnings, imageUrl: preview, file },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setAnalyzing(false);
    }
  };

  const updateWeight = (key: keyof typeof weights, value: number) => {
    const others = Object.keys(weights).filter((k) => k !== key) as (keyof typeof weights)[];
    const remaining = 100 - value;
    const currentOthersSum = others.reduce((s, k) => s + weights[k], 0);
    const newWeights = { ...weights, [key]: value };
    others.forEach((k) => {
      newWeights[k] = currentOthersSum > 0 ? Math.round((weights[k] / currentOthersSum) * remaining) : Math.round(remaining / 3);
    });
    // Fix rounding
    const sum = Object.values(newWeights).reduce((a, b) => a + b, 0);
    if (sum !== 100) newWeights[others[0]] += 100 - sum;
    setWeights(newWeights);
  };

  return (
    <div className="min-h-[calc(100vh-64px)] flex flex-col items-center justify-center px-4 py-12">
      {/* Hero */}
      <div className="text-center mb-10 max-w-2xl">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.05] border border-white/[0.08] text-xs text-gray-400 mb-6">
          <Eye className="w-3 h-3" /> AI-Powered Photo Analysis
        </div>
        <h1 className="text-4xl text-white mb-4" style={{ fontWeight: 700 }}>
          Score your photos with{" "}
          <span className="bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            VisionScore
          </span>
        </h1>
        <p className="text-gray-400">
          Upload any image and get instant AI-powered analysis across technical quality, aesthetics, composition, and more.
        </p>
      </div>

      {/* Upload Zone */}
      <div className="w-full max-w-xl">
        {!file ? (
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all
              ${dragging ? "border-blue-400 bg-blue-400/[0.05]" : "border-white/10 hover:border-white/20 bg-white/[0.02]"}`}
          >
            <input
              ref={inputRef}
              type="file"
              accept={ACCEPT_ATTR}
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
            />
            <div className="flex flex-col items-center gap-4">
              <div className="p-4 rounded-full bg-white/[0.05]">
                <Upload className="w-8 h-8 text-gray-400" />
              </div>
              <div>
                <p className="text-white mb-1">Drop your image here or click to browse</p>
                <p className="text-xs text-gray-500">JPEG, PNG, WebP, or HEIC • Max 20MB</p>
              </div>
            </div>
          </div>
        ) : (
          <div className="relative rounded-2xl overflow-hidden border border-white/10">
            <img src={preview!} alt="Preview" className="w-full max-h-80 object-cover" />
            <button
              onClick={() => {
                setFile(null);
                setPreview(null);
              }}
              className="absolute top-3 right-3 p-1.5 rounded-full bg-black/60 hover:bg-black/80 transition-colors"
            >
              <X className="w-4 h-4 text-white" />
            </button>
            <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/80 to-transparent p-4">
              <div className="flex items-center gap-2 text-sm text-gray-300">
                <Image className="w-4 h-4" />
                <span>{file.name}</span>
                <span className="text-gray-500">({(file.size / 1024 / 1024).toFixed(1)} MB)</span>
              </div>
            </div>
          </div>
        )}

        {/* Options */}
        <div className="mt-6 space-y-4">
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

          {error && (
            <div className="flex items-center gap-2 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {error}
            </div>
          )}

          <button
            onClick={handleAnalyze}
            disabled={!file || analyzing}
            className={`w-full py-3 rounded-xl transition-all flex items-center justify-center gap-2 ${
              file && !analyzing
                ? "bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white"
                : "bg-white/[0.05] text-gray-600 cursor-not-allowed"
            }`}
          >
            {analyzing ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Eye className="w-4 h-4" />
                Analyze Image
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
