Design a web dashboard frontend for "VisionScore" — an AI-powered photo evaluation tool that scores images on technical quality, aesthetics, composition, and provides natural language AI feedback.

Product Context
VisionScore is a Python backend (FastAPI REST API) that accepts an image upload, runs it through 4 AI/CV analyzers in parallel, and returns a detailed quality report with scores, a letter grade, and actionable feedback. The frontend needs to be the web interface for this API.

Backend API (already built)
Base URL: /api/v1

Endpoint	Method	Purpose
/health	GET	Health check (returns version, Supabase status)
/analyze	POST	Upload image → get full analysis report (no persistence)
/analyze/save	POST	Upload image → analyze → save to database
/reports	GET	List saved reports (paginated: limit, offset)
/reports/{id}	GET	Get a single saved report
/reports/{id}	DELETE	Delete a saved report
Upload constraints: JPEG, PNG, WebP only. Max 20MB. Multipart form upload.

Query params on /analyze: skip_ai (boolean), weights (string like 25:30:25:20 for custom scoring weights).

Data Model — Analysis Report
Each report contains:


{
  "image_meta": {
    "path": "photo.jpg",
    "width": 4032,
    "height": 3024,
    "format": "JPEG",
    "exif": { "camera": "iPhone 15 Pro", "iso": 50, "aperture": "f/1.8", "shutter_speed": "1/120", "focal_length": "24mm", ... }
  },
  "technical": {
    "sharpness": 82.3,
    "exposure": 91.0,
    "noise": 88.5,
    "dynamic_range": 75.2,
    "overall": 84.1
  },
  "aesthetic": {
    "nima_score": 72.5,
    "std_dev": 1.8,
    "confidence": 0.85,
    "overall": 72.5
  },
  "composition": {
    "rule_of_thirds": 88.0,
    "subject_position": 76.3,
    "horizon": 95.0,
    "balance": 70.1,
    "overall": 83.2
  },
  "ai_feedback": {
    "description": "A golden hour beach landscape with dramatic cloud formations",
    "genre": "landscape",
    "strengths": ["Excellent golden hour lighting", "Strong leading lines from shoreline"],
    "improvements": ["Consider leveling the horizon (-2°)", "Foreground could use more interest"],
    "mood": "serene",
    "score": 78.0,
    "reasoning": "Strong natural lighting and composition with minor technical issues"
  },
  "overall_score": 78.3,
  "grade": "B",
  "analysis_time_seconds": 3.2,
  "timestamp": "2026-03-06T14:30:00"
}
Scoring System
All scores are 0–100
4 categories with default weights: Technical (25%), Aesthetic (30%), Composition (25%), AI Feedback (20%)
Letter grades: S (95–100, exceptional), A (85–94, excellent), B (70–84, good), C (55–69, average), D (40–54, below average), F (0–39, poor)
Sub-scores within each category (e.g., Technical has Sharpness, Exposure, Noise, Dynamic Range)
Users can customize weights. Missing analyzers have weight automatically redistributed.
Pages / Views to Design
1. Landing / Upload Page
Hero section explaining VisionScore (AI photo scoring tool)
Large drag-and-drop upload zone (accepts JPEG, PNG, WebP, max 20MB)
Option to toggle "Skip AI Feedback" before uploading
Optional advanced settings: custom weights slider (4 sliders for Technical/Aesthetic/Composition/AI that must sum to 100%)
Clean, modern, dark-mode-first design
2. Analysis Results Page
Image preview — the uploaded photo displayed prominently
Overall score — large, prominent display with the letter grade (S/A/B/C/D/F) styled as a badge. Color-coded: S=gold, A=green, B=blue, C=yellow, D=orange, F=red
Category score cards — 4 cards for Technical, Aesthetic, Composition, AI Feedback, each showing:
Category name and weight percentage
Overall category score with a circular progress indicator or radial chart
Sub-score breakdown (e.g., Sharpness 82, Exposure 91, Noise 88, Dynamic Range 75 for Technical) shown as horizontal progress bars, color-coded by score quality
AI Feedback section — displays:
Genre tag/badge (e.g., "Landscape")
Mood tag (e.g., "Serene")
Scene description paragraph
Strengths listed with green check icons
Improvements listed with yellow/amber suggestion icons
AI reasoning text
Image metadata panel (collapsible) — EXIF data: camera, lens, ISO, aperture, shutter speed, focal length, dimensions
Actions: Save report, download as JSON, download as Markdown, analyze another image
Show analysis time (e.g., "Analyzed in 3.2s")
Loading state: show progress/skeleton while analysis runs (it takes a few seconds)
3. Reports History / Dashboard Page
Grid or list view of previously saved reports
Each card shows: image thumbnail, overall score badge, grade, genre tag, date analyzed
Pagination controls
Click a card to view the full report
Delete button with confirmation
Search/filter by grade, genre, date range
Empty state when no reports exist
4. Report Detail Page (viewing a saved report)
Same layout as the Analysis Results page but loaded from a saved report
"Delete report" action with confirmation modal
"Analyze another" button to go back to upload
Design Guidelines
Style: Modern, clean, minimal. Think professional photography tool — not cluttered.
Color scheme: Dark mode primary (dark grays/blacks with subtle gradients). Accent colors for scores (green spectrum for high scores, red spectrum for low). Optional light mode toggle.
Typography: Clean sans-serif. Large scores should feel impactful. Use monospace or display font for the letter grade.
Score visualization: Use radial/circular charts for category overalls, horizontal bars for sub-scores, and a large prominent display for the overall score. Color transitions: green (80-100), blue (60-79), yellow (40-59), red (0-39).
Responsive: Design for desktop-first but should work on tablet and mobile.
Interactions: Drag-and-drop upload with visual feedback, smooth transitions when results load, hover states on score cards to reveal sub-score details.
Brand feel: Technical but approachable. Like a tool a professional photographer would trust. Think Lightroom meets a modern analytics dashboard.
Component Library Needs
Score badge component (circular, with grade letter)
Progress bar component (horizontal, color-coded)
Upload dropzone component
Report card component (for history grid)
Category score card component
Feedback list component (strengths/improvements)
Metadata table component
Navigation bar
Loading skeleton/spinner states
