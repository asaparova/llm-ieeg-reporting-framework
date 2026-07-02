from __future__ import annotations

import argparse
from pathlib import Path

from orchestration.orchestration_runner import run_orchestration


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True, help="Path to project root")
    parser.add_argument("--subject-id", required=True, help="Example: sub-HUP146")
    parser.add_argument("--model-name", default="qwen3:8b")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434/api/generate")
    args = parser.parse_args()

    project_root = Path(args.project_root)
    subject_id = args.subject_id

    result = run_orchestration(
        project_root=project_root,
        subject_id=subject_id,
        model_name=args.model_name,
        ollama_url=args.ollama_url,
    )

    print(f"Orchestration completed for {subject_id}")
    print(f"Planning decision: {result['plan']['planning_decision']}")
    print(f"Actions executed: {len(result['execution_log'])}")
    print(f"Saved plan to: {project_root / subject_id / 'orchestration' / f'{subject_id}_tool_plan_validated.json'}")
    print(f"Saved execution log to: {project_root / subject_id / 'orchestration' / f'{subject_id}_tool_execution_log.json'}")


if __name__ == "__main__":
    main()