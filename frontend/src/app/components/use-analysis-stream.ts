import { useState, useRef, useCallback } from "react";

export interface AnalysisProgress {
  stage: string;
  stageIndex: number;
  totalStages: number;
  message: string;
  percent: number;
}

interface AnalysisStreamOptions {
  skipAI?: boolean;
  skipSuggestions?: boolean;
  weights?: string;
  onComplete?: (data: { report: any; warnings: string[] }) => void;
  onError?: (error: string) => void;
}

interface UseAnalysisStreamReturn {
  analyze: (file: File, options?: AnalysisStreamOptions) => Promise<void>;
  progress: AnalysisProgress | null;
  isAnalyzing: boolean;
  abort: () => void;
}

export function useAnalysisStream(): UseAnalysisStreamReturn {
  const [progress, setProgress] = useState<AnalysisProgress | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const abort = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsAnalyzing(false);
    setProgress(null);
  }, []);

  const analyze = useCallback(
    async (file: File, options: AnalysisStreamOptions = {}) => {
      // Abort any in-flight request
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setIsAnalyzing(true);
      setProgress(null);

      try {
        // Step 1: Upload the file
        const formData = new FormData();
        formData.append("file", file);

        const params = new URLSearchParams();
        if (options.skipAI) params.set("skip_ai", "true");
        if (options.skipSuggestions) params.set("skip_suggestions", "true");
        if (options.weights) params.set("weights", options.weights);

        const uploadRes = await fetch(`/api/v1/analyze/upload?${params}`, {
          method: "POST",
          body: formData,
          signal: controller.signal,
        });

        if (!uploadRes.ok) {
          const body = await uploadRes.json().catch(() => null);
          throw new Error(body?.detail || `Upload failed (${uploadRes.status})`);
        }

        const { task_id } = await uploadRes.json();

        // Step 2: Connect to SSE stream
        const streamRes = await fetch(`/api/v1/analyze/stream/${task_id}`, {
          signal: controller.signal,
        });

        if (!streamRes.ok) {
          const body = await streamRes.json().catch(() => null);
          throw new Error(body?.detail || `Stream failed (${streamRes.status})`);
        }

        const reader = streamRes.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Parse SSE events from buffer
          const blocks = buffer.split("\n\n");
          buffer = blocks.pop()!; // Keep incomplete block in buffer

          for (const block of blocks) {
            if (!block.trim()) continue;

            let eventType = "message";
            let data = "";
            for (const line of block.split("\n")) {
              if (line.startsWith("event: ")) eventType = line.slice(7);
              else if (line.startsWith("data: ")) data = line.slice(6);
            }

            if (!data) continue;
            const parsed = JSON.parse(data);

            if (eventType === "progress") {
              setProgress({
                stage: parsed.stage,
                stageIndex: parsed.stage_index,
                totalStages: parsed.total_stages,
                message: parsed.message,
                percent: parsed.percent,
              });
            } else if (eventType === "complete") {
              options.onComplete?.({ report: parsed.report, warnings: parsed.warnings });
              setIsAnalyzing(false);
              setProgress(null);
              return;
            } else if (eventType === "error") {
              throw new Error(parsed.detail || "Analysis failed");
            }
          }
        }
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        const message = err instanceof Error ? err.message : "Analysis failed";
        options.onError?.(message);
      } finally {
        setIsAnalyzing(false);
        abortRef.current = null;
      }
    },
    []
  );

  return { analyze, progress, isAnalyzing, abort };
}
