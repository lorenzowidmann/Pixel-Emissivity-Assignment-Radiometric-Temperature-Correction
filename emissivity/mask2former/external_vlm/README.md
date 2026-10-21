# emissivity/mask2former/external_vlm/

`review_low_confidence.py` re-reviews the low-confidence regions of a finished
`../classify_session_m2f.py` run with a vision-language model (paper §IV-D,
"VLM context implementation"). It is a **fallback stage**, not a classifier.
Only regions whose CLIP confidence is below `--min-confidence` (0.5) are sent.
The model sees the **whole frame with the region outlined in red**, so it gets
the scene context that a crop-only CLIP score lacks: a shape that looks like
oxidised steel on texture alone is a painted radiator once you see it under a
window. The run directory is **never modified**.

(The paper's §IV-D is still a placeholder in v1 of the manuscript.)

## Setup

```powershell
pip install -r requirements.txt          # ollama, pydantic, numpy, pillow
# Local engine (default): install Ollama from https://ollama.com, then
ollama pull moondream
ollama serve                             # or keep the Ollama app running
```

Cloud engines, optional. Install only the SDK of the key you set:

| Env var | Provider | Default model | SDK |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Claude | `claude-opus-5` | `anthropic` (version not pinned: not installed in the working env) |
| `GEMINI_API_KEY` | Gemini | `gemini-flash-latest` | `google-genai==2.22.0` |
| `OPENAI_API_KEY` | OpenAI | `gpt-5.6-luna` | `openai==3.10.0` |

Keys are read from the **environment only**, never from a file or a flag. If
several are set, the priority is claude → gemini → openai, or force one with
`--api-provider`.

The script imports `annotate.py` (the renderer) and `gt_common.py` (run loader,
material table) from `../../ground_truth/`. Keep the folder layout.

## Usage

```powershell
# local, free, no key
py review_low_confidence.py --run $S\material_map_m2f --session-dir $S
# render the images and count regions, call no model
py review_low_confidence.py --run $S\material_map_m2f --session-dir $S --dry-run
# cloud, provider picked by whichever key is set
$env:GEMINI_API_KEY="..."; py review_low_confidence.py --run $S\material_map_m2f --session-dir $S --use-api
# only the benchmark frames, so the result can be scored against ground_truth_m2f.csv
py review_low_confidence.py --run <corridor>\material_map_m2f --session-dir <corridor> --frames ..\..\ground_truth\eval_frames.txt
```

| Flag | Default |
|---|---|
| `--run DIR` | a `material_map/v1` run (read-only) |
| `--session-dir DIR` | ZED `fullrate/` (frames to draw on) |
| `--out CSV` | `<run>_vlm_review.csv` next to the run |
| `--frames TXT` | all frames |
| `--min-confidence` | 0.5 |
| `--table` | `../../emissivity_table.csv` |
| `--low-emissivity-max` | 0.5 |
| `--low-emissivity-min-conf` | 0.50 |
| `--use-api`, `--api-provider {claude,gemini,openai}` | local |
| `--model` | `moondream` / provider default |
| `--image-max-px` | 1024 |
| `--jpeg-quality` | 85 |
| `--outline-width` | 0 = auto |
| `--temperature` | 0.0 (local) |
| `--keep-alive` | `0`: unload moondream after every call. Keeping it loaded let Ollama grow to ~9.5 GB and get OOM-killed on a 16 GB machine. |
| `--request-interval` | 0.5 s |
| `--max-retries` | 4 |
| `--retry-base-seconds` | 2.0 |
| `--dry-run`, `--redo` | |

## Merge rule

| VLM vs pipeline | Result | `vlm_status` |
|---|---|---|
| same material | keep; confidence = max(CLIP, VLM) | `confirmed` |
| different | take the VLM label and confidence | `overridden` |
| different, ε < 0.5 and VLM confidence < 0.50 | keep the pipeline label | `rejected_low_emissivity` |
| error / no answer | keep the pipeline label | `error` / `missing_from_results` |

The low-ε gate is applied **again** to the VLM's answer with the same defaults.
Otherwise the VLM could reintroduce exactly the bare-metal calls that the prior
and the gate exclude.

## Output

- `<run>_vlm_review.csv`, one row per region. Columns:
  `session, run_used, frame, region_id, area_px, ade, labels_md5`,
  `pipeline_material, pipeline_confidence`,
  `material, confidence, emissivity, solar_absorptance`,
  `vlm_reviewed, vlm_status, vlm_material, vlm_confidence, vlm_reasoning, reviewed_utc`.
  The identity columns join with `../../ground_truth/ground_truth_m2f.csv`.
- `<run>_vlm_review_work/images/<frame>-r<id>.jpg`: exactly what the model saw.
- `<run>_vlm_review_work/results.json`: written after every region. Rerunning
  the same command resumes; `--redo` starts over.

**Caveat (local engine).** moondream (1B parameters, 2K context) often copies
the prompt text into its "reasoning". In a 28-region test, the one `overridden`
row that was checked by eye was wrong. Spot-check `overridden` rows, or use
`--use-api` when the result feeds real temperatures.

**How the review output feeds back into correction:** the CSV is not read by
`project_to_flir.py` / `correct_session.py`. Applying the reviewed labels to a
run is not implemented in this repository (TODO, if the paper's §IV-D needs it).
