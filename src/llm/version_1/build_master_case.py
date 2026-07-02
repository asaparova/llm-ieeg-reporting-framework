from pathlib import Path
import json
from typing import Any, Dict, List, Optional


# =========================================================
# CONFIG
# =========================================================
SUBJECT_ID = "sub-HUP146"
ROOT = Path(r"D:\LLM_unified_HUP") / SUBJECT_ID

HFO_DIR = ROOT / "hfo"
SEIZURE_DIR = ROOT / "seizure"
INTEGRATION_DIR = ROOT / "integration"
INTEGRATION_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_JSON = INTEGRATION_DIR / f"{SUBJECT_ID}_master_case.json"


# =========================================================
# HELPERS
# =========================================================
def load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_single_file(folder: Path, pattern: str) -> Path:
    matches = sorted(folder.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No file matching {pattern} found in {folder}")
    if len(matches) > 1:
        print(f"[WARN] Multiple files match {pattern} in {folder}. Using: {matches[0].name}")
    return matches[0]


def safe_get(d: Dict[str, Any], *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def classify_false_positive_burden(interictal_json: Dict[str, Any]) -> str:
    frac_pos = safe_get(
        interictal_json,
        "window_level_summary",
        "fraction_predicted_positive",
        default=None,
    )
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

    ordered = []
    for ch in strong + moderate:
        if ch not in ordered:
            ordered.append(ch)
    return ordered


def get_reserved_run_summary(seizure_json: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "run_id": seizure_json.get("run_id"),
        "task": seizure_json.get("task"),
        "predicted_ictal_present": safe_get(
            seizure_json,
            "run_level_interpretation",
            "predicted_ictal_present",
            default=None,
        ),
        "first_positive_start_sec": safe_get(
            seizure_json,
            "run_level_interpretation",
            "first_positive_start_sec",
            default=None,
        ),
        "last_positive_end_sec": safe_get(
            seizure_json,
            "run_level_interpretation",
            "last_positive_end_sec",
            default=None,
        ),
        "n_windows": safe_get(
            seizure_json,
            "window_level_summary",
            "n_windows",
            default=None,
        ),
        "n_true_ictal_windows": safe_get(
            seizure_json,
            "window_level_summary",
            "n_true_ictal_windows",
            default=None,
        ),
        "n_true_nonictal_windows": safe_get(
            seizure_json,
            "window_level_summary",
            "n_true_nonictal_windows",
            default=None,
        ),
        "n_predicted_positive_windows": safe_get(
            seizure_json,
            "window_level_summary",
            "n_predicted_positive_windows",
            default=None,
        ),
        "fraction_predicted_positive": safe_get(
            seizure_json,
            "window_level_summary",
            "fraction_predicted_positive",
            default=None,
        ),
        "mean_prob_smooth": safe_get(
            seizure_json,
            "window_level_summary",
            "mean_prob_smooth",
            default=None,
        ),
        "peak_prob_smooth": safe_get(
            seizure_json,
            "window_level_summary",
            "peak_prob_smooth",
            default=None,
        ),
        "threshold_used": safe_get(
            seizure_json,
            "window_level_summary",
            "threshold_used",
            default=None,
        ),
        "candidate_segments": safe_get(
            seizure_json,
            "run_level_interpretation",
            "candidate_segments",
            default=[],
        ),
    }


def build_master_case(
    subject_id: str,
    hfo_json: Dict[str, Any],
    seizure_ictal_json: Dict[str, Any],
    seizure_interictal_json: Dict[str, Any],
) -> Dict[str, Any]:
    hfo_candidate_channels = build_hfo_candidate_channels(hfo_json)
    hfo_consensus_strength = classify_hfo_consensus_strength(hfo_json)
    interictal_fp_burden = classify_false_positive_burden(seizure_interictal_json)

    seizure_channel_level_available = False
    hfo_channel_level_available = True
    direct_channel_concordance_supported = (
        hfo_channel_level_available and seizure_channel_level_available
    )

    master = {
        "case_id": f"{subject_id}_case_v1",
        "subject_id": subject_id,
        "dataset": "HUP",
        "system_version": "v1_unified_case_integration",
        "input_description": {
            "hfo_input_type": "merged subject-level HFO JSON",
            "seizure_input_type": "reserved run-level seizure JSONs",
            "supports_patient_level_fusion": True,
            "supports_direct_channel_concordance": False,
        },
        "branch_inputs": {
            "hfo_subject_json": hfo_json,
            "seizure_ictal_json": seizure_ictal_json,
            "seizure_interictal_json": seizure_interictal_json,
        },
        "integration_workspace": {
            "supports_patient_level_fusion": True,
            "hfo_channel_level_available": hfo_channel_level_available,
            "seizure_channel_level_available": seizure_channel_level_available,
            "direct_channel_concordance_supported": direct_channel_concordance_supported,
            "hfo_candidate_channels": hfo_candidate_channels,
            "hfo_consensus_strength": hfo_consensus_strength,
            "seizure_reserved_runs": {
                "ictal": get_reserved_run_summary(seizure_ictal_json),
                "interictal": get_reserved_run_summary(seizure_interictal_json),
            },
            "seizure_interictal_false_positive_burden": interictal_fp_burden,
            "recommended_interpretation_mode": (
                "limited_unified_reporting"
                if not direct_channel_concordance_supported
                else "full_channel_level_unified_reporting"
            ),
            "cross_modal_constraints": [
                "Seizure JSON currently does not include channel-level onset or spread evidence.",
                "Direct HFO-seizure channel concordance cannot be established from the present files.",
                "The LLM may compare subject-level HFO findings with reserved seizure run behavior, but must not invent seizure onset channels.",
            ],
            "system_confidence": (
                "limited"
                if interictal_fp_burden in {"high", "moderate"}
                else "moderate"
            ),
        },
        "llm_constraints": [
            "Use only information explicitly present in this JSON.",
            "Do not invent channels, seizure onset locations, spread patterns, or concordance.",
            "Do not claim direct HFO-seizure spatial overlap unless seizure channel-level evidence is present.",
            "State uncertainty clearly, especially if the interictal false-positive burden is high.",
            "Differentiate observed data from interpretation.",
        ],
        "suggested_llm_tasks": [
            "Summarize HFO findings.",
            "Summarize reserved ictal seizure run behavior.",
            "Summarize reserved interictal seizure false-positive behavior.",
            "Describe integration constraints and uncertainty.",
            "Generate a final technical unified report.",
        ],
    }
    return master


# =========================================================
# MAIN
# =========================================================
def main():
    print(f"[INFO] Building master case for {SUBJECT_ID}")

    hfo_json_path = find_single_file(HFO_DIR, "*_hfo_subject_summary_for_llm.json")
    ictal_json_path = find_single_file(SEIZURE_DIR, "*task-ictal*_seizure_summary_for_llm.json")
    interictal_json_path = find_single_file(SEIZURE_DIR, "*task-interictal*_seizure_summary_for_llm.json")

    print(f"[INFO] HFO JSON: {hfo_json_path.name}")
    print(f"[INFO] Ictal seizure JSON: {ictal_json_path.name}")
    print(f"[INFO] Interictal seizure JSON: {interictal_json_path.name}")

    hfo_json = load_json(hfo_json_path)
    seizure_ictal_json = load_json(ictal_json_path)
    seizure_interictal_json = load_json(interictal_json_path)

    master_case = build_master_case(
        subject_id=SUBJECT_ID,
        hfo_json=hfo_json,
        seizure_ictal_json=seizure_ictal_json,
        seizure_interictal_json=seizure_interictal_json,
    )

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(master_case, f, indent=2)

    print(f"[INFO] Saved master case JSON to:\n{OUTPUT_JSON}")


if __name__ == "__main__":
    main()