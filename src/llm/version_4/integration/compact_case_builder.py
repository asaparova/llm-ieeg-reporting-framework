from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from integration.fusion_logic import (
    build_consistency_checks,
    build_hfo_candidate_channels,
    classify_false_positive_burden,
    classify_hfo_consensus_strength,
    compute_exact_channel_concordance,
    safe_get,
)
from utils.io_utils import load_json, save_json


def find_single_file(folder: Path, pattern: str) -> Path:
    matches = sorted(folder.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No file matching {pattern} found in {folder}")
    if len(matches) > 1:
        print(f"[WARN] Multiple files matched {pattern} in {folder}. Using {matches[0].name}")
    return matches[0]


def first_n(items: List[Any], n: int) -> List[Any]:
    return items[:n] if isinstance(items, list) else []


def _summarize_hfo_rows(rows: List[Dict[str, Any]], n: int = 5) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in first_n(rows, n):
        out.append(
            {
                "channel": row.get("channel"),
                "fr_rate_mean": row.get("fr_rate_mean"),
                "frandr_rate_mean": row.get("frandr_rate_mean"),
                "appears_in_top_fr_runs": row.get("appears_in_top_fr_runs"),
                "appears_in_top_frandr_runs": row.get("appears_in_top_frandr_runs"),
                "appears_in_frandr_area_95p_runs": row.get("appears_in_frandr_area_95p_runs"),
            }
        )
    return out


def build_master_case(subject_id: str, hfo_json: Dict[str, Any], seizure_ictal_json: Dict[str, Any], seizure_interictal_json: Dict[str, Any]) -> Dict[str, Any]:
    concordance = compute_exact_channel_concordance(hfo_json, seizure_ictal_json)
    consistency = build_consistency_checks(hfo_json, seizure_ictal_json, seizure_interictal_json, concordance)

    master = {
        "case_id": f"{subject_id}_case_v3",
        "subject_id": subject_id,
        "dataset": "HUP",
        "system_version": "v3_exact_channel_match",
        "hfo_json": hfo_json,
        "seizure_ictal_json": seizure_ictal_json,
        "seizure_interictal_json": seizure_interictal_json,
        "integration_workspace": {
            "hfo_candidate_channels": build_hfo_candidate_channels(hfo_json),
            "hfo_consensus_strength": classify_hfo_consensus_strength(hfo_json),
            "seizure_interictal_false_positive_burden": classify_false_positive_burden(seizure_interictal_json),
            "channel_concordance": concordance,
            "consistency_checks": consistency,
        }
    }
    return master


def build_compact_case(master_case: Dict[str, Any]) -> Dict[str, Any]:
    hfo_json = master_case["hfo_json"]
    seizure_ictal = master_case["seizure_ictal_json"]
    seizure_interictal = master_case["seizure_interictal_json"]
    iw = master_case["integration_workspace"]

    strong_channels = safe_get(hfo_json, "consensus_summary", "strong_consensus_channels", default=[]) or []
    moderate_channels = safe_get(hfo_json, "consensus_summary", "moderate_consensus_channels", default=[]) or []
    seizure_top_channels = iw["channel_concordance"]["seizure_candidate_channels"]

    allowed_channels = []
    for ch in strong_channels + moderate_channels + seizure_top_channels:
        if ch and ch != "PAD" and ch not in allowed_channels:
            allowed_channels.append(ch)

    compact = {
        "case_id": master_case["case_id"],
        "subject_id": master_case["subject_id"],
        "dataset": master_case["dataset"],
        "integration_mode": "exact_channel_match",
        "system_confidence_seed": iw["consistency_checks"]["integration_confidence"],
        "hfo_evidence": {
            "consensus_strength": iw["hfo_consensus_strength"],
            "strong_consensus_channels": strong_channels,
            "supportive_channels": moderate_channels,
            "overall_summary": {
                "total_epochs_used": safe_get(hfo_json, "overall_summary", "total_epochs_used", default=None),
                "total_ripple_events": safe_get(hfo_json, "overall_summary", "total_ripple_events", default=None),
                "total_fr_events": safe_get(hfo_json, "overall_summary", "total_fr_events", default=None),
                "total_frandr_pairs": safe_get(hfo_json, "overall_summary", "total_frandr_pairs", default=None),
            },
            "top_aggregated_channels": _summarize_hfo_rows(hfo_json.get("aggregated_channel_evidence", []), n=5),
        },
        "seizure_evidence": {
            "ictal_detected": bool(safe_get(seizure_ictal, "run_level_interpretation", "predicted_ictal_present", default=False)),
            "ictal_candidate_segments": first_n(safe_get(seizure_ictal, "run_level_interpretation", "candidate_segments", default=[]), 3),
            "interictal_false_positive_burden": iw["seizure_interictal_false_positive_burden"],
            "channel_evidence_type": "model-derived saliency proxy",
            "top_supportive_channels": seizure_top_channels,
            "ictal_run_id": seizure_ictal.get("run_id"),
            "interictal_run_id": seizure_interictal.get("run_id"),
        },
        "integration_evidence": {
            "concordance_mode": iw["channel_concordance"]["concordance_mode"],
            "concordance_level": iw["channel_concordance"]["concordance_level"],
            "overlap_channels": iw["channel_concordance"]["overlap_channels"],
            "consistency_flags": iw["consistency_checks"]["flags"],
        },
        "allowed_channels": allowed_channels,
        "llm_constraints": [
            "Use only information explicitly present in this JSON.",
            "Do not copy this input JSON structure into the answer.",
            "Return only the target reasoning JSON schema.",
            "Do not invent channel names or localization claims.",
            "Treat seizure channel evidence as supportive saliency-proxy evidence.",
            "If overlap_channels is empty, concordance_level must be none.",
        ]
    }
    return compact


def build_case_files(project_root: Path, subject_id: str) -> None:
    subject_dir = project_root / subject_id
    hfo_dir = subject_dir / "hfo"
    seizure_dir = subject_dir / "seizure"
    integration_dir = subject_dir / "integration"
    integration_dir.mkdir(parents=True, exist_ok=True)

    hfo_path = find_single_file(hfo_dir, "*_hfo_subject_summary_for_llm.json")
    ictal_path = find_single_file(seizure_dir, "*task-ictal*_seizure_summary_for_llm.json")
    interictal_path = find_single_file(seizure_dir, "*task-interictal*_seizure_summary_for_llm.json")

    hfo_json = load_json(hfo_path)
    seizure_ictal_json = load_json(ictal_path)
    seizure_interictal_json = load_json(interictal_path)

    master_case = build_master_case(subject_id, hfo_json, seizure_ictal_json, seizure_interictal_json)
    compact_case = build_compact_case(master_case)

    save_json(integration_dir / f"{subject_id}_master_case.json", master_case)
    save_json(integration_dir / f"{subject_id}_compact_case.json", compact_case)