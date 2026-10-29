"""Check that a rot180 FLIR .npy folder holds the NEUTRAL apparent temperature.

correct_session.py applies its own emissivity, transmittance and reflected
temperature, so its --flir-dir input must be flyr's reading with neutral camera
settings (emissivity 1, object distance 0; ThermalData.neutral_celsius), not
flyr's plain `.celsius`, which applies the settings stored in the JPEG
(emissivity 0.98, 50 m on the paper sessions; 0.6-0.9 C higher).

For up to three frames (first, middle, last) the neutral reading is recomputed
from the original *_R.jpg, rotated 180 degrees like rotate_flir_poses.py --npy,
and compared with the .npy. correct_session.py calls verify_or_exit() before it
processes anything; this file can also be run on its own:

    py flir_input_guard.py --flir-dir <session>_rot180 --flir-jpg-dir <original dir(s)>

Exit code 0 = neutral, 1 = not neutral.
"""

import argparse
import sys
from pathlib import Path

import numpy as np

TOL_C = 0.01
FAIL_MESSAGE = ("FLIR npy were not produced with neutral settings (emissivity=1, distance=0); "
                "regenerate them with rotate_flir_poses.py")


def index_jpgs(dirs) -> dict:
    """Original *_R.jpg by file name; the first folder wins (as in correct_session.py)."""
    jpgs = {}
    for d in dirs:
        for jpg in Path(d).glob("*_R.jpg"):
            jpgs.setdefault(jpg.name, jpg)
    return jpgs


def neutral_rot180(jpg, reader=None) -> np.ndarray:
    """Neutral apparent temperature of one original JPEG, rotated like rotate_flir_poses.py --npy."""
    if reader is None:
        from ThermalData import neutral_celsius as reader
    return np.rot90(reader(jpg), 2).astype(np.float32)


def check_flir_npy(flir_dir, stems, jpgs, reader=None) -> list:
    """[(stem, max abs diff in C)] for the first, middle and last checkable frame.

    A frame is checkable when both <flir_dir>/<stem without _R>.npy and the
    original <stem>.jpg exist.
    """
    flir_dir = Path(flir_dir)
    usable = [s for s in stems
              if (flir_dir / f"{s.replace('_R', '')}.npy").exists() and f"{s}.jpg" in jpgs]
    picked = sorted({0, len(usable) // 2, len(usable) - 1}) if usable else []
    results = []
    for i in picked:
        stem = usable[i]
        npy = np.load(flir_dir / f"{stem.replace('_R', '')}.npy").astype(np.float64)
        ref = neutral_rot180(jpgs[f"{stem}.jpg"], reader).astype(np.float64)
        if npy.shape != ref.shape:
            results.append((stem, float("inf")))
            continue
        results.append((stem, float(np.nanmax(np.abs(npy - ref)))))
    return results


def verify_or_exit(flir_dir, stems, jpg_dirs, allow_stored_settings=False, tol=TOL_C, reader=None):
    """Stop the run unless the sampled .npy match the neutral reading within `tol` C."""
    results = check_flir_npy(flir_dir, stems, index_jpgs(jpg_dirs), reader)
    if not results:
        print(f"WARNING: no frame of {flir_dir} has an original JPEG in {list(map(str, jpg_dirs))}: "
              "the FLIR input convention (neutral settings) cannot be verified", file=sys.stderr)
        return results
    for stem, diff in results:
        print(f"FLIR input check {stem}: max |npy - neutral| = {diff:.4f} C")
    worst_stem, worst = max(results, key=lambda r: r[1])
    if worst <= tol:
        print(f"FLIR input check passed: neutral settings (tolerance {tol} C)")
        return results
    if allow_stored_settings:
        print("\n" + "!" * 78 + f"\nWARNING: {FAIL_MESSAGE}.\n"
              f"max abs diff {worst:.3f} C on {worst_stem}. Continuing because of "
              "--allow-stored-settings:\nthe camera-stored emissivity/distance are applied "
              "TWICE, results are not comparable.\n" + "!" * 78 + "\n", file=sys.stderr)
        return results
    sys.exit(f"{FAIL_MESSAGE} (max abs diff {worst:.3f} C on {worst_stem}, tolerance {tol} C). "
             "Use --allow-stored-settings to bypass.")


def main():
    p = argparse.ArgumentParser(description="Check that rot180 FLIR .npy hold the neutral apparent temperature")
    p.add_argument("--flir-dir", required=True, metavar="DIR", help="rot180 .npy folder")
    p.add_argument("--flir-jpg-dir", nargs="+", required=True, metavar="DIR",
                   help="Folder(s) with the original FLIR *_R.jpg")
    p.add_argument("--tol", type=float, default=TOL_C, help=f"Max abs diff in C (default {TOL_C})")
    args = p.parse_args()
    stems = sorted(f"{f.stem}_R" for f in Path(args.flir_dir).glob("*.npy"))
    try:
        results = verify_or_exit(args.flir_dir, stems, args.flir_jpg_dir, tol=args.tol)
    except SystemExit as e:
        print(e, file=sys.stderr)
        return 1
    return 0 if results else 1


if __name__ == "__main__":
    sys.exit(main())
