# calibration/intrinsic/

Intrinsics of the ZED 2i **right** camera and of the FLIR Vue Pro R (paper
§III-B, Appendix A). Capture in Python, calibrate in MATLAB.

| File | What | Env |
|---|---|---|
| `capture_zed_right.py` | Grabs ZED right-eye frames on a keypress, with live preview and an optional "board visible" indicator. No ZED SDK: the camera is opened as a UVC webcam and the right half of the side-by-side frame is kept. | rover/any, `requirements-rover.txt` |
| `IntCalibration_ZED.m` | MATLAB calibration of the ZED images. | MATLAB + Computer Vision Toolbox |
| `IntCalibration_Flir.m` | Same for the FLIR images (checkerboard of bare aluminium + adhesive paper, 45 mm squares). The script does **not** rotate. Feed it frames already rotated 180° (e.g. with `../extrinsic/conversion/rotate_flir_poses.py`), as `rig_calibration.yaml` records `flir.rotated_180_before_calibration: true`. | MATLAB + Computer Vision Toolbox |
| `zed_right_intrinsic.yaml` | ZED result in OpenCV `FileStorage` format (`CameraMat`, `DistCoeff`, `ImageSize`), read by LVT2Calib. | — |
| `thermal_intrinsic.yaml` | FLIR result, same format. | — |

## `capture_zed_right.py`

**Output:** PNGs in `--out-dir` (default `ZedCaptures/` next to the script, git-ignored).

| Flag | Default / meaning |
|---|---|
| `--out-dir DIR` | `ZedCaptures/` |
| `--camera-index N` | 0 |
| `--resolution {1344x376,2560x720,3840x1080,4416x1242,driver}` | `4416x1242`. This is the side-by-side mode, so per-eye width is half. `3840x1080` gives 1920×1080 per eye, the resolution of the paper's calibration. |
| `--checkerboard-size COLS ROWS` | inner corners, only for the live indicator |
| `--detect-every N` | 5 |

Keys: `SPACE`/`ENTER` save, `u` delete the last saved frame, `q`/`ESC` quit.

```bash
python3 capture_zed_right.py --resolution 3840x1080 --checkerboard-size 8 6
```

## MATLAB scripts

Edit the top of each script, then run it:

- `folderPath`: the placeholder is `C:\path\to\ZedCaptures` / `C:\path\to\FlirCaptures`.
  ZED reads `*.png`, FLIR reads `*.jpg`.
- `squareSize`: 25 mm (ZED) and 45 mm (FLIR). Measure the printed board.

The model is skew-free pinhole with radial (k1, k2) and tangential (p1, p2)
distortion. A second skew-estimating fit is printed for comparison only.
Nothing is saved to file. Results are printed to the console:
- K, distortion and the mean reprojection error;
- dropped and partial boards;
- per-image error ranking with suggested outliers;
- principal point vs centre;
- implied FOV;
- corner-coverage plot.

Copy the printed values into the two YAMLs here **and** into the `zed:`/`flir:`
blocks of `../../sensor_fusion/rig_calibration.yaml`.

## Values used in the paper (Appendix A)

| | ZED 2i (right) | FLIR |
|---|---|---|
| Resolution | 1920×1080 | 336×256 |
| fx, fy | 1412.3362, 1414.4716 | 570.4796, 545.4275 |
| cx, cy | 1012.8503, 569.7181 | 149.1501, 117.0047 |
| k1, k2, p1, p2 | −0.1558, 0.0090, 6.21e−4, 5.67e−4 | −0.4241, −0.1241, −5.26e−3, 2.51e−3 |
| Images / mean reprojection error | 25 / 0.2151 px | 28 / 0.1395 px |

The YAMLs carry Italian comments from the original calibration notes. They are
kept verbatim.
