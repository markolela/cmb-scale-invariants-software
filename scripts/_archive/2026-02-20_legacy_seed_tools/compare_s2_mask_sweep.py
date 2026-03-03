# scripts/compare_s2_mask_sweep.py
import pandas as pd
from pathlib import Path

rep = Path("reports/astro")

csvs = {
    ("SMICA","65"): rep/"T3_seeds_planck_smica_cmb__fov12_b65_n128_sm10am_s2.csv",
    ("SMICA","70"): rep/"T3_seeds_planck_smica_cmb__fov12_b70_n128_sm10am_s2.csv",
    ("SMICA","75"): rep/"T3_seeds_planck_smica_cmb__fov12_b75_n128_sm10am_s2.csv",
    ("NILC","65"):  rep/"T3_seeds_planck_nilc_cmb__fov12_b65_n128_sm10am_s2.csv",
    ("NILC","70"):  rep/"T3_seeds_planck_nilc_cmb__fov12_b70_n128_sm10am_s2.csv",
    ("NILC","75"):  rep/"T3_seeds_planck_nilc_cmb__fov12_b75_n128_sm10am_s2.csv",
}

def medians_from_csv(p: Path):
    df = pd.read_csv(p)
    # robuste Spaltennamen
    te = df.get("theta_e", df.get("theta", None))
    tn = df.get("theta_n", None)
    dt = df.get("dtheta", None)
    if te is None or tn is None:
        raise ValueError(f"Spalten fehlen in {p}")
    te_m = float(te.median())
    tn_m = float(tn.median())
    dt_m = float(dt.median()) if dt is not None else te_m - tn_m
    return te_m, tn_m, dt_m

rows = []
for b in ("65","70","75"):
    te_s, tn_s, dt_s = medians_from_csv(csvs[("SMICA",b)])
    te_n, tn_n, dt_n = medians_from_csv(csvs[("NILC",b)])
    rows.append({
        "mask_label": f"|b|≥{b}; FOV 12°",
        "smica_theta_e_s2": te_s,
        "smica_theta_n_s2": tn_s,
        "smica_dtheta_s2": dt_s,
        "nilc_theta_e_s2": te_n,
        "nilc_theta_n_s2": tn_n,
        "nilc_dtheta_s2": dt_n,
        "Δdtheta_nilc_minus_smica": dt_n - dt_s
    })

out_csv = rep/"T3_s2_mask_sweep_compare_sm10am.csv"
out_json = rep/"T3_s2_mask_sweep_compare_sm10am.json"

df = pd.DataFrame(rows)
df.to_csv(out_csv, index=False)
df.to_json(out_json, orient="records", indent=2)

print(df.to_string(index=False))
print(f"\nWrote: {out_csv} and {out_json}")
