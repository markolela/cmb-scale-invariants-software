"""
Fill [R7:...] placeholders in paper/latex/sections/07_results.tex.

Source of truth:
- data/processed/astro/suite/<dataset_id>/<dataset_id>_null_summary.json

This script fills exactly the placeholders that are currently used in 07_results.tex:
SMICA, NILC, HM1, HM2, NORTH, SOUTH, B65, B70, B75.

It writes a timestamped backup of the TeX file before modifying it.
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


def _read_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _load_null_summary(dataset_id: str) -> dict:
    p = SUITE / dataset_id / f"{dataset_id}_null_summary.json"
    if not p.exists():
        raise SystemExit(f"Fehlt: {p}")
    return _read_json(p)


def _fmt_theta(x: float) -> str:
    return f"{float(x):.6f}"


def _fmt_pp(x: float) -> str:
    return f"{float(x):.2f}"


def _fmt_ci_theta(ci: list[float]) -> str:
    a, b = float(ci[0]), float(ci[1])
    return f"[{a:.6f}, {b:.6f}]"


def _fmt_ci_pp(ci: list[float]) -> str:
    a, b = float(ci[0]), float(ci[1])
    return f"[{a:.2f}, {b:.2f}]"


def _add_block(repl: dict[str, str], *, tag: str, dataset_id: str) -> None:
    sd = _load_null_summary(dataset_id)

    need = ["dtheta_med", "dtheta_ci95", "dpp_med", "dpp_ci95"]
    for k in need:
        if k not in sd:
            raise SystemExit(f"Missing key {k} in null summary for {dataset_id}")

    repl[f"DTHETA_MED_{tag}"] = _fmt_theta(sd["dtheta_med"])
    repl[f"DTHETA_CI95_{tag}"] = _fmt_ci_theta(sd["dtheta_ci95"])
    repl[f"DPP_MED_{tag}"] = _fmt_pp(sd["dpp_med"])
    repl[f"DPP_CI95_{tag}"] = _fmt_ci_pp(sd["dpp_ci95"])


def _replace(tex: str, repl: dict[str, str]) -> tuple[str, dict[str, int]]:
    missing: dict[str, int] = {}

    def _one(m: re.Match) -> str:
        key_raw = m.group(1)
        key = key_raw.replace("\\_", "_")
        if key in repl:
            return repl[key]
        missing[key] = missing.get(key, 0) + 1
        return m.group(0)

    out = R7_PATTERN.sub(_one, tex)
    return out, missing


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tex", default="paper/latex/sections/07_results.tex")
    args = ap.parse_args()

    tex_path = Path(args.tex)
    if not tex_path.is_absolute():
        tex_path = (REPO / tex_path).resolve()
    if not tex_path.exists():
        raise SystemExit(f"TeX file not found: {tex_path}")

    repl: dict[str, str] = {}

    # Headline maps
    _add_block(repl, tag="SMICA", dataset_id="planck2018_SMICA_T_fov12_b65_n256_sm10am")
    _add_block(repl, tag="NILC", dataset_id="planck2018_NILC_T_fov12_b65_n256_sm10am")

    # HM split
    _add_block(repl, tag="HM1", dataset_id="planck2018_SMICA_HM1_T_fov12_b75_n256_sm10am")
    _add_block(repl, tag="HM2", dataset_id="planck2018_SMICA_HM2_T_fov12_b75_n256_sm10am")

    # Hemispheres
    _add_block(repl, tag="NORTH", dataset_id="planck2018_SMICA_T_fov12_b65_n256_sm10am_hemiN")
    _add_block(repl, tag="SOUTH", dataset_id="planck2018_SMICA_T_fov12_b65_n256_sm10am_hemiS")

    # Mask sweep
    _add_block(repl, tag="B65", dataset_id="planck2018_SMICA_T_fov12_b65_n256_sm10am")
    _add_block(repl, tag="B70", dataset_id="planck2018_SMICA_T_fov12_b70_n256_sm10am")
    _add_block(repl, tag="B75", dataset_id="planck2018_SMICA_T_fov12_b75_n256_sm10am")

    src = tex_path.read_text(encoding="utf-8")
    dst, missing = _replace(src, repl)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = tex_path.with_suffix(tex_path.suffix + f".bak_{stamp}")
    bak.write_text(src, encoding="utf-8")
    tex_path.write_text(dst, encoding="utf-8")

    print(f"Updated: {tex_path}")
    print(f"Backup:  {bak}")

    if missing:
        print("Nicht befüllte R7 Keys im TeX:")
        for k, n in sorted(missing.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"  {k}  occurrences={n}")

    left = re.findall(r"\[R7:[A-Z0-9_\\]+\]", dst)
    if left:
        print("Noch vorhandene R7 Platzhalter:")
        for p in sorted(set(left)):
            print(" ", p)


if __name__ == "__main__":
    main()
