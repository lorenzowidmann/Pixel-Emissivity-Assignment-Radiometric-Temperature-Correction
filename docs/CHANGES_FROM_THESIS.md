# Provenance, edit log and consistency check

This repository was extracted on 2026-10-21 from:

- the thesis repository `Robotic-Thermal-Modelling-Eplus` (HEAD `311f86c`, clean
  working tree);
- `lvt2calib_adapted`, a copy of the LVT2Calib install used for the calibration
  (no `.git`). It is identical to upstream `Clothooo/lvt2calib@9dd3def`
  (`ros_noetic`) except for the files listed in
  `calibration/extrinsic/lvt2calib_patches/README.md`.

Files were **copied**. Algorithm behaviour is unchanged. The only edits are the
import/path fixes and the placeholder paths listed below. Line endings (CRLF)
are preserved.

## 1. Where each file came from

| Destination | Source |
|---|---|
| `acquisition/zed_record.py`, `extract_fullrate_frames.py`, `qos.yaml` | `DataAcquisition/` |
| `acquisition/rtd_reading/*.m` | `MATLAB_NIRTDReading/` |
| `calibration/intrinsic/capture_zed_right.py`, `IntCalibration_*.m` | `IntrinsicCalibration/` |
| `calibration/intrinsic/{zed_right,thermal}_intrinsic.yaml` | `lvt2calib_adapted/data/camera_info/` |
| `calibration/extrinsic/conversion/` | `LVTCalibConversion/convert_livox_bag.py`, `rotate_flir_poses.py` |
| `calibration/extrinsic/record_check/` | `LVTCalibConversion/RecordCheck/` (5 scripts) |
| `calibration/extrinsic/session_split/` | `LVTCalibConversion/SessionSplit/` (4 scripts) |
| `calibration/extrinsic/zed_fill/` | `LVTCalibConversion/ZedFill/fill_board_holes.py` |
| `calibration/extrinsic/board_generation/` | `LVTCalibBoardGenearation/generate_board_template.py`, `TragetHoles/TragetHoles.STEP` |
| `calibration/extrinsic/validation/` | `MATLAB_SensorFusionValidation/FlirLidarZedViewer_calib2.m` |
| `calibration/extrinsic/lvt2calib_patches/{launch,config,rviz,data}` | `lvt2calib_adapted/` (same relative paths). The three launch/config files are byte-identical to the copies in `LVTCalibConversion/`. |
| `calibration/extrinsic/lvt2calib_patches/catkin_ws_src/` | `LVTCalibConversion/{zed,flir}_frame_publisher/` |
| `synchronization/` | `TimeSyncCheck/sync_manifest_interpolation.py`, `sync_manifest_neighbour.py`, `retime_fullrate_frames.py` |
| `sensor_fusion/rig_calibration.{py,yaml}`, `projection.py` | `SensorFusionLoader/` |
| `sensor_fusion/livox_odometry_loader.py` | `PointCloudElaboration/LivoxLidarOdometryLoader/` (needed by `project_to_flir.py --raw-lidar`) |
| `emissivity/` (scripts, table, `emissivity/` package) | `EmissivityCalculation/` |
| `emissivity/sam/classify_session_sam.py` | `EmissivityCalculation/classify_session.py` (moved and renamed after the first commit, so SAM and Mask2Former sit side by side) |
| `emissivity/mask2former/` | `EmissivityCalculation/Mask2Former/` |
| `emissivity/mask2former/external_vlm/` | `EmissivityCalculation/Mask2Former/ExtrenalVLM/` (typo fixed in the folder name) |
| `emissivity/ground_truth/` | `EmissivityCalculation/GroundTruth/` (scripts, `eval_frames.txt`, `ground_truth_{m2f,sam}.csv`) |
| `radiometric_correction/` (scripts, `radiometric/` package) | `RadiometricCalibration/` |
| `radiometric_correction/matlab/` | `EmissivityCalculation/{ShowTemperatureCorrection,VoxelCorrectionTable,ViewThermalPLY}.m` |

All READMEs, requirements files and the `.gitignore` are new. The two catkin
packages keep their own thesis READMEs.

## 2. Edits to copied files

| File | Line(s) | Change | Reason |
|---|---|---|---|
| `emissivity/sam/classify_session_sam.py` (was `emissivity/classify_session.py`) | 79, 82, 269, 272 (before the move) | `"SensorFusionLoader"` → `"sensor_fusion"` (root search, error message, `sys.path`, default YAML) | folder renamed |
| `emissivity/mask2former/classify_session_m2f.py` | 104, 107, 180 (help), 351, 355 | same | folder renamed |
| `emissivity/project_to_flir.py` | 41, 193 | `"SensorFusionLoader"` → `"sensor_fusion"` | folder renamed |
| `emissivity/project_to_flir.py` | 178 (help), 217–218 | `PointCloudElaboration/LivoxLidarOdometryLoader` → `sensor_fusion` | loader moved |
| `emissivity/sam/classify_session_sam.py` | after imports; docstring usage | added `sys.path.insert(0, <emissivity/>)` so the shared `emissivity` package is found from `sam/`; usage lines renamed to `classify_session_sam.py` | moved into `sam/` |
| `emissivity/voxel_consensus.py` | 54, 431 | `"SensorFusionLoader"` → `"sensor_fusion"` | folder renamed |
| `emissivity/mask2former/external_vlm/review_low_confidence.py` | 165 | `"GroundTruth"` → `"ground_truth"` | folder renamed |
| `radiometric_correction/correct_session.py` | 38 | `"EmissivityCalculation"` → `"emissivity"` | folder renamed |
| `radiometric_correction/radiometric/io_maps.py` | 17 | `"EmissivityCalculation"` → `"emissivity"` (default table path) | folder renamed |
| `calibration/extrinsic/record_check/find_board_limits.py` | 145 | `"RecordCheck"` → `"record_check"` | folder renamed |
| `calibration/extrinsic/zed_fill/fill_board_holes.py` | 84 | `"RecordCheck"` → `"record_check"` | folder renamed |
| `calibration/extrinsic/zed_fill/fill_board_holes.py` | 605 | `parents[3]` → `parents[4]` (default `--camera-info`: `lvt2calib/` next to the repo folder) | one more directory level |
| `calibration/intrinsic/IntCalibration_ZED.m`, `IntCalibration_Flir.m` | 10 | `folderPath` → `C:\path\to\ZedCaptures` / `C:\path\to\FlirCaptures` | personal absolute path |
| `acquisition/rtd_reading/read_plot_acquisitions.m` | 5 | `acqFolder` → `C:\path\to\data\Acquisitions` | personal absolute path |
| `calibration/extrinsic/validation/FlirLidarZedViewer_calib2.m` | 46 | `sessionRoot` → `C:\path\to\data\AcquistionGroundTruth` | personal absolute path |
| `radiometric_correction/matlab/ShowTemperatureCorrection.m` | 46–47 | `sessionDir`, `flirDir` → `C:\path\to\data\...` | personal absolute path |
| `radiometric_correction/matlab/VoxelCorrectionTable.m` | 45 | `sessionDir` → `C:\path\to\data\...` | personal absolute path |
| `radiometric_correction/matlab/ViewThermalPLY.m` | 22 | `plyPath` → `C:\path\to\data\...` | personal absolute path |
| `calibration/extrinsic/conversion/convert_livox_bag.py` | 26–27 (docstring) | `C:\Users\...\SLAM\` → `C:\path\to\` | personal absolute path |
| `radiometric_correction/ThermalData.py` | 10 (docstring) | `C:\Users\...\FlyrCamera\...` → `C:\path\to\flir_session` | personal absolute path |
| `lvt2calib_patches/catkin_ws_src/{zed,flir}_frame_publisher/README.md` | 40 / 48 | `C:\Users\...\SLAM` → `C:\path\to\bags` | personal absolute path |

No CLI flag was added, removed or renamed. No API key was found (grep for
`sk-`, `sk-ant-`, `AIza`, and `api_key=` literals). Keys are read only from
environment variables. Not edited on purpose:
- the maintainer e-mail in the two `package.xml` files;
- comments and help texts that still mention old folder names, or the SAM
  script's old name `classify_session.py` (e.g. in `classify_session_m2f.py`,
  `project_to_flir.py`, `voxel_consensus.py`). The SAM script also still writes
  `"generated_by": "classify_session.py"` into `segments.json`, unchanged so
  the output format stays identical. The only
  user-visible stale default is `--calibration` in
  `classify_session_sam.py`/`project_to_flir.py --help`.

## 3. Left out (and why)

| Thesis path | Reason |
|---|---|
| `TimeSyncCheck/sync_manifest.py` | byte-identical to `sync_manifest_interpolation.py` |
| `DataAcquisition/zed_record_dual.py` | both-eye recorder for V-LOAM, not used |
| `MATLAB_SensorFusionValidation/FlirLidarZedViewer_calib1.m`, `output/*.png` | first calibration; images |
| `EmissivityCalculation/test_images/`, `docs/img/` | images |
| `3DModelPointCloudExtraction/`, `PointCloudElaboration/` (except `livox_odometry_loader.py`), `MATLAB_PointCloudVisualization/` | out of scope (SLAM/loop closure, OpenStudio/EnergyPlus, U-values, openings, solar) |
| thesis `requirements.txt` / `.gitignore` files | rebuilt from the actual imports |
| `lvt2calib_adapted/data/calibration_result/`, `pattern_collection_result/` | run outputs / logs |
| `lvt2calib_adapted/data/camera_info/*_OLD_backup_20260802.yaml`, `template_pcl/*_ORIGINAL.pcd` | superseded backups |
| upstream LVT2Calib, koide3 `livox_to_pointcloud2` | not vendored, cloned per README |

## 4. Requirements: how they were built

Third-party imports were collected with `ast` over every `.py` file. Pins come
from `C:\venvs\emissivity` (heavy) and `C:\venvs\sensorfusion` /
`C:\venvs\extcalib` (light), all Python 3.13.14. They were tested in fresh
venvs: install, import every module, `--help` on every script.

- Light env: 50/51 modules import. The exception is `lidar_hole_check.py`,
  which needs open3d. All scripts' `--help` work except the two catkin nodes
  (`rospy`, container only).
- Heavy env: same. `ThermalData.py` needs `flyr`, which belongs to the light env.
- **Found by the test:** `torchvision` is never imported but is required at
  runtime by transformers' `AutoImageProcessor` (Mask2Former). It was added
  (`0.28.0`, the version in the working env).
- `open3d==0.19.0` has no Python 3.13 wheel. `lidar_hole_check.py` runs in a
  Python 3.12 env (verified in `C:\venvs\planefit`).
- `anthropic` was not installed in any working env, so it is unpinned.
- **Not verified:** a real model run. The Mask2Former/CLIP/SAM checkpoints are
  not cached on this machine, and `--check-only` stopped at the download.

## 5. Consistency check: code and config vs paper (v1)

Reported, **not fixed**.

### Matches

| Item | Paper | Code / config |
|---|---|---|
| ZED–LiDAR extrinsic | t = (−0.036, 0.126, 0.010), rpy = (−2.957, −1.521, −1.759) | `rig_calibration.yaml`: t = (−0.0360, 0.1258, 0.0100). ZYX of the same matrix: (−2.957, −1.521, −1.759). ✓ |
| FLIR–LiDAR extrinsic | t = (−0.114, 0.122, −0.004), rpy = (1.092, −1.532, 0.476) | t = (−0.1137, 0.1221, −0.0039), rpy = (1.092, −1.532, 0.476). ✓ |
| Extrinsic RMSE | 0.070 / 0.110 m | `rmse_3d_m` 0.0703 / 0.1101 ✓ |
| ZED intrinsics | 1412.34, 1414.47, 1012.85, 569.72; k1 −0.1558, k2 0.0090, p1 0.62e−3, p2 0.57e−3 | identical in both YAMLs ✓ |
| FLIR intrinsics | 570.48, 545.43, 149.15, 117.00; k1 −0.4241, k2 −0.1241, p1 −5.26e−3, p2 2.51e−3 | identical (but see the rounding note below) ✓ |
| Emissivity LUT | painted metal 0.94, glass 0.92, ceramic 0.92, oxidised Al 0.25 | `emissivity_table.csv` ✓ |
| Low-ε gate | ε < 0.5 needs conf ≥ 0.50 and margin ≥ 0.15 | defaults of `classify_session_m2f.py` / `classify_session_sam.py` ✓ |
| Voxel size | 20 cm | `voxel_consensus.py --voxel` default 0.20; consensus outputs record `voxel_m: 0.2` ✓ |
| RH, T_refl | 50 % assumed, T_refl ≈ T_air | `correction_report.json` of all three sessions ✓ |
| FLIR bias | 4.6 / 4.9 / 4.8 °C | `offset_report.json`: 4.644 / 4.863 / 4.804 ✓ |
| FLIR–ZED offset spread | std 0.009–0.011 s | manifests: 0.0112 / 0.0094 / 0.0109 s ✓ |
| ZED rate | ~27 Hz | fullrate frames / duration: 27.3 / 26.5 / 26.6 Hz ✓ |
| Benchmark | 228 regions, 4 excluded, 224 scored | `ground_truth_m2f.csv`: 228 rows, 224 labeled, 2 mixed, 2 unclear ✓ |
| FLIR frames A1 / A9 | 62 / 33 | 62 / 33 triplets ✓ |

### Mismatches and open points

1. **Radiance model (important).** The paper's Eq. 3–4 use the camera's Planck
   calibration (R1, R2, B, F, O from the metadata). `radiometric/radiance.py`
   implements S(T) ∝ T⁴ (Stefan–Boltzmann, temperatures in K), and
   `correct_session.py` uses that default. The paper equations and the code
   that produced the numbers differ.
2. **FLIR frames, aluminium session.** The paper's table says 44. The A10
   manifest and `Fllir/session_A10_rot180` have **117** frames/triplets. The 44
   may be a subset (e.g. frames with the plate in view), but nothing in the
   code or outputs selects 44.
3. **FLIR lens.** The paper says a 9 mm lens. `thermal_intrinsic.yaml` says
   "lente 8mm".
4. **FLIR FOV.** The paper says nominal 35° × 27°. The `rig_calibration.yaml`
   caveat says fx was validated against a "documented 32×26 deg FOV". The
   implied FOV from fx = 570.5 px over 336 px is 32.8°.
5. **FLIR distortion in the pipeline vs the paper/LVT2Calib.**
   `rig_calibration.yaml` (used by the pipeline) stores FLIR k1, k2, p1, p2
   rounded to 4 decimals (p1 = −0.0053, p2 = 0.0025). `thermal_intrinsic.yaml`
   and the paper use −5.26e−3 and 2.51e−3. The difference is small but not zero.
6. **Bias estimation method wording.** §IV-E presents the RTD comparison as "the
   proper way … as in our ground-truth sessions". In code, the bias is always
   estimated from T_air: the 10th percentile of wall/ceiling/column pixels for
   A1, a hand-picked wall ROI for A9/A10. The RTD only enters as a reported
   residual (0.03 / 1.32 / 1.82 °C).
7. **Extrinsic dates and pose labels in `rig_calibration.yaml`.** The
   `lidar_to_flir` block says 2026-09-14, but LVT2Calib's log has the 8-pose
   min2d solution on 2026-09-21. Its `tool` string lists poses
   "1,4,6,10,12,16,18,19 of 12 collected" (indices above 12). The values
   themselves match the paper.
8. **NI DAQ model.** The paper says USB-9162. The script is named `USB9126_…`.
9. **Board templates.** The PCDs used for the calibration (copied into
   `lvt2calib_patches/data/template_pcl/`) are 4-field (`x y z intensity`). The
   current `generate_board_template.py` writes 5 fields and warns that 4 fields
   may load misaligned in PCL. The points are identical.
10. **Euler angles.** Both pitches are ≈ −87.5° (−1.52 rad), close to the ZYX
    singularity. Roll and yaw are individually ill-conditioned there, and only
    their combination is well defined. The table is correct, but a reader
    recomputing the angles with another convention will get very different
    numbers.
11. **§IV-D (VLM)** is still a placeholder in the paper. The review CSV is not
    consumed by any later step, so the paper's numbers do not include a VLM pass.
12. A9 RTD: 22.9 °C (paper, `offset_report.json`) vs 22.95 °C (thesis notes).
