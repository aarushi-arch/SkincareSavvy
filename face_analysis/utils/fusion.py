"""
YOLO + MobileNet confidence fusion.

Combines:
  - MobileNet per-class probability (calibrated via temperature scaling)
  - YOLO detection scores for the same concern label

Returns a single fused score and a human-readable confidence label.
"""
from __future__ import annotations
import numpy as np


# ── Temperature scaling ───────────────────────────────────────────────────────

def calibrate(prob: float, temperature: float = 1.5) -> float:
    """
    Soften overconfident probabilities via temperature scaling.
    MobileNet often outputs values close to 1.0 — this brings them
    into a more realistic range.
    """
    prob = float(np.clip(prob, 1e-6, 1 - 1e-6))
    logit = np.log(prob / (1 - prob))
    return float(1 / (1 + np.exp(-logit / temperature)))


# ── YOLO aggregation ──────────────────────────────────────────────────────────

def aggregate_yolo(detections: list[dict], label: str, conf_threshold: float = 0.15) -> float:
    """
    Aggregate YOLO detection confidences for a specific concern label.

    Args:
        detections:     list of {label, confidence, box}
        label:          concern label to filter on (case-insensitive)
        conf_threshold: ignore detections below this

    Returns:
        aggregated score 0–1
    """
    label_l = label.lower()
    valid = [
        d["confidence"] for d in detections
        if d.get("label", "").lower() == label_l
        and d["confidence"] >= conf_threshold
    ]

    if not valid:
        # No matching detections — use all detections as a weak signal
        all_valid = [d["confidence"] for d in detections if d["confidence"] >= conf_threshold]
        if not all_valid:
            return 0.0
        valid = all_valid

    mean_conf = float(np.mean(valid))
    max_conf  = float(np.max(valid))
    return (0.6 * max_conf) + (0.4 * mean_conf)


# ── Fusion ────────────────────────────────────────────────────────────────────

def fuse(
    mobilenet_conf: float,
    yolo_detections: list[dict],
    concern_label: str,
    mobilenet_weight: float = 0.70,
    yolo_weight: float      = 0.30,
    temperature: float      = 2.0,
    conf_threshold: float   = 0.15,
) -> dict:
    """
    Fuse MobileNet + YOLO scores for a single concern.

    Args:
        mobilenet_conf:   raw MobileNet probability for this concern (0–1)
        yolo_detections:  list of YOLO detection dicts
        concern_label:    concern name (e.g. "acne", "wrinkles")
        mobilenet_weight: weight for MobileNet in fusion (default 0.70)
        yolo_weight:      weight for YOLO in fusion (default 0.30)
        temperature:      calibration temperature (default 1.5)
        conf_threshold:   minimum YOLO confidence to include (default 0.15)

    Returns:
        {
            "final_score":           float 0–1,
            "final_pct":             int   0–100,
            "mobilenet_calibrated":  float,
            "yolo_score":            float,
            "label":                 str,   # human-readable tier
        }
    """
    cal_mobilenet = calibrate(mobilenet_conf, temperature)
    yolo_score    = aggregate_yolo(yolo_detections, concern_label, conf_threshold)

    final = (mobilenet_weight * cal_mobilenet) + (yolo_weight * yolo_score)
    final = float(np.clip(final, 0.0, 1.0))

    if final > 0.75:
        tier = "High"
    elif final > 0.50:
        tier = "Moderate"
    elif final > 0.30:
        tier = "Low"
    else:
        tier = "None"

    return {
        "final_score":          round(final, 4),
        "final_pct":            round(final * 100),
        "mobilenet_calibrated": round(cal_mobilenet, 4),
        "yolo_score":           round(yolo_score, 4),
        "tier":                 tier,
    }


# ── Batch fusion for all concerns ─────────────────────────────────────────────

def fuse_all(
    mobilenet_predictions: list[dict],
    yolo_detections: list[dict],
    **kwargs,
) -> list[dict]:
    """
    Apply fusion to every MobileNet prediction.

    Args:
        mobilenet_predictions: list of {class, confidence} from MobileNet
        yolo_detections:       list of YOLO detection dicts
        **kwargs:              forwarded to fuse()

    Returns:
        list of {class, confidence (fused), tier, ...} sorted by final_score desc
    """
    fused = []
    for pred in mobilenet_predictions:
        label = pred.get("class", "")
        raw   = float(pred.get("confidence", 0))
        result = fuse(raw, yolo_detections, label, **kwargs)
        fused.append({
            "class":      label,
            "confidence": result["final_score"],
            "final_pct":  result["final_pct"],
            "tier":       result["tier"],
            "mobilenet_calibrated": result["mobilenet_calibrated"],
            "yolo_score": result["yolo_score"],
        })

    return sorted(fused, key=lambda x: x["confidence"], reverse=True)
