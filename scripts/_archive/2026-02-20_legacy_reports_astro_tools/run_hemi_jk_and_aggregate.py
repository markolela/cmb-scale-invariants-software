# scripts/run_hemi_jk_and_aggregate.py
"""
Batch Runner: Hemisphären Jackknife plus Aggregation N und S

Ablauf pro Skala
1. scripts/jackknife_hemi_t3.py erzeugt und evaluiert hemiN und hemiS
2. scripts/aggregate_tags_any.py bündelt hemiN und hemiS zu <base>_hemi_s<skala>

Beispiel
python3 scripts/run_hemi_jk_and_aggregate.py
python3 scripts/run_hemi_jk_and_aggregate.py --datasets planck2018_SMICA_T_fov12_b65_n256_sm10am,planck2018_NILC_T_fov12_b65_n256_sm10am --scales 1 2 4
"""

from __future__ import annotations

import argparse
import sys
import subprocess as sp
from pathlib import Path
from time import perf_counter


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
JK_SCRIPT = SCRIPTS / "jackknife_hemi_t3.py"
AGG_SCRIPT = SCRIPTS / "aggregate_tags_any.py"
PATCHES_ROOT = REPO / "data" / "processed" / "astro" / "patches"

DEFAULT_BASE_TAGS = [
    "planck2018_SMICA_T_fov12_b65_n256_sm10am",
    "planck2018_NILC_T_fov12_b65_n256_sm10am",
]


def run(cmd: list[str]) -> None:
    print("\n[RUN]", " ".join(cmd))
    sp.run(cmd, check=True)


def must_exist(path: Path, what: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Fehlt: {what} -> {path}")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--datasets",
        type=str,
        default="",
        help="Kommagetrennt: <tag1>,<tag2>,... Leer bedeutet Default.",
    )
    ap.add_argument(
        "--scales",
        nargs="+",
        type=int,
        default=[1, 2, 4],
        help="Liste von Skalen. Beispiel: --scales 1 2 4",
    )
    ap.add_argument("--trend", type=str, default="log")
    ap.add_argument("--null-n", type=int, default=40)
    ap.add_argument("--null-seed", type=int, default=20251)
    ap.add_argument("--skip-agg", action="store_true", help="Nur Jackknife, keine Aggregation.")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    t0 = perf_counter()

    must_exist(JK_SCRIPT, "jackknife_hemi_t3.py")
    must_exist(AGG_SCRIPT, "aggregate_tags_any.py")
    must_exist(PATCHES_ROOT, "patches root")

    if args.datasets.strip():
        base_tags = [t.strip() for t in args.datasets.split(",") if t.strip()]
    else:
        base_tags = list(DEFAULT_BASE_TAGS)

    # Nur vorhandene Patch Ordner zulassen
    ok: list[str] = []
    missing: list[str] = []
    for t in base_tags:
        if (PATCHES_ROOT / t).exists():
            ok.append(t)
        else:
            missing.append(t)

    if missing:
        print("[WARN] Fehlende Patch Ordner. Diese Tags werden uebersprungen.")
        for t in missing:
            print("  ", t)

    if not ok:
        raise SystemExit("Keine gueltigen Datasets gefunden. Abbruch.")

    datasets_arg = ",".join(ok)

    for s in args.scales:
        # Jackknife fuer genau eine Skala
        run([
            sys.executable, str(JK_SCRIPT),
            "--datasets", datasets_arg,
            "--trend", str(args.trend),
            "--scales", str(s),
            "--null-n", str(args.null_n),
            "--null-seed", str(args.null_seed),
        ])

        if args.skip_agg:
            continue

        # Aggregation hemiN und hemiS fuer genau diese Skala
        for b in ok:
            tags = f"{b}_hemiN,{b}_hemiS"
            out_name = f"{b}_hemi_s{s}"
            run([
                sys.executable, str(AGG_SCRIPT),
                "--tags", tags,
                "--out-name", out_name,
            ])

    dt = perf_counter() - t0
    print(f"\n[OK] Fertig. Gesamtlaufzeit: {dt:.1f} s")


if __name__ == "__main__":
    main()
