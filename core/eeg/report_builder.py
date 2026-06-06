"""EEG Report Builder - assembles complete inspection report."""

import time

from core.eeg.reader import load_eeg, safe_load
from core.eeg.inspector import (
    extract_channel_info,
    extract_events,
    compute_psd,
    compute_faa,
    detect_known_dataset,
    extract_metadata,
)
from core.shared.artifact_detector import detect_eeg_artifacts


def compute_eeg_quality_score(report):
    """Compute overall Data Quality Score (0-100) for EEG.

    Scoring rubric:
      Sampling frequency >= 128 Hz         -> +15 pts
      Channel count >= 8                   -> +10 pts
      No flat/dead channels                -> +15 pts
      No line noise                        -> +15 pts
      EOG artifacts < 20% of recording     -> +10 pts
      EMG gamma ratio < 30%                -> +10 pts
      Duration >= 5 minutes                -> +10 pts
      Events/labels present                -> +10 pts
      Channel locations available          -> +5  pts
    """
    score = 0
    breakdown = []

    # Sampling frequency
    fs = report.get("metadata", {}).get("Sampling Frequency", "0 Hz")
    fs_val = float(fs.replace(" Hz", "")) if isinstance(fs, str) else fs
    if fs_val >= 128:
        score += 15
        breakdown.append(("\u2705 Sampling frequency \u2265 128 Hz", "+15"))
    else:
        breakdown.append(("\u26a0\ufe0f Sampling frequency < 128 Hz", "0/15"))

    # Channel count
    n_ch = report.get("metadata", {}).get("Number of Channels", 0)
    if isinstance(n_ch, str):
        n_ch = int(n_ch) if n_ch.isdigit() else 0
    if n_ch >= 8:
        score += 10
        breakdown.append(("\u2705 Channel count \u2265 8", "+10"))
    else:
        breakdown.append(("\u26a0\ufe0f Channel count < 8", "0/10"))

    # Artifacts
    artifacts = report.get("artifacts", {})

    # Flat channels
    flat = artifacts.get("flat_channels", {})
    if flat.get("status") == "pass":
        score += 15
        breakdown.append(("\u2705 No flat/dead channels", "+15"))
    else:
        breakdown.append(("\u274c Flat channels detected", "0/15"))

    # Line noise
    line_noise = artifacts.get("line_noise", {})
    if line_noise.get("status") == "pass":
        score += 15
        breakdown.append(("\u2705 No line noise", "+15"))
    else:
        breakdown.append(("\u274c Line noise detected", "0/15"))

    # EOG
    eog = artifacts.get("eog_artifacts", {})
    if eog.get("status") in ("pass", "low"):
        score += 10
        breakdown.append(("\u2705 EOG artifacts low", "+10"))
    else:
        breakdown.append(("\u26a0\ufe0f EOG artifacts detected", "0/10"))

    # EMG
    emg = artifacts.get("emg_artifacts", {})
    if emg.get("status") in ("pass", "low"):
        score += 10
        breakdown.append(("\u2705 EMG contamination low", "+10"))
    else:
        breakdown.append(("\u26a0\ufe0f EMG contamination high", "0/10"))

    # Duration
    duration_str = report.get("metadata", {}).get("Duration", "0 min 0 s")
    try:
        parts = duration_str.split()
        mins = int(parts[0])
    except (ValueError, IndexError):
        mins = 0
    if mins >= 5:
        score += 10
        breakdown.append(("\u2705 Duration \u2265 5 minutes", "+10"))
    else:
        breakdown.append(("\u26a0\ufe0f Duration < 5 minutes", "0/10"))

    # Events
    has_events = report.get("events", {}).get("has_events", False)
    if has_events:
        score += 10
        breakdown.append(("\u2705 Events/labels present", "+10"))
    else:
        breakdown.append(("\u26a0\ufe0f No events/labels found", "0/10"))

    # Channel locations
    channel_info = report.get("channel_info")
    has_locs = False
    if channel_info is not None and "Has Location" in channel_info.columns:
        has_locs = channel_info["Has Location"].any()
    if has_locs:
        score += 5
        breakdown.append(("\u2705 Channel locations available", "+5"))
    else:
        breakdown.append(("\u26a0\ufe0f No channel locations", "0/5"))

    return {"score": score, "max_score": 100, "breakdown": breakdown}


def build_eeg_report(filepath, format_key, depth="full"):
    """Build complete EEG inspection report.

    Parameters
    ----------
    filepath : str
        Path to EEG file.
    format_key : str
        Format identifier from router.
    depth : str
        'quick', 'full', or 'research'

    Returns
    -------
    dict
        Complete inspection report.
    """
    report = {"modality": "EEG", "success": True}

    # Load file
    start_time = time.time()
    result = safe_load(filepath, format_key)
    load_time = time.time() - start_time

    if not result["success"]:
        return {
            "modality": "EEG",
            "success": False,
            "error_type": result["error_type"],
            "message": result["message"],
            "suggestion": result["suggestion"],
        }

    raw = result["data"]
    report["raw"] = raw
    report["load_time"] = load_time

    # Metadata
    report["metadata"] = extract_metadata(raw, filepath, format_key, load_time)

    # Channel info
    report["channel_info"] = extract_channel_info(raw)

    # Known dataset detection
    report["known_dataset"] = detect_known_dataset(raw)

    if depth == "quick":
        report["events"] = {"has_events": False}
        report["spectral"] = None
        report["artifacts"] = {}
        report["faa"] = {"available": False}
        report["quality_score"] = None
        return report

    # Events
    report["events"] = extract_events(raw)

    # Spectral analysis
    try:
        report["spectral"] = compute_psd(raw)
    except Exception:
        report["spectral"] = None

    # Artifacts
    try:
        report["artifacts"] = detect_eeg_artifacts(raw)
    except Exception:
        report["artifacts"] = {}

    # FAA
    report["faa"] = compute_faa(raw)

    # Quality score
    report["quality_score"] = compute_eeg_quality_score(report)

    return report
