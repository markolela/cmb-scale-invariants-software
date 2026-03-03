# scripts/compare_smica_wmap_n128.py
# Zweck:
#  - Gepaarter Vergleich SMICA vs. WMAP auf denselben Seeds (41–45 standardmäßig)
#  - Kennzahlen je Instrument: Δpp- und Δθ-Verteilung (Median + 95%-KI)
#  - Per-Seed-Tabelle: (Seed, Δpp_SMICA, Δpp_WMAP, Differenz)
#
# Eingaben (aus dem Aggregationsskript erzeugt):
#   reports/astro/T3_seeds_<smica_base>.csv
#   reports/astro/T3_seeds_<wmap_base>.csv
#
# Ausgaben:
#   reports/astro/T3_compare_smica_vs_wmap_<suffix>.csv
#   reports/astro/T3_compare_smica_vs_wmap_<suffix>.json
#
# Aufruf (Repo-Root):
#   python scripts\compare_smica_wmap_n128.py
#   # optional mit eigenen Tags/Suffix:
#   python scripts\compare_smica_wmap_n128.py --smica-base planck_smica_cmb__fov12_b60_n128 --wmap-base wmap_ilc9__fov12_b60_n128 --suffix fov12_b60_n128

from pathlib import Path
import argparse, re, json
import numpy as np
import pandas as pd


def parse_args():
    p = argparse.ArgumentParser(description="Vergleiche SMICA vs. WMAP (gepaarte Seeds) – Δpp & Δθ.")
    p.add_argument("--astro-dir", default=str(Path("reports") / "astro"),
                   help="Verzeichnis mit den Aggregations-CSV-Dateien.")
    p.add_argument("--smica-base", default="planck_smica_cmb__fov12_b60_n128",
                   help="Basistag für SMICA (ohne .csv-Präfix).")
    p.add_argument("--wmap-base", default="wmap_ilc9__fov12_b60_n128",
                   help="Basistag für WMAP (ohne .csv-Präfix).")
    p.add_argument("--suffix", default="fov12_b60_n128",
                   help="Suffix für die Ausgabedateien.")
    return p.parse_args()


def seed_of(tag: str) -> int:
    # Konvention: kein _seedNN -> Seed 41
    m = re.search(r"_seed(\d+)$", tag)
    return 41 if m is None else int(m.group(1))


def ci95(x):
    arr = np.asarray(x, float)
    if arr.size == 0:
        return [None, None, None]
    return [float(np.percentile(arr, q)) for q in (2.5, 50.0, 97.5)]


def main():
    args = parse_args()
    astro = Path(args.astro_dir)
    astro.mkdir(parents=True, exist_ok=True)

    smica_csv = astro / f"T3_seeds_{args.smica_base}.csv"
    wmap_csv  = astro / f"T3_seeds_{args.wmap_base}.csv"

    if not smica_csv.exists():
        raise FileNotFoundError(f"Fehlt: {smica_csv} – bitte erst Aggregation für SMICA laufen lassen.")
    if not wmap_csv.exists():
        raise FileNotFoundError(f"Fehlt: {wmap_csv} – bitte erst Aggregation für WMAP laufen lassen.")

    sm = pd.read_csv(smica_csv)
    wm = pd.read_csv(wmap_csv)

    # Seeds extrahieren
    sm["seed"] = sm["tag"].map(seed_of)
    wm["seed"] = wm["tag"].map(seed_of)

    # Relevante Spalten
    keep = ["seed", "theta_e", "theta_n", "dtheta", "plateau_e", "plateau_n", "dpp"]
    # (Robustheit: falls Spaltennamen minimal abweichen)
    for need in keep:
        if need not in sm.columns:
            raise KeyError(f"Spalte '{need}' fehlt in {smica_csv}")
        if need not in wm.columns:
            raise KeyError(f"Spalte '{need}' fehlt in {wmap_csv}")

    sm_s = sm[keep].rename(columns={c: f"smica_{c}" for c in keep if c != "seed"})
    wm_s = wm[keep].rename(columns={c: f"wmap_{c}"  for c in keep if c != "seed"})

    # Merge nach Seed (gepaarter Vergleich)
    df = pd.merge(sm_s, wm_s, on="seed", how="inner").sort_values("seed").reset_index(drop=True)
    if df.empty:
        raise RuntimeError("Leeres Merge-Ergebnis. Prüfe, ob beide CSVs dieselben Seeds enthalten.")

    # Differenzen
    df["dpp_diff_wmap_minus_smica"]   = df["wmap_dpp"]   - df["smica_dpp"]
    df["dtheta_diff_wmap_minus_smica"] = df["wmap_dtheta"] - df["smica_dtheta"]

    # Zusammenfassungen
    summary = {
        "seeds": df["seed"].tolist(),
        "rows": int(df.shape[0]),
        "smica": {
            "dpp_ci95":    ci95(df["smica_dpp"]),
            "dtheta_ci95": ci95(df["smica_dtheta"]),
        },
        "wmap": {
            "dpp_ci95":    ci95(df["wmap_dpp"]),
            "dtheta_ci95": ci95(df["wmap_dtheta"]),
        },
        "diffs": {
            "dpp_wmap_minus_smica_ci95":    ci95(df["dpp_diff_wmap_minus_smica"]),
            "dtheta_wmap_minus_smica_ci95": ci95(df["dtheta_diff_wmap_minus_smica"]),
        }
    }

    # Ausgaben
    out_csv  = astro / f"T3_compare_smica_vs_wmap_{args.suffix}.csv"
    out_json = astro / f"T3_compare_smica_vs_wmap_{args.suffix}.json"
    df.to_csv(out_csv, index=False)
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Konsolenreport
    print("Wrote:", out_csv, "and", out_json)
    print("\nPer-Seed Δpp Vergleich (Werte in Prozentpunkten):")
    print(df[["seed","smica_dpp","wmap_dpp","dpp_diff_wmap_minus_smica"]].to_string(index=False))
    print("\nZusammenfassung (Median [95%-KI]):")
    sm_dpp_lo, sm_dpp_med, sm_dpp_hi = summary["smica"]["dpp_ci95"]
    wm_dpp_lo, wm_dpp_med, wm_dpp_hi = summary["wmap"]["dpp_ci95"]
    sm_dt_lo,  sm_dt_med,  sm_dt_hi  = summary["smica"]["dtheta_ci95"]
    wm_dt_lo,  wm_dt_med,  wm_dt_hi  = summary["wmap"]["dtheta_ci95"]
    ddpp_lo, ddpp_med, ddpp_hi       = summary["diffs"]["dpp_wmap_minus_smica_ci95"]

    print(f"  SMICA Δpp:   median={sm_dpp_med:.3f}  CI95=[{sm_dpp_lo:.3f}, {sm_dpp_hi:.3f}]")
    print(f"  WMAP  Δpp:   median={wm_dpp_med:.3f}  CI95=[{wm_dpp_lo:.3f}, {wm_dpp_hi:.3f}]")
    print(f"  Diff Δpp(W−S): median={ddpp_med:.3f}  CI95=[{ddpp_lo:.3f}, {ddpp_hi:.3f}]")
    print(f"  SMICA Δθ:    median={sm_dt_med:.3f}  CI95=[{sm_dt_lo:.3f}, {sm_dt_hi:.3f}]")
    print(f"  WMAP  Δθ:    median={wm_dt_med:.3f}  CI95=[{wm_dt_lo:.3f}, {wm_dt_hi:.3f}]")


if __name__ == "__main__":
    main()
