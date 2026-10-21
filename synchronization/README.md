# synchronization/

Time alignment of the three streams (paper §III-B). LiDAR and ZED share the
rover PC clock (offset taken as 0). The FLIR records on its own clock, so its
offset is found from a common event: a bare aluminium plate held in front of
the rig, picked in the FLIR and in the ZED. The FLIR frames drive the output.
Each FLIR frame becomes one **triplet** (FLIR file, nearest ZED frame, LiDAR
pose). Light env (`requirements.txt`).

| Script | What |
|---|---|
| `retime_fullrate_frames.py` | **Pre-step.** Re-timestamps `fullrate/` frames (from `../acquisition/extract_fullrate_frames.py`, uniform grid) using the real `t_offset_s` of the recorder's subsampled PNGs as anchors (NCC match to mp4 frames, interpolation in between). |
| `sync_manifest_interpolation.py` | Triplet manifest; the LiDAR pose is **interpolated** onto the FLIR time (linear position + SLERP). **Used for all three paper sessions** (their manifests carry `"pose_source": "interpolated"`). |
| `sync_manifest_neighbour.py` | Same, but takes the **nearest** `/Odometry` sample. Kept for comparison: at FLIR 1 Hz and odometry 5 Hz the nearest-sample lag is a constant, not random, error. |

The thesis repo also had `sync_manifest.py`, byte-identical to
`sync_manifest_interpolation.py`. It is not copied. Manifests still say
`"generated_by": "sync_manifest.py"`.

## `retime_fullrate_frames.py`

**Input:** `--session-dir` = the zed_record.py session (with `metadata.json`,
`session_right.mp4`, `fullrate/`).

**Output (with `--apply`):** rewrites `fullrate/metadata.json` and backs up the
old one as `fullrate/metadata.uniform.json`. Without `--apply` it is a dry run.

Flag: `--search-window N` (default 90 mp4 frames ≈ 3.3 s).

```powershell
py retime_fullrate_frames.py --session-dir D:\GroundTruthFiles\Dati\Zed\20260911_094055 --apply
```

After retiming, regenerate the manifest with `--recompute-offset`.

## `sync_manifest_interpolation.py` / `sync_manifest_neighbour.py`

Stage 1 is the FLIR↔ZED event offset. An interactive viewer picks the event
frame in each stream (or pass `--flir-event-frame N --zed-event-frame N`). The
result is saved to `<session-dir>/flir_zed_offset.json` and reused unless
`--recompute-offset` is given.

Stage 2 is the manifest: for every FLIR `*_R.jpg`, the nearest ZED frame and
the LiDAR pose from `--odom-topic`, on the ZED clock. Triplets with any
pairwise delta > `--max-delta` are flagged `low-confidence`.

| Flag | Default |
|---|---|
| `--session-dir DIR` | required; use the `fullrate/` folder (manifest and offset are written there) |
| `--flir-dir DIR` | required; FLIR `*_R.jpg` folder (read with `flyr`) |
| `--bag DIR` | required; ROS 2 bag with `/Odometry` |
| `--odom-topic` | `/Odometry` |
| `--store` | `ROS2_HUMBLE` |
| `--max-delta` | 0.1 s |
| `--lidar-zed-offset` | 0.0 s (shared host clock; the paper verified it against the system clock) |
| `--recompute-offset` | off |
| `--flir-event-frame`, `--zed-event-frame` | — |
| `--output-format` | `json` |
| `--output` | `sync_manifest.json` |

**Outputs** (in `--session-dir`):
- `sync_manifest.json`: schema `sync_manifest/v1`, one triplet per FLIR frame
  with files, timestamps, LiDAR pose, deltas and `match_status`;
- `flir_zed_offset.json`: schema `flir_zed_offset/v1`.

```powershell
py sync_manifest_interpolation.py --session-dir D:\GroundTruthFiles\Dati\Zed\20260911_094055\fullrate `
   --flir-dir D:\GroundTruthFiles\Dati\Fllir\session_A1_rot180 --bag D:\GroundTruthFiles\Dati\Lidar\rosbag2_2026_09_11-11_40_48
```

The manifests record their inputs (`inputs.flir_dir`). A1 and A9 were built
from the **raw** FLIR folders (`session_A1`, `session_A9`) and A10 from
`session_125010_rot180`. `GroundTruthFiles` contains only the `_rot180` folders.
They hold the same `*_R.jpg` file names, which is what the manifest stores.
