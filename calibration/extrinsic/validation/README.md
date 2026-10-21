# calibration/extrinsic/validation/

`FlirLidarZedViewer_calib2.m` is a visual check that the LiDAR↔camera extrinsics
line up on real scene geometry, not only on the four board holes they were
fitted to.

For a synced triplet it projects the same LiDAR scan into the FLIR **and** into
the ZED, with a per-camera z-buffer for occlusion. It then paints each ZED pixel
with the FLIR value sampled at the corresponding FLIR pixel. With a correct
calibration, thermal colours land on the matching structures. With a wrong one,
they bleed across edges.

**Requirements:** an interactive MATLAB desktop session (not `-batch`) and
**ROS Toolbox** (`ros2bagreader`). The other toolboxes are not verified (TODO).

**Inputs:** edit the block at the top:
- `sessionRoot` (placeholder `C:\path\to\data\AcquistionGroundTruth`), which
  must contain `Zed/20260911_105024`, `Flir/session_125010_rot180` (now
  `Fllir/session_A10_rot180` in `GroundTruthFiles`), `Lidar/rosbag2_2026_09_11-12_50_10`
  and the session's `sync_manifest.json`;
- `S.lidarAccumHalfWindow_s` (0.1 s);
- `S.zBufferTol_m` (0.08 m).

The extrinsics and intrinsics are **hard-coded** in the file. They equal the
values in `../../../sensor_fusion/rig_calibration.yaml` (checked). If you
recalibrate, update both.

**Usage:** `FlirLidarZedViewer_calib2(startIdx)` (default `startIdx = 9`). Arrow
keys step through the triplets, and `s` saves the current view to
`output/flir_on_zed_125010_calib2_pose<NN>.png` next to the script (git-ignored).
