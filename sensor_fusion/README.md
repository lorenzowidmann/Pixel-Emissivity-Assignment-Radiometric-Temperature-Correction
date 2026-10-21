# sensor_fusion/

Shared library, not a pipeline step: the rig geometry and the LiDAR→camera
projection used by every script that puts a LiDAR point on an image (paper
§IV-C, Appendix A and B). Light env (`requirements.txt`).

| File | What |
|---|---|
| `rig_calibration.yaml` | **The canonical calibration.** FLIR and ZED intrinsics + LiDAR→FLIR and LiDAR→ZED extrinsics of the **second calibration** (NewCalibration, 2026-09, LVT2Calib min2d; paper Appendix B). Edit this file, not code, when you recalibrate. |
| `rig_calibration.py` | `load_rig_calibration(path)` returns a `RigCalibration` (intrinsics, `T_lidar_to_flir`, `T_lidar_to_zed`, `flir_rotated_180`, `zed_K_for(w, h)`). |
| `projection.py` | `project_lidar_to_camera(...)`: world → LiDAR (undo the `/Odometry` pose) → camera (`T_lidar_to_cam`) → pixels (K + distortion). `flir_fov_bbox_in_zed(...)`: the part of a ZED frame the FLIR can see, used for cropping. |
| `livox_odometry_loader.py` | Rebuilds world clouds from raw `/livox/lidar` + `/Odometry` (per-point deskew), instead of FAST-LIO's cropped `/cloud_registered`. Imported by `../emissivity/project_to_flir.py --raw-lidar`. It also has a diagnostic CLI (`--bag`, `--inspect`, `--compare`, `--export-ply`, `--fix-digests`, ...; see `--help`). |

Who imports it: `../emissivity/sam/classify_session_sam.py` and
`mask2former/classify_session_m2f.py` (FLIR-FOV crop), and
`../emissivity/project_to_flir.py` and `voxel_consensus.py` (projection). They
find this folder by its name, `sensor_fusion/`, so do not rename it.

## `rig_calibration.yaml` schema (`rig_calibration/v1`)

- `flir`: `image_size`, `fx fy cx cy skew`, `dist_coeffs [k1 k2 p1 p2 k3]`,
  `rotated_180_before_calibration: true`. **FLIR frames must be rotated 180°**
  before any projection.
- `zed`: `calibration_image_size` (1920×1080), `fx fy cx cy skew`,
  `dist_coeffs`, `mean_reproj_px`.
- `lidar_to_flir`, `lidar_to_zed`: `T_lidar_to_cam` (row-major 4×4, maps a
  point in the LiDAR frame to the camera optical frame: z forward, x right,
  y down), `rmse_3d_m`, `reproj_px`, `caveats`.

The YAML comments mention the source notes of the thesis (Obsidian files) and
the superseded first calibration (`Exttr_tryN`, 2026-08-03) for provenance
only. No values from the first calibration are in the file.

## Example

```python
import sys; sys.path.insert(0, "sensor_fusion")
from rig_calibration import load_rig_calibration
cal = load_rig_calibration("sensor_fusion/rig_calibration.yaml")
print(cal.T_lidar_to_flir, cal.flir.K, cal.zed_K_for(1920, 1080))
```
