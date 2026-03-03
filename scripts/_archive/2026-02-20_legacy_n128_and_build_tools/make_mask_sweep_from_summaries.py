# scripts/make_mask_sweep_from_summaries.py
import json, re, os, csv
from pathlib import Path

TAGS = [
  "planck_smica_cmb__fov12_b65_n128_sm10am",
  "planck_smica_cmb__fov12_b70_n128_sm10am",
  "planck_smica_cmb__fov12_b75_n128_sm10am",
  "planck_nilc_cmb__fov12_b65_n128_sm10am",
  "planck_nilc_cmb__fov12_b70_n128_sm10am",
  "planck_nilc_cmb__fov12_b75_n128_sm10am",
]

SUITE = Path("data/processed/astro/suite")
OUT_DIR = Path("reports/astro"); OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV = OUT_DIR/"T3_mask_sweep_smica_vs_nilc_fov12_n128_sm10am.csv"
OUT_JSON = OUT_DIR/"T3_mask_sweep_smica_vs_nilc_fov12_n128_sm10am.json"

def load_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def mask_label_from_tag(tag:str)->str:
    m = re.search(r"_b(\d+)_", tag)
    b = m.group(1) if m else "?"
    return f"|b|≥{b}; FOV 12°"

def get_plateau(d):
    # kompatibel zu alten (plateau) und neuen (plateau_pct) Summaries
    return d.get("plateau_pct", d.get("plateau"))

rows = []
for tag in TAGS:
    base = SUITE / tag / tag
    base_str = str(base)

    js_e = load_json(base_str + "_summary.json")
    js_n = load_json(base_str + "_null_summary.json")

    theta_e = js_e.get("theta")
    theta_n = js_n.get("theta")
    plat_e  = get_plateau(js_e)
    plat_n  = get_plateau(js_n)

    rows.append({
        "dataset": tag,
        "family": "SMICA" if "smica" in tag else "NILC",
        "mask_label": mask_label_from_tag(tag),
        "theta_e": float(theta_e),
        "theta_n": float(theta_n),
        "dtheta": float(theta_e - theta_n),
        "plateau_e": float(plat_e) if plat_e is not None else None,
        "plateau_n": float(plat_n) if plat_n is not None else None,
        "dpp": (float(plat_n) - float(plat_e)) if (plat_e is not None and plat_n is not None) else None,
        "subset_size": js_e.get("subset_size"),
        "meta_sha12": js_e.get("meta_sha12"),
    })

# CSV
with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)

# JSON
with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump({"rows": rows}, f, ensure_ascii=False, indent=2)

print(f"[OK] CSV : {OUT_CSV}")
print(f"[OK] JSON: {OUT_JSON}")
