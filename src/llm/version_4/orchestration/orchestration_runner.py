from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from integration.compact_case_builder import build_case_files
from orchestration.planner_runner import run_planner_with_repair
from tools.tool_executor import execute_tool_plan
from utils.io_utils import load_json, save_json


def ensure_case_files(project_root: Path, subject_id: str) -> Dict[str, Path]:
    subject_dir = project_root / subject_id
    integration_dir = subject_dir / "integration"
    integration_dir.mkdir(parents=True, exist_ok=True)

    master_case_path = integration_dir / f"{subject_id}_master_case.json"
    compact_case_path = integration_dir / f"{subject_id}_compact_case.json"

    if not master_case_path.exists() or not compact_case_path.exists():
        print("[orchestration] Missing master/compact case. Building them now...")
        build_case_files(project_root=project_root, subject_id=subject_id)

    if not master_case_path.exists():
        raise FileNotFoundError(f"Master case was not created: {master_case_path}")
    if not compact_case_path.exists():
        raise FileNotFoundError(f"Compact case was not created: {compact_case_path}")

    return {
        "master_case_path": master_case_path,
        "compact_case_path": compact_case_path,
    }


def get_artifact_paths(project_root: Path, subject_id: str) -> Dict[str, Path]:
    subject_dir = project_root / subject_id

    reasoning_dir = subject_dir / "reasoning"
    reports_dir = subject_dir / "reports"
    orchestration_dir = subject_dir / "orchestration"

    reasoning_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    orchestration_dir.mkdir(parents=True, exist_ok=True)

    return {
        "reasoning_validated": reasoning_dir / f"{subject_id}_reasoning_validated.json",
        "report_txt": reports_dir / f"{subject_id}_final_report.txt",
        "tool_plan": orchestration_dir / f"{subject_id}_tool_plan_validated.json",
        "tool_log": orchestration_dir / f"{subject_id}_tool_execution_log.json",
        "orch_state": orchestration_dir / f"{subject_id}_orchestration_state.json",
    }


def make_forced_plan_if_outputs_missing(project_root: Path, subject_id: str) -> Dict[str, Any] | None:
    paths = get_artifact_paths(project_root, subject_id)

    reasoning_exists = paths["reasoning_validated"].exists()
    report_exists = paths["report_txt"].exists()

    if report_exists:
        return None

    if reasoning_exists:
        print("[orchestration] Final report is missing. Forcing run_report.")
        return {
            "planning_decision": "rerun_reasoning_report",
            "reason": "Final report file is missing; validated reasoning already exists.",
            "actions": [
                {
                    "step": 1,
                    "tool_name": "run_report",
                    "args": {},
                }
            ],
        }

    print("[orchestration] Reasoning/report outputs are missing. Forcing run_reasoning -> run_report.")
    return {
        "planning_decision": "rerun_reasoning_report",
        "reason": "Derived outputs are missing; validated reasoning and/or final report do not exist.",
        "actions": [
            {
                "step": 1,
                "tool_name": "run_reasoning",
                "args": {},
            },
            {
                "step": 2,
                "tool_name": "run_report",
                "args": {},
            },
        ],
    }


def run_orchestration(
    project_root: Path,
    subject_id: str,
    model_name: str = "qwen3:8b",
    ollama_url: str = "http://127.0.0.1:11434/api/generate",
) -> Dict[str, Any]:
    subject_dir = project_root / subject_id
    orch_dir = subject_dir / "orchestration"
    orch_dir.mkdir(parents=True, exist_ok=True)

    case_paths = ensure_case_files(project_root, subject_id)
    compact_case = load_json(case_paths["compact_case_path"])

    forced_plan = make_forced_plan_if_outputs_missing(project_root, subject_id)

    if forced_plan is not None:
        plan = forced_plan
    else:
        print("[orchestration] Running planner...")
        plan = run_planner_with_repair(
            compact_case=compact_case,
            project_root=project_root,
            subject_id=subject_id,
            model_name=model_name,
            ollama_url=ollama_url,
        )

    print(f"[orchestration] Planner decision: {plan['planning_decision']}")
    print(f"[orchestration] Planner reason: {plan['reason']}")

    actions: List[Dict[str, Any]] = plan.get("actions", [])

    if actions:
        execution_log = execute_tool_plan(
            plan=plan,
            project_root=project_root,
            subject_id=subject_id,
            model_name=model_name,
            ollama_url=ollama_url,
        )
    else:
        print("[orchestration] No actions to execute.")
        execution_log = []

    orchestration_state = {
        "case_id": compact_case.get("case_id", subject_id),
        "subject_id": subject_id,
        "planning_decision": plan.get("planning_decision"),
        "reason": plan.get("reason"),
        "n_actions": len(actions),
        "execution_status": "ok",
    }

    save_json(orch_dir / f"{subject_id}_tool_plan_validated.json", plan)
    save_json(orch_dir / f"{subject_id}_tool_execution_log.json", {"events": execution_log})
    save_json(orch_dir / f"{subject_id}_orchestration_state.json", orchestration_state)

    return {
        "plan": plan,
        "execution_log": execution_log,
        "orchestration_state": orchestration_state,
    }