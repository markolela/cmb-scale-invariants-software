"""
Fill [R7:...] placeholders in paper/latex/sections/07_results.tex
from data/processed/astro/suite/<dataset_id>/<dataset_id>_null_summary.json.

Source of truth: *_null_summary.json only.
No YAML. No manifest. No pandas/numpy.
Creates a timestamped backup next to the TeX file.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SUITE = REPO / "data" / "processed" / "astro" / "suite"

R7_PATTERN = re.compile(r"\[R7:([A-Z0-9_\\]+)\]")

DATASETS = {
    # Headline maps (B65)
    "SMICA": "planck2018_SMICA_T_fov12_b65_n256_sm10am",
    "NILC":  "planck2018_NILC_T_fov12_b65_n256_sm10am",

    # Mask sweep (SMICA)
    "B65": "planck2018_SMICA_T_fov12_b65_n256_sm10am",
    "B70": "planck2018_SMICA_T_fov12_b70_n256_sm10am",
    "B75": "planck2018_SMICA_T_fov12_b75_n256_sm10am",

    # Half-mission (SMICA, b75)
    "HM1": "planck2018_SMICA_HM1_T_fov12_b75_n256_sm10am",
    "HM2": "planck2018_SMICA_HM2_T_fov12_b75_n256_sm10am",

    # Hemispheres (SMICA, b65)
    "NORTH": "planck2018_SMICA_T_fov12_b65_n256_sm10am_hemiN",
    "SOUTH": "planck2018_SMICA_T_fov12_b65_n256_sm10am_hemiS",
}


def _load_null_summary(dataset_id: str) -> dict:
    p = SUITE / dataset_id / f"{dataset_id}_null_summary.json"
    if not p.exists():
        raise SystemExit(f"Fehlt: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def _fmt_theta(x: float) -> str:
    return f"{float(x):.6f}"


def _fmt_pp(x: float) -> str:
    # dpp_* in deinen Null-Summaries ist bereits in Prozentpunkten
    return f"{float(x):.2f}"


def _fmt_ci(ci, kind: str) -> str:
    a = float(ci[0])
    b = float(ci[1])
    if kind == "theta":
        return f"[{a:.6f}, {b:.6f}]"
    if kind == "pp":
        return f"[{a:.2f}, {b:.2f}]"
    raise ValueError(kind)


def _build_mapping() -> dict[str, str]:
    m: dict[str, str] = {}

    for slot, ds in DATASETS.items():
        d = _load_null_summary(ds)

        need = ["dtheta_med", "dtheta_ci95", "dpp_med", "dpp_ci95"]
        miss = [k for k in need if k not in d]
        if miss:
            raise SystemExit(f"Null summary missing keys {miss} in dataset {ds}")

        m[f"DTHETA_MED_{slot}"] = _fmt_theta(d["dtheta_med"])
        m[f"DTHETA_CI95_{slot}"] = _fmt_ci(d["dtheta_ci95"], "theta")
        m[f"DPP_MED_{slot}"] = _fmt_pp(d["dpp_med"])
        m[f"DPP_CI95_{slot}"] = _fmt_ci(d["dpp_ci95"], "pp")

    return m


def _replace_r7(tex: str, mapping: dict[str, str]) -> tuple[str, dict[str, int]]:
    missing: dict[str, int] = {}

    def repl(match: re.Match) -> str:
        key_raw = match.group(1)
        key = key_raw.replace("\\_", "_")
        if key in mapping:
            return mapping[key]
        missing[key] = missing.get(key, 0) + 1
        return match.group(0)

    return R7_PATTERN.sub(repl, tex), missing


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tex", default="paper/latex/sections/07_results.tex")
    args = ap.parse_args()

    tex_path = Path(args.tex)
    if not tex_path.is_absolute():
        tex_path = (REPO / tex_path).resolve()
    if not tex_path.exists():
        raise SystemExit(f"TeX file not found: {tex_path}")

    mapping = _build_mapping()

    original = tex_path.read_text(encoding="utf-8")
    updated, missing = _replace_r7(original, mapping)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = tex_path.with_suffix(tex_path.suffix + f".bak_{stamp}")
    backup.write_text(original, encoding="utf-8")
    tex_path.write_text(updated, encoding="utf-8")

    print(f"Updated: {tex_path}")
    print(f"Backup:  {backup}")

    if missing:
        keys = sorted(missing.items(), key=lambda kv: (-kv[1], kv[0]))
        print("Unfilled [R7:...] placeholders that still remain:")
        for k, n in keys:
            print(f"  {k}  occurrences={n}")

    left = re.findall(r"\[R7:[A-Z0-9_\\]+\]", updated)
    if left:
        print("Noch vorhandene R7 Platzhalter (raw tokens):")
        for p in sorted(set(left)):
            print(" ", p)


if __name__ == "__main__":
    main()
