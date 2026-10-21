# calibration/extrinsic/session_split/

Splits a continuous calibration recording into one folder per board pose, so
each pose can be replayed into LVT2Calib on its own. Light env (`../requirements.txt`).

| Script | Input | Output |
|---|---|---|
| `split_zed_poses.py` | `--session` (zed_record.py folder), `--check-csv zed_check.csv` (from `../record_check/zed_pose_check.py`) | `--outdir/pose_NN/` with `frames/` + `metadata.json` |
| `split_flir_poses.py` | `--raw-dir DIR ...` (e.g. `100_FLIR 101_FLIR`), `--check-csv flir_check.csv` (from `detect_board_poses.py --check-inside`) | `--outdir/pose_NN/` with the `*_R.jpg` files (`--pattern`, default `*_R.jpg`) |
| `pick_hole_patch.py` | `--frame` one PNG of a pose | interactive (OpenCV window): 3 clicks (centre, rim, clean colour); prints `--cx --cy --radius --color` |
| `patch_hole_pose.py` | `--pose-dir`, `--outdir`, `--cx --cy --radius --color` | a copy of the pose with a filled circle on every frame, same `metadata.json` |

Both splitters take `--verdict` (exact match, default `INSIDE`) and
`--verdict-prefix` (e.g. `CLIPPED` to also take `CLIPPED [L]`).

`pick_hole_patch.py` + `patch_hole_pose.py` are the manual fix for one
obstructed hole. `../zed_fill/fill_board_holes.py` is the automatic one that
repaints all four holes. Which of the two produced the final ZED poses of the
paper calibration was not recorded (TODO).

```powershell
py split_zed_poses.py  --session D:\calib\Zed\20260914_101500 --check-csv zed_check.csv  --outdir D:\calib\Zed\Poses
py split_flir_poses.py --raw-dir D:\calib\Flir\100_FLIR D:\calib\Flir\101_FLIR --check-csv flir_check.csv --outdir D:\calib\Flir\Poses
py pick_hole_patch.py  --frame D:\calib\Zed\Poses\pose_01\frames\right_000120.png
py patch_hole_pose.py  --pose-dir D:\calib\Zed\Poses\pose_01 --outdir D:\calib\Zed\Poses\pose_01_patched --cx 430 --cy 210 --radius 65 --color 210,205,200
```
