# cmb-scale-invariants-software

Software for the paper:
"Robust Separation from Patch-wise Null Surrogates in Planck 2018 CMB Patches: An Encoding-Based Diagnostic".

## Software DOI
Concept DOI (all versions): https://doi.org/10.5281/zenodo.18855045
Version DOI (v1.0.2): https://doi.org/10.5281/zenodo.18855133

## What this repository contains
This repository contains the Python analysis pipeline and helper scripts used to generate the paper's numerical results.
It does not contain large artifact bundles.

## Reproducibility
The paper defines dataset IDs and an artifact layout under:
`data/processed/astro/suite/<dataset_id>/`

Large artifacts are published separately (Zenodo dataset record to be linked in the paper).
Run outputs include JSON summaries and CSV metrics, and are traceable as described in the paper appendix.

## Main entry points
- `scripts/run_t3_on_patches.py`  
  Runs the T3 pipeline on an existing patch stack dataset directory and produces summaries and figures.

- `scripts/build_headline_patches.py`  
  Builds the headline patch stacks (Planck products, mask cut, patch centers) used by the paper.

- `scripts/build_hm_diff_patches.py`  
  Builds the half-mission difference map patch stacks used for negative controls.

## Installation
Create a virtual environment and install dependencies.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
````

## License

Apache-2.0. See `LICENSE`.

## Citation

See `CITATION.cff`.

