# calibration/extrinsic/conversion/

Gets the raw recordings into a form LVT2Calib, and the rest of the pipeline,
can use. Host-side, light env (`../requirements.txt`).

## `convert_livox_bag.py`: ROS 2 → ROS 1 bag

The HAP driver writes a ROS 2 bag with `livox_ros_driver2/msg/CustomMsg`.
LVT2Calib runs on ROS 1 Noetic, and koide3's `livox_to_pointcloud2` (ROS 1
branch) expects `livox_ros_driver/msg/CustomMsg`. The script registers the
CustomMsg type with `rosbags` and rewrites the namespace. The fields are
identical, so only the namespace changes.

**Input:** `--src` ROS 2 bag folder (`metadata.yaml` + `.db3`).
**Output:** `--dst` ROS 1 `.bag`. It does **not** convert to PointCloud2. Do
that in the container with `rosrun livox_to_pointcloud2 livox_to_pointcloud2_node`.

| Flag | Default |
|---|---|
| `--src SRC`, `--dst DST` | required |
| `--src-namespace` | `livox_ros_driver2` |
| `--ros1-namespace` | `livox_ros_driver` |
| `--topics TOPIC ...` | all. `--topics /livox/lidar` is enough for calibration and much faster. |

```powershell
py convert_livox_bag.py --src C:\path\to\rosbag2_2026_09_10-16_38_14 --dst C:\path\to\calib_ros1.bag --topics /livox/lidar
```

## `rotate_flir_poses.py`: 180° rotation of FLIR frames

The FLIR is mounted upside down, and the LiDAR↔FLIR extrinsic was estimated on
rotated images. Originals are never touched. Output goes to a sibling folder
`<dir><suffix>` with the same file names.

| Flag | Meaning |
|---|---|
| `--poses-root DIR` / `--pose-dir DIR` | many `pose_XX/` folders, or a single folder (mutually exclusive) |
| `--suffix` | output folder suffix, default `_rot180` |
| `--npy` | also write `<name>.npy`: the apparent-temperature map in °C (read with `flyr`), rotated |
| `--dry-run` | show, write nothing |

The rotated JPEG loses the embedded radiometric EXIF block (OpenCV does not keep
it). That is fine for LVT2Calib, which only uses the palette image. **For the
main pipeline use `--npy`**: the `*_rot180/*.npy` frames are the `--flir-dir`
input of `../../../radiometric_correction/correct_session.py` and
`../../../emissivity/prepare_voxel_comparison.py`.

```powershell
py rotate_flir_poses.py --pose-dir D:\GroundTruthFiles\Dati\Fllir\session_A1 --npy   # -> session_A1_rot180\
```
