from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict

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

    # ---------- First parse ----------
    try:
        reasoning_json = try_parse_json(raw_reasoning)
    except Exception as e:
        reasoning_json = {
            "_parse_error": str(e),
            "_stage": "initial_reasoning_parse",
        }

    validation = validate_reasoning_json(reasoning_json, compact_case, schema_path)
    if validation["is_valid"]:
        save_json(validated_path, reasoning_json)
        save_json(validation_report_path, validation)
        return reasoning_json

    # ---------- Repair ----------
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

    # ---------- Repair parse ----------
    try:
        repaired_json = try_parse_json(raw_repair)
    except Exception as e:
        repaired_validation = {
            "is_valid": False,
            "errors": [
                f"Repair output could not be parsed as JSON: {str(e)}"
            ],
            "warnings": []
        }
        save_json(validation_report_path, repaired_validation)
        raise ValueError(
            "Repair output is not valid JSON.\n"
            f"See raw repair output here:\n{raw_repair_path}\n\n"
            f"Parse error: {str(e)}"
        )

    repaired_validation = validate_reasoning_json(repaired_json, compact_case, schema_path)
    save_json(validation_report_path, repaired_validation)

    if not repaired_validation["is_valid"]:
        raise ValueError(
            "Reasoning JSON is still invalid after repair.\n"
            + "\n".join(repaired_validation["errors"])
        )

    save_json(validated_path, repaired_json)
    return repaired_json