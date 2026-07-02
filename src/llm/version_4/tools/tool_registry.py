from __future__ import annotations

from typing import Callable, Dict

from tools.integration_tools import (
    rebuild_compact_case,
    rebuild_master_case,
    run_reasoning,
    run_report,
)

TOOL_REGISTRY: Dict[str, Callable] = {
    "rebuild_master_case": rebuild_master_case,
    "rebuild_compact_case": rebuild_compact_case,
    "run_reasoning": run_reasoning,
    "run_report": run_report,
}