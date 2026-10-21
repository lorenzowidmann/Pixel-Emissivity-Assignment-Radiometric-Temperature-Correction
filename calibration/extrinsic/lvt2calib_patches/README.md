# calibration/extrinsic/lvt2calib_patches/

Only the files that were **added or modified** relative to upstream
[LVT2Calib](https://github.com/Clothooo/lvt2calib) to run it with this rig
(Livox HAP, ZED 2i right eye, FLIR Vue Pro R, our 100×70 cm board). Upstream
itself is not vendored.

**Upstream base:** branch `ros_noetic`, commit
**`9dd3defcc2b3486dba862b6060e2e0dd65407213`** (2026-03-25, *fix(build): add
robosense_pattern and transform_point_cloud targets*). Every other upstream
file, including `docker/`, is unchanged in the setup that produced the paper's
calibration.

| Path (same as upstream) | Status | Why |
|---|---|---|
| `launch/lidar/livox/livox_hap_pattern.launch` | **added** | HAP is not supported upstream (only Horizon, Mid-70, Mid-40, Avia). Horizon-style wrapper with `ns_=livox_hap` and `cloud_tp=/livox/points` (PointCloud2 from `livox_to_pointcloud2`). Forwards `px/py/pz_min/max`. `acc_num` defaults to 3 (see the comment in the file). |
| `launch/lidar/livox_pattern.launch` | **modified** | Adds the `px_min…pz_max` args (upstream fails with "unused args" when the HAP wrapper passes them) and a Z passthrough that removes the stand below the board. `use_gauss_filter` and `use_i_filter` set to `false`. |
| `config/lidar_pattern_param.yaml` | **modified** | Board geometry: `circle_radius 0.065` (⌀13 cm holes), `centroid_dis_max 0.28`. |
| `rviz/livox_hap_pattern.rviz` | **added** | `livox_pattern.launch` loads `rviz/$(arg ns_)_pattern.rviz`. Copy of the Horizon config with the three topics renamed to `/livox_hap/...`. |
| `data/template_pcl/four_circle_boundary.pcd`, `four_circle_dense.pcd` | **modified** | Templates of the real board (see `../board_generation/README.md` about the 4- vs 5-field schema). |
| `catkin_ws_src/zed_frame_publisher/` | **added** (separate catkin package, goes in `catkin_ws/src/`, not inside `lvt2calib/`) | Publishes recorded ZED PNG sessions as `sensor_msgs/Image` (`/zed_right/image_raw`). |
| `catkin_ws_src/flir_frame_publisher/` | **added** (same) | Publishes FLIR RJPG frames as `sensor_msgs/Image` (`/thermal_cam/thermal_image`). |

Also needed, but stored elsewhere in this repository: the camera intrinsics
`../../intrinsic/zed_right_intrinsic.yaml` and `thermal_intrinsic.yaml`. They go
into `data/camera_info/`.

Not included, on purpose: LVT2Calib's run outputs (`data/calibration_result/`,
`data/pattern_collection_result/`), backups of the original templates and of
older intrinsics.

## 1. Clone and overlay

PowerShell (host):

```powershell
git clone https://github.com/Clothooo/lvt2calib.git C:\ws\catkin_ws\src\lvt2calib
git -C C:\ws\catkin_ws\src\lvt2calib checkout 9dd3defcc2b3486dba862b6060e2e0dd65407213
$P = "<this repo>\calibration\extrinsic\lvt2calib_patches"
Copy-Item -Recurse -Force "$P\launch","$P\config","$P\rviz","$P\data" C:\ws\catkin_ws\src\lvt2calib\
Copy-Item "<this repo>\calibration\intrinsic\*.yaml" C:\ws\catkin_ws\src\lvt2calib\data\camera_info\
Copy-Item -Recurse "$P\catkin_ws_src\*" C:\ws\catkin_ws\src\
git clone https://github.com/koide3/livox_to_pointcloud2.git C:\ws\catkin_ws\src\livox_to_pointcloud2
#   (ROS 1 branch: TODO record the branch/commit that was used. It also needs the
#    livox_ros_driver (v1) CustomMsg definition in the workspace: TODO verify.)
```

## 2. Docker image (upstream Dockerfile, unchanged)

```powershell
cd C:\ws\catkin_ws\src\lvt2calib\docker
docker build --network=host -t lvt2calib:noetic .
```

## 3. Run the container on Windows with VcXsrv

Start **VcXsrv** (XLaunch: *Multiple windows*, *Disable access control*), then:

```powershell
docker run -it --name lvt2calib_gui `
  -e DISPLAY=host.docker.internal:0.0 -e QT_X11_NO_MITSHM=1 `
  -v C:\ws\catkin_ws\src:/home/catkin_ws/src `
  -v C:\path\to\bags:/data/bags `
  lvt2calib:noetic
```

**TODO: verify.** The original `lvt2calib_gui` run command was not saved. What
is known from the thesis notes: the container name is `lvt2calib_gui`, the
workspace is `/home/catkin_ws`, and the host bag folder is mounted at
`/data/bags`. `DISPLAY=host.docker.internal:0.0` is the usual VcXsrv setting.
Upstream's Linux script is `docker/priv_run.sh` (`--network=host --privileged`,
X11 socket).

The workspace was built with **`catkin_make`**, the same tool the image's entrypoint runs at every
start. If the packages were copied in later, build by hand:

```bash
cd /home/catkin_ws && catkin_make && source devel/setup.zsh
```

Do not use `catkin build` in this workspace: `catkin_make` and `catkin build`
cannot be mixed. The publishers' own READMEs still mention `catkin build`.

## 4. Calibrate (inside the container, one terminal each)

The LVT2Calib README says to run `roscore` first.

```bash
# LiDAR: replay a pose and convert to PointCloud2
rosbag play /data/bags/<pose>.bag                                   # from convert_livox_bag.py
rosrun livox_to_pointcloud2 livox_to_pointcloud2_node               # /livox/lidar -> /livox/points
roslaunch lvt2calib livox_hap_pattern.launch use_passthrough_preprocess:=true \
    px_min:=3.0 px_max:=6.5 py_min:=-1.5 py_max:=1.5 pz_min:=0.0 pz_max:=1.2   # per pose: find_board_limits.py

# ZED (RGB)
rosrun zed_frame_publisher zed_frame_publisher.py --session-dir /data/bags/zed_poses/pose_01_filled --loop
roslaunch lvt2calib rgb_cam_pattern.launch image_tp:=/zed_right/image_raw \
    cam_info_filename:=zed_right_intrinsic.yaml isDarkBoard:=true          # black board, light holes
roslaunch lvt2calib pattern_collection_lc.launch ns_l:=livox_hap ns_c:=rgb

# FLIR (thermal)
rosrun flir_frame_publisher flir_frame_publisher.py --image-dir /data/bags/flir_poses/pose_01_rot180 --image-mode embedded --loop
roslaunch lvt2calib thermal_cam_pattern.launch cam_info_filename:=thermal_intrinsic.yaml
roslaunch lvt2calib pattern_collection_lc.launch ns_l:=livox_hap ns_c:=thermal

# Solve, after collecting all poses
roslaunch lvt2calib extrinsic_calib_l2c.launch ns_l:=livox_hap ns_c:=rgb     cam_info_filename:=zed_right_intrinsic.yaml
roslaunch lvt2calib extrinsic_calib_l2c.launch ns_l:=livox_hap ns_c:=thermal cam_info_filename:=thermal_intrinsic.yaml
```

The namespaces match the result files of the paper calibration:
`features_info_livox_hap_to_{rgb,thermal}.csv` and
`livox_hap_to_{rgb,thermal}_exParam_{min2d,min3d}.csv`. Results go to
`data/calibration_result/`. The paper uses **min2d**. Copy the 4×4 matrix into
`../../../sensor_fusion/rig_calibration.yaml`.

Exact per-pose passthrough bounds, the order in which poses were replayed, and
whether FLIR frames were published with `--image-mode embedded` or `raw` were
not recorded (TODO). The publishers' own READMEs (`catkin_ws_src/*/README.md`)
are copied from the thesis. They mention old folder names (`SensorFusion/`,
`Thesis/Calibration/`). The intrinsics are now in `calibration/intrinsic/`.

## Licence

LVT2Calib's `package.xml` declares **GPLv2** (no LICENSE file in the repository).
The two modified files and the derived HAP launch/rviz are derivative works of
GPLv2 files.
