from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from integration.compact_case_builder import build_case_files
from llm.reasoning_runner import run_reasoning_with_repair
from reporting.report_renderer import build_report_data, save_report_outputs
from utils.io_utils import load_json


def rebuild_master_case(project_root: Path, subject_id: str, **kwargs) -> Dict[str, Any]:
    build_case_files(project_root, subject_id)
    master_path = project_root / subject_id / "integration" / f"{subject_id}_master_case.json"
    return {
        "status": "ok",
        "tool_name": "rebuild_master_case",
        "output_path": str(master_path),
    }


def rebuild_compact_case(project_root: Path, subject_id: str, **kwargs) -> Dict[str, Any]:
    # build_case_files writes both master_case and compact_case, so reuse it
    build_case_files(project_root, subject_id)
    compact_path = project_root / subject_id / "integration" / f"{subject_id}_compact_case.json"
    return {
        "status": "ok",
        "tool_name": "rebuild_compact_case",
        "output_path": str(compact_path),
    }


def run_reasoning(
    project_root: Path,
    subject_id: str,
    model_name: str,
    ollama_url: str,
    **kwargs
) -> Dict[str, Any]:
    compact_case_path = project_root / subject_id / "integration" / f"{subject_id}_compact_case.json"
    compact_case = load_json(compact_case_path)

    reasoning = run_reasoning_with_repair(
        compact_case=compact_case,
        project_root=project_root,
        subject_id=subject_id,
        model_name=model_name,
        ollama_url=ollama_url,
    )

    reasoning_path = project_root / subject_id / "reasoning" / f"{subject_id}_reasoning_validated.json"
    return {
        "status": "ok",
        "tool_name": "run_reasoning",
        "output_path": str(reasoning_path),
        "reasoning_keys": list(reasoning.keys()),
    }


def run_report(project_root: Path, subject_id: str, **kwargs) -> Dict[str, Any]:
    subject_dir = project_root / subject_id
    compact_case = load_json(subject_dir / "integration" / f"{subject_id}_compact_case.json")
    reasoning = load_json(subject_dir / "reasoning" / f"{subject_id}_reasoning_validated.json")

    report_data = build_report_data(compact_case, reasoning)
    save_report_outputs(subject_dir, subject_id, report_data)

    report_path = subject_dir / "reports" / f"{subject_id}_final_report.txt"
    return {
        "status": "ok",
        "tool_name": "run_report",
        "output_path": str(report_path),
    }