# calibration/extrinsic/zed_fill/

`fill_board_holes.py` repaints the **4 holes of the calibration board** white
in every ZED frame of a pose. It is needed because LVT2Calib's RGB detector
otherwise rejects the pose. Host-side, light env (`../requirements.txt`, uses
`scipy` when available).

## Why

LVT2Calib's `cam_pattern` runs `findCirclesGrid(2x2, SYMMETRIC_GRID + CLUSTERING)`
with a `SimpleBlobDetector` (`cfg/Camera.cfg`: `minCircularity 0.8`,
`minInertiaRatio 0.1`, `minArea 50`, `blobColor 255`). The board is black and
the holes show the light wall behind it. When a dark object (a cabinet handle,
the gap between two doors) shows through a hole, the blob loses circularity
and the pose is **never** accepted. In the thesis calibration session this
happened in 8 of 9 ZED poses.

## How

1. Reference frame: median of `--ref-frames` (15) frames of the pose. The board is
   static, and the centres drift ≤ 0.2 px within a pose.
2. Initial centres with `../record_check/zed_pose_check.py::detect_holes`
   (same `--hole-*` flags and defaults).
3. Homography H from the board plane, where the geometry is exact: 4 holes of
   ⌀0.13 m at (±0.15, ±0.15) m.
4. Robust refinement of H plus a radius scale on the hole-boundary points
   (`scipy.optimize.least_squares`, soft-L1). The centre of an obstructed hole's
   blob is biased by 5–7 px, which is why this step exists. Without scipy, a
   numpy-only fallback is used.
5. Fill the 4 projected ellipses (`--fill`, default 255).
6. `--check` reproduces LVT2Calib exactly: undistort with
   `zed_right_intrinsic.yaml`, then `findCirclesGrid` with the same blob
   parameters. It counts detections before and after.

## Usage

**Input:** `--pose-dir` (one `pose_NN/` with `frames/` + `metadata.json`, from
`../session_split/`) or `--poses-root` (all `pose_*` inside).

**Output:** `<pose><suffix>/` (default `_filled`; `--outdir` with `--pose-dir`),
containing:
- the filled `frames/`;
- `metadata.json` (copied);
- `holes.json` (fitted geometry);
- `debug.png`.

| Flag | Default |
|---|---|
| `--suffix` | `_filled` |
| `--force` | overwrite an existing output |
| `--dry-run` | geometry, `debug.png`, `holes.json`, `--check`, no frames |
| `--ref-frames` | 15 |
| `--fill` | 255 |
| `--radius-scale` | 1.0 |
| `--no-refine` | homography from the detected centres only |
| `--occluded-frac` | 0.95 |
| `--click` | manual fallback: click the 4 centres |
| `--check`, `--check-step` (20) | LVT2Calib-equivalent detection count |
| `--camera-info YAML` | intrinsics for `--check`. **Default: `lvt2calib/data/camera_info/zed_right_intrinsic.yaml` in a `lvt2calib/` clone next to this repository's folder.** Pass `../../intrinsic/zed_right_intrinsic.yaml` explicitly instead. |
| `--hole-downscale`, `--hole-kernel`, `--hole-min-area`, `--hole-max-area`, `--hole-min-circ`, `--rect-tol`, `--hole-spacing-ratio-min/max` | as `zed_pose_check.py` |

```powershell
py fill_board_holes.py --poses-root D:\calib\Zed\Poses --check --camera-info ..\..\intrinsic\zed_right_intrinsic.yaml
```

The filled pose folder is then published with
`lvt2calib_patches/catkin_ws_src/zed_frame_publisher` (`--session-dir`).
Console messages are in Italian.
