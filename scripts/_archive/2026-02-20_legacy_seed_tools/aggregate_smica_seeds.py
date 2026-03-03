# scripts/aggregate_smica_seeds.py
# Zweck: Seed-Läufe für einen SMICA-Dataset-Basis-Tag zusammenfassen (θ, Plateau, Δθ, Δpp)
# Robuste Version: legt Ausgabeverzeichnisse automatisch an, überspringt fehlende Nulltests,
# optional automatische Seed-Erkennung.
#
# Nutzung (Repo-Root als Arbeitsverzeichnis):
#   python scripts\aggregate_smica_seeds.py
#   python scripts\aggregate_smica_seeds.py --base-tag planck_smica_cmb__fov12_b60_n64 --seeds 41,42,43,44,45
#   python scripts\aggregate_smica_seeds.py --seeds auto
#
# Definitionen:
#   Δθ  = θ(echt) − θ(null)
#   Δpp = Plateau(null) − Plateau(echt)    (in Prozentpunkten; > 0 gewünscht)
#
# Eingaben pro Tag (im Ordner data/processed/astro/suite/<tag>/):
#   <tag>_summary.json         ... echte Daten (enthält "theta", "plateau_pct")
#   <tag>_null_summary.json    ... Nulltests (dito)
#
# Ausgaben:
#   reports/astro/T3_seeds_<base-tag>.csv
#   reports/astro/T3_seeds_<base-tag>_summary.json  (Median & 95%-KI)

import argparse
import json
import os
from pathlib import Path
import re
from typing import List, Optional, Dict, Any

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Aggregate SMICA Seed-Runs (θ, Plateau) für einen Basis-Tag.")
    p.add_argument(
        "--base-tag",
        default="planck_smica_cmb__fov12_b60_n64",
        help="Basis-Tag ohne Seed-Suffix (Standard: planck_smica_cmb__fov12_b60_n64)",
    )
    p.add_argument(
        "--seeds",
        default="41,42,43,44,45",
        help="Kommagetrennt: z. B. 41,42,43,44,45 oder 'auto' für automatische Erkennung.",
    )
    p.add_argument(
        "--suite-dir",
        default=str(Path("data") / "processed" / "astro" / "suite"),
        help="Wurzelverzeichnis der Suite-Outputs.",
    )
    p.add_argument(
        "--out-dir",
        default=str(Path("reports") / "astro"),
        help="Zielverzeichnis für CSV/JSON.",
    )
    return p.parse_args()


def discover_seed_tags(base_tag: str, suite_dir: Path) -> List[str]:
    """
    Automatische Erkennung: Alle Unterordner in suite_dir, die mit base_tag beginnen
    und entweder exakt base_tag heißen (Basis/Seed41) oder base_tag_seedNN enthalten.
    """
    tags = []
    if not suite_dir.exists():
        return tags
    pattern = re.compile(rf"^{re.escape(base_tag)}(?:_seed\d+)?$")
    for p in suite_dir.iterdir():
        if p.is_dir() and pattern.match(p.name):
            tags.append(p.name)
    # Sortiere konsistent: zuerst Basis, dann aufsteigende Seeds
    def tag_key(t: str) -> tuple:
        m = re.search(r"_seed(\d+)$", t)
        return (0, 41) if t == base_tag else (1, int(m.group(1)) if m else 9999)
    tags.sort(key=tag_key)
    return tags


def build_tags_from_seeds(base_tag: str, seeds_spec: str) -> List[str]:
    """
    seeds_spec = "41,42,43,44,45" -> [base_tag, base_tag_seed42, ...]
    Hinweis: Seed 41 wird als Basis-Tag (ohne _seed41) interpretiert.
    """
    seeds = []
    for tok in seeds_spec.split(","):
        tok = tok.strip()
        if not tok:
            continue
        if tok.lower() == "auto":
            return []
        try:
            seeds.append(int(tok))
        except ValueError:
            raise ValueError(f"Ungültiger Seed-Wert: {tok}")
    tags = []
    for s in seeds:
        if s == 41:
            tags.append(base_tag)
        else:
            tags.append(f"{base_tag}_seed{s}")
    return tags


def load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception as e:
            print(f"[WARN] Kann JSON nicht laden: {path} ({e})")
            return None


def ci95(values: List[float]) -> Dict[str, Any]:
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return {"median": None, "ci95": [None, None], "n": 0}
    med = float(np.median(arr))
    lo, hi = np.percentile(arr, [2.5, 97.5])
    return {"median": med, "ci95": [float(lo), float(hi)], "n": int(arr.size)}


def aggregate(base_tag: str, tags: List[str], suite_dir: Path) -> pd.DataFrame:
    rows = []
    missing_any = False
    for t in tags:
        base_path = suite_dir / t
        sum_path = base_path / f"{t}_summary.json"
        nul_path = base_path / f"{t}_null_summary.json"

        s = load_json(sum_path)
        if s is None:
            print(f"[WARN] Fehlt oder fehlerhaft: {sum_path} -> überspringe {t}")
            missing_any = True
            continue

        n = load_json(nul_path)
        if n is None:
            print(f"[WARN] Null-Summary fehlt: {nul_path} -> überspringe {t}")
            missing_any = True
            continue

        try:
            theta_e = float(s["theta"])
            plat_e = float(s["plateau_pct"])
            theta_n = float(n["theta"])
            plat_n = float(n["plateau_pct"])
        except KeyError as e:
            print(f"[WARN] Schlüssel fehlt in JSON ({e}) bei {t} -> überspringe")
            missing_any = True
            continue

        rows.append(
            dict(
                tag=t,
                theta_e=theta_e,
                theta_n=theta_n,
                dtheta=theta_e - theta_n,
                plateau_e=plat_e,
                plateau_n=plat_n,
                dpp=plat_n - plat_e,
            )
        )

    if missing_any:
        print("[INFO] Hinweis: Ein oder mehrere Tags wurden ausgelassen (fehlende/defekte Dateien).")
    df = pd.DataFrame(rows)
    if df.empty:
        print("[ERROR] Keine verwertbaren Einträge gefunden. Prüfe Basis-Tag/Seeds und Nulltests.")
    return df


def main():
    args = parse_args()
    suite_dir = Path(args.suite_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Tags bestimmen
    if args.seeds.strip().lower() == "auto":
        tags = discover_seed_tags(args.base_tag, suite_dir)
        if not tags:
            print(f"[ERROR] Keine Tags automatisch gefunden für Basis '{args.base_tag}' in '{suite_dir}'.")
            return
        print(f"[INFO] Auto-erkannt: {', '.join(tags)}")
    else:
        tags = build_tags_from_seeds(args.base_tag, args.seeds)
        print(f"[INFO] Verwende explizite Tags: {', '.join(tags)}")

    df = aggregate(args.base_tag, tags, suite_dir)
    if df.empty:
        return

    # Kennzahlen (Median & 95%-KI)
    metrics = {}
    for col in ["theta_e", "theta_n", "dtheta", "plateau_e", "plateau_n", "dpp"]:
        metrics[col] = ci95(df[col].tolist())

    # Ausgabe-Dateinamen (Basis-Tag in Dateinamen kodieren)
    safe_base = args.base_tag
    csv_path = out_dir / f"T3_seeds_{safe_base}.csv"
    json_path = out_dir / f"T3_seeds_{safe_base}_summary.json"

    # Speichern
    df.to_csv(csv_path, index=False)
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    # Konsolenausgabe (kurzer Überblick)
    print(f"\n[OK] Gespeichert:\n  CSV : {csv_path}\n  JSON: {json_path}\n")
    print("Tabelle:")
    print(df.to_string(index=False))
    print("\nMedian & 95%-KI:")
    for k, v in metrics.items():
        print(f"  {k:12s}: median={v['median']}, ci95={v['ci95']}, n={v['n']}")


if __name__ == "__main__":
    main()
