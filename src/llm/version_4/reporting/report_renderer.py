from __future__ import annotations

from typing import Any, Dict

from utils.io_utils import save_json, save_text


def build_report_data(compact_case: Dict[str, Any], reasoning: Dict[str, Any]) -> Dict[str, str]:
    subject_id = compact_case["subject_id"]
    dataset = compact_case["dataset"]

    hfo = reasoning["hfo_assessment"]
    seiz = reasoning["seizure_assessment"]
    integ = reasoning["integration_assessment"]

    hfo_strong = ", ".join(hfo["strong_consensus_channels"]) if hfo["strong_consensus_channels"] else "none"
    hfo_supportive = ", ".join(hfo["supportive_channels"]) if hfo["supportive_channels"] else "none"
    seiz_top = ", ".join(seiz["top_supportive_channels"]) if seiz["top_supportive_channels"] else "none"
    overlap = ", ".join(integ["overlap_channels"]) if integ["overlap_channels"] else "none"

    case_overview = (
        f"Subject {subject_id} from the {dataset} dataset was analyzed with integrated HFO and seizure branches. "
        f"Cross-modal comparison used exact channel-name matching."
    )

    hfo_findings = (
        f"HFO consensus strength was {hfo['consensus_strength']}. "
        f"Strong consensus channels were {hfo_strong}. "
        f"Additional supportive channels were {hfo_supportive}. "
        f"{hfo['summary']}"
    )

    seizure_findings = (
        f"{seiz['ictal_detection_summary']} "
        f"{seiz['interictal_behavior_summary']} "
        f"Seizure channel-level evidence was treated as {seiz['channel_evidence_type']}. "
        f"Top supportive seizure channels were {seiz_top}. "
        f"{seiz['summary']}"
    )

    cross_modal_integration = (
        f"Concordance mode was {integ['concordance_mode']}. "
        f"Concordance level was {integ['concordance_level']}. "
        f"Overlap channels: {overlap}. "
        f"{integ['summary']}"
    )

    limitations = reasoning["limitations"]
    limitations_text = " ".join(limitations) if limitations else "No additional limitations were stated."

    limitations_and_confidence = (
        f"Overall confidence was {reasoning['overall_confidence']}. "
        f"{reasoning['confidence_rationale']} "
        f"{limitations_text}"
    )

    final_impression = reasoning["ez_hypothesis"]["summary"]

    return {
        "case_overview": case_overview,
        "hfo_findings": hfo_findings,
        "seizure_findings": seizure_findings,
        "cross_modal_integration": cross_modal_integration,
        "limitations_and_confidence": limitations_and_confidence,
        "final_impression": final_impression,
    }


def render_markdown(report_data: Dict[str, str]) -> str:
    return (
        "Case overview\n"
        f"{report_data['case_overview']}\n\n"
        "HFO findings\n"
        f"{report_data['hfo_findings']}\n\n"
        "Seizure findings\n"
        f"{report_data['seizure_findings']}\n\n"
        "Cross-modal integration\n"
        f"{report_data['cross_modal_integration']}\n\n"
        "Limitations and confidence\n"
        f"{report_data['limitations_and_confidence']}\n\n"
        "Final impression\n"
        f"{report_data['final_impression']}\n"
    )


def render_plaintext(report_data: Dict[str, str]) -> str:
    return render_markdown(report_data)


def save_report_outputs(subject_dir, subject_id: str, report_data: Dict[str, str]) -> None:
    reports_dir = subject_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    save_json(reports_dir / f"{subject_id}_report_data.json", report_data)
    save_text(reports_dir / f"{subject_id}_final_report.md", render_markdown(report_data))
    save_text(reports_dir / f"{subject_id}_final_report.txt", render_plaintext(report_data))