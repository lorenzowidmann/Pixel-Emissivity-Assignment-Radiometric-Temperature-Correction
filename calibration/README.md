# calibration/

Camera intrinsics and LiDAR–camera extrinsics (paper §III-B, Appendix A and B).

| Folder | What |
|---|---|
| [`intrinsic/`](intrinsic) | ZED 2i right eye and FLIR intrinsics: capture (Python, rover) and calibration (MATLAB). The OpenCV-format YAMLs that LVT2Calib reads. |
| [`extrinsic/`](extrinsic) | Everything around LVT2Calib: data conversion, pose checks and splitting, board templates, the patches to the upstream repo, and a MATLAB overlay viewer. |

The final numbers live in one file, [`../sensor_fusion/rig_calibration.yaml`](../sensor_fusion).
Every downstream script reads only that file. The full step-by-step walkthrough
is in the [root README](../README.md#calibration-walkthrough).
