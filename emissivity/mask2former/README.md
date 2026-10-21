# emissivity/mask2former/

**The classifier used in the paper** (§IV-A, Fig. "material flow"). Heavy env
(`requirements.txt`, which includes `../requirements.txt`).

1. **Object segmentation.** One Mask2Former forward pass
   (`facebook/mask2former-swin-large-ade-semantic`, ADE20K-150). Only the part
   of the ZED frame the FLIR can see is segmented (`--crop-to-flir-fov`, via
   `../../sensor_fusion/`).
2. **Object class per region.** The ADE label of each connected region (`--min-area` 1500 px).
3. **CLIP scores** on the region crop (`--crop-mode bbox`) against every
   material of `../emissivity_table.csv` (`--clip-model`, default
   `laion/CLIP-ViT-H-14-laion2B-s32B-b79K`).
4. **Prior gate.** `ade_material_prior.csv` keeps only the materials plausible
   for that ADE class and renormalises the scores (`--category-prior`, on). No
   group allows a bare metal.
5. **Low-ε gate.** A material with ε < 0.5 is accepted only if confidence ≥ 0.50
   **and** its margin over the runner-up ≥ 0.15. Otherwise the best candidate
   above the threshold is used.
6. The material's emissivity is assigned to every pixel of the region.

The CLIP classifier, the table and the gate function are imported from
`../emissivity/` (shared with the SAM alternative, `../sam/classify_session_sam.py`), not copied.

## Usage

```powershell
C:\venvs\emissivity\Scripts\python.exe classify_session_m2f.py --session-dir $S --overlay
C:\venvs\emissivity\Scripts\python.exe classify_session_m2f.py --session-dir $S --every-n 5 --limit 20     # benchmark frame set
C:\venvs\emissivity\Scripts\python.exe classify_session_m2f.py --session-dir . --check-only              # validate a prior-table edit
C:\venvs\emissivity\Scripts\python.exe classify_session_m2f.py --session-dir $S --no-gating             # aluminium "no gate" run (§V)
C:\venvs\emissivity\Scripts\python.exe classify_session_m2f.py --session-dir $S --no-category-prior --out-dir $S\material_map_m2f_noprior   # §IV-B prior OFF
```

**Input:** `--session-dir` = ZED `fullrate/` with `metadata.json`, `frames/`, `sync_manifest.json`.

**Output:** `--out-dir` (default `<session>/material_map_m2f`) / `<flir_stem>/`:

| File | Content |
|---|---|
| `labels.npy` | int32 region-id raster on the full ZED grid; −1 outside the crop or below `--min-area` |
| `segments.json` | schema `material_map/v1`: per region `ade`, `ade_confidence`, ranked materials + `confidence`, `emissivity`, `prior`/`gated` blocks, `zone` |
| `overlay.png` | with `--overlay`: contours labelled `<ade> -> <material> e=<ε>`. Orange marks a region the prior changed, red one the gate changed. |

| Flag | Default |
|---|---|
| `--model REPO` | `facebook/mask2former-swin-large-ade-semantic` |
| `--min-area PX` | 1500 |
| `--crop-mode {bbox,masked,texture}` | `bbox` |
| `--category-prior / --no-category-prior` | on |
| `--prior-table CSV` | `ade_material_prior.csv` |
| `--crop-to-flir-fov / --no-...` | on |
| `--fov-margin-px` | 45 |
| `--calibration` | `../../sensor_fusion/rig_calibration.yaml` |
| `--top-k` | 3 |
| `--table` | `../emissivity_table.csv` |
| `--low-emissivity-max` | **0.5** |
| `--low-emissivity-min-conf` | **0.50** |
| `--low-emissivity-min-margin` | **0.15** |
| `--no-gating` | off |
| `--clip-model` | `laion/CLIP-ViT-H-14-laion2B-s32B-b79K` |
| `--every-n`, `--limit`, `--overlay`, `--check-only` | |

Cost on CPU: about 5 s/frame for Mask2Former plus about 2 s per region for CLIP
ViT-H/14. The checkpoints are about 850 MB and 3.9 GB, downloaded on first use.

## `ade_material_prior.csv`

Columns:
- `group`: echoed as `prior_group`;
- `ade`: `;`-separated ADE labels, matched on the first comma synonym;
- `zone`: `floor|ceiling|vertical|any`. It must be a subset of
  `../emissivity/zones.py` for `voxel_consensus.py`;
- `materials`: `;`-separated names from `../emissivity_table.csv`;
- `notes`.

19 groups cover 119 of the 150 ADE classes. Unmapped classes fall back to the
emissivity floor only. `--check-only` fails loudly on:
- unknown materials or ADE labels;
- duplicate ADE claims;
- an unknown zone;
- empty lists.

## `m2f_materials/` (package)

| Module | What |
|---|---|
| `segmentation_m2f.py` | loads the checkpoint (`AutoImageProcessor` + `Mask2FormerForUniversalSegmentation`; **needs torchvision at runtime**) and returns regions, ADE label and confidence |
| `category_prior.py` | reads and validates the CSV, restricts and renormalises the ranking |
| `crops.py` | the three `--crop-mode` implementations (`bbox` measured best) |

## Measured effect of the prior

§IV-B. 224 hand-labelled regions from session `20260730_161223`:

| | Prior ON | Prior OFF |
|---|---|---|
| Accuracy | 0.696 | 0.522 |
| Macro F1 (4 GT classes) | 0.771 | 0.573 |
| Regions with \|Δε\| > 0.10 | 0 | 12 |
| Worst \|ΔT\| | 3.2 K | 316.1 K |

See `../ground_truth/README.md` for how to reproduce it.
