from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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
        if ch not in ordered:
            ordered.append(ch)
    return ordered


def get_seizure_candidate_channels(seizure_ictal_json: Dict[str, Any], top_k: int = 10) -> List[str]:
    early = safe_get(seizure_ictal_json, "channel_level_summary", "early_ictal_channels_topk", default=[]) or []
    onset = safe_get(seizure_ictal_json, "channel_level_summary", "channel_onset_scores", default=[]) or []
    ordered: List[str] = []
    for item in early + onset:
        ch = item.get("channel")
        if ch and ch not in ordered:
            ordered.append(ch)
        if len(ordered) >= top_k:
            break
    return ordered


def compute_channel_concordance(hfo_json: Dict[str, Any], seizure_ictal_json: Dict[str, Any]) -> Dict[str, Any]:
    hfo_candidates = build_hfo_candidate_channels(hfo_json)
    seizure_candidates = get_seizure_candidate_channels(seizure_ictal_json)
    overlap = [ch for ch in seizure_candidates if ch in set(hfo_candidates)]

    hfo_evidence = {row["channel"]: row for row in hfo_json.get("aggregated_channel_evidence", [])}
    seiz_evidence = {row["channel"]: row for row in safe_get(seizure_ictal_json, "channel_level_summary", "channel_onset_scores", default=[]) or []}

    weighted_rows = []
    for ch in overlap:
        hfo_row = hfo_evidence.get(ch, {})
        seiz_row = seiz_evidence.get(ch, {})
        score = (
            1.5 * float(hfo_row.get("appears_in_frandr_area_95p_runs", 0))
            + 1.0 * float(hfo_row.get("appears_in_top_frandr_runs", 0))
            + 0.5 * float(hfo_row.get("appears_in_top_fr_runs", 0))
            + 4.0 * float(seiz_row.get("mean_saliency", 0.0))
        )
        weighted_rows.append(
            {
                "channel": ch,
                "weighted_concordance_score": score,
                "hfo_frandr_area_hits": int(hfo_row.get("appears_in_frandr_area_95p_runs", 0)),
                "hfo_top_frandr_hits": int(hfo_row.get("appears_in_top_frandr_runs", 0)),
                "seizure_mean_saliency": float(seiz_row.get("mean_saliency", 0.0)),
            }
        )

    weighted_rows.sort(key=lambda x: x["weighted_concordance_score"], reverse=True)

    if overlap:
        if len(overlap) >= 2:
            level = "moderate"
        else:
            level = "limited"
    else:
        level = "none"

    return {
        "hfo_candidate_channels": hfo_candidates,
        "seizure_candidate_channels": seizure_candidates,
        "overlap_channels": overlap,
        "overlap_count": len(overlap),
        "concordance_level": level,
        "channel_scores": weighted_rows,
        "summary": (
            "No direct overlap between current HFO candidate channels and seizure saliency proxy channels."
            if not overlap
            else f"Found {len(overlap)} overlapping candidate channel(s) across HFO and seizure branches."
        ),
    }


def build_consistency_checks(hfo_json: Dict[str, Any], seizure_ictal_json: Dict[str, Any], seizure_interictal_json: Dict[str, Any], concordance: Dict[str, Any]) -> Dict[str, Any]:
    flags: List[Dict[str, str]] = []
    fp_burden = classify_false_positive_burden(seizure_interictal_json)
    hfo_strength = classify_hfo_consensus_strength(hfo_json)
    seizure_predicted = bool(safe_get(seizure_ictal_json, "run_level_interpretation", "predicted_ictal_present", default=False))
    seizure_channel_avail = bool(safe_get(seizure_ictal_json, "channel_level_summary", default=None))

    if hfo_strength in {"strong", "moderate"} and concordance["overlap_count"] == 0 and seizure_channel_avail:
        flags.append({
            "severity": "warning",
            "code": "cross_modal_mismatch",
            "message": "Strong or moderate HFO evidence is present, but no direct overlap with seizure channel saliency proxy channels was found.",
        })
    if fp_burden in {"high", "moderate"}:
        flags.append({
            "severity": "warning",
            "code": "interictal_false_positive_burden",
            "message": f"Interictal seizure branch false-positive burden is {fp_burden}, which lowers confidence in onset localization.",
        })
    if not seizure_predicted:
        flags.append({
            "severity": "critical",
            "code": "ictal_run_not_detected",
            "message": "Reserved ictal run was not confidently detected as ictal by the seizure branch.",
        })
    if not seizure_channel_avail:
        flags.append({
            "severity": "warning",
            "code": "missing_seizure_channel_evidence",
            "message": "Seizure channel-level evidence is missing; channel concordance claims must remain limited.",
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
