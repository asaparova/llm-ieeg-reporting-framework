from __future__ import annotations

import argparse
from pathlib import Path

from integration.compact_case_builder import build_case_files
from llm.reasoning_runner import run_reasoning_with_repair
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

    build_case_files(project_root, subject_id)

    compact_case_path = project_root / subject_id / "integration" / f"{subject_id}_compact_case.json"
    compact_case = load_json(compact_case_path)

    run_reasoning_with_repair(
        compact_case=compact_case,
        project_root=project_root,
        subject_id=subject_id,
        model_name=args.model_name,
        ollama_url=args.ollama_url,
    )

    print(f"Reasoning completed for {subject_id}")
    print(f"Saved compact case to: {compact_case_path}")
    print(f"Saved validated reasoning to: {project_root / subject_id / 'reasoning' / f'{subject_id}_reasoning_validated.json'}")


if __name__ == "__main__":
    main()