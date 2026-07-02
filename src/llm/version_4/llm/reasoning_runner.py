from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from llm.ollama_client import call_ollama
from llm.reasoning_validator import validate_reasoning_json
from utils.io_utils import load_text, save_json, save_text


def extract_json_block(text: str) -> str:
    text = text.strip()

    fenced = re.search(r"```json\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1].strip()

    raise ValueError("Could not extract JSON object from model output.")


def try_parse_json(raw_text: str) -> Dict[str, Any]:
    extracted = extract_json_block(raw_text)
    return json.loads(extracted)


def _clean_string_list(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []
    out: List[str] = []
    for v in values:
        if isinstance(v, str):
            s = v.strip()
            if s:
                out.append(s)
    return out


def _build_fallback_limitations(compact_case: Dict[str, Any]) -> List[str]:
    integration = compact_case.get("integration_evidence", {}) or {}
    seizure = compact_case.get("seizure_evidence", {}) or {}

    concordance_level = integration.get("concordance_level")
    consistency_flags = integration.get("consistency_flags", []) or []
    channel_evidence_type = seizure.get("channel_evidence_type", "")

    fallback: List[str] = []

    if channel_evidence_type == "model-derived saliency proxy":
        fallback.append(
            "Seizure channel evidence is model-derived saliency proxy rather than direct electrophysiological localization."
        )

    if concordance_level == "none":
        fallback.append(
            "No direct cross-modal overlap was identified between HFO and seizure supportive channels."
        )

    if isinstance(consistency_flags, list):
        for flag in consistency_flags:
            if isinstance(flag, dict):
                msg = flag.get("message")
                if isinstance(msg, str):
                    msg = msg.strip()
                    if msg:
                        fallback.append(msg)

    # Always guarantee at least two non-empty strings
    defaults = [
        "Cross-modal interpretation should be treated cautiously.",
        "Findings should be interpreted in the context of model and integration limitations.",
    ]

    seen = set()
    merged: List[str] = []
    for item in fallback + defaults:
        if item not in seen:
            merged.append(item)
            seen.add(item)

    return merged[:4]


def _ensure_minimum_limitations(reasoning: Dict[str, Any], compact_case: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(reasoning, dict):
        reasoning = {}

    integration = compact_case.get("integration_evidence", {}) or {}
    seizure = compact_case.get("seizure_evidence", {}) or {}

    concordance_level = integration.get("concordance_level")
    consistency_flags = integration.get("consistency_flags", []) or []
    channel_evidence_type = seizure.get("channel_evidence_type", "")

    requires_two = (
        channel_evidence_type == "model-derived saliency proxy"
        or concordance_level == "none"
        or (isinstance(consistency_flags, list) and len(consistency_flags) > 0)
    )

    cleaned = _clean_string_list(reasoning.get("limitations"))
    fallback = _build_fallback_limitations(compact_case)

    # If model output is missing/bad/empty, replace it entirely with deterministic fallback
    if requires_two:
        merged: List[str] = []
        seen = set()

        for item in cleaned + fallback:
            if item and item not in seen:
                merged.append(item)
                seen.add(item)

        while len(merged) < 2:
            extra = [
                "Confidence is limited by indirect seizure channel evidence.",
                "Cross-modal interpretation should be treated cautiously.",
            ][len(merged)]
            if extra not in seen:
                merged.append(extra)
                seen.add(extra)

        reasoning["limitations"] = merged[:4]
    else:
        reasoning["limitations"] = cleaned

    return reasoning


def run_reasoning_with_repair(
    compact_case: Dict[str, Any],
    project_root: Path,
    subject_id: str,
    model_name: str = "qwen3:8b",
    ollama_url: str = "http://127.0.0.1:11434/api/generate",
) -> Dict[str, Any]:
    prompts_dir = project_root / "prompts"
    config_dir = project_root / "config"

    reasoning_dir = project_root / subject_id / "reasoning"
    reasoning_dir.mkdir(parents=True, exist_ok=True)

    schema_path = config_dir / "reasoning_schema.json"
    reasoning_prompt_path = prompts_dir / "reasoning_prompt_v3.txt"
    repair_prompt_path = prompts_dir / "repair_reasoning_prompt_v3.txt"

    raw_reasoning_path = reasoning_dir / f"{subject_id}_reasoning_raw.txt"
    raw_repair_path = reasoning_dir / f"{subject_id}_reasoning_repair_raw.txt"
    validated_path = reasoning_dir / f"{subject_id}_reasoning_validated.json"
    validation_report_path = reasoning_dir / f"{subject_id}_reasoning_validation_report.json"

    reasoning_prompt = load_text(reasoning_prompt_path).replace(
        "{{COMPACT_CASE_JSON}}",
        json.dumps(compact_case, indent=2, ensure_ascii=False),
    )

    raw_reasoning = call_ollama(
        reasoning_prompt,
        model_name=model_name,
        ollama_url=ollama_url,
        json_mode=True,
    )
    save_text(raw_reasoning_path, raw_reasoning)

    try:
        reasoning_json = try_parse_json(raw_reasoning)
    except Exception as e:
        reasoning_json = {
            "_parse_error": str(e),
            "_stage": "initial_reasoning_parse",
        }

    reasoning_json = _ensure_minimum_limitations(reasoning_json, compact_case)
    validation = validate_reasoning_json(reasoning_json, compact_case, schema_path)

    if validation["is_valid"]:
        save_json(validated_path, reasoning_json)
        save_json(validation_report_path, validation)
        return reasoning_json

    repair_prompt = load_text(repair_prompt_path)
    repair_prompt = repair_prompt.replace(
        "{{VALIDATION_ERRORS}}",
        json.dumps(validation["errors"], indent=2, ensure_ascii=False),
    )
    repair_prompt = repair_prompt.replace(
        "{{COMPACT_CASE_JSON}}",
        json.dumps(compact_case, indent=2, ensure_ascii=False),
    )
    repair_prompt = repair_prompt.replace(
        "{{BAD_REASONING_JSON}}",
        json.dumps(reasoning_json, indent=2, ensure_ascii=False),
    )

    raw_repair = call_ollama(
        repair_prompt,
        model_name=model_name,
        ollama_url=ollama_url,
        json_mode=True,
    )
    save_text(raw_repair_path, raw_repair)

    try:
        repaired_json = try_parse_json(raw_repair)
    except Exception as e:
        repaired_validation = {
            "is_valid": False,
            "errors": [f"Repair output could not be parsed as JSON: {str(e)}"],
            "warnings": [],
        }
        save_json(validation_report_path, repaired_validation)
        raise ValueError(
            "Repair output is not valid JSON.\n"
            f"See raw repair output here:\n{raw_repair_path}\n\n"
            f"Parse error: {str(e)}"
        )

    repaired_json = _ensure_minimum_limitations(repaired_json, compact_case)
    repaired_validation = validate_reasoning_json(repaired_json, compact_case, schema_path)
    save_json(validation_report_path, repaired_validation)

    if not repaired_validation["is_valid"]:
        raise ValueError(
            "Reasoning JSON is still invalid after repair.\n"
            + "\n".join(repaired_validation["errors"])
        )

    save_json(validated_path, repaired_json)
    return repaired_json