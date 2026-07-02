from __future__ import annotations

from typing import Any, Dict, List


def safe_get(d: Dict[str, Any], *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def classify_false_positive_burden(interictal_json: Dict[str, Any]) -> str:
    frac_pos = safe_get(interictal_json, "window_level_summary", "fraction_predicted_positive", default=None)
    if frac_pos is None:
        return "unknown"
    if frac_pos >= 0.50:
        return "high"
    if frac_pos >= 0.20:
        return "moderate"
    return "low"


def classify_hfo_consensus_strength(hfo_json: Dict[str, Any]) -> str:
    consensus = safe_get(hfo_json, "consensus_summary", default={}) or {}
    strong = consensus.get("strong_consensus_channels", []) or []
    moderate = consensus.get("moderate_consensus_channels", []) or []

    if len(strong) >= 2:
        return "strong"
    if len(strong) == 1 or len(moderate) >= 2:
        return "moderate"
    if len(moderate) >= 1:
        return "limited"
    return "weak"


def build_hfo_candidate_channels(hfo_json: Dict[str, Any]) -> List[str]:
    consensus = safe_get(hfo_json, "consensus_summary", default={}) or {}
    strong = consensus.get("strong_consensus_channels", []) or []
    moderate = consensus.get("moderate_consensus_channels", []) or []
    ordered: List[str] = []
    for ch in strong + moderate:
        if ch and ch not in ordered:
            ordered.append(ch)
    return ordered


def get_seizure_candidate_channels(seizure_ictal_json: Dict[str, Any], top_k: int = 5) -> List[str]:
    onset = safe_get(seizure_ictal_json, "channel_level_summary", "channel_onset_scores", default=[]) or []
    ordered: List[str] = []

    for item in onset:
        ch = item.get("channel")
        if not ch or ch == "PAD":
            continue
        if ch not in ordered:
            ordered.append(ch)
        if len(ordered) >= top_k:
            break

    return ordered


def compute_exact_channel_concordance(hfo_json: Dict[str, Any], seizure_ictal_json: Dict[str, Any]) -> Dict[str, Any]:
    hfo_candidates = build_hfo_candidate_channels(hfo_json)
    seizure_candidates = get_seizure_candidate_channels(seizure_ictal_json, top_k=5)

    hfo_set = set(hfo_candidates)
    overlap = [ch for ch in seizure_candidates if ch in hfo_set]

    if not overlap:
        level = "none"
    elif len(overlap) == 1:
        level = "limited"
    elif len(overlap) >= 2:
        level = "moderate"
    else:
        level = "none"

    return {
        "concordance_mode": "exact_channel_match",
        "hfo_candidate_channels": hfo_candidates,
        "seizure_candidate_channels": seizure_candidates,
        "overlap_channels": overlap,
        "overlap_count": len(overlap),
        "concordance_level": level,
    }


def build_consistency_checks(
    hfo_json: Dict[str, Any],
    seizure_ictal_json: Dict[str, Any],
    seizure_interictal_json: Dict[str, Any],
    concordance: Dict[str, Any],
) -> Dict[str, Any]:
    flags: List[Dict[str, str]] = []

    fp_burden = classify_false_positive_burden(seizure_interictal_json)
    hfo_strength = classify_hfo_consensus_strength(hfo_json)
    seizure_predicted = bool(safe_get(seizure_ictal_json, "run_level_interpretation", "predicted_ictal_present", default=False))
    seizure_channel_avail = bool(safe_get(seizure_ictal_json, "channel_level_summary", default=None))

    if hfo_strength in {"strong", "moderate"} and concordance["overlap_count"] == 0 and seizure_channel_avail:
        flags.append({
            "severity": "warning",
            "code": "cross_modal_mismatch",
            "message": "Strong or moderate HFO evidence is present, but no direct overlap with seizure supportive channels was found under exact matching."
        })

    if fp_burden in {"high", "moderate"}:
        flags.append({
            "severity": "warning",
            "code": "interictal_false_positive_burden",
            "message": f"Interictal seizure false-positive burden is {fp_burden}."
        })

    if not seizure_predicted:
        flags.append({
            "severity": "critical",
            "code": "ictal_run_not_detected",
            "message": "Reserved ictal run was not detected as ictal."
        })

    if not seizure_channel_avail:
        flags.append({
            "severity": "warning",
            "code": "missing_seizure_channel_evidence",
            "message": "Seizure channel-level evidence is missing."
        })

    confidence = "moderate"
    if any(f["severity"] == "critical" for f in flags):
        confidence = "low"
    elif len(flags) >= 2:
        confidence = "limited"

    return {
        "flags": flags,
        "overall_consistency": "inconsistent" if any(f["severity"] == "critical" for f in flags) else ("cautious" if flags else "acceptable"),
        "integration_confidence": confidence,
    }