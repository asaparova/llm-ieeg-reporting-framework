# Data

This folder documents the datasets and derived data files used in the thesis project:

**Automatic Generation of Text-Based Summaries of Intracranial EEG Seizure Events Using Large Language Models (LLMs)**

Raw and processed datasets are **not stored directly in this GitHub repository** because they are large and may be subject to dataset access restrictions.

---

## Overview

The project uses three main datasets:

| Dataset | Used For | Repository Status | Notes |
|---|---|---|---|
| OpenNeuro ds003498 | Initial HFO detection experiments | Not included | Download/access separately |
| SWEC-ETHZ | Initial seizure detection experiments | Not included | Download/access separately |
| HUP | Final HFO detection, seizure detection, and LLM case studies | Not included | Access-controlled / external storage |

---

## External Data Links

Add dataset and processed-data links in:

```text
data/external_links.md
```

Recommended format:

```markdown
# External Data Links

## Raw Data

### OpenNeuro ds003498

- Source: https://openneuro.org/datasets/ds003498/versions/1.1.1
- Used for: Initial HFO detection experiments

### SWEC-ETHZ

- Source: http://ieeg-swez.ethz.ch/
- Used for: Initial seizure detection experiments

### HUP Dataset

- Source: https://openneuro.org/datasets/ds004100/versions/1.1.1
- Used for: Final HFO detection, seizure detection, and LLM case studies

## Processed Data

The HUP dataset for HFO detection takes 13 Gb and processed OpenNeuro ds003498 dataet takes 78 Gb of storage, so I did not manage to add it to the free storage in cloud. You can run the pre-processing scripts to reproduce the results

### Processed SWEC-ETHZ Files

- Link: <ADD_LINK_HERE>
- Description: Preprocessed files used for seizure detection experiments

### Processed HUP Files (for HFO detection)

- Link: https://drive.google.com/file/d/1lebSnyId6PRgI7X9LmePVv7GfE79OxDZ/view?usp=drive_link
- Description: Preprocessed HUP files used for final HFO branch


---

## Data Used by Each Project Branch

### 1. HFO Detection Branch

The HFO branch uses:

- OpenNeuro ds003498 for initial HFO detection experiments;
- HUP dataset for final subject-level HFO analysis;
- ripple, fast ripple, and FRandR detections;
- channel-level HFO rates;
- HFO area estimation based on high-rate channels.

Expected derived output:

```text
sub-HUPXXX_hfo_subject_summary_for_llm.json
```

Example:

```text
sub-HUP146_hfo_subject_summary_for_llm.json
```

This JSON is used as an input to the LLM reporting module.

---

### 2. Seizure Detection Branch

The seizure branch uses:

- SWEC-ETHZ for initial seizure detection experiments;
- HUP dataset for final seizure detection experiments;
- window-based segmentation;
- CNN-transformer-based seizure detection;
- run-level and subject-level evaluation;
- ictal and interictal summary export.

Expected derived outputs:

```text
sub-HUPXXX_*task-ictal*_seizure_summary_for_llm.json
sub-HUPXXX_*task-interictal*_seizure_summary_for_llm.json
```

Example:

```text
sub-HUP146_ses-presurgery_task-ictal_acq-seeg_run-03_seizure_summary_for_llm.json
sub-HUP146_ses-presurgery_task-interictal_acq-seeg_run-02_seizure_summary_for_llm.json
```

These JSON files are used as inputs to the LLM reporting module.

---

### 3. LLM Reporting Branch

The LLM branch does not use raw iEEG data directly.

Instead, it uses structured JSON summaries produced by the HFO and seizure branches:

```text
src/llm/version_X/sub-HUPXXX/hfo/
src/llm/version_X/sub-HUPXXX/seizure/
```

Expected input structure:

```text
src/llm/version_X/sub-HUPXXX/
  hfo/
    sub-HUPXXX_hfo_subject_summary_for_llm.json

  seizure/
    sub-HUPXXX_*task-ictal*_seizure_summary_for_llm.json
    sub-HUPXXX_*task-interictal*_seizure_summary_for_llm.json
```

The LLM pipeline then generates:

```text
integration/
reasoning/
reports/
orchestration/
```

depending on the LLM version.

---


