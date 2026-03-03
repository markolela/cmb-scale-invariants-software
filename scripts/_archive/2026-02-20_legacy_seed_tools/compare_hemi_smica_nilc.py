import pandas as pd
from pathlib import Path
import json

REPO = Path(__file__).resolve().parents[1]
RDIR = REPO / "reports" / "astro"

def load_csv(name):
    return pd.read_csv(RDIR / name)

# Dateien aus Schritt 1:
sm = load_csv("T3_seeds_planck_smica_cmb__fov12_b60_n128_sm10am_hemi.csv")
nl = load_csv("T3_seeds_planck_nilc_cmb__fov12_b60_n128_sm10am_hemi.csv")

# Hemi-Label aus Tag ableiten
def hemi_of(tag): return "N" if tag.endswith("_hemiN") else "S"

sm["hemi"] = sm["tag"].map(hemi_of)
nl["hemi"] = nl["tag"].map(hemi_of)

cols = ["hemi","theta_e","theta_n","dtheta","plateau_e","plateau_n","dpp"]
sm2 = sm[["hemi","dtheta","dpp"]].rename(columns={"dtheta":"smica_dtheta","dpp":"smica_dpp"})
nl2 = nl[["hemi","dtheta","dpp"]].rename(columns={"dtheta":"nilc_dtheta","dpp":"nilc_dpp"})

df = sm2.merge(nl2, on="hemi")
df["dpp_diff_nilc_minus_smica"] = df["nilc_dpp"] - df["smica_dpp"]
df["dtheta_diff_nilc_minus_smica"] = df["nilc_dtheta"] - df["smica_dtheta"]

out_csv = RDIR / "T3_compare_hemi_smica_vs_nilc_fov12_b60_n128_sm10am.csv"
df.to_csv(out_csv, index=False)

summary = {
  "rows": len(df),
  "hemi": dict(zip(df["hemi"], df["dpp_diff_nilc_minus_smica"])),
  "dpp_diff_median": float(df["dpp_diff_nilc_minus_smica"].median()),
  "dtheta_diff_median": float(df["dtheta_diff_nilc_minus_smica"].median())
}
(RDIR / "T3_compare_hemi_smica_vs_nilc_fov12_b60_n128_sm10am.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

print(df.to_string(index=False))
print("\nSaved:", out_csv)
