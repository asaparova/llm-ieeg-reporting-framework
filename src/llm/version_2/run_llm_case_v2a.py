from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import requests

SUBJECT_ID = "sub-HUP146"
ROOT = Path(r"D:\LLM_unified_HUP_ver2")
CASE_DIR = ROOT / SUBJECT_ID
MASTER_CASE_PATH = CASE_DIR / "integration" / f"{SUBJECT_ID}_master_case.json"
PROMPTS_DIR = ROOT / "prompts"
REASONING_PROMPT_PATH = PROMPTS_DIR / "reasoning_prompt_v2a.txt"
REPORT_PROMPT_PATH = PROMPTS_DIR / "report_prompt_v2a.txt"
REPORTS_DIR = CASE_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
COMPACT_INPUT_PATH = REPORTS_DIR / f"{SUBJECT_ID}_compact_llm_input.json"
REASONING_JSON_PATH = REPORTS_DIR / f"{SUBJECT_ID}_reasoning.json"
FINAL_REPORT_PATH = REPORTS_DIR / f"{SUBJECT_ID}_final_report.txt"
RAW_REASONING_PATH = REPORTS_DIR / f"{SUBJECT_ID}_reasoning_raw.txt"
RAW_REPORT_PATH = REPORTS_DIR / f"{SUBJECT_ID}_report_raw.txt"
MODEL_NAME = "qwen3:8b"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def save_json(path: Path, obj: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def extract_json_block(text: str) -> str:
    text = text.strip()
    fenced = re.search(r"```json\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1].strip()
    raise ValueError("Could not extract JSON from model output.")


def call_ollama(prompt: str, model_name: str, json_mode: bool = False) -> str:
    payload = {
    "model": model_name,
    "prompt": prompt,
    "stream": False,
    "options": {
        "temperature": 0.0,
        "top_p": 1.0,
        "num_predict": 1000,
     },
    }
    if json_mode:
        payload["format"] = "json"
    resp = requests.post(OLLAMA_URL, json=payload, timeout=600)
    resp.raise_for_status()
    data = resp.json()
    return data["response"]


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
    iw = master_case.get("integration_workspace", {})
    hfo_branch = master_case.get("branch_inputs", {}).get("hfo_subject_json", {})
    seizure_ictal = master_case.get("branch_inputs", {}).get("seizure_ictal_json", {})
    seizure_interictal = master_case.get("branch_inputs", {}).get("seizure_interictal_json", {})

    compact = {
        "case_id": master_case.get("case_id"),
        "subject_id": master_case.get("subject_id"),
        "dataset": master_case.get("dataset"),
        "system_view": {
            "recommended_interpretation_mode": iw.get("recommended_interpretation_mode"),
            "system_confidence": iw.get("system_confidence"),
            "direct_channel_concordance_supported": iw.get("direct_channel_concordance_supported"),
        },
        "hfo_summary": {
            "candidate_channels": iw.get("hfo_candidate_channels", []),
            "consensus_strength": iw.get("hfo_consensus_strength"),
            "overall_summary": hfo_branch.get("overall_summary", {}),
            "top_aggregated_channels": first_n(hfo_branch.get("aggregated_channel_evidence", []), 8),
        },
        "seizure_summary": {
            "ictal_run": {
                "run_id": seizure_ictal.get("run_id"),
                "window_level_summary": seizure_ictal.get("window_level_summary", {}),
                "candidate_segments_top3": first_n(safe_get(seizure_ictal, "run_level_interpretation", "candidate_segments", default=[]), 3),
                "channel_level_method": safe_get(seizure_ictal, "channel_level_summary", "method", default=None),
                "early_ictal_channels_top5": first_n(safe_get(seizure_ictal, "channel_level_summary", "early_ictal_channels_topk", default=[]), 5),
                "channel_onset_scores_top5": first_n(safe_get(seizure_ictal, "channel_level_summary", "channel_onset_scores", default=[]), 5),
            },
            "interictal_run": {
                "run_id": seizure_interictal.get("run_id"),
                "window_level_summary": seizure_interictal.get("window_level_summary", {}),
                "candidate_segments_top3": first_n(safe_get(seizure_interictal, "run_level_interpretation", "candidate_segments", default=[]), 3),
            },
            "interictal_false_positive_burden": iw.get("seizure_interictal_false_positive_burden"),
        },
        "deterministic_integration": {
            "channel_concordance": iw.get("channel_concordance", {}),
            "consistency_checks": iw.get("consistency_checks", {}),
        },
        "integration_constraints": iw.get("cross_modal_constraints", []),
        "llm_constraints": master_case.get("llm_constraints", []),
    }
    return compact


def main() -> None:
    master_case = load_json(MASTER_CASE_PATH)
    compact = build_compact_llm_input(master_case)
    save_json(COMPACT_INPUT_PATH, compact)

    reasoning_prompt = load_text(REASONING_PROMPT_PATH).replace("{{COMPACT_INPUT_JSON}}", json.dumps(compact, indent=2, ensure_ascii=False))
    reasoning_raw = call_ollama(reasoning_prompt, MODEL_NAME, json_mode=True)
    save_text(RAW_REASONING_PATH, reasoning_raw)
    reasoning_json = json.loads(extract_json_block(reasoning_raw))
    save_json(REASONING_JSON_PATH, reasoning_json)

    report_prompt = load_text(REPORT_PROMPT_PATH)
    report_prompt = report_prompt.replace("{{COMPACT_INPUT_JSON}}", json.dumps(compact, indent=2, ensure_ascii=False))
    report_prompt = report_prompt.replace("{{REASONING_JSON}}", json.dumps(reasoning_json, indent=2, ensure_ascii=False))
    report_raw = call_ollama(report_prompt, MODEL_NAME, json_mode=False)
    save_text(RAW_REPORT_PATH, report_raw)
    save_text(FINAL_REPORT_PATH, report_raw.strip())
    print(f"Saved V2A final report to: {FINAL_REPORT_PATH}")


if __name__ == "__main__":
    main()
