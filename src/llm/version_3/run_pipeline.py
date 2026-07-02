from __future__ import annotations

import argparse
from pathlib import Path

from integration.compact_case_builder import build_case_files
from llm.reasoning_runner import run_reasoning_with_repair
from reporting.report_renderer import build_report_data, save_report_outputs
from utils.io_utils import load_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True, help="Path to LLM_unified_HUP_ver3")
    parser.add_argument("--subject-id", required=True, help="Example: sub-HUP146")
    parser.add_argument("--model-name", default="qwen3:8b")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434/api/generate")
    args = parser.parse_args()

    project_root = Path(args.project_root)
    subject_id = args.subject_id
    subject_dir = project_root / subject_id

    build_case_files(project_root, subject_id)

    compact_case = load_json(subject_dir / "integration" / f"{subject_id}_compact_case.json")

    reasoning = run_reasoning_with_repair(
        compact_case=compact_case,
        project_root=project_root,
        subject_id=subject_id,
        model_name=args.model_name,
        ollama_url=args.ollama_url,
    )

    report_data = build_report_data(compact_case, reasoning)
    save_report_outputs(subject_dir, subject_id, report_data)

    print(f"Pipeline completed for {subject_id}")
    print(f"Master case: {subject_dir / 'integration' / f'{subject_id}_master_case.json'}")
    print(f"Compact case: {subject_dir / 'integration' / f'{subject_id}_compact_case.json'}")
    print(f"Reasoning: {subject_dir / 'reasoning' / f'{subject_id}_reasoning_validated.json'}")
    print(f"Report: {subject_dir / 'reports' / f'{subject_id}_final_report.md'}")


if __name__ == "__main__":
    main()