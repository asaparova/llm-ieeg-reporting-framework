from __future__ import annotations

import re
from typing import Any, Dict, List

from utils.io_utils import load_json


def _check_required(obj: Dict[str, Any], keys: List[str], prefix: str, errors: List[str]) -> None:
    for key in keys:
        if key not in obj:
            errors.append(f"Missing key: {prefix}{key}")


def _all_channels_from_compact_case(compact_case: Dict[str, Any]) -> set[str]:
    return set(compact_case.get("allowed_channels", []))


def _check_channel_list(name: str, values: Any, allowed_channels: set[str], errors: List[str]) -> None:
    if not isinstance(values, list):
        errors.append(f"{name} must be a list")
        return
    for ch in values:
        if not isinstance(ch, str):
            errors.append(f"{name} contains non-string channel")
            continue
        if ch not in allowed_channels:
            errors.append(f"{name} contains unknown channel: {ch}")


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _contains_any(text: str, terms: List[str]) -> int:
    text_l = text.lower()
    count = 0
    for term in terms:
        if term.lower() in text_l:
            count += 1
    return count


def _has_timing_pattern(text: str) -> bool:
    patterns = [
        r"\d+\.\d+",
        r"\d+\s*[-–]\s*\d+",
        r"\d+\.\d+\s*[-–]\s*\d+\.\d+",
        r"\d+\s*to\s*\d+",
        r"\d+\.\d+\s*to\s*\d+\.\d+",
    ]
    return any(re.search(p, text) for p in patterns)


def validate_reasoning_json(reasoning: Dict[str, Any], compact_case: Dict[str, Any], schema_path) -> Dict[str, Any]:
    schema = load_json(schema_path)
    errors: List[str] = []
    warnings: List[str] = []

    _check_required(reasoning, schema["required_top_level_keys"], "", errors)

    if errors:
        return {"is_valid": False, "errors": errors, "warnings": warnings}

    overall_confidence = reasoning.get("overall_confidence")
    if overall_confidence not in schema["overall_confidence_allowed"]:
        errors.append(f"Invalid overall_confidence: {overall_confidence}")

    hfo_assessment = reasoning.get("hfo_assessment", {})
    seizure_assessment = reasoning.get("seizure_assessment", {})
    integration_assessment = reasoning.get("integration_assessment", {})
    ez_hypothesis = reasoning.get("ez_hypothesis", {})

    _check_required(hfo_assessment, schema["required_hfo_keys"], "hfo_assessment.", errors)
    _check_required(seizure_assessment, schema["required_seizure_keys"], "seizure_assessment.", errors)
    _check_required(integration_assessment, schema["required_integration_keys"], "integration_assessment.", errors)
    _check_required(ez_hypothesis, schema["required_ez_keys"], "ez_hypothesis.", errors)

    if errors:
        return {"is_valid": False, "errors": errors, "warnings": warnings}

    allowed_channels = _all_channels_from_compact_case(compact_case)

    if seizure_assessment.get("channel_evidence_type") not in schema["channel_evidence_type_allowed"]:
        errors.append(f"Invalid seizure_assessment.channel_evidence_type: {seizure_assessment.get('channel_evidence_type')}")

    if integration_assessment.get("concordance_level") not in schema["concordance_level_allowed"]:
        errors.append(f"Invalid integration_assessment.concordance_level: {integration_assessment.get('concordance_level')}")

    if ez_hypothesis.get("status") not in schema["ez_status_allowed"]:
        errors.append(f"Invalid ez_hypothesis.status: {ez_hypothesis.get('status')}")

    _check_channel_list("hfo_assessment.strong_consensus_channels", hfo_assessment.get("strong_consensus_channels"), allowed_channels, errors)
    _check_channel_list("hfo_assessment.supportive_channels", hfo_assessment.get("supportive_channels"), allowed_channels, errors)
    _check_channel_list("seizure_assessment.top_supportive_channels", seizure_assessment.get("top_supportive_channels"), allowed_channels, errors)
    _check_channel_list("integration_assessment.overlap_channels", integration_assessment.get("overlap_channels"), allowed_channels, errors)

    overlap_channels = integration_assessment.get("overlap_channels", [])
    concordance_level = integration_assessment.get("concordance_level")
    if isinstance(overlap_channels, list) and len(overlap_channels) == 0 and concordance_level != "none":
        errors.append("If overlap_channels is empty, concordance_level must be 'none'")

    compact_channel_type = compact_case.get("seizure_evidence", {}).get("channel_evidence_type")
    if compact_channel_type == "model-derived saliency proxy":
        if seizure_assessment.get("channel_evidence_type") != "model-derived saliency proxy":
            errors.append("seizure_assessment.channel_evidence_type must be 'model-derived saliency proxy'")

    for key in ["confidence_rationale"]:
        value = reasoning.get(key)
        if not _is_nonempty_string(value):
            errors.append(f"{key} must be a non-empty string")

    for section_name, section in [
        ("hfo_assessment", hfo_assessment),
        ("seizure_assessment", seizure_assessment),
        ("integration_assessment", integration_assessment),
        ("ez_hypothesis", ez_hypothesis),
    ]:
        summary = section.get("summary")
        if not _is_nonempty_string(summary):
            errors.append(f"{section_name}.summary must be a non-empty string")

    limitations = reasoning.get("limitations")
    if not isinstance(limitations, list):
        errors.append("limitations must be a list")
    else:
        for i, item in enumerate(limitations):
            if not _is_nonempty_string(item):
                errors.append(f"limitations[{i}] must be a non-empty string")

    # -------- Stronger reasoning requirements --------

    # 1. confidence_rationale must cite at least 2 evidence factors
    confidence_rationale = reasoning.get("confidence_rationale", "")
    evidence_terms = schema.get("confidence_rationale_required_evidence_terms", [])
    evidence_hits = _contains_any(confidence_rationale, evidence_terms)
    if evidence_hits < 2:
        errors.append(
            "confidence_rationale must mention at least 2 concrete evidence factors "
            "(for example HFO consensus, ictal detection, interictal false-positive burden, proxy evidence, overlap/concordance, mismatch warning)."
        )

    # 2. ictal_detection_summary must include timings if ictal segments exist
    ictal_segments = compact_case.get("seizure_evidence", {}).get("ictal_candidate_segments", [])
    ictal_detection_summary = seizure_assessment.get("ictal_detection_summary", "")
    if isinstance(ictal_segments, list) and len(ictal_segments) > 0:
        if not _has_timing_pattern(ictal_detection_summary):
            errors.append("seizure_assessment.ictal_detection_summary must include timing information when ictal_candidate_segments are present")

    # 3. limitations must have at least 2 items under mismatch/proxy conditions
    consistency_flags = compact_case.get("integration_evidence", {}).get("consistency_flags", [])
    requires_limitations = (
        compact_channel_type == "model-derived saliency proxy"
        or concordance_level == "none"
        or (isinstance(consistency_flags, list) and len(consistency_flags) > 0)
    )
    if requires_limitations:
        if not isinstance(limitations, list) or len(limitations) < 2:
            errors.append(
                "limitations must contain at least 2 items when concordance is none, consistency flags are present, or seizure evidence is proxy-derived"
            )

    # 4. integration summary must mention mismatch or confidence impact when mismatch flags are present
    integration_summary = integration_assessment.get("summary", "")
    has_mismatch_flag = False
    if isinstance(consistency_flags, list):
        for flag in consistency_flags:
            if isinstance(flag, dict) and flag.get("code") == "cross_modal_mismatch":
                has_mismatch_flag = True
                break

    if has_mismatch_flag:
        integration_summary_lower = integration_summary.lower()
        mismatch_ok_terms = [
            "confidence",
            "limit",
            "limits",
            "limited",
            "lower",
            "lowers",
            "reduce",
            "reduces",
            "cautious",
            "mismatch",
            "warning",
        ]
        if not any(word in integration_summary_lower for word in mismatch_ok_terms):
            errors.append(
                "integration_assessment.summary must explicitly mention mismatch or confidence limitation when cross_modal_mismatch is present"
            )

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }