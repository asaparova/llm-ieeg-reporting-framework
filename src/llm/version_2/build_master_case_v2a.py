from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from integration_logic_v2a import (
    build_consistency_checks,
    build_hfo_candidate_channels,
    classify_false_positive_burden,
    classify_hfo_consensus_strength,
    compute_channel_concordance,
    load_json,
    safe_get,
)

# =============================
# CONFIG
# =============================
SUBJECT_ID = "sub-HUP146"
ROOT = Path(r"D:\LLM_unified_HUP_ver2") / SUBJECT_ID
HFO_DIR = ROOT / "hfo"
SEIZURE_DIR = ROOT / "seizure"
INTEGRATION_DIR = ROOT / "integration"
INTEGRATION_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_JSON = INTEGRATION_DIR / f"{SUBJECT_ID}_master_case.json"


def find_single_file(folder: Path, pattern: str) -> Path:
    matches = sorted(folder.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No file matching {pattern} found in {folder}")
    if len(matches) > 1:
        print(f"[WARN] Multiple files match {pattern} in {folder}. Using: {matches[0].name}")
    return matches[0]


def get_reserved_run_summary(seizure_json: Dict[str, Any]) -> Dict[str, Any]:
    out = {
        "run_id": seizure_json.get("run_id"),
        "task": seizure_json.get("task"),
        "predicted_ictal_present": safe_get(seizure_json, "run_level_interpretation", "predicted_ictal_present", default=None),
        "first_positive_start_sec": safe_get(seizure_json, "run_level_interpretation", "first_positive_start_sec", default=None),
        "last_positive_end_sec": safe_get(seizure_json, "run_level_interpretation", "last_positive_end_sec", default=None),
        "n_windows": safe_get(seizure_json, "window_level_summary", "n_windows", default=None),
        "n_predicted_positive_windows": safe_get(seizure_json, "window_level_summary", "n_predicted_positive_windows", default=None),
        "fraction_predicted_positive": safe_get(seizure_json, "window_level_summary", "fraction_predicted_positive", default=None),
        "peak_prob_smooth": safe_get(seizure_json, "window_level_summary", "peak_prob_smooth", default=None),
        "threshold_used": safe_get(seizure_json, "window_level_summary", "threshold_used", default=None),
        "candidate_segments": safe_get(seizure_json, "run_level_interpretation", "candidate_segments", default=[]),
    }
    ch_summary = safe_get(seizure_json, "channel_level_summary", default=None)
    if ch_summary:
        out["channel_level_summary"] = {
            "method": ch_summary.get("method"),
            "n_windows_used": ch_summary.get("n_windows_used"),
            "early_ictal_channels_topk": ch_summary.get("early_ictal_channels_topk", [])[:5],
            "channel_onset_scores_topk": ch_summary.get("channel_onset_scores", [])[:5],
        }
    return out


def build_master_case(subject_id: str, hfo_json: Dict[str, Any], seizure_ictal_json: Dict[str, Any], seizure_interictal_json: Dict[str, Any]) -> Dict[str, Any]:
    hfo_candidate_channels = build_hfo_candidate_channels(hfo_json)
    hfo_consensus_strength = classify_hfo_consensus_strength(hfo_json)
    interictal_fp_burden = classify_false_positive_burden(seizure_interictal_json)
    concordance = compute_channel_concordance(hfo_json, seizure_ictal_json)
    consistency = build_consistency_checks(hfo_json, seizure_ictal_json, seizure_interictal_json, concordance)

    seizure_channel_level_available = bool(safe_get(seizure_ictal_json, "channel_level_summary", default=None))
    direct_channel_concordance_supported = seizure_channel_level_available

    master = {
        "case_id": f"{subject_id}_case_v2a",
        "subject_id": subject_id,
        "dataset": "HUP",
        "system_version": "v2a_channel_level_fusion",
        "input_description": {
            "hfo_input_type": "merged subject-level HFO JSON",
            "seizure_input_type": "reserved run-level seizure JSONs with optional channel saliency proxy",
            "supports_patient_level_fusion": True,
            "supports_direct_channel_concordance": bool(direct_channel_concordance_supported),
        },
        "branch_inputs": {
            "hfo_subject_json": hfo_json,
            "seizure_ictal_json": seizure_ictal_json,
            "seizure_interictal_json": seizure_interictal_json,
        },
        "integration_workspace": {
            "supports_patient_level_fusion": True,
            "hfo_channel_level_available": True,
            "seizure_channel_level_available": bool(seizure_channel_level_available),
            "direct_channel_concordance_supported": bool(direct_channel_concordance_supported),
            "hfo_candidate_channels": hfo_candidate_channels,
            "hfo_consensus_strength": hfo_consensus_strength,
            "seizure_reserved_runs": {
                "ictal": get_reserved_run_summary(seizure_ictal_json),
                "interictal": get_reserved_run_summary(seizure_interictal_json),
            },
            "seizure_interictal_false_positive_burden": interictal_fp_burden,
            "channel_concordance": concordance,
            "consistency_checks": consistency,
            "recommended_interpretation_mode": "channel_level_unified_reporting" if direct_channel_concordance_supported else "limited_unified_reporting",
            "cross_modal_constraints": [
                "Seizure channel-level evidence is a saliency proxy, not direct electrophysiological onset annotation.",
                "Direct HFO-seizure overlap can be discussed only at the level of supportive concordance, not definitive localization.",
                "Observed disagreement between modalities should lower confidence rather than be forced into a single conclusion.",
            ],
            "system_confidence": consistency["integration_confidence"],
        },
        "llm_constraints": [
            "Use only information explicitly present in this JSON.",
            "Do not invent channels, seizure onset locations, spread patterns, concordance, diagnoses, or outcomes.",
            "If seizure channel evidence is based on saliency proxy, describe it as supportive model-derived evidence.",
            "Differentiate observed data, deterministic fusion outputs, and clinical-style interpretation.",
        ],
        "suggested_llm_tasks": [
            "Summarize HFO findings.",
            "Summarize reserved ictal and interictal seizure behavior.",
            "Summarize seizure channel-level supportive evidence when available.",
            "Summarize deterministic HFO-seizure concordance and consistency checks.",
            "Generate a final technical unified report with uncertainty.",
        ],
    }
    return master


def main() -> None:
    hfo_path = find_single_file(HFO_DIR, "*_hfo_subject_summary_for_llm.json")
    ictal_path = find_single_file(SEIZURE_DIR, "*task-ictal*_seizure_summary_for_llm.json")
    interictal_path = find_single_file(SEIZURE_DIR, "*task-interictal*_seizure_summary_for_llm.json")

    hfo_json = load_json(hfo_path)
    seizure_ictal_json = load_json(ictal_path)
    seizure_interictal_json = load_json(interictal_path)

    master = build_master_case(SUBJECT_ID, hfo_json, seizure_ictal_json, seizure_interictal_json)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(master, f, indent=2, ensure_ascii=False)
    print(f"Saved V2A master case JSON to: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
