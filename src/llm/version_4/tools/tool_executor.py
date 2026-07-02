from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from tools.tool_registry import TOOL_REGISTRY


def execute_tool_plan(
    plan: Dict[str, Any],
    project_root: Path,
    subject_id: str,
    model_name: str,
    ollama_url: str,
) -> List[Dict[str, Any]]:
    actions = plan.get("actions", [])
    execution_log: List[Dict[str, Any]] = []

    if len(actions) == 0:
        print("[orchestration] No actions to execute.")
        return execution_log

    print(f"[orchestration] Executing {len(actions)} planned action(s)...")

    for action in actions:
        step = action["step"]
        tool_name = action["tool_name"]
        args = action.get("args", {}) or {}

        if tool_name not in TOOL_REGISTRY:
            raise ValueError(f"Unknown tool: {tool_name}")

        fn = TOOL_REGISTRY[tool_name]

        print(f"[orchestration] Step {step}: calling tool '{tool_name}' with args={args}")

        try:
            result = fn(
                project_root=project_root,
                subject_id=subject_id,
                model_name=model_name,
                ollama_url=ollama_url,
                **args,
            )

            print(f"[orchestration] Step {step}: tool '{tool_name}' finished successfully")

            execution_log.append(
                {
                    "step": step,
                    "tool_name": tool_name,
                    "args": args,
                    "status": "ok",
                    "result": result,
                }
            )
        except Exception as e:
            print(f"[orchestration] Step {step}: tool '{tool_name}' failed: {str(e)}")

            execution_log.append(
                {
                    "step": step,
                    "tool_name": tool_name,
                    "args": args,
                    "status": "error",
                    "error": str(e),
                }
            )
            raise

    return execution_log