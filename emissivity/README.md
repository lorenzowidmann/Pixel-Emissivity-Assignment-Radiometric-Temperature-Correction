# emissivity/

Per-pixel emissivity (paper §IV-A, §IV-C). Each region of the ZED frame gets a
material from `emissivity_table.csv`. The material map is then moved onto the
FLIR pixel grid **through the LiDAR**: there is no direct FLIR↔ZED calibration.
Each LiDAR point visible in both cameras reads its material on the ZED side and
writes it at its own FLIR pixel, together with its distance.

## Two segmentation methods, one folder each

Both segment the ZED frame into regions and give each region a material with
the same CLIP classifier and the same `emissivity_table.csv`. Only the
segmenter, and therefore the prior, differs. Both write the same
`material_map/v1` format, so everything downstream works with either.

| Folder | Script | Segmenter | Prior on CLIP's materials | Output folder | Status |
|---|---|---|---|---|---|
| [`mask2former/`](mask2former) | `classify_session_m2f.py` | **Mask2Former** (ADE20K semantic classes) | category prior from the ADE class (`ade_material_prior.csv`) | `<session>/material_map_m2f/` | **Used in the paper** (§IV-A) |
| [`sam/`](sam) | `classify_session_sam.py` | **SAM** (Segment Anything; SLIC available too) | geometric zone prior from the region's bbox shape | `<session>/material_map/` | Tested alternative, **not used** (§IV-A: SAM regions too small for CLIP) |

Both apply the low-ε gate (ε < 0.5 needs confidence ≥ 0.50 and margin ≥ 0.15).

## Everything else in this folder

| Path | What | Env |
|---|---|---|
| [`mask2former/external_vlm/`](mask2former/external_vlm) | Optional VLM re-review of low-confidence regions of a Mask2Former run | heavy (+ VLM reqs) |
| [`ground_truth/`](ground_truth) | Hand labels and scoring (§IV-B benchmark): `ground_truth_m2f.csv` (Mask2Former), `ground_truth_sam.csv` (SAM) | light |
| `emissivity/` (package) | **Shared library** used by both methods, not a third method: `table.py` (CSV loader), `classifier.py` (CLIP zero-shot, lazy torch import), `segmentation.py` (the SAM and SLIC segmenters used by `sam/`), `zones.py` (geometric prior), `sources.py` (live-camera grabbers, no current caller) | — |
| `emissivity_table.csv` | 20 materials: `material, emissivity, emissivity_range, solar_absorptance, solar_absorptance_range, prompt, notes`. The CLIP classes are generated from it. Shared by both methods. | — |
| `project_to_flir.py` | Material map (ZED) → FLIR pixels via LiDAR, plus per-pixel distance | light |
| `voxel_consensus.py` | `--stage vote`: multi-view material vote per 20 cm voxel. `--stage thermal`: 3-D voxel map of a per-pixel temperature map. | light |
| `prepare_voxel_comparison.py` | Writes the "before" and "emissivity-only" maps that `--stage thermal` voxelises for the before/after table | light |

All scripts take `--session-dir` = the ZED session's **`fullrate/`** folder,
which holds `sync_manifest.json` (from `../synchronization/`). With the SAM
output, pass `--material-map-dir <session>/material_map` to the later steps;
with the paper's Mask2Former output, pass `<session>/material_map_m2f`.

## `project_to_flir.py`

**Inputs:**
- `--session-dir`;
- `--bag` (ROS 2 bag with `/cloud_registered`, or with `--raw-lidar`: `/livox/lidar` + `/Odometry`);
- `--material-map-dir` (default `<session>/material_map`; for the paper use `material_map_m2f`);
- `--calibration` (default `../sensor_fusion/rig_calibration.yaml`).

**Output:** `--out-dir` (default `<session>/emissivity_map`) / `<flir_stem>/`:

| File | Content |
|---|---|
| `emissivity.npy` | float32 336×256 per-pixel ε |
| `distance.npy` | float32, metres |
| `segment_id.npy` | ZED region id per FLIR pixel |
| `sampled_mask.npy` | direct LiDAR hit vs nearest-neighbour fill |
| `stats.json` | coverage etc. |
| `overlay.png` | with `--overlay` |

Other flags: `--odom-topic` (the cloud topic read), `--store`, `--every-n`,
`--limit`, `--raw-lidar`.

> **Keep the default `--out-dir`.** `../radiometric_correction/correct_session.py`
> and `estimate_offset.py` only look in `<session>/emissivity_map/`.

```powershell
C:\venvs\sensorfusion\Scripts\python.exe project_to_flir.py --session-dir $S --bag $B --material-map-dir $S\material_map_m2f --overlay
```

## `voxel_consensus.py`

| Stage | Reads | Writes (default `--out-dir`) |
|---|---|---|
| `vote` (after `project_to_flir.py`) | per-frame map in `--material-map-dir` (default `<session>/material_map`; for the paper `material_map_m2f`) + the LiDAR bag | `<session>/material_map_consensus/<stem>/` (`labels.npy` copied, `segments.json` with the consensus material) |
| `thermal` (after correction) | `--emissivity-map-dir` (default `emissivity_map`)`/<stem>/<--corrected-name>` + `--material-map-dir` (default `material_map_consensus`) | `<session>/voxel_map/thermal_voxels.csv` (`x,y,z,t_mean_c,t_std_c,n_obs,material,solar_absorptance`) and `thermal_voxels.ply` |

| Flag | Default |
|---|---|
| `--voxel` | **0.20 m** (paper) |
| `--respect-zones` | on |
| `--min-emissivity` | 0.5 |
| `--min-agreement` | 0.0 |
| `--min-vote-confidence` | 0.5 |
| `--depth-power` | 0.0 |
| `--corrected-name` | `corrected_temperature.npy` |
| `--calibration`, `--odom-topic`, `--store`, `--every-n`, `--limit` | |

```powershell
& $L voxel_consensus.py --stage vote --session-dir $S --bag $B --voxel 0.20 --material-map-dir $S\material_map_m2f
& $L voxel_consensus.py --stage thermal --session-dir $S --bag $B --voxel 0.20 --corrected-name corrected_temperature_debiased.npy --out-dir $S\voxel_map
```

## `prepare_voxel_comparison.py`

**Inputs:**
- `--session-dir`;
- `--flir-dir` (rot180 `.npy`);
- `--emissivity-map-dir` (default `<session>/emissivity_map`);
- `--corrected-name` (default `corrected_temperature.npy`);
- `--overwrite`.

**Writes**, into each `emissivity_map/<stem>/`:
- `apparent_temperature_masked.npy`: apparent T, NaN where the corrected map is NaN;
- `emissivity_correction.npy`: corrected minus apparent, i.e. the correction
  without the bias.

Use them with `voxel_consensus.py --stage thermal --corrected-name ...`, then
`../radiometric_correction/matlab/VoxelCorrectionTable.m`.

## Adding a material

Add a row to `emissivity_table.csv`. The `prompt` describes how the material
*looks*, at object level ("a photo of a painted metal radiator…"). No retraining
is needed. If you use the Mask2Former prior, also list the material in
`mask2former/ade_material_prior.csv` and run `--check-only`.

No viewing-angle correction: tabulated normal emissivity only (paper §IV-C).
