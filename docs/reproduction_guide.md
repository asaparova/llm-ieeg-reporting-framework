# Reproduction Guide

This document describes how to reproduce the main thesis outputs for the project:

**Automatic Generation of Text-Based Summaries of Intracranial EEG Seizure Events Using Large Language Models (LLMs)**

Author: **Azhar Saparova**  
Thesis: MSc Robotics, Nazarbayev University, 2026  

---

## Overview

The full project contains three main branches:

1. **HFO detection branch**
2. **Seizure detection branch**
3. **LLM reasoning and report-generation branch**

The final system uses structured JSON outputs from the HFO and seizure branches as inputs for the LLM reporting module.

Because the raw iEEG datasets are large and may have access restrictions, the project can be reproduced at different levels.

---

# Reproduction Levels

## Level 1: Reproduce LLM Reports from Existing JSON Summaries

This is the easiest and most reliable reproduction level.

It assumes that HFO and seizure JSON summaries are already available in the repository or in the corresponding subject folders.

Use this level to reproduce:

- LLM reasoning outputs;
- validated reasoning JSON;
- final report files;
- Version 4 orchestration logs.

---

## Level 2: Reproduce LLM Input JSON Files from Processed HFO and Seizure Outputs

This level assumes that processed HFO and seizure branch outputs are available.

Use this level to reproduce:

- HFO summary JSON;
- seizure summary JSON;
- master case JSON;
- compact case JSON.

---

## Level 3: Full Reproduction from Raw Datasets

This is the most complete but also the hardest reproduction level.

It requires access to the original datasets and the correct local environment (for the information about the datasets please refere to the data folder).

Use this level to reproduce:

- raw data preprocessing;
- HFO detection;
- seizure model training/evaluation;
- JSON export;
- LLM report generation.

---

# Environment Setup

## 1. Clone the Repository

```bash
git clone https://github.com/asaparova/Master-Thesis.git
cd Master-Thesis
```

If the repository is private, make sure that the user has been granted access.

---

## 2. Install and Run Ollama

The LLM pipeline was developed for local inference through Ollama.

Install Ollama from:

```text
https://ollama.com/
```

Pull the model:

```bash
ollama pull qwen3:8b
```

Start Ollama:

```bash
ollama serve
```

Default endpoint expected by the scripts:

```text
http://127.0.0.1:11434/api/generate
```

---

# Data Setup

Raw datasets are not stored directly in the repository.

Expected local structure:

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
```

External data links should be documented in:

```text
data/external_links.md
```

---

## Datasets Used

| Dataset | Used For | Included in GitHub |
|---|---|---|
| OpenNeuro ds003498 | Initial HFO detection experiments | No |
| SWEC-ETHZ | Initial seizure detection experiments | No |
| HUP | Final HFO, seizure, and LLM experiments | No |

---

## Files Not Stored in GitHub

The following files should not be committed to GitHub:

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
```

These files should be stored externally using Google Drive, OneDrive, institutional storage, or another access-controlled storage system.

---

# Level 1: Reproduce LLM Reports from Existing JSON Summaries

This level uses prepared JSON summaries from the HFO and seizure branches.

It does not require raw iEEG data.

---

## Expected LLM Input Files

For each subject:

```text
src/llm/version_X/sub-HUPXXX/hfo/
  sub-HUPXXX_hfo_subject_summary_for_llm.json

src/llm/version_X/sub-HUPXXX/seizure/
  sub-HUPXXX_*task-ictal*_seizure_summary_for_llm.json
  sub-HUPXXX_*task-interictal*_seizure_summary_for_llm.json
```

Example for `sub-HUP146`:

```text
src/llm/version_4/sub-HUP146/hfo/
  sub-HUP146_hfo_subject_summary_for_llm.json

src/llm/version_4/sub-HUP146/seizure/
  sub-HUP146_ses-presurgery_task-ictal_acq-seeg_run-03_seizure_summary_for_llm.json
  sub-HUP146_ses-presurgery_task-interictal_acq-seeg_run-02_seizure_summary_for_llm.json
```

---

## Reproduce Version 1

Go to the Version 1 folder:

```bash
cd src/llm/version_1
```

Run:

```bash
python build_master_case.py
python run_llm_case.py
```

Expected outputs:

```text
sub-HUP146/integration/
  sub-HUP146_master_case.json

sub-HUP146/reports/
  sub-HUP146_compact_llm_input.json
  sub-HUP146_reasoning.json
  sub-HUP146_reasoning_raw.txt
  sub-HUP146_report_raw.txt
  sub-HUP146_final_report.txt
```

---

## Reproduce Version 2

Go to the Version 2 folder:

```bash
cd src/llm/version_2
```

Run:

```bash
python build_master_case_v2a.py
python run_llm_case_v2a.py
```

Expected outputs:

```text
sub-HUP146/integration/
  sub-HUP146_master_case.json

sub-HUP146/reports/
  sub-HUP146_compact_llm_input.json
  sub-HUP146_reasoning.json
  sub-HUP146_reasoning_raw.txt
  sub-HUP146_reasoning_repair_raw.txt
  sub-HUP146_report_raw.txt
  sub-HUP146_final_report.txt
```

---

## Reproduce Version 3

Go to the Version 3 folder:

```bash
cd src/llm/version_3
```

Run the full pipeline:

```bash
python run_pipeline.py \
  --project-root . \
  --subject-id sub-HUP146 \
  --model-name qwen3:8b \
  --ollama-url http://127.0.0.1:11434/api/generate
```

Expected outputs:

```text
sub-HUP146/integration/
  sub-HUP146_master_case.json
  sub-HUP146_compact_case.json

sub-HUP146/reasoning/
  sub-HUP146_reasoning_raw.txt
  sub-HUP146_reasoning_repair_raw.txt
  sub-HUP146_reasoning_validated.json
  sub-HUP146_reasoning_validation_report.json

sub-HUP146/reports/
  sub-HUP146_report_data.json
  sub-HUP146_final_report.md
  sub-HUP146_final_report.txt
```

To run only reasoning:

```bash
python run_reasoning.py \
  --project-root . \
  --subject-id sub-HUP146 \
  --model-name qwen3:8b \
  --ollama-url http://127.0.0.1:11434/api/generate
```

To regenerate only the deterministic report:

```bash
python run_report.py \
  --project-root . \
  --subject-id sub-HUP146
```

---

## Reproduce Version 4

Go to the Version 4 folder:

```bash
cd src/llm/version_4
```

Run the static Version 4 pipeline:

```bash
python run_pipeline.py \
  --project-root . \
  --subject-id sub-HUP146 \
  --model-name qwen3:8b \
  --ollama-url http://127.0.0.1:11434/api/generate
```

Expected outputs:

```text
sub-HUP146/integration/
  sub-HUP146_master_case.json
  sub-HUP146_compact_case.json

sub-HUP146/reasoning/
  sub-HUP146_reasoning_raw.txt
  sub-HUP146_reasoning_repair_raw.txt
  sub-HUP146_reasoning_validated.json
  sub-HUP146_reasoning_validation_report.json

sub-HUP146/reports/
  sub-HUP146_report_data.json
  sub-HUP146_final_report.md
  sub-HUP146_final_report.txt
```

---

## Reproduce Version 4 Orchestration

From the Version 4 folder:

```bash
python run_orchestration.py \
  --project-root . \
  --subject-id sub-HUP146 \
  --model-name qwen3:8b \
  --ollama-url http://127.0.0.1:11434/api/generate
```

Expected outputs:

```text
sub-HUP146/orchestration/
  sub-HUP146_orchestration_state.json
  sub-HUP146_tool_execution_log.json
  sub-HUP146_tool_plan_raw.txt
  sub-HUP146_tool_plan_validated.json
  sub-HUP146_tool_plan_validation_report.json
```

---

## Reproduce Additional Version 4 Subjects

The final Version 4 system can also be run on additional subjects if their input JSON files are available.

Example:

```bash
python run_pipeline.py \
  --project-root . \
  --subject-id sub-HUP164 \
  --model-name qwen3:8b \
  --ollama-url http://127.0.0.1:11434/api/generate
```

For orchestration:

```bash
python run_orchestration.py \
  --project-root . \
  --subject-id sub-HUP164 \
  --model-name qwen3:8b \
  --ollama-url http://127.0.0.1:11434/api/generate
```

---

# Level 2: Reproduce LLM Input JSON Files from Processed Outputs

This level requires processed outputs from the HFO and seizure branches.

---

## Expected HFO Output

The HFO branch should produce:

```text
sub-HUPXXX_hfo_subject_summary_for_llm.json
```

This file should include:

- subject ID;
- sampling frequency;
- HFO detector settings;
- analyzed runs;
- ripple rate per channel;
- fast ripple rate per channel;
- FRandR rate per channel;
- HFO area;
- top HFO channels;
- cross-run HFO summary.

---

## Expected Seizure Output

The seizure branch should produce run-level JSON summaries:

```text
sub-HUPXXX_*task-ictal*_seizure_summary_for_llm.json
sub-HUPXXX_*task-interictal*_seizure_summary_for_llm.json
```

These files should include:

- subject ID;
- run ID;
- task type;
- number of windows;
- predicted positive fraction;
- seizure probability statistics;
- candidate ictal segments;
- seizure-supportive channels;
- run-level interpretation.

---

## Procedure

1. Run the HFO preprocessing notebooks.
2. Run the HFO detection notebooks.
3. Export the HFO subject summary JSON.
4. Run the seizure preprocessing notebooks.
5. Run the seizure detection notebooks.
6. Export seizure summary JSON files.
7. Copy the exported JSON files into the relevant LLM version subject folder.
8. Run the LLM pipeline.

Example target folder:

```text
src/llm/version_4/sub-HUP146/
  hfo/
  seizure/
```

---

# Level 3: Full Reproduction from Raw Datasets

This level requires access to the original datasets.

---

## Expected Raw Data Folders

```text
data/raw/openneuro_ds003498/
data/raw/swec_ethz/
data/raw/hup/
```

---

## General Full Pipeline Order

Run the project in this order:

1. Check sampling frequency and metadata.
2. Run HFO preprocessing.
3. Run HFO detection.
4. Run FRandR analysis.
5. Export HFO summary JSON.
6. Run seizure preprocessing.
7. Train or load the seizure detection model.
8. Evaluate seizure detection.
9. Export seizure summary JSON.
10. Run the LLM reporting pipeline.
11. Compare generated outputs with thesis figures and tables.

---

## HFO Branch Reproduction

The HFO branch includes:

- OpenNeuro ds003498 initial experiments;
- HUP adaptation;
- ripple detection;
- fast ripple detection;
- FRandR detection;
- HFO-area estimation using channel-level rates.

Relevant folders:

```text
src/hfo/
src/legacy/code of old models/
```

Relevant notebooks may include:

```text
HFO detection with HUP.ipynb
HUP pre-processing for HFO detection.ipynb
Pre-processing ds003498.ipynb
STE and Hilbert HFO detector with FRandR labeling.ipynb
```

Expected final HFO output:

```text
sub-HUPXXX_hfo_subject_summary_for_llm.json
```

---

## Seizure Branch Reproduction

The seizure branch includes:

- SWEC-ETHZ initial seizure detection experiments;
- HUP seizure detection;
- CNN-transformer model;
- window-based segmentation;
- class imbalance handling;
- run-level evaluation;
- subject-level evaluation.

Relevant folders:

```text
src/seizure/
src/legacy/HUP seizure detection ver 1/
src/legacy/code of old models/
```

Relevant notebooks may include:

```text
Check HUP sampling freq.ipynb
New pre-processing ver2 HUP dataset.ipynb
Seizure detection ver 2.ipynb
Seizure detection v3.ipynb
New model with pre-processing SWEC ETHZ.ipynb
Pre-processing SWEC ETHZ.ipynb
```

Expected final seizure outputs:

```text
sub-HUPXXX_*task-ictal*_seizure_summary_for_llm.json
sub-HUPXXX_*task-interictal*_seizure_summary_for_llm.json
```

---

# Expected Final LLM Outputs

The final LLM system should produce:

```text
integration/
  sub-HUPXXX_master_case.json
  sub-HUPXXX_compact_case.json

reasoning/
  sub-HUPXXX_reasoning_raw.txt
  sub-HUPXXX_reasoning_repair_raw.txt
  sub-HUPXXX_reasoning_validated.json
  sub-HUPXXX_reasoning_validation_report.json

reports/
  sub-HUPXXX_report_data.json
  sub-HUPXXX_final_report.md
  sub-HUPXXX_final_report.txt

orchestration/
  sub-HUPXXX_orchestration_state.json
  sub-HUPXXX_tool_execution_log.json
  sub-HUPXXX_tool_plan_raw.txt
  sub-HUPXXX_tool_plan_validated.json
  sub-HUPXXX_tool_plan_validation_report.json
```

---

# Reproducibility Notes

LLM-based results may vary slightly depending on:

- model version;
- Ollama version;
- decoding parameters;
- operating system;
- GPU/CPU environment;
- prompt changes.

For this reason, the repository stores several intermediate artifacts:

- compact LLM input;
- raw LLM output;
- validated reasoning JSON;
- reasoning validation report;
- deterministic report data;
- final report;
- orchestration logs.

These files make the pipeline easier to inspect and compare.

---

# Troubleshooting

## Ollama is not running

Error symptoms:

```text
Connection refused
Failed to connect to 127.0.0.1:11434
```

Fix:

```bash
ollama serve
```

---

## Model is missing

Error symptoms:

```text
model not found
```

Fix:

```bash
ollama pull qwen3:8b
```

---

## JSON validation fails

Possible reasons:

- LLM output is not valid JSON;
- required fields are missing;
- field names do not match the schema;
- model produced explanatory text around JSON.

Fix:

1. Check the raw reasoning output.
2. Check the validation report.
3. Run the repair step if available.
4. Rerun reasoning with stricter prompt or same model.

---

## Script cannot find files

Possible reasons:

- subject ID is wrong;
- files are placed in the wrong folder;
- local absolute paths are still present in early scripts;
- expected JSON files are missing.

Fix:

1. Check the subject folder.
2. Check HFO and seizure input folders.
3. Replace local absolute paths with relative paths.
4. Confirm that filenames match the expected pattern.

---

## Windows path issues

Some early scripts may contain paths such as:

```text
D:\LLM_unified_HUP
```

Replace them with repository-relative paths where possible.

Recommended structure:

```text
src/llm/version_X/sub-HUPXXX/
```

---

# Authorship and Citation

Unless explicitly stated otherwise, all original code, prompts, schemas, reports, figures, and documentation were developed by **Azhar Saparova** as part of the MSc thesis project.

Any reuse of this repository, code, prompts, schemas, outputs, or reports should properly credit:

```text
Azhar Saparova.
Automatic Generation of Text-Based Summaries of Intracranial EEG Seizure Events Using Large Language Models (LLMs).
MSc Thesis, Nazarbayev University, 2026.
```
