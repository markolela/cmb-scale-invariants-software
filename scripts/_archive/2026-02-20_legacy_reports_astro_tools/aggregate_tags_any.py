# scripts/aggregate_tags_any.py
# Aggregiert beliebige Tags (kommagetrennt) zu θ/Plateau/Δθ/Δpp und speichert CSV/JSON.
import json
from pathlib import Path
import argparse, numpy as np, pandas as pd

REPO = Path(__file__).resolve().parents[1]
SUITE = REPO / "data" / "processed" / "astro" / "suite"
OUT   = REPO / "reports" / "astro"

def load_sum(tag):
    d = SUITE / tag
    s = d / f"{tag}_summary.json"
    n = d / f"{tag}_null_summary.json"
    if not s.exists() or not n.exists():
        return None

    S = json.loads(s.read_text("utf-8"))
    N = json.loads(n.read_text("utf-8"))

    def _pp_frac(obj: dict) -> float:
        # Neu: "pp" ist Anteil (0.097 = 9.7%)
        if "pp" in obj:
            return float(obj["pp"])
        # Alt: "plateau_pct" evtl. Prozent (9.7) oder Anteil (0.097)
        if "plateau_pct" in obj:
            v = float(obj["plateau_pct"])
            return v / 100.0 if v > 1.0 else v
        raise KeyError(f"[{tag}] Kein pp/plateau_pct gefunden. Keys={list(obj.keys())}")

    def _theta_null(obj: dict) -> float:
        # Neu: Null-Referenz (Median über Reps)
        for k in ("theta_null_ref_median_over_reps", "theta_null_ref"):
            if k in obj:
                return float(obj[k])
        # Alt: Null hatte "theta" direkt
        if "theta" in obj:
            return float(obj["theta"])
        # Fallback aus dtheta_med (neu): dtheta_med = theta_null - theta_data
        if "dtheta_med" in obj and "theta_data" in obj:
            return float(obj["theta_data"]) + float(obj["dtheta_med"])
        raise KeyError(f"[{tag}] Keine theta-Null gefunden. Keys={list(obj.keys())}")

    def _pp_null_frac(obj: dict) -> float:
        for k in ("pp_null_ref_median_over_reps", "pp_null_ref"):
            if k in obj:
                return float(obj[k])
        # Alt
        if "plateau_pct" in obj:
            v = float(obj["plateau_pct"])
            return v / 100.0 if v > 1.0 else v
        # Fallback aus dpp_med (neu): dpp_med in Prozentpunkten
        if "dpp_med" in obj and "pp_data" in obj:
            return float(obj["pp_data"]) - float(obj["dpp_med"]) / 100.0
        raise KeyError(f"[{tag}] Keine pp-Null gefunden. Keys={list(obj.keys())}")

    try:
        theta_e = float(S["theta"])
        theta_n = _theta_null(N)

        pp_e_frac = _pp_frac(S)
        pp_n_frac = _pp_null_frac(N)

        plateau_e = 100.0 * pp_e_frac          # Prozent
        plateau_n = 100.0 * pp_n_frac          # Prozent
        dpp = plateau_e - plateau_n            # Prozentpunkte

        dtheta = theta_e - theta_n             # Daten minus Null (wie bei Δpp)

        return dict(
            tag=tag,
            theta_e=theta_e,
            theta_n=theta_n,
            dtheta=dtheta,
            plateau_e=plateau_e,
            plateau_n=plateau_n,
            dpp=dpp,
        )
    except Exception as e:
        print(f"[ERROR] Tag {tag}: {e}")
        return None

def ci95(vals):
    a=np.asarray(vals, float)
    if a.size==0: return dict(median=None, ci95=[None,None], n=0)
    return dict(median=float(np.median(a)),
                ci95=[float(np.percentile(a,2.5)), float(np.percentile(a,97.5))],
                n=int(a.size))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--tags", required=True, help="Kommagetrennt: <tag1>,<tag2>,...")
    ap.add_argument("--out-name", required=True, help="Basisname für Output-Dateien (ohne Pfad)")
    args=ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    tags=[t.strip() for t in args.tags.split(",") if t.strip()]
    rows=[]
    for t in tags:
        r=load_sum(t)
        if r is None:
            print(f"[WARN] Fehlt Summary/Null für: {t} -> überspringe")
            continue
        rows.append(r)
    df=pd.DataFrame(rows)
    if df.empty:
        print("[ERROR] Nichts aggregiert."); return

    metrics={k:ci95(df[k].tolist()) for k in ["theta_e","theta_n","dtheta","plateau_e","plateau_n","dpp"]}
    csv=OUT / f"T3_seeds_{args.out_name}.csv"
    js =OUT / f"T3_seeds_{args.out_name}_summary.json"
    df.to_csv(csv, index=False)
    js.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] CSV : {csv}\n[OK] JSON: {js}")
    print(df.to_string(index=False))

if __name__=="__main__":
    main()
