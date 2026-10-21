# radiometric_correction/matlab/

MATLAB viewers and the before/after table for the validation sessions (paper
§V). They only read outputs of the Python pipeline. Every default path is a
placeholder (`C:\path\to\data\AcquistionGroundTruth\...`) to edit, or pass the
paths as arguments.

| File | Input | Output |
|---|---|---|
| `ShowTemperatureCorrection.m` `(sessionDirIn, flirDirIn)` | session `fullrate/` (`emissivity_map/`, consensus materials) + rot180 FLIR folder | Interactive figure: apparent vs corrected on one colour scale, plus ΔT. Hovering shows ε, distance, consensus material and direct-vs-filled LiDAR. Arrow/PgUp/PgDn/Home/End move between frames; `c` locks the reading, `s` shows LiDAR samples, `b` shows boundaries. Source of the "apparent vs corrected" figures. |
| `VoxelCorrectionTable.m` `(beforeCsv, afterCsv, opts)` | `voxel_map_before/thermal_voxels.csv`, `voxel_map_after_check/thermal_voxels.csv`; options `EmissivityOnlyCsv`, `ReferenceC` (RTD), `Roi [xmin xmax ymin ymax zmin zmax]`, `OutputCsv` | Max/mean/min of `t_mean_c` per case, printed, saved to `voxel_correction_table.csv` next to `beforeCsv`, and printed as a LaTeX `booktabs` table (`siunitx`) |
| `ViewThermalPLY.m` | `plyPath` to `voxel_map*/thermal_voxels.ply` | 3-D view of the voxel map (temperature baked into RGB). Source of the voxel figure. |

With no arguments, the defaults are:
- `ShowTemperatureCorrection`: session A9 (glass);
- `VoxelCorrectionTable`: A1 (painted metal, 22.19 °C);
- `ViewThermalPLY`: A10.

Requirements:
- `ShowTemperatureCorrection.m` calls `readNPY`, which is **not** in this
  repository or in MATLAB. It comes from [npy-matlab](https://github.com/kwikteam/npy-matlab),
  which must be on the MATLAB path.
- `ViewThermalPLY.m` uses `pcread`/`pcshow` (Computer Vision Toolbox).
- The exact toolbox list was not verified (TODO).

```matlab
d = 'D:\GroundTruthFiles\Dati\Zed\20260911_094055\fullrate';
VoxelCorrectionTable(fullfile(d,'voxel_map_before','thermal_voxels.csv'), ...
    fullfile(d,'voxel_map_after_check','thermal_voxels.csv'), ...
    'EmissivityOnlyCsv', fullfile(d,'voxel_map_emis_corr','thermal_voxels.csv'), ...
    'ReferenceC', 22.19)
```

The ROI around the RTD used for the paper tables was not recorded (TODO).
