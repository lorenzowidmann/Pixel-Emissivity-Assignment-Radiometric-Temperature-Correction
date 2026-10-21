# emissivity/sam/

**SAM-based material classification: the tested alternative, not used in the
paper.** The paper's classifier is in [`../mask2former/`](../mask2former). §IV-A
explains why SAM was dropped: its class-agnostic regions were too small for
CLIP to recognise the material reliably.

`classify_session_sam.py` does the same job as `../mask2former/classify_session_m2f.py`:
a material and an emissivity for every region of every synced ZED frame. It
uses a different segmenter and a different prior:

| | `sam/classify_session_sam.py` | `mask2former/classify_session_m2f.py` |
|---|---|---|
| Segmenter | **SAM** (`facebook/sam-vit-base`, point-grid prompts) or **SLIC** superpixels (`--segmenter slic`) | **Mask2Former** (`facebook/mask2former-swin-large-ade-semantic`) |
| What a region is | class-agnostic mask | ADE20K object class (wall, window, radiator…) |
| Prior on CLIP's materials | **geometric zone** from the bbox shape (floor / ceiling / vertical), `../zones.py` | **category prior** from the ADE class, `../mask2former/ade_material_prior.csv` |
| CLIP model, material table, low-ε gate | shared (`../clip_classifier.py`, `../emissivity_table.py` + `.csv`) | shared |
| Output | `<session>/material_map/` | `<session>/material_map_m2f/` |
| Ground truth | `../ground_truth/ground_truth_sam.csv` | `../ground_truth/ground_truth_m2f.csv` |

| File | What |
|---|---|
| `classify_session_sam.py` | the script you run |
| `segmentation.py` | the segmenters it calls: `sam_segments()` (SAM, point-grid prompts + NMS), `superpixel_segments()` (SLIC), `segment_boxes()` |

The shared CLIP classifier, table and zone prior are imported from the main
`emissivity/` folder (one level up).

Env: heavy (`requirements.txt` includes `../requirements.txt`). The SAM weights
(~375 MB) and CLIP ViT-H/14 (~3.9 GB) download from Hugging Face on first use.

## Usage

```powershell
C:\venvs\emissivity\Scripts\python.exe classify_session_sam.py --session-dir $S --overlay
C:\venvs\emissivity\Scripts\python.exe classify_session_sam.py --session-dir $S --every-n 5 --limit 20 --overlay   # benchmark frame set
C:\venvs\emissivity\Scripts\python.exe classify_session_sam.py --session-dir $S --segmenter slic --n-segments 100  # fast SLIC variant
```

**Input:** `--session-dir` = ZED `fullrate/` with `metadata.json`, `frames/`, `sync_manifest.json`.

**Output:** `--out-dir` (default `<session>/material_map`) / `<flir_stem>/`:

| File | Content |
|---|---|
| `labels.npy` | int32 region-id raster on the full ZED grid; −1 outside the FLIR-FOV crop |
| `segments.json` | schema `material_map/v1`: per region `zone`, ranked materials + `confidence`, `emissivity`, `gated` block |
| `overlay.png` | with `--overlay`: region boundaries + material labels |

| Flag | Default |
|---|---|
| `--segmenter {sam,slic}` | `sam` |
| `--sam-model REPO` | `facebook/sam-vit-base` |
| `--sam-grid N` | 16 (N×N point prompts) |
| `--sam-min-area PX` | 1500 |
| `--sam-nms-iou` | 0.7 |
| `--n-segments`, `--compactness`, `--sigma` | 100, 10.0, 0.0 (SLIC only) |
| `--zone-constraint / --no-zone-constraint` | on |
| `--crop-to-flir-fov / --no-...` | on |
| `--fov-margin-px` | 45 |
| `--calibration` | `../../sensor_fusion/rig_calibration.yaml` (its `--help` text still says `../Calibration/…`, an old name) |
| `--top-k` | 3 |
| `--table` | `../emissivity_table.csv` |
| `--low-emissivity-max / -min-conf / -min-margin` | 0.5 / 0.50 / 0.15 |
| `--no-gating` | off |
| `--clip-model` | `laion/CLIP-ViT-H-14-laion2B-s32B-b79K` |
| `--every-n`, `--limit`, `--overlay` | |

Cost on CPU: about 27 s/frame for SAM segmentation plus about 2 s per region
for CLIP ViT-H/14.

To use a SAM run downstream, point the next steps at its folder, e.g.
`../project_to_flir.py --material-map-dir <session>/material_map`.

In the thesis repository this script was `EmissivityCalculation/classify_session.py`.
It was moved and renamed here so that the two methods sit side by side.
