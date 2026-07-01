# Automatic Generation of Text-Based Summaries of Intracranial EEG Seizure Events Using LLMs

Author: Azhar Saparova  
Thesis: MSc Robotics, Nazarbayev University, 2026  
Supervisor: Berdakh Abibullaev  

## Project Summary

This repository contains the code and documentation for a thesis project on automatic iEEG analysis and report generation. The system includes:

1. HFO detection branch
2. Seizure detection branch
3. LLM-based reasoning and report generation branch

## Repository Structure

Explain every main folder here.

## Methodology Overview

### HFO Detection

- OpenNeuro ds003498 experiments
- HUP adaptation
- Ripple / fast ripple / FRandR analysis
- 95th percentile channel ranking

### Seizure Detection

- SWEC-ETHZ initial experiments
- HUP final experiments
- CNN-transformer model
- Windowing and class imbalance handling
- Export to JSON

### LLM Reporting

- Version 1: report generation
- Version 2: channel-level seizure evidence and fusion
- Version 3: schema validation and deterministic report rendering
- Version 4: bounded tool orchestration and planning

## Data Availability

Raw and processed datasets are not stored in this repository because of file size and data-use restrictions. See `data/README.md`.

## Trained Models

Model checkpoints are stored externally. See `models/README.md`.

## Reproducing Results

1. Create environment
2. Download data
3. Run preprocessing
4. Run HFO detection
5. Run seizure detection
6. Generate JSON outputs
7. Run LLM report generation

## Citation

If you use this code, models, outputs, or documentation, please cite:

Azhar Saparova. Automatic Generation of Text-Based Summaries of Intracranial EEG Seizure Events Using Large Language Models (LLMs). MSc Thesis, Nazarbayev University, 2026.

## License

See `LICENSE.md`.
