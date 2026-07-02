from __future__ import annotations

import argparse
from pathlib import Path

from reporting.report_renderer import build_report_data, save_report_outputs
from utils.io_utils import load_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True, help="Path to LLM_unified_HUP_ver3")
    parser.add_argument("--subject-id", required=True, help="Example: sub-HUP146")
    args = parser.parse_args()

    project_root = Path(args.project_root)
    subject_id = args.subject_id
    subject_dir = project_root / subject_id

    compact_case = load_json(subject_dir / "integration" / f"{subject_id}_compact_case.json")
    reasoning = load_json(subject_dir / "reasoning" / f"{subject_id}_reasoning_validated.json")

    report_data = build_report_data(compact_case, reasoning)
    save_report_outputs(subject_dir, subject_id, report_data)

    print(f"Saved report data to: {subject_dir / 'reports' / f'{subject_id}_report_data.json'}")
    print(f"Saved final report to: {subject_dir / 'reports' / f'{subject_id}_final_report.md'}")


if __name__ == "__main__":
    main()