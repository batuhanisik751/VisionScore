import { useState, useEffect, useRef, useCallback } from "react";
import { GraduationCap, Upload, Play, RefreshCw, AlertCircle, CheckCircle2, X, FileText } from "lucide-react";

interface TrainingStatus {
  running: boolean;
  progress: {
    status?: string;
    epochs?: number;
    current_epoch?: number;
    best_epoch?: number;
    best_val_loss?: number;
    final_train_loss?: number;
    final_val_loss?: number;
    training_time_seconds?: number;
    total_images?: number;
    output_path?: string;
    error?: string;
  };
}

export function TrainingPage() {
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [imageFiles, setImageFiles] = useState<File[]>([]);
  const [epochs, setEpochs] = useState(20);
  const [batchSize, setBatchSize] = useState(16);
  const [learningRate, setLearningRate] = useState(0.0001);
  const [valSplit, setValSplit] = useState(0.2);
  const [fullFinetune, setFullFinetune] = useState(false);
  const [augment, setAugment] = useState(true);
  const [scale, setScale] = useState<"ava" | "visionscore">("ava");

  const [status, setStatus] = useState<TrainingStatus | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const csvInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch("/api/v1/training/status");
      if (res.ok) {
        const data: TrainingStatus = await res.json();
        setStatus(data);
        // Stop polling when not running
        if (!data.running && pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      }
    } catch {
      // ignore fetch errors during poll
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [fetchStatus]);

  const handleStart = async () => {
    if (!csvFile || imageFiles.length === 0) {
      setError("Please upload a CSV file and training images");
      return;
    }

    setStarting(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("csv_file", csvFile);
      imageFiles.forEach((f) => formData.append("image_files", f));

      const params = new URLSearchParams({
        epochs: String(epochs),
        batch_size: String(batchSize),
        learning_rate: String(learningRate),
        val_split: String(valSplit),
        full_finetune: String(fullFinetune),
        augment: String(augment),
        scale,
      });

      const res = await fetch(`/api/v1/training/start?${params}`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Failed to start training (${res.status})`);
      }

      // Start polling
      pollRef.current = setInterval(fetchStatus, 3000);
      await fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start training");
    } finally {
      setStarting(false);
    }
  };

  const isRunning = status?.running ?? false;
  const progress = status?.progress ?? {};

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl text-white" style={{ fontWeight: 700 }}>
            Training
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Fine-tune the NIMA aesthetic model on your own rated images
          </p>
        </div>
        <button
          onClick={fetchStatus}
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm bg-white/[0.05] text-gray-300 border border-white/[0.08] hover:bg-white/[0.08] transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${isRunning ? "animate-spin" : ""}`} />
          Status
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 mb-6">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
          <button onClick={() => setError(null)} className="ml-auto text-red-400/60 hover:text-red-400">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Status banner */}
      {status && progress.status && (
        <div
          className={`rounded-xl border p-5 mb-6 ${
            progress.status === "completed"
              ? "bg-emerald-500/10 border-emerald-500/20"
              : progress.status === "failed"
              ? "bg-red-500/10 border-red-500/20"
              : "bg-blue-500/10 border-blue-500/20"
          }`}
        >
          <div className="flex items-center gap-3 mb-3">
            {progress.status === "completed" ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            ) : progress.status === "failed" ? (
              <AlertCircle className="w-5 h-5 text-red-400" />
            ) : (
              <div className="w-5 h-5 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin" />
            )}
            <span
              className={`text-sm ${
                progress.status === "completed"
                  ? "text-emerald-400"
                  : progress.status === "failed"
                  ? "text-red-400"
                  : "text-blue-400"
              }`}
              style={{ fontWeight: 600 }}
            >
              {progress.status === "completed"
                ? "Training Complete"
                : progress.status === "failed"
                ? "Training Failed"
                : `Training in Progress — Epoch ${progress.current_epoch || 0} / ${progress.epochs || "?"}`}
            </span>
          </div>

          {progress.status === "failed" && progress.error && (
            <p className="text-xs text-red-400/80">{progress.error}</p>
          )}

          {progress.status === "completed" && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3">
              {[
                { label: "Epochs", value: progress.epochs },
                { label: "Best Epoch", value: progress.best_epoch },
                { label: "Best Val Loss", value: progress.best_val_loss?.toFixed(4) },
                { label: "Time", value: progress.training_time_seconds ? `${Math.round(progress.training_time_seconds)}s` : "—" },
                { label: "Train Loss", value: progress.final_train_loss?.toFixed(4) },
                { label: "Val Loss", value: progress.final_val_loss?.toFixed(4) },
                { label: "Images", value: progress.total_images },
              ]
                .filter((m) => m.value != null)
                .map((m) => (
                  <div key={m.label} className="bg-white/[0.03] rounded-lg p-2.5">
                    <p className="text-[10px] text-gray-500 uppercase tracking-wider">{m.label}</p>
                    <p className="text-sm text-white mt-0.5" style={{ fontWeight: 600 }}>
                      {m.value}
                    </p>
                  </div>
                ))}
            </div>
          )}

          {isRunning && progress.epochs && progress.current_epoch != null && (
            <div className="mt-3">
              <div className="w-full h-2 bg-white/[0.05] rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded-full transition-all duration-500"
                  style={{ width: `${(progress.current_epoch / progress.epochs) * 100}%` }}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Upload section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {/* CSV upload */}
        <div
          onClick={() => !isRunning && csvInputRef.current?.click()}
          className={`bg-white/[0.03] border border-white/[0.06] rounded-xl p-6 text-center cursor-pointer hover:bg-white/[0.05] transition-colors ${
            isRunning ? "opacity-50 pointer-events-none" : ""
          }`}
        >
          <input
            ref={csvInputRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && setCsvFile(e.target.files[0])}
          />
          <FileText className="w-8 h-8 text-gray-400 mx-auto mb-3" />
          {csvFile ? (
            <div>
              <p className="text-sm text-white">{csvFile.name}</p>
              <p className="text-xs text-gray-500 mt-1">
                {(csvFile.size / 1024).toFixed(1)} KB
              </p>
            </div>
          ) : (
            <div>
              <p className="text-sm text-gray-300">Upload Ratings CSV</p>
              <p className="text-xs text-gray-500 mt-1">Format: filename,score</p>
            </div>
          )}
        </div>

        {/* Images upload */}
        <div
          onClick={() => !isRunning && imageInputRef.current?.click()}
          className={`bg-white/[0.03] border border-white/[0.06] rounded-xl p-6 text-center cursor-pointer hover:bg-white/[0.05] transition-colors ${
            isRunning ? "opacity-50 pointer-events-none" : ""
          }`}
        >
          <input
            ref={imageInputRef}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={(e) => e.target.files && setImageFiles(Array.from(e.target.files))}
          />
          <Upload className="w-8 h-8 text-gray-400 mx-auto mb-3" />
          {imageFiles.length > 0 ? (
            <div>
              <p className="text-sm text-white">{imageFiles.length} images selected</p>
              <p className="text-xs text-gray-500 mt-1">
                {(imageFiles.reduce((s, f) => s + f.size, 0) / 1024 / 1024).toFixed(1)} MB total
              </p>
            </div>
          ) : (
            <div>
              <p className="text-sm text-gray-300">Upload Training Images</p>
              <p className="text-xs text-gray-500 mt-1">Select multiple image files</p>
            </div>
          )}
        </div>
      </div>

      {/* Hyperparameters */}
      <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-5 mb-6">
        <h3 className="text-white text-sm mb-4" style={{ fontWeight: 600 }}>
          Configuration
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Epochs</label>
            <input
              type="number"
              min={1}
              max={200}
              value={epochs}
              onChange={(e) => setEpochs(Number(e.target.value))}
              disabled={isRunning}
              className="w-full bg-white/[0.05] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white disabled:opacity-50"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Batch Size</label>
            <input
              type="number"
              min={1}
              max={128}
              value={batchSize}
              onChange={(e) => setBatchSize(Number(e.target.value))}
              disabled={isRunning}
              className="w-full bg-white/[0.05] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white disabled:opacity-50"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Learning Rate</label>
            <input
              type="number"
              step={0.00001}
              min={0.000001}
              max={0.01}
              value={learningRate}
              onChange={(e) => setLearningRate(Number(e.target.value))}
              disabled={isRunning}
              className="w-full bg-white/[0.05] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white disabled:opacity-50"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Validation Split</label>
            <input
              type="number"
              step={0.05}
              min={0.05}
              max={0.5}
              value={valSplit}
              onChange={(e) => setValSplit(Number(e.target.value))}
              disabled={isRunning}
              className="w-full bg-white/[0.05] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white disabled:opacity-50"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Score Scale</label>
            <select
              value={scale}
              onChange={(e) => setScale(e.target.value as "ava" | "visionscore")}
              disabled={isRunning}
              className="w-full bg-white/[0.05] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-white disabled:opacity-50"
            >
              <option value="ava">AVA (1-10)</option>
              <option value="visionscore">VisionScore (0-100)</option>
            </select>
          </div>
        </div>

        {/* Toggle options */}
        <div className="flex items-center gap-6 mt-4 pt-4 border-t border-white/[0.06]">
          <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
            <button
              onClick={() => !isRunning && setFullFinetune(!fullFinetune)}
              disabled={isRunning}
              className={`w-9 h-5 rounded-full transition-colors relative ${fullFinetune ? "bg-blue-500" : "bg-white/10"}`}
            >
              <div
                className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${fullFinetune ? "left-[18px]" : "left-0.5"}`}
              />
            </button>
            Full Fine-tune
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
            <button
              onClick={() => !isRunning && setAugment(!augment)}
              disabled={isRunning}
              className={`w-9 h-5 rounded-full transition-colors relative ${augment ? "bg-blue-500" : "bg-white/10"}`}
            >
              <div
                className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${augment ? "left-[18px]" : "left-0.5"}`}
              />
            </button>
            Data Augmentation
          </label>
        </div>
      </div>

      {/* Start button */}
      <button
        onClick={handleStart}
        disabled={isRunning || starting || !csvFile || imageFiles.length === 0}
        className={`w-full py-3 rounded-xl transition-all flex items-center justify-center gap-2 text-sm ${
          !isRunning && !starting && csvFile && imageFiles.length > 0
            ? "bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white"
            : "bg-white/[0.05] text-gray-600 cursor-not-allowed"
        }`}
      >
        {starting ? (
          <>
            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            Starting...
          </>
        ) : isRunning ? (
          <>
            <div className="w-4 h-4 border-2 border-gray-500/30 border-t-gray-500 rounded-full animate-spin" />
            Training in Progress...
          </>
        ) : (
          <>
            <GraduationCap className="w-4 h-4" />
            Start Training
          </>
        )}
      </button>
    </div>
  );
}
