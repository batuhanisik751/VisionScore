export interface AnalysisReport {
  id: string;
  image_url: string;
  image_meta: {
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
  technical: {
    sharpness: number;
    exposure: number;
    noise: number;
    dynamic_range: number;
    overall: number;
  } | null;
  aesthetic: {
    nima_score: number;
    std_dev: number;
    confidence: number;
    overall: number;
  } | null;
  composition: {
    rule_of_thirds: number;
    subject_position: number;
    horizon: number;
    balance: number;
    overall: number;
    subject_centroid?: [number, number];
    subject_bbox?: [number, number, number, number];
    horizon_angle?: number | null;
    image_dimensions?: [number, number];
  } | null;
  ai_feedback: {
    description: string;
    genre: string;
    strengths: string[];
    improvements: string[];
    mood: string;
    score: number;
    reasoning: string;
  } | null;
  overall_score: number;
  grade: string;
  analysis_time_seconds: number;
  timestamp: string;
}

export const MOCK_REPORTS: AnalysisReport[] = [
  {
    id: "rpt-001",
    image_url:
      "https://images.unsplash.com/photo-1723507343767-49fe41ad47db?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxnb2xkZW4lMjBob3VyJTIwYmVhY2glMjBsYW5kc2NhcGUlMjBwaG90b2dyYXBoeXxlbnwxfHx8fDE3NzI4NDY0ODN8MA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral",
    image_meta: {
      path: "golden_hour_beach.jpg",
      width: 4032,
      height: 3024,
      format: "JPEG",
      exif: {
        camera: "iPhone 15 Pro",
        iso: 50,
        aperture: "f/1.8",
        shutter_speed: "1/120",
        focal_length: "24mm",
      },
    },
    technical: { sharpness: 82.3, exposure: 91.0, noise: 88.5, dynamic_range: 75.2, overall: 84.1 },
    aesthetic: { nima_score: 72.5, std_dev: 1.8, confidence: 0.85, overall: 72.5 },
    composition: { rule_of_thirds: 88.0, subject_position: 76.3, horizon: 95.0, balance: 70.1, overall: 83.2 },
    ai_feedback: {
      description: "A golden hour beach landscape with dramatic cloud formations",
      genre: "Landscape",
      strengths: ["Excellent golden hour lighting", "Strong leading lines from shoreline", "Vivid warm tones"],
      improvements: ["Consider leveling the horizon (-2°)", "Foreground could use more interest"],
      mood: "Serene",
      score: 78.0,
      reasoning: "Strong natural lighting and composition with minor technical issues in horizon leveling.",
    },
    overall_score: 78.3,
    grade: "B",
    analysis_time_seconds: 3.2,
    timestamp: "2026-03-06T14:30:00",
  },
  {
    id: "rpt-002",
    image_url:
      "https://images.unsplash.com/photo-1642761684233-9d2d6b0cb4d8?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxtb3VudGFpbiUyMHN1bnJpc2UlMjBkcmFtYXRpYyUyMGxhbmRzY2FwZXxlbnwxfHx8fDE3NzI4NDY0ODN8MA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral",
    image_meta: {
      path: "mountain_sunrise.jpg",
      width: 6000,
      height: 4000,
      format: "JPEG",
      exif: {
        camera: "Sony A7R V",
        iso: 100,
        aperture: "f/8",
        shutter_speed: "1/250",
        focal_length: "35mm",
        lens: "Sony FE 35mm f/1.4 GM",
      },
    },
    technical: { sharpness: 94.1, exposure: 88.5, noise: 96.2, dynamic_range: 91.0, overall: 92.5 },
    aesthetic: { nima_score: 88.3, std_dev: 1.2, confidence: 0.92, overall: 88.3 },
    composition: { rule_of_thirds: 91.0, subject_position: 85.5, horizon: 98.0, balance: 88.2, overall: 90.7 },
    ai_feedback: {
      description: "A dramatic mountain sunrise with layered peaks and golden light breaking through clouds",
      genre: "Landscape",
      strengths: ["Exceptional sharpness throughout", "Perfect exposure for high dynamic range scene", "Masterful use of layered depth"],
      improvements: ["Slight chromatic aberration at edges", "Could benefit from polarizing filter"],
      mood: "Majestic",
      score: 90.0,
      reasoning: "Outstanding technical execution with compelling composition. Near-professional quality.",
    },
    overall_score: 90.4,
    grade: "A",
    analysis_time_seconds: 2.8,
    timestamp: "2026-03-05T09:15:00",
  },
  {
    id: "rpt-003",
    image_url:
      "https://images.unsplash.com/photo-1693946953973-3d9ddaf7a977?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxjaXR5JTIwc2t5bGluZSUyMG5pZ2h0JTIwcGhvdG9ncmFwaHl8ZW58MXx8fHwxNzcyODE5ODcxfDA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral",
    image_meta: {
      path: "city_night.jpg",
      width: 5472,
      height: 3648,
      format: "JPEG",
      exif: {
        camera: "Canon EOS R5",
        iso: 3200,
        aperture: "f/2.8",
        shutter_speed: "1/30",
        focal_length: "24mm",
        lens: "Canon RF 24-70mm f/2.8L",
      },
    },
    technical: { sharpness: 68.5, exposure: 72.0, noise: 55.3, dynamic_range: 62.1, overall: 64.5 },
    aesthetic: { nima_score: 75.8, std_dev: 2.1, confidence: 0.78, overall: 75.8 },
    composition: { rule_of_thirds: 70.2, subject_position: 65.0, horizon: 80.5, balance: 72.3, overall: 72.0 },
    ai_feedback: {
      description: "A city skyline at night with reflections on water and ambient street lighting",
      genre: "Urban",
      strengths: ["Interesting reflections captured", "Good use of ambient light"],
      improvements: ["High ISO noise is visible", "Consider using a tripod for longer exposure", "White balance could be warmer"],
      mood: "Atmospheric",
      score: 62.0,
      reasoning: "Creative composition but hampered by high ISO noise and slight softness from handheld shooting.",
    },
    overall_score: 68.1,
    grade: "C",
    analysis_time_seconds: 4.1,
    timestamp: "2026-03-04T21:45:00",
  },
  {
    id: "rpt-004",
    image_url:
      "https://images.unsplash.com/photo-1506695656850-3a341946425f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxwb3J0cmFpdCUyMHBob3RvZ3JhcGh5JTIwc3R1ZGlvJTIwbGlnaHRpbmd8ZW58MXx8fHwxNzcyNzgwODk4fDA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral",
    image_meta: {
      path: "studio_portrait.jpg",
      width: 3840,
      height: 5760,
      format: "JPEG",
      exif: {
        camera: "Nikon Z8",
        iso: 200,
        aperture: "f/2.0",
        shutter_speed: "1/200",
        focal_length: "85mm",
        lens: "Nikon Z 85mm f/1.2 S",
      },
    },
    technical: { sharpness: 96.0, exposure: 94.5, noise: 98.0, dynamic_range: 85.0, overall: 93.4 },
    aesthetic: { nima_score: 91.2, std_dev: 0.9, confidence: 0.95, overall: 91.2 },
    composition: { rule_of_thirds: 94.0, subject_position: 92.0, horizon: 100.0, balance: 90.5, overall: 94.1 },
    ai_feedback: {
      description: "A professionally lit studio portrait with beautiful bokeh and sharp focus on the subject",
      genre: "Portrait",
      strengths: ["Tack-sharp focus on eyes", "Beautiful creamy bokeh", "Professional studio lighting", "Excellent skin tones"],
      improvements: ["Minor highlight clipping on forehead"],
      mood: "Elegant",
      score: 95.0,
      reasoning: "Exceptional portrait with professional lighting, razor-sharp focus, and masterful depth of field control.",
    },
    overall_score: 95.2,
    grade: "S",
    analysis_time_seconds: 2.5,
    timestamp: "2026-03-03T16:20:00",
  },
];

export function getGradeColor(grade: string): string {
  switch (grade) {
    case "S": return "text-amber-400";
    case "A": return "text-emerald-400";
    case "B": return "text-blue-400";
    case "C": return "text-yellow-400";
    case "D": return "text-orange-400";
    case "F": return "text-red-400";
    default: return "text-gray-400";
  }
}

export function getGradeBg(grade: string): string {
  switch (grade) {
    case "S": return "bg-amber-400/15 border-amber-400/30";
    case "A": return "bg-emerald-400/15 border-emerald-400/30";
    case "B": return "bg-blue-400/15 border-blue-400/30";
    case "C": return "bg-yellow-400/15 border-yellow-400/30";
    case "D": return "bg-orange-400/15 border-orange-400/30";
    case "F": return "bg-red-400/15 border-red-400/30";
    default: return "bg-gray-400/15 border-gray-400/30";
  }
}

export function getScoreColor(score: number): string {
  if (score >= 80) return "#34d399";
  if (score >= 60) return "#60a5fa";
  if (score >= 40) return "#fbbf24";
  return "#f87171";
}

export function getScoreBarClass(score: number): string {
  if (score >= 80) return "bg-emerald-400";
  if (score >= 60) return "bg-blue-400";
  if (score >= 40) return "bg-yellow-400";
  return "bg-red-400";
}
