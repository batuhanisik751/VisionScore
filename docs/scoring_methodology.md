# Scoring Methodology

VisionScore evaluates images across four categories, combining them into an overall score (0-100) with a letter grade.

## Overall Score

```
overall = technical × 0.25 + aesthetic × 0.30 + composition × 0.25 + ai_feedback × 0.20
```

If an analyzer is unavailable (e.g., no NIMA weights, no Ollama), its weight is redistributed proportionally among the remaining analyzers.

### Grade Scale

| Grade | Score Range | Description |
|-------|------------|-------------|
| S | 95 -- 100 | Exceptional |
| A | 85 -- 94 | Excellent |
| B | 70 -- 84 | Good |
| C | 55 -- 69 | Average |
| D | 40 -- 54 | Below average |
| F | 0 -- 39 | Poor |

---

## 1. Technical Quality (25%)

Weighted combination of four objective metrics.

| Sub-metric | Weight | Algorithm |
|------------|--------|-----------|
| Sharpness | 35% | Laplacian variance + Sobel gradient |
| Exposure | 30% | LAB L-channel analysis |
| Noise | 20% | Immerkaer estimation |
| Dynamic Range | 15% | Percentile tonal utilization |

### Sharpness

Dual-component scoring:

**Laplacian component (70%):** Computes variance of `cv2.Laplacian(gray, CV_64F)`. Mapped via sigmoid:

```
score = 100 / (1 + exp(-2 * (ln(variance) - ln(100))))
```

**Sobel component (30%):** Mean magnitude of Sobel X/Y gradients, mapped via sigmoid with reference magnitude 20.

### Exposure

Analyzes the L-channel of LAB color space:

- **In-range (40-220):** Score based on deviation from center (130). Perfect center = 100, edge of range = 70.
- **Out-of-range:** Steep falloff, max score 70.
- **Clipping penalty:** Pixels at L <= 5 or L >= 250 incur up to 60-point penalty.

### Noise

Uses the Immerkaer method -- convolves with a specific 3x3 Laplacian kernel, estimates sigma from the absolute sum:

```
sigma = (sum(|convolved|) * sqrt(pi/2)) / (6 * (W-2) * (H-2))
score = 100 * exp(-(ln(2) / 10) * sigma)
```

Clean images (sigma near 0) score ~100; sigma of 10 scores ~50.

### Dynamic Range

Measures tonal utilization between 2nd and 98th percentiles:

```
score = 100 * (tonal_range / 255)^0.8
```

Full-range gradient scores high; flat gray scores near 0.

---

## 2. Aesthetic Quality (30%)

Uses NIMA (Neural Image Assessment) with a MobileNetV2 backbone.

### Model

- Input: 224x224 image, ImageNet-normalized
- Output: 10-class probability distribution over AVA aesthetic scores (1-10)

### Score Conversion

```
mean = sum(probability[i] * i) for i in 1..10
nima_score = (mean - 1) * 100 / 9
```

Maps AVA's 1-10 scale to 0-100.

### Confidence

```
std_dev = sqrt(sum(probability[i] * (i - mean)^2))
confidence = clamp(1 - std_dev / 4.5, 0, 1)
```

Peaked distributions (low std_dev) = high confidence.

---

## 3. Composition (25%)

Combines spatial analysis metrics using spectral residual saliency detection.

| Sub-metric | Weight | What it measures |
|------------|--------|-----------------|
| Rule of Thirds | 40% | Subject proximity to power points |
| Subject Position | 25% | Prominence + edge avoidance |
| Horizon | 20% | Levelness of detected horizon lines |
| Balance | 15% | Left/right and top/bottom symmetry |

### Saliency Detection

FFT-based spectral residual method:
1. Compute log amplitude spectrum
2. Subtract smoothed version (average filter)
3. Reconstruct via inverse FFT
4. Threshold + contour detection to find primary subject centroid

### Rule of Thirds

Distance from subject centroid to nearest power point (1/3, 2/3 intersections):

```
min_dist = min(euclidean(centroid, point)) for each of 4 power points
score = 100 * (1 - (min_dist / 0.9428)^0.7)
```

### Subject Position

50% prominence (Gaussian centered at 17% salient pixel ratio, sigma 0.12) + 50% edge avoidance (50-point penalty per axis if centroid is within 5% of edge).

### Horizon

Canny + HoughLinesP (min length 30% of width). Filters lines within 15 degrees of horizontal. Scores by deviation:
- <= 3 degrees: 10 points/degree penalty
- > 3 degrees: 30 + 5 points/degree penalty
- No horizon detected: neutral score of 75

### Balance

Combines luminance symmetry (LAB L-channel) and edge density symmetry (Canny edges) across left/right (60% weight) and top/bottom (40% weight):

```
score = 100 * (1 - imbalance)^1.5
```

---

## 4. AI Feedback (20%)

Ollama + LLaVA vision LLM provides:
- Genre classification
- Scene description
- Strengths and improvement suggestions
- Quality score (0-100)

The LLM-extracted score is used directly. When Ollama is unavailable, this category is skipped and its weight redistributed.

---

## Calibration Notes

- Thresholds were tuned empirically against a mix of professional and amateur photographs
- The 0.8 power in dynamic range scoring compresses the scale slightly to avoid penalizing images that intentionally use a limited tonal range
- The 1.5 power in balance scoring is conservative -- intentional asymmetry (e.g., a subject on one side) receives a moderate score rather than a harsh penalty
- Horizon detection returns a neutral 75 when no horizon is found, avoiding false penalization of genres like macro or portrait
