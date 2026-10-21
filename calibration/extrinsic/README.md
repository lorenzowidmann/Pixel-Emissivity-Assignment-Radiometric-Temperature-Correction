# calibration/extrinsic/

LiDAR (Livox HAP) ↔ camera (ZED 2i right, FLIR) extrinsics with
[LVT2Calib](https://github.com/Clothooo/lvt2calib) (paper §III-B, Appendix B).
Upstream LVT2Calib is **not** included. Only the files we changed or added are
here, in [`lvt2calib_patches/`](lvt2calib_patches).

> **The result is not stored here.** The extrinsics used by every downstream
> script are in [`../../sensor_fusion/rig_calibration.yaml`](../../sensor_fusion/rig_calibration.yaml)
> (`lidar_to_zed`, `lidar_to_flir`: the second calibration, 2026-09, min2d
> solutions). That YAML sits in `sensor_fusion/` because its loader reads it
> from there.

| Folder | What | Where it runs |
|---|---|---|
| [`conversion/`](conversion) | ROS 2 Livox bag → ROS 1 bag; 180° rotation of FLIR frames (+ apparent-temperature `.npy`) | host, light env |
| [`record_check/`](record_check) | Pose detection and quality checks on the recorded calibration session; suggested LiDAR passthrough bounds | host, light env (`lidar_hole_check.py`: Python 3.12 + open3d) |
| [`session_split/`](session_split) | One folder per board pose; optional manual hole patch | host, light env |
| [`zed_fill/`](zed_fill) | Repaints the 4 board holes in ZED frames so LVT2Calib's blob detector accepts the pose | host, light env |
| [`board_generation/`](board_generation) | PCD templates of the real board (100×70 cm, 4 × ⌀13 cm holes) + hole-insert CAD | host, stdlib only |
| [`lvt2calib_patches/`](lvt2calib_patches) | Overlay for an upstream clone (HAP launch, board parameters, rviz, templates) + 2 catkin frame publishers | ROS 1 Noetic container |
| [`validation/`](validation) | MATLAB FLIR→ZED overlay through the LiDAR, to check the extrinsics on real scene geometry | MATLAB |

Install for the host-side scripts: `pip install -r requirements.txt`.

## Order of operations

1. Record the calibration session: board at ~9–12 poses, LiDAR bag + ZED + FLIR
   (`../../acquisition/README.md`; FAST-LIO is not needed).
2. `conversion/convert_livox_bag.py`, then `conversion/rotate_flir_poses.py`.
3. `record_check/` to find the poses and check that the board is fully in frame.
   `find_board_limits.py` gives per-pose `px/py/pz` bounds.
4. `session_split/` to get `pose_NN/` folders, then `zed_fill/` where a background
   object breaks a hole.
5. Inside the container: replay, detect, collect, solve (see `lvt2calib_patches/README.md`).
6. Copy the min2d matrices into `../../sensor_fusion/rig_calibration.yaml`.
7. Optional: check visually with `validation/FlirLidarZedViewer_calib2.m`.

## Result used in the paper (Appendix B)

| | ZED–LiDAR | FLIR–LiDAR |
|---|---|---|
| x, y, z [m] | −0.036, 0.126, 0.010 | −0.114, 0.122, −0.004 |
| roll, pitch, yaw [rad] (ZYX) | −2.957, −1.521, −1.759 | 1.092, −1.532, 0.476 |
| Poses used | 7 of 9 | 8 of 12 |
| RMSE x / y / z / total [m] | 0.070 / 0.004 / 0.007 / 0.070 | 0.110 / 0.007 / 0.007 / 0.110 |

LVT2Calib writes a file per run (`data/calibration_result/livox_hap_to_*_exParam_min2d.csv`)
and appends every run to `L2C_CalibLog.csv`. On the original machine the
`livox_hap_to_rgb_exParam_min2d.csv` left on disk is a **later 6-pose run**
(2026-09-14 22:15), not the 7-pose run (22:09:58) used in the paper.
Take the matrix from the log row, not from the last file written.
