# scripts/compare_smica_nilc_n128.py
# Gepaarter Vergleich SMICA vs. NILC (Seeds 41–45): Δpp & Δθ, inkl. 95%-KI.

from pathlib import Path
import argparse, re, json
import numpy as np
import pandas as pd

def parse_args():
    p = argparse.ArgumentParser(description="Vergleiche SMICA vs. NILC (gepaarte Seeds) – Δpp & Δθ.")
    p.add_argument("--astro-dir", default=str(Path("reports")/"astro"),
                   help="Verzeichnis mit den Aggregations-CSV-Dateien.")
    p.add_argument("--smica-base", default="planck_smica_cmb__fov12_b60_n128",
                   help="Basistag SMICA (ohne .csv-Präfix).")
    p.add_argument("--nilc-base",  default="planck_nilc_cmb__fov12_b60_n128",
                   help="Basistag NILC (ohne .csv-Präfix).")
    p.add_argument("--suffix",     default="fov12_b60_n128_smica_vs_nilc",
                   help="Suffix für Ausgabedateien.")
    return p.parse_args()
"""
def seed_of(tag: str) -> int:
    m = re.search(r"_seed(\d+)$", tag)
    return 41 if m is None else int(m.group(1))
"""

def seed_of(tag: str) -> int:
    m = re.search(r"_seed(\d+)(?:_|$)", tag)  # findet auch ..._seed42_sm10am
    return 41 if m is None else int(m.group(1))

def ci95(x):
    arr = np.asarray(x, float)
    if arr.size == 0: return [None, None, None]
    return [float(np.percentile(arr, q)) for q in (2.5, 50.0, 97.5)]

def main():
    args = parse_args()
    astro = Path(args.astro_dir); astro.mkdir(parents=True, exist_ok=True)

    smica_csv = astro / f"T3_seeds_{args.smica_base}.csv"
    nilc_csv  = astro / f"T3_seeds_{args.nilc_base}.csv"
    if not smica_csv.exists(): raise FileNotFoundError(f"Fehlt: {smica_csv}")
    if not nilc_csv.exists():  raise FileNotFoundError(f"Fehlt: {nilc_csv}")

    sm = pd.read_csv(smica_csv); nl = pd.read_csv(nilc_csv)
    sm["seed"] = sm["tag"].map(seed_of); nl["seed"] = nl["tag"].map(seed_of)

    keep = ["seed","theta_e","theta_n","dtheta","plateau_e","plateau_n","dpp"]
    for need in keep:
        if need not in sm.columns: raise KeyError(f"Spalte '{need}' fehlt in {smica_csv}")
        if need not in nl.columns: raise KeyError(f"Spalte '{need}' fehlt in {nilc_csv}")

    sm_s = sm[keep].rename(columns={c:f"smica_{c}" for c in keep if c!="seed"})
    nl_s = nl[keep].rename(columns={c:f"nilc_{c}"  for c in keep if c!="seed"})

    df = pd.merge(sm_s, nl_s, on="seed", how="inner").sort_values("seed").reset_index(drop=True)
    if df.empty: raise RuntimeError("Leeres Merge-Ergebnis – Seeds prüfen.")

    df["dpp_diff_nilc_minus_smica"]   = df["nilc_dpp"]   - df["smica_dpp"]
    df["dtheta_diff_nilc_minus_smica"] = df["nilc_dtheta"] - df["smica_dtheta"]

    summary = {
        "seeds": df["seed"].tolist(),
        "rows": int(df.shape[0]),
        "smica": {"dpp_ci95": ci95(df["smica_dpp"]), "dtheta_ci95": ci95(df["smica_dtheta"])},
        "nilc":  {"dpp_ci95": ci95(df["nilc_dpp"]),  "dtheta_ci95": ci95(df["nilc_dtheta"])},
        "diffs": {
            "dpp_nilc_minus_smica_ci95":    ci95(df["dpp_diff_nilc_minus_smica"]),
            "dtheta_nilc_minus_smica_ci95": ci95(df["dtheta_diff_nilc_minus_smica"]),
        },
    }

    out_csv  = astro / f"T3_compare_smica_vs_nilc_{args.suffix}.csv"
    out_json = astro / f"T3_compare_smica_vs_nilc_{args.suffix}.json"
    df.to_csv(out_csv, index=False)
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("Wrote:", out_csv, "and", out_json)
    print("\nPer-Seed Δpp Vergleich (pp):")
    print(df[["seed","smica_dpp","nilc_dpp","dpp_diff_nilc_minus_smica"]].to_string(index=False))
    sm_lo,sm_md,sm_hi = summary["smica"]["dpp_ci95"]; nl_lo,nl_md,nl_hi = summary["nilc"]["dpp_ci95"]
    dd_lo,dd_md,dd_hi = summary["diffs"]["dpp_nilc_minus_smica_ci95"]
    print(f"\nSMICA Δpp: median={sm_md:.3f} CI95=[{sm_lo:.3f}, {sm_hi:.3f}]")
    print(f"NILC  Δpp: median={nl_md:.3f} CI95=[{nl_lo:.3f}, {nl_hi:.3f}]")
    print(f"Diff (N−S): median={dd_md:.3f} CI95=[{dd_lo:.3f}, {dd_hi:.3f}]")

if __name__ == "__main__":
    main()
