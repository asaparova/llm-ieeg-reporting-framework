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

## Expected Local Data Structure

After downloading or receiving access to the datasets, organize them locally as follows:

```text
data/
  raw/
    openneuro_ds003498/
    swec_ethz/
    hup/

  processed/
    openneuro_ds003498/
    swec_ethz/
    hup/

  external_links.md
  checksums.sha256
```

The `raw/` and `processed/` folders are intentionally ignored by Git and should not be pushed to GitHub.

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

- Source: <ADD_LINK_HERE>
- Access notes: <ADD_ACCESS_NOTES_HERE>
- Used for: Initial HFO detection experiments

### SWEC-ETHZ

- Source: <ADD_LINK_HERE>
- Access notes: <ADD_ACCESS_NOTES_HERE>
- Used for: Initial seizure detection experiments

### HUP Dataset

- Source / storage: <ADD_RESTRICTED_LINK_HERE>
- Access notes: <ADD_ACCESS_NOTES_HERE>
- Used for: Final HFO detection, seizure detection, and LLM case studies

## Processed Data

### Processed OpenNeuro Files

- Link: <ADD_LINK_HERE>
- Description: Preprocessed files used for initial HFO detection experiments

### Processed SWEC-ETHZ Files

- Link: <ADD_LINK_HERE>
- Description: Preprocessed files used for seizure detection experiments

### Processed HUP Files

- Link: <ADD_LINK_HERE>
- Description: Preprocessed HUP files used for final HFO and seizure branches

## LLM Input JSON Files

- Link: <ADD_LINK_HERE>
- Description: HFO and seizure JSON summaries used as input for the LLM reporting module
```

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

## Files That Should Not Be Committed

Do not commit raw biomedical signals, large arrays, trained model checkpoints, or local environment files.

Examples:

```text
*.edf
*.fif
*.mat
*.npy
*.npz
*.h5
*.hdf5
*.pkl
*.pickle
*.pt
*.pth
*.ckpt
*.onnx
.env
```

These files should be stored externally.

---

## Files That May Be Committed

Small derived files may be committed if they do not violate dataset restrictions and do not contain sensitive information.

Examples:

```text
*_hfo_subject_summary_for_llm.json
*_seizure_summary_for_llm.json
*_compact_case.json
*_master_case.json
*_reasoning_validated.json
*_final_report.md
*_final_report.txt
```

Before committing derived files, confirm that they do not contain restricted or identifiable patient information.

---

## Checksums

If external data packages are shared, add checksums to:

```text
data/checksums.sha256
```

Example format:

```text
<sha256_hash>  processed_hup_llm_inputs.zip
<sha256_hash>  trained_seizure_model_checkpoint.pt
<sha256_hash>  hfo_processed_outputs.zip
```

To generate a checksum on Windows Git Bash:

```bash
sha256sum file_name.zip
```

---

## Notes on Access

Some datasets may require permission, institutional access, or agreement with dataset-use conditions.

If a dataset cannot be redistributed, this repository should only provide:

- dataset name;
- original source;
- access instructions;
- expected local folder structure;
- scripts/notebooks for processing after access is obtained.

---

## Contact

For questions about dataset organization, processed outputs, or reproduction of the thesis results, contact:

**Azhar Saparova**  
MSc Robotics, Nazarbayev University, 2026
