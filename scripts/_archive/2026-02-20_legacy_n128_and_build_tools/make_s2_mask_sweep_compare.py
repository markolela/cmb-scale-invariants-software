# scripts/make_s2_mask_sweep_compare.py
# s=2 Mask-Sweep Vergleich (SMICA vs. NILC) – findet *_s2_summary.json
# entweder in reports/astro/T3_seeds_<tag>_s2_summary.json (bevorzugt)
# oder in data/processed/astro/suite/<tag>/<tag>_s2_summary.json (Fallback).

from __future__ import annotations
import json, re
from pathlib import Path
from datetime import datetime
import pandas as pd

SMICA_TAGS = [
    "planck_smica_cmb__fov12_b65_n128_sm10am",
    "planck_smica_cmb__fov12_b70_n128_sm10am",
    "planck_smica_cmb__fov12_b75_n128_sm10am",
]
NILC_TAGS = [
    "planck_nilc_cmb__fov12_b65_n128_sm10am",
    "planck_nilc_cmb__fov12_b70_n128_sm10am",
    "planck_nilc_cmb__fov12_b75_n128_sm10am",
]

SUITE_DIR   = Path("data/processed/astro/suite")
REPORTS_DIR = Path("reports/astro")
OUT_DIR     = Path("reports/astro")
OUT_CSV     = OUT_DIR / "T3_s2_mask_sweep_compare_sm10am.csv"
OUT_JSON    = OUT_DIR / "T3_s2_mask_sweep_compare_sm10am.json"
OUT_WIDE    = OUT_DIR / "T3_s2_mask_sweep_compare_sm10am_wide.csv"

def mask_label_from_tag(tag: str) -> str:
    m = re.search(r"_b(\d+)_", tag); b = m.group(1) if m else "?"
    return f"|b|≥{b}; FOV 12°"

def method_from_tag(tag: str) -> str:
    return "SMICA" if tag.startswith("planck_smica") else "NILC"

def find_summary_path(tag: str) -> Path | None:
    # 1) bevorzugt: Reports-Aggregat (mit Seeds): T3_seeds_<tag>_s2_summary.json
    p1 = REPORTS_DIR / f"T3_seeds_{tag}_s2_summary.json"
    if p1.exists(): 
        print(f"[USE] {tag} -> {p1}")
        return p1
    # 2) Fallback: Suite-Einzeldatei: <tag>_s2_summary.json
    p2 = SUITE_DIR / tag / f"{tag}_s2_summary.json"
    if p2.exists():
        print(f"[USE] {tag} -> {p2}")
        return p2
    # 3) nichts gefunden
    print(f"[WARN] Keine s2-Summary gefunden für {tag}")
    return None

def load_s2_summary(tag: str) -> dict | None:
    p = find_summary_path(tag)
    if p is None: 
        return None
    try:
        j = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[WARN] Defekt: {p} ({e})")
        return None

    # Aggregat-Struktur: { "theta_e": {"median":..,"n":..}, "theta_n":.., "dtheta": {"median":..,"ci95":[lo,hi]} }
    def get(d, path, default=None):
        cur = d
        for k in path:
            if not isinstance(cur, dict) or k not in cur: return default
            cur = cur[k]
        return cur

    theta_e_med = get(j, ["theta_e","median"])
    theta_n_med = get(j, ["theta_n","median"])
    dtheta_med  = get(j, ["dtheta","median"])
    ci95        = get(j, ["dtheta","ci95"], [None, None]) or [None, None]
    if not isinstance(ci95, (list,tuple)) or len(ci95)<2: ci95=[None,None]
    n           = get(j, ["theta_e","n"], get(j, ["n"]))

    return dict(theta_e_med=theta_e_med, theta_n_med=theta_n_med,
                dtheta_med=dtheta_med, dtheta_ci95_lo=ci95[0], dtheta_ci95_hi=ci95[1], n=n)

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    for tag in SMICA_TAGS + NILC_TAGS:
        rec = load_s2_summary(tag)
        if rec is None: 
            continue
        rows.append({
            "method"        : method_from_tag(tag),
            "mask_label"    : mask_label_from_tag(tag),
            "dataset"       : tag,
            "n"             : rec["n"],
            "theta_e_med"   : rec["theta_e_med"],
            "theta_n_med"   : rec["theta_n_med"],
            "dtheta_med"    : rec["dtheta_med"],
            "dtheta_ci95_lo": rec["dtheta_ci95_lo"],
            "dtheta_ci95_hi": rec["dtheta_ci95_hi"],
        })

    if not rows:
        raise SystemExit("[ERROR] Keine s=2-Summaries gefunden. Prüfe, ob T3_seeds_<tag>_s2_summary.json in reports/astro liegt oder <tag>_s2_summary.json in suite/… vorhanden ist.")

    df = pd.DataFrame(rows).sort_values(["mask_label","method"]).reset_index(drop=True)
    df.to_csv(OUT_CSV, index=False)

    # Zusatz: Wide + Δ
    try:
        wide = df.pivot(index="mask_label", columns="method", values="dtheta_med").reset_index()
        if "NILC" in wide and "SMICA" in wide:
            wide["Δdθ(NILC−SMICA)"] = wide.get("NILC") - wide.get("SMICA")
        wide.to_csv(OUT_WIDE, index=False)
        print(f"[OK] CSV (wide): {OUT_WIDE}")
    except Exception as e:
        print(f"[WARN] Wide-Ansicht nicht erzeugt: {e}")

    payload = {
        "created_at": datetime.utcnow().isoformat(timespec="seconds")+"Z",
        "inputs": {"smica_tags": SMICA_TAGS, "nilc_tags": NILC_TAGS},
        "rows": df.to_dict(orient="records"),
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[OK] CSV : {OUT_CSV}")
    print(f"[OK] JSON: {OUT_JSON}")

    # Kurz-Output
    print("\nKurzüberblick dθ @ s=2 (Median) [95%-KI]:")
    for mlabel in df["mask_label"].unique():
        sub = df[df["mask_label"]==mlabel]
        parts = []
        for _,r in sub.sort_values("method").iterrows():
            parts.append(f"{r['method']}={r['dtheta_med']:.3f}[{r['dtheta_ci95_lo']:.3f},{r['dtheta_ci95_hi']:.3f}]")
        print(f"  {mlabel}: " + "  |  ".join(parts))

if __name__ == "__main__":
    main()
