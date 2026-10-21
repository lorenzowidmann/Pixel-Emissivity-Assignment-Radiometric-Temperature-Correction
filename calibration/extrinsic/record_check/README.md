# calibration/extrinsic/record_check/

Report-only checks on a recorded calibration session, run **before** LVT2Calib.
No input file is modified. They read ROS 2 bags directly (`.db3`/`rosbags`),
without ROS or Docker. Light env (`../requirements.txt`).

| Script | Input | Output | Notes |
|---|---|---|---|
| `detect_board_poses.py` | image folder(s), or `--db3`/`--bag` LiDAR | console table; `--csv-out` (with `--check-inside` this is the `flir_check.csv` read by `../session_split/split_flir_poses.py`); `--debug-dir` PNGs | Counts the board poses (frame-diff for images, voxel occupancy change for LiDAR). `--check-inside` (FLIR) checks that the 4-hole board is not clipped. `--compare --flir ... --zed ... --db3 ...` compares pose gaps across sensors. |
| `zed_pose_check.py` | ZED `session` (positional; `metadata.json` + `frames/`) | console; `--csv-out zed_check.csv` (read by `split_zed_poses.py`); `--debug-dir` | Per pose: board present and fully inside the frame (INSIDE / CLIPPED [sides] / inconclusive). Imports `detect_board_poses`. |
| `find_board_limits.py` | `--bag` (ROS 2), `--windows label:start_s:duration_s ...` | console | Depth histogram per pose window, background subtraction, and suggested `px/py/pz` passthrough bounds for `livox_hap_pattern.launch`. `--tune` adds a sliding-window search with planarity/fill gates. Long method notes are in `--help`. |
| `lidar_quality_check.py` | `--bag` | console; `--csv-out` gap table | Continuity of `/livox/lidar` and `/livox/imu`, expected rates `/livox/lidar=4.5:4.9`, `/livox/imu=195:210` Hz. |
| `lidar_hole_check.py` | `--bag` | console | Do the LiDAR returns resolve the 4 holes? **Needs open3d: Python 3.12 env** (see `../requirements.txt`). |

`find_board_limits.py` and `../zed_fill/fill_board_holes.py` import
`detect_board_poses`/`zed_pose_check` from this folder, so the folder names must
stay as they are.

```powershell
py zed_pose_check.py D:\calib\Zed\20260914_101500 --csv-out zed_check.csv --debug-dir dbg_zed
py detect_board_poses.py D:\calib\Flir\100_FLIR D:\calib\Flir\101_FLIR --check-inside --csv-out flir_check.csv
py find_board_limits.py --bag D:\calib\rosbag2_2026_09_10-16_38_14 --windows 1:0:106 3:190:97 4:299:94 --tune
py lidar_quality_check.py --bag D:\calib\rosbag2_2026_09_10-16_38_14 --csv-out gaps.csv
```

Some help texts and console messages are in Italian (as in the thesis).
