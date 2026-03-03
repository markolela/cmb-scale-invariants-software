# scripts/fill_results_placeholders_hm.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from datetime import datetime


REPO = Path(__file__).resolve().parents[1]
SUITE = REPO / "data" / "processed" / "astro" / "suite"


def _load_null_summary(dataset: str) -> dict:
    p = SUITE / dataset / f"{dataset}_null_summary.json"
    if not p.exists():
        raise SystemExit(f"Fehlt: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def _fmt_theta(x: float) -> str:
    return f"{float(x):.6f}"


def _fmt_pp(x: float) -> str:
    return f"{float(x):.2f}"


def _fmt_ci(ci: list[float], kind: str) -> str:
    a, b = float(ci[0]), float(ci[1])
    if kind == "theta":
        return f"[{a:.6f}, {b:.6f}]"
    if kind == "pp":
        return f"[{a:.2f}, {b:.2f}]"
    raise ValueError(kind)


def _tex_key(key: str) -> str:
    return key.replace("_", r"\_")


def _replace_all(tex: str, repl: dict[str, str]) -> tuple[str, list[str]]:
    missing = []
    out = tex

    for key, val in repl.items():
        ph_plain = f"[R7:{key}]"
        ph_tex = f"[R7:{_tex_key(key)}]"

        hit = False
        if ph_plain in out:
            out = out.replace(ph_plain, val)
            hit = True
        if ph_tex in out:
            out = out.replace(ph_tex, val)
            hit = True

        if not hit:
            missing.append(key)

    return out, missing


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tex", required=True, help="Pfad zur 07_results.tex relativ zu REPO oder absolut")
    ap.add_argument("--hm1", required=True, help="Dataset-Tag für HM1")
    ap.add_argument("--hm2", required=True, help="Dataset-Tag für HM2")
    args = ap.parse_args()

    tex_path = Path(args.tex)
    if not tex_path.is_absolute():
        tex_path = (REPO / tex_path).resolve()

    if not tex_path.exists():
        raise SystemExit(f"TeX file not found: {tex_path}")

    hm1 = _load_null_summary(args.hm1)
    hm2 = _load_null_summary(args.hm2)

    repl = {
        "DTHETA_MED_HM1": _fmt_theta(hm1["dtheta_med"]),
        "DTHETA_CI95_HM1": _fmt_ci(hm1["dtheta_ci95"], "theta"),
        "DPP_MED_HM1": _fmt_pp(hm1["dpp_med"]),
        "DPP_CI95_HM1": _fmt_ci(hm1["dpp_ci95"], "pp"),
        "DTHETA_MED_HM2": _fmt_theta(hm2["dtheta_med"]),
        "DTHETA_CI95_HM2": _fmt_ci(hm2["dtheta_ci95"], "theta"),
        "DPP_MED_HM2": _fmt_pp(hm2["dpp_med"]),
        "DPP_CI95_HM2": _fmt_ci(hm2["dpp_ci95"], "pp"),
    }

    src = tex_path.read_text(encoding="utf-8")
    dst, missing = _replace_all(src, repl)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = tex_path.with_suffix(tex_path.suffix + f".bak_{stamp}")
    bak.write_text(src, encoding="utf-8")
    tex_path.write_text(dst, encoding="utf-8")

    print(f"Updated: {tex_path}")
    print(f"Backup:  {bak}")

    if missing:
        print("Nicht gefunden im TeX, Platzhalter Keys:")
        for k in missing:
            print(" ", k)

    left = re.findall(r"\[R7:[A-Z0-9_\\]+\]", dst)
    if left:
        print("Noch vorhandene R7 Platzhalter:")
        for p in sorted(set(left)):
            print(" ", p)


if __name__ == "__main__":
    main()
