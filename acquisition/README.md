# acquisition/

Sensor recording (paper §III-A) and the first post-processing step of the ZED
stream. RTD ground truth is in [`rtd_reading/`](rtd_reading).

| File | Runs on | Env |
|---|---|---|
| `zed_record.py` | rover (Ubuntu NUC) | `requirements-rover.txt` (+ ZED SDK `pyzed` for `--backend sdk`) |
| `extract_fullrate_frames.py` | host | `requirements.txt` (opencv) + `ffprobe` on PATH |
| `qos.yaml` | rover, `ros2 bag record` | — |

## `zed_record.py`: ZED 2i recorder

**Input:** the camera. Backends: `--backend sdk` (ZED SDK/pyzed, CUDA GPU,
writes SVO2), `uvc` (plain OpenCV webcam, RGB only), and `auto` (default: sdk,
falling back to uvc).

**Output:** `<--output-dir>/<UTC YYYYmmdd_HHMMSS>/` (default `--output-dir` is
`recordings/` next to the script), containing:
- `session.svo2` (sdk only);
- `session_<eye>.mp4`;
- `frames/<eye>_NNNNNN.png`;
- `metadata.json` (schema `zed_record/v1`: settings, `started_utc`, per-frame
  `t_offset_s`).

Key flags (all in `--help`):

| Flag | Default |
|---|---|
| `--resolution {HD2K,HD1080,HD720,VGA}` | `HD1080` (**must match the intrinsics: 1920×1080**) |
| `--fps` | 30 |
| `--eye {left,right}` | `right` |
| `--frame-interval SEC` | `0.0` = dump every frame |
| `--duration SEC` | record until Ctrl+C |
| `--camera-index`, `--svo-compression`, `--no-mp4`, `--no-frames`, `--session-name` | |

```bash
python3 zed_record.py --backend uvc --resolution HD1080 --frame-interval 0.4
```

## `extract_fullrate_frames.py`: every mp4 frame

**Input:** `--session-dir` = a `zed_record.py` session (`metadata.json` +
`session_right.mp4`).

**Output:** `<session>/fullrate/frames/*.png` + `fullrate/metadata.json`.
Timestamps are a **uniform grid** at the fps measured with `ffprobe
-count_frames`. Always follow with
`../synchronization/retime_fullrate_frames.py`.

```powershell
py extract_fullrate_frames.py --session-dir D:\GroundTruthFiles\Dati\Zed\20260911_094055
```

## Recording a session (LiDAR + ZED + FLIR)

From the thesis protocol, used for the ground-truth sessions.

1. **FLIR**: power on and start its SD-card recording **first**, and stop it last.
2. **T1, LiDAR driver**: `sudo ifconfig enp89s0 192.168.1.50`, then
   `ros2 launch livox_ros_driver2 msg_HAP_launch.py`.
3. **T2, FAST-LIO**: `ros2 launch fast_lio mapping.launch.py config_file:=haplidar.yaml`
   (provides `/cloud_registered` and `/Odometry`, which the pipeline reads).
4. **T3, bag**:
   `ros2 bag record --qos-profile-overrides-path qos.yaml /cloud_registered /Odometry /livox/lidar /livox/imu`.
   `qos.yaml` (best-effort reliability for `/livox/lidar` and `/livox/imu`) is
   **mandatory**. With the default RELIABLE profile the bag silently comes out empty.
5. **T4, monitor**: keep `ros2 topic hz /livox/lidar` open the whole time (~4.7 Hz).
   `ros2 bag record` keeps recording silence if the driver dies.
6. **T5, ZED**: `python3 zed_record.py --backend uvc --resolution HD1080 --frame-interval 0.4`.
7. **Sync event**: hold a bare aluminium plate in front of the rig so that it
   appears in all three streams (§III-B). It is used by `../synchronization/`.

Stop in reverse order: T5, T3, T4, T2, T1, then the FLIR. Check `ros2 bag info`
and copy with `rsync`.

The FAST-LIO configuration (`haplidar.yaml`) and the ROS 2 workspace are not
part of this repository (TODO).
