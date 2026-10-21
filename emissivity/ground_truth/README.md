# emissivity/ground_truth/

Hand-labelled ground truth for the material classification and its scoring
(paper §IV-B, Table "prior on/off"). Neither script loads a model. Light env
(`requirements.txt`: numpy, pillow; `annotate.py` also needs `tkinter` from
the standard library).

| File | What |
|---|---|
| `annotate.py` | Tkinter tool. Shows each region of a run (zoomed crop + whole frame with the region tinted) and records its true material by key press. |
| `evaluate.py` | Scores one or more runs against a ground-truth CSV: accuracy, macro P/R/F1 over the GT classes, \|Δε\| (mean, area-weighted, count > 0.10), graybody \|ΔT\| bound, confusion matrices. |
| `gt_common.py` | Run loader, `labels_md5`, compatibility gate, material-table reader (also used by `../mask2former/external_vlm/`). |
| `eval_frames.txt` | The 20 pinned FLIR stems: `sorted(stems)[::5][:20]`, i.e. `--every-n 5 --limit 20`. |
| `ground_truth_m2f.csv` | **The paper's labels.** Session `20260730_161223`, run `material_map_m2f`: 228 regions, 224 `labeled`, 2 `mixed`, 2 `unclear`. |
| `ground_truth_sam.csv` | Labels for the SAM alternative (`material_map_sam_v2`, same frames, 611 regions). |

CSV columns: `session, run_used, frame, region_id, area_px, ade, status, ground_truth, labels_md5, annotated_utc`.

**Region ids are positional.** A label is only valid for a run whose
`labels.npy` for that frame has the same md5. `evaluate.py` refuses a
mismatching run, and there is no `--force`. Prior on and prior off share one
segmentation, so one annotation pass covers both. SAM and Mask2Former need
separate passes.

## Reproducing §IV-B

The benchmark session `20260730_161223` is **not** in `GroundTruthFiles`
(TODO: data availability). With it:

```powershell
$S="<...>\Zed\20260730_161223\fullrate"
& $H ..\mask2former\classify_session_m2f.py --session-dir $S --every-n 5 --limit 20
& $H ..\mask2former\classify_session_m2f.py --session-dir $S --every-n 5 --limit 20 --no-category-prior --out-dir $S\material_map_m2f_noprior
& $L evaluate.py --ground-truth ground_truth_m2f.csv --runs $S\material_map_m2f $S\material_map_m2f_noprior --names prior-on prior-off
```

Expected result: accuracy 0.696 / 0.522, macro F1 0.771 / 0.573, 0 / 12 regions
with |Δε| > 0.10, worst |ΔT| 3.2 / 316.1 K. The regenerated `labels.npy` must
match the annotated md5. Otherwise `evaluate.py` stops: a different checkpoint
or calibration changes the regions. The paper and thesis do not record whether
the gate was left at the defaults for both runs. The paper says the gate was
active in both cases.

## `annotate.py`

| Flag | Meaning |
|---|---|
| `--run DIR` | run whose `labels.npy` defines the regions |
| `--session-dir DIR` | ZED `fullrate/` |
| `--frames TXT` | default `eval_frames.txt` |
| `--out CSV` | default `ground_truth.csv`; use `ground_truth_<segmenter>.csv` |
| `--table CSV` | alternative material table |
| `--min-area PX` | smaller regions are recorded `unclear` |
| `--show-prediction` | off on purpose, so the run's answer does not bias the label |
| `--redo` | revisit labelled regions |
| `--init-frames --n 20 --stride 5` | write `eval_frames.txt` and exit |

Keys:
- `1`–`0` and `a`–`j`: materials (legend drawn from the table);
- `m`: mixed; `u`: unclear;
- `←` `→`: navigate; `Esc`: quit.

The CSV is saved after every label.

## `evaluate.py`

| Flag | Meaning |
|---|---|
| `--ground-truth CSV` | labels to score against |
| `--runs DIR ...` | runs to score |
| `--names NAME ...` | column names (default: directory names) |
| `--out CSV` | default `out/comparison.csv` |
| `--confusion-dir DIR` | default: next to `--out`, one `confusion_<name>.csv` per run |
| `--table CSV` | alternative material table |

`out/` is generated and git-ignored. Read accuracy and macro F1 rather than
macro precision, which ignores predictions of classes absent from the GT. The
|ΔT| is a naive graybody bound at 22 °C that ignores reflections. Use it to
rank errors, not as the pipeline's temperature error.
