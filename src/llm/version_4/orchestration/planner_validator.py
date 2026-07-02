from __future__ import annotations

from typing import Any, Dict, List

from utils.io_utils import load_json


def _check_required(obj: Dict[str, Any], keys: List[str], prefix: str, errors: List[str]) -> None:
    for key in keys:
        if key not in obj:
            errors.append(f"Missing key: {prefix}{key}")


def validate_planner_json(plan: Dict[str, Any], compact_case: Dict[str, Any], schema_path) -> Dict[str, Any]:
    schema = load_json(schema_path)
    errors: List[str] = []
    warnings: List[str] = []

    _check_required(plan, schema["required_top_level_keys"], "", errors)
    if errors:
        return {"is_valid": False, "errors": errors, "warnings": warnings}

    planning_decision = plan.get("planning_decision")
    if planning_decision not in schema["planning_decision_allowed"]:
        errors.append(f"Invalid planning_decision: {planning_decision}")

    reason = plan.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        errors.append("reason must be a non-empty string")

    actions = plan.get("actions")
    if not isinstance(actions, list):
        errors.append("actions must be a list")
        return {"is_valid": False, "errors": errors, "warnings": warnings}

    allowed_tool_names = set(schema["allowed_tool_names"])

    # If no_action, actions must be empty
    if planning_decision == "no_action" and len(actions) != 0:
        errors.append("If planning_decision is no_action, actions must be empty")

    # If actions empty, planning_decision must be no_action
    if len(actions) == 0 and planning_decision != "no_action":
        errors.append("If actions is empty, planning_decision must be no_action")

    expected_step = 1
    for i, action in enumerate(actions):
        if not isinstance(action, dict):
            errors.append(f"actions[{i}] must be an object")
            continue

        for required_key in ["step", "tool_name", "args"]:
            if required_key not in action:
                errors.append(f"actions[{i}] missing key: {required_key}")

        if "step" in action:
            if not isinstance(action["step"], int):
                errors.append(f"actions[{i}].step must be an integer")
            elif action["step"] != expected_step:
                errors.append(
                    f"actions[{i}].step must be sequential starting at 1; expected {expected_step}, got {action['step']}"
                )
            expected_step += 1

        if "tool_name" in action:
            tool_name = action["tool_name"]
            if tool_name not in allowed_tool_names:
                errors.append(f"actions[{i}].tool_name is not allowed: {tool_name}")

        if "args" in action and not isinstance(action["args"], dict):
            errors.append(f"actions[{i}].args must be an object")

    # Optional consistency check with compact case
    integration_evidence = compact_case.get("integration_evidence", {})
    concordance_level = integration_evidence.get("concordance_level")
    consistency_flags = integration_evidence.get("consistency_flags", [])

    needs_refresh = (
        concordance_level == "none"
        or (isinstance(consistency_flags, list) and len(consistency_flags) > 0)
    )

    if needs_refresh and planning_decision == "no_action":
        warnings.append(
            "Compact case contains mismatch/flags but planner chose no_action"
        )

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }