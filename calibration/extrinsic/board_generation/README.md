# calibration/extrinsic/board_generation/

PCD templates of the **real** calibration board for LVT2Calib's LiDAR board
matching. They replace upstream's stock board. The board is 100 × 70 cm with
four circular holes of ⌀13 cm (radius 0.065 m), centred at (±0.15, ±0.15) m.

| File | What |
|---|---|
| `generate_board_template.py` | Writes `four_circle_boundary.pcd` (outer rectangle + 4 circles; LVT2Calib's `model_path`, used by PCA + ICP in `isCalibBoard()`) and `four_circle_dense.pcd` (filled surface with holes). Python stdlib only. |
| `TragetHoles.STEP` | CAD of the **hole insert**, the piece fitted into each cut hole to make it a true ⌀13 cm circle. It is not the whole board. (The filename typo is kept from the thesis.) |

| Flag | Default |
|---|---|
| `--outdir` | required |
| `--board-width` | 1.0 m |
| `--board-height` | 0.7 m |
| `--hole-diameter` | 0.13 m (measure with callipers after cutting) |
| `--hole-offset` | 0.15 m |
| `--boundary-spacing` | 0.004 m |
| `--dense-spacing` | 0.004 m |

```powershell
py generate_board_template.py --outdir out_pcd
```

The run also prints the matching `circle_radius` / `centroid_dis_*` values for
`config/lidar_pattern_param.yaml`. The patched file uses `circle_radius 0.065`,
`centroid_dis_min 0.15` and `centroid_dis_max 0.28` (the script suggests 0.27).

## Which templates were used

The templates in `../lvt2calib_patches/data/template_pcl/` are the files that
were in the LVT2Calib install used for the paper calibration (dated
2026-07-29). Their points are **identical** to what this script generates, but
they use the **4-field** PCD schema `x y z intensity`. The current script writes
5 fields (`x y z intensity range`, like upstream's original). Its docstring
warns that the 4-field version can load misaligned in `pcl::io::loadPCDFile`.
The overlay ships the files **as used**. Whether to regenerate them with this
script is your decision (see the extraction report).
