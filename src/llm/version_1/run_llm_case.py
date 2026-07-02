from pathlib import Path
import json
import re
import sys
from typing import Any, Dict, List

import requests


# =========================================================
# CONFIG
# =========================================================
SUBJECT_ID = "sub-HUP146"
ROOT = Path(r"D:\LLM_unified_HUP")
CASE_DIR = ROOT / SUBJECT_ID

MASTER_CASE_PATH = CASE_DIR / "integration" / f"{SUBJECT_ID}_master_case.json"
PROMPTS_DIR = ROOT / "prompts"
REASONING_PROMPT_PATH = PROMPTS_DIR / "reasoning_prompt.txt"
REPORT_PROMPT_PATH = PROMPTS_DIR / "report_prompt.txt"

REPORTS_DIR = CASE_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

COMPACT_INPUT_PATH = REPORTS_DIR / f"{SUBJECT_ID}_compact_llm_input.json"
REASONING_JSON_PATH = REPORTS_DIR / f"{SUBJECT_ID}_reasoning.json"
FINAL_REPORT_PATH = REPORTS_DIR / f"{SUBJECT_ID}_final_report.txt"
RAW_REASONING_PATH = REPORTS_DIR / f"{SUBJECT_ID}_reasoning_raw.txt"
RAW_REPORT_PATH = REPORTS_DIR / f"{SUBJECT_ID}_report_raw.txt"
RAW_REPAIR_PATH = REPORTS_DIR / f"{SUBJECT_ID}_reasoning_repair_raw.txt"

# Use the exact name from: ollama list
MODEL_NAME = "qwen3:8b"

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
USE_LOW_TEMPERATURE = True

REQUIRED_REASONING_KEYS = [
    "case_assessment",
    "hfo_assessment",
    "seizure_assessment",
    "integration_assessment",
    "limitations",
    "final_interpretation",
]


# =========================================================
# IO HELPERS
# =========================================================
def load_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def save_json(path: Path, obj: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


# =========================================================
# JSON PARSING HELPERS
# =========================================================
def extract_json_block(text: str) -> str:
    text = text.strip()

    fenced = re.search(r"```json\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()

    fenced_any = re.search(r"```\s*(.*?)\s*```", text, flags=re.DOTALL)
    if fenced_any:
        candidate = fenced_any.group(1).strip()
        if candidate.startswith("{") and candidate.endswith("}"):
            return candidate

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1].strip()

    raise ValueError("Could not extract JSON from model output.")


def try_parse_json(text: str) -> Dict[str, Any]:
    json_str = extract_json_block(text)
    return json.loads(json_str)


def has_valid_hfo_subschema(obj: Dict[str, Any]) -> bool:
    if "hfo_assessment" not in obj or not isinstance(obj["hfo_assessment"], dict):
        return False

    hfo = obj["hfo_assessment"]
    required_hfo_keys = [
        "strong_consensus_channels",
        "moderate_candidate_channels",
        "consensus_strength",
        "summary",
    ]
    return all(k in hfo for k in required_hfo_keys)

def has_required_reasoning_schema(obj: Dict[str, Any]) -> bool:
    if not isinstance(obj, dict):
        return False
    if not all(k in obj for k in REQUIRED_REASONING_KEYS):
        return False
    return has_valid_hfo_subschema(obj)

# =========================================================
# OLLAMA
# =========================================================
def call_ollama(prompt: str, model_name: str, json_mode: bool = False) -> str:
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0 if USE_LOW_TEMPERATURE else 0.2,
            "num_predict": 2048,
        },
    }

    if json_mode:
        payload["format"] = "json"

    resp = requests.post(OLLAMA_URL, json=payload, timeout=600)
    resp.raise_for_status()
    data = resp.json()

    if "response" not in data:
        raise RuntimeError(f"Unexpected Ollama response: {data}")

    return data["response"]


# =========================================================
# COMPACT INPUT BUILDER
# =========================================================
def safe_get(d: Dict[str, Any], *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def first_n(items: List[Any], n: int) -> List[Any]:
    return items[:n] if isinstance(items, list) else []


def build_compact_llm_input(master_case: Dict[str, Any]) -> Dict[str, Any]:
    """
    Smaller, more focused input for the LLM.
    Keep only the fields needed for reasoning/reporting.
    """
    iw = master_case.get("integration_workspace", {})

    hfo_branch = master_case.get("branch_inputs", {}).get("hfo_subject_json", {})
    seizure_ictal = master_case.get("branch_inputs", {}).get("seizure_ictal_json", {})
    seizure_interictal = master_case.get("branch_inputs", {}).get("seizure_interictal_json", {})

    ictal_segments = safe_get(
        seizure_ictal, "run_level_interpretation", "candidate_segments", default=[]
    ) or []
    interictal_segments = safe_get(
        seizure_interictal, "run_level_interpretation", "candidate_segments", default=[]
    ) or []

    compact = {
        "case_id": master_case.get("case_id"),
        "subject_id": master_case.get("subject_id"),
        "dataset": master_case.get("dataset"),

        "system_view": {
            "supports_patient_level_fusion": iw.get("supports_patient_level_fusion"),
            "hfo_channel_level_available": iw.get("hfo_channel_level_available"),
            "seizure_channel_level_available": iw.get("seizure_channel_level_available"),
            "direct_channel_concordance_supported": iw.get("direct_channel_concordance_supported"),
            "recommended_interpretation_mode": iw.get("recommended_interpretation_mode"),
            "system_confidence": iw.get("system_confidence"),
        },

        "hfo_summary": {
            "candidate_channels": iw.get("hfo_candidate_channels", []),
            "consensus_strength": iw.get("hfo_consensus_strength"),
            "n_runs": hfo_branch.get("n_runs"),
            "overall_summary": hfo_branch.get("overall_summary", {}),
            "consensus_summary": hfo_branch.get("consensus_summary", {}),
            "top_aggregated_channels": first_n(
                hfo_branch.get("aggregated_channel_evidence", []), 5
            ),
        },

        "seizure_summary": {
            "ictal_run": {
                "run_id": seizure_ictal.get("run_id"),
                "task": seizure_ictal.get("task"),
                "window_level_summary": seizure_ictal.get("window_level_summary", {}),
                "predicted_ictal_present": safe_get(
                    seizure_ictal, "run_level_interpretation", "predicted_ictal_present", default=None
                ),
                "first_positive_start_sec": safe_get(
                    seizure_ictal, "run_level_interpretation", "first_positive_start_sec", default=None
                ),
                "last_positive_end_sec": safe_get(
                    seizure_ictal, "run_level_interpretation", "last_positive_end_sec", default=None
                ),
                "candidate_segments_top3": first_n(ictal_segments, 3),
            },
            "interictal_run": {
                "run_id": seizure_interictal.get("run_id"),
                "task": seizure_interictal.get("task"),
                "window_level_summary": seizure_interictal.get("window_level_summary", {}),
                "predicted_ictal_present": safe_get(
                    seizure_interictal, "run_level_interpretation", "predicted_ictal_present", default=None
                ),
                "first_positive_start_sec": safe_get(
                    seizure_interictal, "run_level_interpretation", "first_positive_start_sec", default=None
                ),
                "last_positive_end_sec": safe_get(
                    seizure_interictal, "run_level_interpretation", "last_positive_end_sec", default=None
                ),
                "candidate_segments_top3": first_n(interictal_segments, 3),
            },
            "interictal_false_positive_burden": iw.get("seizure_interictal_false_positive_burden"),
        },

        "integration_constraints": iw.get("cross_modal_constraints", []),
        "llm_constraints": master_case.get("llm_constraints", []),
    }

    return compact


# =========================================================
# REASONING SCHEMA REPAIR
# =========================================================
def build_repair_prompt(bad_json: Dict[str, Any]) -> str:
    bad_json_str = json.dumps(bad_json, indent=2, ensure_ascii=False)

    return f"""
You are repairing a medical-technical reasoning JSON.

The previous model output was valid JSON, but it did NOT follow the required schema.

Your task:
- convert the input JSON into the exact target schema
- use only information already present
- do not invent channels, seizure onset locations, spread patterns, concordance, diagnoses, or outcomes
- output ONLY valid JSON
- do not use markdown
- do not use code fences
- be concise and technical

Required schema:

{{
  "case_assessment": {{
    "supports_patient_level_fusion": true,
    "direct_channel_concordance_supported": false,
    "overall_confidence": "",
    "reason_for_confidence": ""
  }},
    "hfo_assessment": {{
    "strong_consensus_channels": [],
    "moderate_candidate_channels": [],
    "consensus_strength": "",
    "summary": ""
  }},,
  "seizure_assessment": {{
    "ictal_run_summary": "",
    "interictal_run_summary": "",
    "false_positive_burden": "",
    "summary": ""
  }},
  "integration_assessment": {{
    "can_compare_modalities": true,
    "can_claim_direct_spatial_overlap": false,
    "summary": ""
  }},
  "limitations": [],
  "final_interpretation": ""
}}

Input JSON:
{bad_json_str}
""".strip()


def repair_reasoning_json_if_needed(reasoning_json: Dict[str, Any], model_name: str) -> Dict[str, Any]:
    if has_required_reasoning_schema(reasoning_json):
        return reasoning_json

    print("[WARN] Reasoning JSON does not match required schema. Running repair pass...")
    repair_prompt = build_repair_prompt(reasoning_json)
    repaired_raw = call_ollama(repair_prompt, model_name, json_mode=True)
    save_text(RAW_REPAIR_PATH, repaired_raw)

    repaired_json = try_parse_json(repaired_raw)

    if not has_required_reasoning_schema(repaired_json):
        raise ValueError("Repair pass failed: reasoning JSON still does not match required schema.")

    return repaired_json


# =========================================================
# PROMPT BUILDERS
# =========================================================
def build_reasoning_input(reasoning_prompt: str, compact_input: Dict[str, Any]) -> str:
    compact_str = json.dumps(compact_input, indent=2, ensure_ascii=False)
    return (
        f"{reasoning_prompt}\n\n"
        f"COMPACT UNIFIED CASE JSON:\n"
        f"{compact_str}\n"
    )


def build_report_input(report_prompt: str, compact_input: Dict[str, Any], reasoning_json: Dict[str, Any]) -> str:
    compact_str = json.dumps(compact_input, indent=2, ensure_ascii=False)
    reasoning_str = json.dumps(reasoning_json, indent=2, ensure_ascii=False)

    return (
        f"{report_prompt}\n\n"
        f"COMPACT UNIFIED CASE JSON:\n"
        f"{compact_str}\n\n"
        f"REASONING JSON:\n"
        f"{reasoning_str}\n"
    )


# =========================================================
# MAIN
# =========================================================
def main():
    print(f"[INFO] Loading master case from: {MASTER_CASE_PATH}")
    master_case = load_json(MASTER_CASE_PATH)

    print(f"[INFO] Loading prompts from: {PROMPTS_DIR}")
    reasoning_prompt = load_text(REASONING_PROMPT_PATH)
    report_prompt = load_text(REPORT_PROMPT_PATH)

    compact_input = build_compact_llm_input(master_case)
    save_json(COMPACT_INPUT_PATH, compact_input)
    print(f"[INFO] Saved compact LLM input to: {COMPACT_INPUT_PATH}")

    # -----------------------------
    # Pass 1: Reasoning JSON
    # -----------------------------
    print(f"[INFO] Running reasoning pass with model: {MODEL_NAME}")
    reasoning_input = build_reasoning_input(reasoning_prompt, compact_input)
    reasoning_raw = call_ollama(reasoning_input, MODEL_NAME, json_mode=True)
    save_text(RAW_REASONING_PATH, reasoning_raw)

    try:
        reasoning_json = try_parse_json(reasoning_raw)
    except Exception as e:
        print("[ERROR] Failed to parse reasoning JSON.")
        print(f"[ERROR] Raw reasoning saved to: {RAW_REASONING_PATH}")
        raise e

    reasoning_json = repair_reasoning_json_if_needed(reasoning_json, MODEL_NAME)
    save_json(REASONING_JSON_PATH, reasoning_json)
    print(f"[INFO] Saved reasoning JSON to: {REASONING_JSON_PATH}")

    # -----------------------------
    # Pass 2: Final report
    # -----------------------------
    print(f"[INFO] Running report pass with model: {MODEL_NAME}")
    report_input = build_report_input(report_prompt, compact_input, reasoning_json)
    report_raw = call_ollama(report_input, MODEL_NAME, json_mode=False)
    save_text(RAW_REPORT_PATH, report_raw)

    final_report = report_raw.strip()
    save_text(FINAL_REPORT_PATH, final_report)
    print(f"[INFO] Saved final report to: {FINAL_REPORT_PATH}")

    print("[INFO] Done.")
    print(f"[INFO] Outputs:")
    print(f"  - Compact input:   {COMPACT_INPUT_PATH}")
    print(f"  - Reasoning JSON:  {REASONING_JSON_PATH}")
    print(f"  - Final report:    {FINAL_REPORT_PATH}")
    print(f"  - Raw reasoning:   {RAW_REASONING_PATH}")
    print(f"  - Raw repair:      {RAW_REPAIR_PATH}")
    print(f"  - Raw report:      {RAW_REPORT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[FATAL] {e}")
        sys.exit(1)