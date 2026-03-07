import { useState } from "react";
import { ChevronDown, Camera } from "lucide-react";

interface MetadataPanelProps {
  meta: {
    path: string;
    width: number;
    height: number;
    format: string;
    exif: {
      camera: string;
      iso: number;
      aperture: string;
      shutter_speed: string;
      focal_length: string;
      lens?: string;
    };
  };
}

export function MetadataPanel({ meta }: MetadataPanelProps) {
  const [open, setOpen] = useState(false);

  const rows = [
    { label: "Camera", value: meta.exif.camera },
    ...(meta.exif.lens ? [{ label: "Lens", value: meta.exif.lens }] : []),
    { label: "ISO", value: String(meta.exif.iso) },
    { label: "Aperture", value: meta.exif.aperture },
    { label: "Shutter Speed", value: meta.exif.shutter_speed },
    { label: "Focal Length", value: meta.exif.focal_length },
    { label: "Dimensions", value: `${meta.width} × ${meta.height}` },
    { label: "Format", value: meta.format },
  ];

  return (
    <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-4 hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex items-center gap-3">
          <Camera className="w-4 h-4 text-gray-400" />
          <span className="text-sm text-gray-300">Image Metadata</span>
        </div>
        <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="px-4 pb-4 pt-1">
          <div className="grid grid-cols-2 gap-x-6 gap-y-2">
            {rows.map((r) => (
              <div key={r.label} className="flex justify-between text-sm py-1">
                <span className="text-gray-500">{r.label}</span>
                <span className="text-gray-300">{r.value}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
