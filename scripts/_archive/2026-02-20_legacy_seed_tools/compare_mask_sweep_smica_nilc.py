# scripts/compare_mask_sweep_smica_nilc.py
# Vergleicht SMICA vs. NILC über Masken |b|>=65/70/75 (oder benutzerdefiniert)
# Liest die *_summary.json aus reports/astro/, fasst Mediane zusammen und schreibt CSV/JSON.

import argparse, json, sys
from pathlib import Path
import csv

DEF_MASKS = [65, 70, 75]

def load_json(p: Path):
    if not p.exists():
        raise FileNotFoundError(f"Fehlt: {p}")
    return json.loads(p.read_text(encoding="utf-8"))

def extract_median(summary_json: dict, key: str):
    """
    Robust: versucht verschiedene Layouts, z.B.:
      - data["summary"][key]["median"]
      - data[key]["median"]
      - data[f"{key}_median"]
    """
    cand = []
    if isinstance(summary_json, dict):
        if "summary" in summary_json and isinstance(summary_json["summary"], dict):
            s = summary_json["summary"]
            if key in s and isinstance(s[key], dict) and "median" in s[key]:
                cand.append(s[key]["median"])
        if key in summary_json and isinstance(summary_json[key], dict) and "median" in summary_json[key]:
            cand.append(summary_json[key]["median"])
        mkey = f"{key}_median"
        if mkey in summary_json:
            cand.append(summary_json[mkey])
    if cand:
        return cand[0]
    raise KeyError(f"Mediandaten nicht gefunden für Schlüssel '{key}'.")

def tag_from_parts(kind: str, fov: str, mask: int, nstr: str, suffix: str):
    # kind: "smica" oder "nilc"
    base = f"planck_{kind}_cmb__{fov}_b{mask}_{nstr}"
    return f"{base}_{suffix}" if suffix else base

def read_one_tag(reports_dir: Path, tag: str):
    p = reports_dir / f"T3_seeds_{tag}_summary.json"
    js = load_json(p)
    out = {}
    for key in ("theta_e","theta_n","dtheta","plateau_e","plateau_n","dpp"):
        try:
            out[key] = float(extract_median(js, key))
        except Exception as e:
            raise RuntimeError(f"Fehler beim Lesen von '{key}' aus {p}: {e}") from e
    return out

def main():
    ap = argparse.ArgumentParser(description="Vergleich SMICA vs. NILC über Masken (|b|>=X) mit T3-Medianen.")
    ap.add_argument("--masks", default="65,70,75", help="Liste der Maskenschwellen, z.B. '65,70,75'")
    ap.add_argument("--fov", default="fov12", help="FOV-Teil im Tag, z.B. 'fov12'")
    ap.add_argument("--n", dest="nstr", default="n128", help="Patchanzahl im Tag, z.B. 'n128'")
    ap.add_argument("--suffix", default="sm10am", help="Suffix im Tag (z.B. 'sm10am'); leer lassen mit '' falls keiner")
    ap.add_argument("--reports-dir", default="reports/astro", help="Verzeichnis mit *_summary.json")
    ap.add_argument("--out-name", default=None, help="Basisname für Output-Dateien (ohne Endung)")
    args = ap.parse_args()

    masks = [int(x) for x in args.masks.split(",") if x.strip()]
    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Default Outputnamen
    if args.out_name:
        base_out = args.out_name
    else:
        base_out = f"T3_mask_sweep_smica_vs_nilc_{args.fov}_{args.nstr}_{args.suffix or 'nosuf'}"

    rows = []
    for m in masks:
        sm_tag  = tag_from_parts("smica", args.fov, m, args.nstr, args.suffix)
        nl_tag  = tag_from_parts("nilc",  args.fov, m, args.nstr, args.suffix)
        sm = read_one_tag(reports_dir, sm_tag)
        nl = read_one_tag(reports_dir, nl_tag)

        rows.append({
            "mask_abs_b": m,
            # SMICA
            "smica_theta": sm["theta_e"],
            "smica_plateau": sm["plateau_e"],
            "smica_dpp": sm["dpp"],
            # NILC
            "nilc_theta": nl["theta_e"],
            "nilc_plateau": nl["plateau_e"],
            "nilc_dpp": nl["dpp"],
            # Gaps
            "gap_dpp_nilc_minus_smica": nl["dpp"] - sm["dpp"],
            "gap_plateau_smica_minus_nilc": sm["plateau_e"] - nl["plateau_e"],
            "gap_theta_nilc_minus_smica": nl["theta_e"] - sm["theta_e"],
        })

    # CSV
    csv_path = reports_dir / f"{base_out}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # JSON
    json_path = reports_dir / f"{base_out}.json"
    json_path.write_text(json.dumps({"rows": rows}, indent=2), encoding="utf-8")

    # Console-Ausgabe (kurz)
    print(f"Wrote: {csv_path} and {json_path}\n")
    print("Mask  smica_dpp  nilc_dpp  gap_dpp(N−S)  smica_plateau  nilc_plateau  gap_plateau(S−N)  smica_theta  nilc_theta  gap_theta(N−S)")
    for r in rows:
        print(f"{r['mask_abs_b']:>4}  {r['smica_dpp']:.3f}     {r['nilc_dpp']:.3f}     {r['gap_dpp_nilc_minus_smica']:.3f}         "
              f"{r['smica_plateau']:.3f}         {r['nilc_plateau']:.3f}         {r['gap_plateau_smica_minus_nilc']:.3f}         "
              f"{r['smica_theta']:.3f}        {r['nilc_theta']:.3f}        {r['gap_theta_nilc_minus_smica']:.3f}")
if __name__ == "__main__":
    main()
