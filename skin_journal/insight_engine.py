"""
Rule-based skin insight engine — v2.
Produces per-concern trend insights with data-backed reasons and confidence levels.
"""
from __future__ import annotations
from typing import Any


# ── Helpers ───────────────────────────────────────────────────────────────────

def _confidence(values: list[int]) -> str:
    n = len(values)
    if n >= 7:  return "high"
    if n >= 4:  return "medium"
    return "low"


def _has_spike(values: list[int]) -> bool:
    return any(values[i] - values[i - 1] >= 2 for i in range(1, len(values)))


def _repeating_plateau(values: list[int]) -> bool:
    """True if the last 3+ values are identical."""
    return len(values) >= 3 and len(set(values[-3:])) == 1


# ── Per-concern insight ───────────────────────────────────────────────────────

def _concern_insight(concern: str, values: list[int]) -> dict[str, Any]:
    label = concern.replace("_", " ").title()

    if len(values) < 2:
        return {
            "concern":    concern,
            "label":      label,
            "title":      f"{label} — not enough data",
            "reason":     "Log at least 2 entries to see a trend.",
            "confidence": "low",
            "trend":      "none",
        }

    start     = values[0]
    end       = values[-1]
    change    = end - start
    variation = max(values) - min(values)
    conf      = _confidence(values)
    n         = len(values)

    if change < 0:
        return {
            "concern":    concern,
            "label":      label,
            "title":      f"{label} is improving",
            "reason":     f"Score dropped from {start} to {end} over {n} entries.",
            "confidence": conf,
            "trend":      "improving",
        }

    if change > 0:
        hint = " Check for new products or dietary changes." if _has_spike(values) else ""
        return {
            "concern":    concern,
            "label":      label,
            "title":      f"{label} is worsening",
            "reason":     f"Score rose from {start} to {end} over {n} entries.{hint}",
            "confidence": conf,
            "trend":      "worsening",
        }

    if variation >= 2:
        extra = " Scores have been repeating recently — possibly a plateau." if _repeating_plateau(values) else ""
        return {
            "concern":    concern,
            "label":      label,
            "title":      f"{label} is fluctuating",
            "reason":     f"Scores ranged {min(values)}–{max(values)}, showing inconsistency.{extra}",
            "confidence": conf,
            "trend":      "fluctuating",
        }

    return {
        "concern":    concern,
        "label":      label,
        "title":      f"{label} is stable",
        "reason":     f"Score held around {end} with minimal variation across {n} entries.",
        "confidence": conf,
        "trend":      "stable",
    }


# ── Summary ───────────────────────────────────────────────────────────────────

def _summary(insights: list[dict]) -> str:
    improving  = [i for i in insights if i["trend"] == "improving"]
    worsening  = [i for i in insights if i["trend"] == "worsening"]
    fluctuating = [i for i in insights if i["trend"] == "fluctuating"]

    if improving and not worsening and not fluctuating:
        return "Your skin is showing consistent improvement. Keep up your current routine."
    if worsening and not improving:
        return "Some concerns are trending upward. Consider reviewing your skincare routine."
    if improving and worsening:
        return "Mixed trends — some concerns are improving while others need attention."
    if fluctuating:
        return "Your skin is fluctuating. Try to maintain a more consistent daily routine."
    return "Your skin condition is relatively stable with no major changes detected."


# ── Public API ────────────────────────────────────────────────────────────────

def get_insights(data: list[dict]) -> dict[str, Any]:
    """
    Main entry point.

    Args:
        data: list of dicts with keys: acne, dark_spots, wrinkles (int 0–5)

    Returns:
        {
            "insights": [ {concern, label, title, reason, confidence, trend}, ... ],
            "summary":  str,
        }
    """
    if not data:
        return {
            "insights": [],
            "summary":  "No journal entries yet. Start logging to see your skin trends.",
        }

    concerns = ["acne", "dark_spots", "wrinkles"]
    insights = []

    for concern in concerns:
        values = [int(e[concern]) for e in data if e.get(concern) is not None]
        if values:
            insights.append(_concern_insight(concern, values))

    return {
        "insights": insights,
        "summary":  _summary(insights),
    }
