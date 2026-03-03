# scripts/hm_diff_qc_build.py
# Erzeugt HM-Diff (HM2−HM1) für SMICA/NILC aus bereits geglätteten HM-FITS
# und baut Patches für |b|≥65/70/75, FoV=12°, n=256.

from __future__ import annotations
from pathlib import Path
import numpy as np
import healpy as hp
from astropy.io import fits
import sys

REPO = Path(__file__).resolve().parents[1]
RAW  = REPO / "data" / "raw" / "astro" / "planck" / "harmonized"
assert RAW.exists(), f"Missing: {RAW}"

def get_ordering(path: Path) -> str:
    try:
        hdr = fits.getheader(path.as_posix(), ext=1)
    except Exception:
        hdr = fits.getheader(path.as_posix(), ext=0)
    ordv = (hdr.get("ORDERING", "RING") or "RING").strip().upper()
    return "NESTED" if ordv.startswith("NEST") else "RING"

def make_hmdiff(mapname: str) -> Path:
    # mapname in {"smica","nilc"}
    hm1 = RAW / f"COM_CMB_IQU-{mapname}_2048_R3.00_hm1_sm10am.fits"
    hm2 = RAW / f"COM_CMB_IQU-{mapname}_2048_R3.00_hm2_sm10am.fits"
    assert hm1.exists() and hm2.exists(), f"Inputs fehlen: {hm1} | {hm2}"

    ordering = get_ordering(hm1)  # beide HMs haben gleiches ORDERING
    nest = (ordering == "NESTED")

    m1 = hp.read_map(hm1.as_posix(), field=0, nest=nest, verbose=False).astype(np.float64, copy=False)
    m2 = hp.read_map(hm2.as_posix(), field=0, nest=nest, verbose=False).astype(np.float64, copy=False)
    md = (m2 - m1).astype(np.float32, copy=False)

    out = RAW / f"COM_CMB_IQU-{mapname}_2048_R3.00_hmdiff_sm10am.fits"
    hp.write_map(out.as_posix(), md, nest=nest, dtype=np.float32, fits_IDL=False, overwrite=True)
    # Header fixups
    with fits.open(out.as_posix(), mode="update", memmap=False) as hdul:
        hdr0 = hdul[0].header
        hdr0["ORDERING"] = ordering
        if "FWHM" not in hdr0:
            hdr0["FWHM"] = (10.0/60.0, "degrees")
        hdul.flush()
    print(f"[OK] HM-DIFF {mapname.upper()}: {out.name} (ORDERING={ordering})")
    return out

def build_patches(mapname: str, diff_fits: Path):
    # Wir nutzen den vorhandenen Builder aus make_real_patches_standalone
    sys.path.insert(0, str(REPO))
    from scripts.make_real_patches_standalone import build  # Kompat-Wrapper

    for b, lat_cut in (("b65",65.0),("b70",70.0),("b75",75.0)):
        tag = f"planck_{mapname}_cmb_hmdiff__fov12_{b}_n256_sm10am"
        res = build(tag, diff_fits, n_patches=256, N=1024, fov_deg=12.0, lat_cut_deg=lat_cut, seed=41)
        assert res is not None, f"Patch-Build fehlgeschlagen: {tag}"
        print(f"[OK] Patches: {tag}")

def main():
    for mp in ("smica","nilc"):
        diff = make_hmdiff(mp)
        build_patches(mp, diff)
    print("\n[OK] HM-Diff-Erzeugung + Patch-Build abgeschlossen.")

if __name__ == "__main__":
    main()
