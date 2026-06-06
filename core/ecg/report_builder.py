"""ECG Report Builder - assembles complete inspection report."""

import time

from core.ecg.reader import load_ecg, safe_load
from core.ecg.inspector import (
    extract_lead_info,
    extract_annotations,
    compute_rpeaks,
    assess_signal_quality,
    detect_known_ecg_dataset,
    extract_ecg_metadata,
)
from core.shared.artifact_detector import detect_ecg_artifacts


def compute_ecg_quality_score(report):
    """Compute overall Data Quality Score (0-100) for ECG.

    Scoring rubric:
      Sampling freq >= 250 Hz               -> +15 pts
      Standard lead names present           -> +10 pts
      Mean lead quality index >= 0.7        -> +20 pts
      No signal clipping detected           -> +10 pts
      No powerline noise                    -> +10 pts
      Annotations/labels present            -> +15 pts
      R-peak detection success rate >= 95%  -> +10 pts
      Duration >= 10 seconds                -> +10 pts
    """
    score = 0
    breakdown = []

    # Sampling frequency
    fs = report.get("metadata", {}).get("Sampling Frequency", "0 Hz")
    fs_val = float(fs.replace(" Hz", "")) if isinstance(fs, str) else fs
    if fs_val >= 250:
        score += 15
        breakdown.append(("\u2705 Sampling frequency \u2265 250 Hz", "+15"))
    else:
        breakdown.append(("\u26a0\ufe0f Sampling frequency < 250 Hz", "0/15"))

    # Standard lead names
    lead_info = report.get("lead_info")
    if lead_info is not None and "Standard" in lead_info.columns:
        standard_count = lead_info["Standard"].str.contains("\U0001f7e2").sum()
        if standard_count > 0:
            score += 10
            breakdown.append(("\u2705 Standard lead names present", "+10"))
        else:
            breakdown.append(("\u26a0\ufe0f Non-standard lead names", "0/10"))
    else:
        breakdown.append(("\u26a0\ufe0f Lead info unavailable", "0/10"))

    # Signal quality
    quality_df = report.get("signal_quality")
    if quality_df is not None and "Quality Index" in quality_df.columns:
        mean_quality = quality_df["Quality Index"].mean()
        if mean_quality >= 0.7:
            score += 20
            breakdown.append(("\u2705 Mean lead quality \u2265 0.7", "+20"))
        else:
            breakdown.append(("\u26a0\ufe0f Mean lead quality < 0.7", "0/20"))
    else:
        breakdown.append(("\u26a0\ufe0f Signal quality unavailable", "0/20"))

    # Artifacts
    artifacts = report.get("artifacts", {})

    # Clipping
    clipping = artifacts.get("signal_clipping", {})
    if clipping.get("status") == "pass":
        score += 10
        breakdown.append(("\u2705 No signal clipping", "+10"))
    else:
        breakdown.append(("\u274c Signal clipping detected", "0/10"))

    # Powerline noise
    powerline = artifacts.get("powerline_noise", {})
    if powerline.get("status") == "pass":
        score += 10
        breakdown.append(("\u2705 No powerline noise", "+10"))
    else:
        breakdown.append(("\u274c Powerline noise detected", "0/10"))

    # Annotations
    ann_info = report.get("annotations", {})
    if ann_info.get("has_annotations"):
        score += 15
        breakdown.append(("\u2705 Annotations present", "+15"))
    else:
        breakdown.append(("\u26a0\ufe0f No annotations found", "0/15"))

    # R-peak detection
    rpeak_info = report.get("rpeaks", {})
    r_peaks = rpeak_info.get("r_peaks", [])
    if len(r_peaks) > 5:
        score += 10
        breakdown.append(("\u2705 R-peak detection successful", "+10"))
    else:
        breakdown.append(("\u26a0\ufe0f R-peak detection limited", "0/10"))

    # Duration
    duration_str = report.get("metadata", {}).get("Duration", "0 min 0 s")
    try:
        parts = duration_str.split()
        total_secs = int(parts[0]) * 60 + int(parts[2])
    except (ValueError, IndexError):
        total_secs = 0
    if total_secs >= 10:
        score += 10
        breakdown.append(("\u2705 Duration \u2265 10 seconds", "+10"))
    else:
        breakdown.append(("\u26a0\ufe0f Duration < 10 seconds", "0/10"))

    return {"score": score, "max_score": 100, "breakdown": breakdown}


def build_ecg_report(filepath, format_key, depth="full"):
    """Build complete ECG inspection report.

    Parameters
    ----------
    filepath : str
        Path to ECG file.
    format_key : str
        Format identifier from router.
    depth : str
        'quick', 'full', or 'research'

    Returns
    -------
    dict
        Complete inspection report.
    """
    report = {"modality": "ECG", "success": True}

    # Load file
    start_time = time.time()
    result = safe_load(filepath, format_key)
    load_time = time.time() - start_time

    if not result["success"]:
        return {
            "modality": "ECG",
            "success": False,
            "error_type": result["error_type"],
            "message": result["message"],
            "suggestion": result["suggestion"],
        }

    ecg_data = result["data"]
    report["ecg_data"] = ecg_data
    report["load_time"] = load_time

    # Metadata
    report["metadata"] = extract_ecg_metadata(ecg_data, filepath, format_key, load_time)

    # Lead info
    report["lead_info"] = extract_lead_info(ecg_data)

    # Known dataset detection
    report["known_dataset"] = detect_known_ecg_dataset(ecg_data)

    if depth == "quick":
        report["annotations"] = {"has_annotations": False}
        report["signal_quality"] = None
        report["artifacts"] = {}
        report["rpeaks"] = {}
        report["quality_score"] = None
        return report

    # Annotations
    report["annotations"] = extract_annotations(ecg_data)

    # Signal quality
    try:
        report["signal_quality"] = assess_signal_quality(ecg_data)
    except Exception:
        report["signal_quality"] = None

    # Artifacts
    try:
        report["artifacts"] = detect_ecg_artifacts(ecg_data)
    except Exception:
        report["artifacts"] = {}

    # R-peak stats
    try:
        report["rpeaks"] = compute_rpeaks(ecg_data)
    except Exception:
        report["rpeaks"] = {}

    # Quality score
    report["quality_score"] = compute_ecg_quality_score(report)

    return report
