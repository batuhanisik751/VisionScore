import { useState, useRef, useEffect, useCallback } from "react";
import { Layers } from "lucide-react";
import { getScoreColor } from "./mock-data";

interface CompositionData {
  rule_of_thirds: number;
  subject_position: number;
  horizon: number;
  balance: number;
  overall: number;
  subject_centroid?: [number, number];
  subject_bbox?: [number, number, number, number];
  horizon_angle?: number | null;
  image_dimensions?: [number, number];
}

interface ImageOverlayProps {
  src: string;
  alt: string;
  composition: CompositionData | null;
  className?: string;
}

const POWER_POINTS: [number, number][] = [
  [1 / 3, 1 / 3],
  [2 / 3, 1 / 3],
  [1 / 3, 2 / 3],
  [2 / 3, 2 / 3],
];

export function ImageOverlay({ src, alt, composition, className }: ImageOverlayProps) {
  const [showOverlay, setShowOverlay] = useState(false);
  const [imgSize, setImgSize] = useState({ width: 0, height: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  const updateSize = useCallback(() => {
    if (imgRef.current) {
      const { clientWidth, clientHeight } = imgRef.current;
      if (clientWidth > 0 && clientHeight > 0) {
        setImgSize({ width: clientWidth, height: clientHeight });
      }
    }
  }, []);

  useEffect(() => {
    const img = imgRef.current;
    if (!img) return;

    // Update on load
    img.addEventListener("load", updateSize);

    // ResizeObserver for responsive
    const observer = new ResizeObserver(updateSize);
    observer.observe(img);

    // Initial size if already loaded
    if (img.complete) updateSize();

    return () => {
      img.removeEventListener("load", updateSize);
      observer.disconnect();
    };
  }, [updateSize]);

  const hasOverlayData = composition && (composition.subject_centroid || composition.horizon_angle != null);
  const w = imgSize.width;
  const h = imgSize.height;

  // Scale bbox from analysis image dimensions to display dimensions
  const scaleBbox = (bbox: [number, number, number, number], dims: [number, number]) => {
    const scaleX = w / dims[0];
    const scaleY = h / dims[1];
    return {
      x: bbox[0] * scaleX,
      y: bbox[1] * scaleY,
      w: bbox[2] * scaleX,
      h: bbox[3] * scaleY,
    };
  };

  return (
    <div ref={containerRef} className={`relative ${className || ""}`}>
      <img
        ref={imgRef}
        src={src}
        alt={alt}
        className="w-full max-h-[420px] object-cover"
      />

      {/* Toggle button */}
      {composition && (
        <button
          onClick={() => setShowOverlay(!showOverlay)}
          className={`absolute top-3 right-3 p-2 rounded-lg backdrop-blur-md transition-all ${
            showOverlay
              ? "bg-blue-500/30 border border-blue-400/40 text-blue-300"
              : "bg-black/40 border border-white/10 text-gray-400 hover:text-white"
          }`}
          title={showOverlay ? "Hide composition overlay" : "Show composition overlay"}
        >
          <Layers className="w-4 h-4" />
        </button>
      )}

      {/* SVG Overlay */}
      {showOverlay && composition && w > 0 && h > 0 && (
        <svg
          className="absolute top-0 left-0 pointer-events-none"
          width={w}
          height={h}
          viewBox={`0 0 ${w} ${h}`}
        >
          {/* Rule of thirds grid lines */}
          <line x1={w / 3} y1={0} x2={w / 3} y2={h} stroke="rgba(255,255,255,0.3)" strokeWidth={1} />
          <line x1={(2 * w) / 3} y1={0} x2={(2 * w) / 3} y2={h} stroke="rgba(255,255,255,0.3)" strokeWidth={1} />
          <line x1={0} y1={h / 3} x2={w} y2={h / 3} stroke="rgba(255,255,255,0.3)" strokeWidth={1} />
          <line x1={0} y1={(2 * h) / 3} x2={w} y2={(2 * h) / 3} stroke="rgba(255,255,255,0.3)" strokeWidth={1} />

          {/* Power point indicators */}
          {POWER_POINTS.map(([px, py], i) => (
            <circle
              key={i}
              cx={px * w}
              cy={py * h}
              r={5}
              fill={getScoreColor(composition.rule_of_thirds)}
              fillOpacity={0.6}
              stroke="white"
              strokeWidth={1}
              strokeOpacity={0.5}
            />
          ))}

          {/* Subject bounding box */}
          {composition.subject_bbox && composition.image_dimensions && (
            (() => {
              const b = scaleBbox(composition.subject_bbox!, composition.image_dimensions!);
              return (
                <rect
                  x={b.x}
                  y={b.y}
                  width={b.w}
                  height={b.h}
                  fill="none"
                  stroke={getScoreColor(composition.subject_position)}
                  strokeWidth={2}
                  strokeDasharray="6 3"
                  strokeOpacity={0.7}
                />
              );
            })()
          )}

          {/* Subject centroid dot */}
          {composition.subject_centroid && (
            <>
              {/* Pulse ring */}
              <circle
                cx={composition.subject_centroid[0] * w}
                cy={composition.subject_centroid[1] * h}
                r={12}
                fill="none"
                stroke={getScoreColor(composition.subject_position)}
                strokeWidth={1.5}
                strokeOpacity={0.5}
              >
                <animate attributeName="r" values="8;16;8" dur="2s" repeatCount="indefinite" />
                <animate attributeName="stroke-opacity" values="0.6;0;0.6" dur="2s" repeatCount="indefinite" />
              </circle>
              {/* Center dot */}
              <circle
                cx={composition.subject_centroid[0] * w}
                cy={composition.subject_centroid[1] * h}
                r={5}
                fill={getScoreColor(composition.subject_position)}
                stroke="white"
                strokeWidth={1.5}
              />
            </>
          )}

          {/* Horizon tilt indicator */}
          {composition.horizon_angle != null && (
            (() => {
              const angle = composition.horizon_angle!;
              const absAngle = Math.abs(angle);
              const color = absAngle < 1 ? "#34d399" : absAngle < 3 ? "#fbbf24" : "#f87171";
              const rad = (angle * Math.PI) / 180;
              const cx = w / 2;
              const cy = h / 2;
              const lineLen = w * 0.4;
              const x1 = cx - Math.cos(rad) * lineLen;
              const y1 = cy - Math.sin(rad) * lineLen;
              const x2 = cx + Math.cos(rad) * lineLen;
              const y2 = cy + Math.sin(rad) * lineLen;

              return (
                <g>
                  <line
                    x1={x1} y1={y1} x2={x2} y2={y2}
                    stroke={color}
                    strokeWidth={2}
                    strokeOpacity={0.7}
                    strokeDasharray="8 4"
                  />
                  {/* Angle label */}
                  <rect
                    x={x2 - 28}
                    y={y2 - 18}
                    width={56}
                    height={20}
                    rx={4}
                    fill="rgba(0,0,0,0.7)"
                  />
                  <text
                    x={x2}
                    y={y2 - 5}
                    textAnchor="middle"
                    fill={color}
                    fontSize={11}
                    fontFamily="monospace"
                  >
                    {angle > 0 ? "+" : ""}{angle.toFixed(1)}°
                  </text>
                </g>
              );
            })()
          )}
        </svg>
      )}
    </div>
  );
}
