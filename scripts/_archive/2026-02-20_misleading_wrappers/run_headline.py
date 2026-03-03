# ======================================================================
# File: scripts/run_headline.py
# Purpose: Run the headline configuration from configs/headline.yaml
# Outputs:
#   - legacy outputs under data/processed/astro/suite/<dataset>/
#   - a small run manifest under outputs/summaries/
# ======================================================================

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception as e:
    raise SystemExit(
        "Missing dependency: pyyaml.\n"
        "Install it inside your venv:\n"
        "  pip install pyyaml\n"
    ) from e


REPO = Path(__file__).resolve().parents[1]

PATCH_ROOT = REPO / "data" / "processed" / "astro" / "patches"
SUITE_ROOT = REPO / "data" / "processed" / "astro" / "suite"

OUT_SUMMARIES = REPO / "outputs" / "summaries"
OUT_SUMMARIES.mkdir(parents=True, exist_ok=True)


def _dataset_id(map_name: str, cfg: dict) -> str:
    fov = int(round(float(cfg["patches"]["fov_deg"])))
    b = int(cfg["mask"]["b_cut_deg"])
    n = int(cfg["patches"]["n_patches"])
    beam = int(cfg["beam"]["fwhm_arcmin"])
    # Stable, explicit, ASCII only.
    # This name must match the patches folder name under data/processed/astro/patches/<dataset_id>/meta.json
    return f"planck2018_{map_name}_T_fov{fov}_b{b}_n{n}_sm{beam}am"


def _check_patches_exist(ds: str) -> None:
    meta = PATCH_ROOT / ds / "meta.json"
    if not meta.exists():
        raise SystemExit(
            "Missing patches.\n"
            f"Expected meta.json here:\n  {meta}\n\n"
            "Next step is to build or copy the headline patches into:\n"
            f"  {PATCH_ROOT / ds}\n"
            "so that meta.json lists the patch .npy files.\n"
        )


def _run_t3(ds: str, scales: list[int], trend: str, agg: str, null_family: str, null_n: int, null_seed: int) -> None:
    cmd = [
        "python",
        str(REPO / "scripts" / "run_t3_on_patches.py"),
        "--dataset",
        ds,
        "--trend",
        str(trend),
        "--agg",
        str(agg),
        "--null-family",
        str(null_family),
        "--scales",
        ",".join(str(x) for x in scales),
        "--null",
        str(null_n),
        "--null-seed",
        str(null_seed),
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=str, default="configs/headline.yaml")
    args = ap.parse_args()

    cfg_path = (REPO / args.config).resolve()
    if not cfg_path.exists():
        raise SystemExit(f"Config not found: {cfg_path}")

    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))

    trend = str(cfg.get("trend", "auto"))
    agg = str(cfg.get("aggregation", {}).get("statistic", "median"))
    if agg not in ("mean", "median"):
        raise SystemExit(f"Config error: aggregation.statistic must be mean|median, got {agg}")

    scales = list(cfg["scales"]["core"])
    if scales != [1, 2, 4]:
        raise SystemExit(f"Config error: scales.core must be [1, 2, 4], got {scales}")

    null_n = int(cfg["null_model"]["n_surrogates"])
    null_seed = int(cfg["null_model"]["seed"])
    null_family = str(cfg["null_model"].get("type", "phase_randomized"))
    null_tag = "" if null_family == "phase_randomized" else f"_{null_family}"

    if trend not in ("log", "inv", "auto"):
        raise SystemExit(f"Config error: trend must be one of log, inv, auto, got {trend}")

    ds_ref = _dataset_id(str(cfg["maps"]["reference"]), cfg)
    ds_cmp = _dataset_id(str(cfg["maps"]["comparison"]), cfg)

    _check_patches_exist(ds_ref)
    _check_patches_exist(ds_cmp)

    SUITE_ROOT.mkdir(parents=True, exist_ok=True)

    print(f"Running T3 headline: {ds_ref}  trend={trend} agg={agg}")
    _run_t3(ds_ref, scales=scales, trend=trend, agg=agg, null_family=null_family, null_n=null_n, null_seed=null_seed)

    print(f"Running T3 headline: {ds_cmp}  trend={trend} agg={agg}")
    _run_t3(ds_cmp, scales=scales, trend=trend, agg=agg, null_family=null_family, null_n=null_n, null_seed=null_seed)

    manifest = {
        "config_path": str(cfg_path),
        "tag": str(cfg["output"]["tag"]),
        "datasets": {"reference": ds_ref, "comparison": ds_cmp},
        "scales_core": scales,
        "null": {"type": null_family, "n_surrogates": null_n, "seed": null_seed},
        "suite_root": str(SUITE_ROOT),
        "trend": trend,
        "aggregation": {"statistic": agg},
        "expected_outputs": {
            "reference_summary": str(SUITE_ROOT / ds_ref / f"{ds_ref}_summary.json"),
            "reference_null_summary": str(SUITE_ROOT / ds_ref / f"{ds_ref}_null{null_tag}_summary.json"),
            "comparison_summary": str(SUITE_ROOT / ds_cmp / f"{ds_cmp}_summary.json"),
            "comparison_null_summary": str(SUITE_ROOT / ds_cmp / f"{ds_cmp}_null{null_tag}_summary.json"),
        },
    }

    out_path = OUT_SUMMARIES / f"{cfg['output']['tag']}_run_manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote manifest: {out_path}")


if __name__ == "__main__":
    main()
