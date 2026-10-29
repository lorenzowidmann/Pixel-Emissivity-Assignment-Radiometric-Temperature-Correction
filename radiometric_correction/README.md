# radiometric_correction/

Per-pixel correction of the FLIR apparent temperature (paper §II, §IV-C) and
the per-session sensor bias (§IV-E). Light env (`requirements.txt`).

```
S_tot = ε τ S_obj + (1−ε) τ S_refl + (1−τ) S_atm                (Eq. 1)
S_obj = [S_tot − (1−ε) τ S_refl − (1−τ) S_atm] / (ε τ)           (Eq. 2)
S(T)  = R1 / (R2 (e^{B/T} − F)) − O,   T = B / ln(R1 / (R2 (S + O)) + F)   (Eq. 3/4, T in K)
T_corr = T_obj − ΔT_bias,   ΔT_bias = T_FLIR(ref. surface) − T_air   (§IV-C, Eq. 5)
```

- **ε**: per pixel, from `../emissivity/project_to_flir.py` (`emissivity_map/<stem>/`).
- **τ**: per pixel, from the LiDAR distance (`distance.npy`), RH and T_air.
  `radiometric/atmosphere.py` implements the FLIR/LOWTRAN double-exponential
  model in √d.
- **T_refl**: approximated by T_air (`--reflected-temp` omitted).

**Radiance model.** The default (`--radiance-model planck`) is the camera's
Planck calibration. R1, R2, B, F, O are read with `flyr` from the **original**
`*_R.jpg` of each corrected frame (`--flir-jpg-dir`; the stripped rot180 copies
carry no metadata). The sign of O follows flyr 5.1.0: O is **subtracted** in S(T)
(the paper's "+O" is wrong). On the A1/A9/A10 camera the constants are the same in
every frame: R1 = 17096.453125, R2 = 0.057946026, B = 1428, F = 1, O = −786.
`--radiance-model t4` keeps the earlier Stefan–Boltzmann approximation.
Planck vs T⁴ on the three sessions: session means +0.0006 / +0.0009 / +0.0013 K,
max per-pixel |Δ| 0.03 K, sensor offsets and RTD residuals within 0.001 K, no
material decision changed. The difference grows at low ε: +0.16 K at ε = 0.25
(radiometric term +18.24 → +18.40 °C).

> ⚠️ **FLIR input = neutral raw-signal apparent temperature.** The FLIR metadata of
> these sessions stores emissivity 0.98, object distance 50 m, reflected −27 °C,
> atmosphere 28 °C, RH 45 %. flyr's plain `.celsius` applies them, so it is
> 0.6–0.9 K above the neutral reading. The pipeline applies its own ε, τ and
> T_refl, so the rot180 `.npy` must be
> `flyr.unpack(p).adjust_metadata(emissivity=1.0, object_distance=0.0).celsius`
> (`ThermalData.neutral_celsius`). Regenerate them with
> `../calibration/extrinsic/conversion/rotate_flir_poses.py --pose-dir <originals> --npy`
> (it refuses to write into an existing folder unless `--overwrite` is passed).
> **Guard:** `correct_session.py` recomputes the neutral reading for the first,
> middle and last frame from `--flir-jpg-dir`. It stops if any `.npy` differs by
> more than 0.01 °C. `--allow-stored-settings` bypasses this with a warning.
> Without `--flir-jpg-dir` it only warns that the input cannot be verified.
> Standalone check: `flir_input_guard.py --flir-dir <rot180> --flir-jpg-dir <originals>`.
>
> The offset table below and the results in the top-level README were obtained
> with the **previous stored-settings input**. The neutral input changes the
> biases to 4.1 / 4.3 / 4.2 °C and the final temperatures by −0.1 to −0.3 °C. See
> `RawSignalResult\REPORT_raw_signal_vs_stored_settings.md` (outside the repo, next
> to the data).

| File | What |
|---|---|
| `correct_session.py` | Batch correction of a synced session, with a physical-plausibility retry: if a segment's material gives temperatures outside `[--t-min, --t-max]`, the next CLIP candidate is tried. A segment where no candidate is plausible becomes NaN. |
| `estimate_offset.py` | ΔT_bias from a surface at air temperature: the `--percentile` (10) of corrected pixels of interior wall/ceiling/column regions (ADE class), or of a hand-picked patch (`--interactive`). `--apply` writes the debiased maps. |
| `main.py` | Single-frame CLI (map or scalar mode) on the same `radiometric/` code. Utility, not part of the paper pipeline. |
| `ThermalData.py` | Reads apparent temperature from FLIR `*_R.jpg` with `flyr` (stats, single frame, hover viewer, `--out` .npy/.csv). Neutral settings by default (`neutral_celsius`); `read_temperature(p, stored_settings=True)` gives the old `.celsius`. Utility. |
| `flir_input_guard.py` | Checks that a rot180 `.npy` folder holds the neutral apparent temperature (first/middle/last frame against the original JPEG, 0.01 °C). Used by `correct_session.py`; also runs standalone. |
| `tests/` | `test_radiance.py` (Planck model), `test_flir_input_guard.py` (guard, fake reader). `py -m pytest tests -q` |
| `radiometric/` | Package: `atmosphere.py` (ω, τ), `radiance.py` (S↔T), `correction.py` (`correct_temperature`, Eq. 2 + inverse), `io_maps.py` (map I/O, default table `../emissivity/emissivity_table.csv`), `sensors.py` (unused hardware stubs). |
| [`matlab/`](matlab) | Figures and the before/after voxel table. |

## `correct_session.py`

**Inputs:**
- `--session-dir`: ZED `fullrate/` with `sync_manifest.json`;
- **`<session>/emissivity_map/<stem>/`**: a fixed name, no flag (`distance.npy`, `segment_id.npy`);
- `--material-map-dir/<stem>/segments.json` (default `<session>/material_map`;
  the paper used `material_map_consensus`);
- `--flir-dir`: rot180 `<stem>.npy` neutral apparent temperature (°C, ε = 1, d = 0);
- `--flir-jpg-dir DIR [DIR ...]`: folders with the original full FLIR `*_R.jpg`
  (Planck constants, and the input guard). Required with `planck`; the run stops
  before writing if any frame has no original, or if the `.npy` are not neutral.

**Outputs**, in `emissivity_map/<stem>/`:
- `--out-name` (default `corrected_temperature.npy`);
- `--emissivity-used-name` (default `emissivity_used.npy`);
- `--report-name` (default `correction_report.json`): conditions, radiance model
  and its five constants, per-segment decisions, retries.

| Flag | Default |
|---|---|
| `--humidity` | required. The paper used **50** (assumed) |
| `--air-temp` | required (20.5 / 21.0 / 21.0 °C) |
| `--reflected-temp` | = air temperature |
| `--radiance-model` | `planck` (`t4` = Stefan–Boltzmann) |
| `--flir-jpg-dir` | required with `planck` |
| `--allow-stored-settings` | off: the run stops if the `.npy` are not neutral |
| `--table` | `../emissivity/emissivity_table.csv` |
| `--t-min` / `--t-max` | −20 / 80 °C |
| `--min-plausible-frac` | 0.99 |
| `--min-emissivity` | 0.5 |
| `--allow-low-emissivity` | off |
| `--every-n`, `--limit` | |

```powershell
& $L correct_session.py --session-dir $S --flir-dir $F --flir-jpg-dir $J1 $J2 --humidity 50 --air-temp 20.5 --material-map-dir $S\material_map_consensus
```

## `estimate_offset.py`

**Inputs:**
- `emissivity_map/<stem>/<--corrected-name>`;
- `--material-map-dir` (default `<session>/material_map_consensus`) for the ADE classes;
- `--air-temp`.

**Outputs:**
- `<session>/<--out-name>` (default `offset_report.json`; `-` to skip): offset,
  reference, method, pixels per class, per-percentile offsets, residual against
  `--thermocouple`;
- with `--apply`: `emissivity_map/<stem>/<--debiased-name>` = corrected − offset.

| Flag | Default |
|---|---|
| `--corrected-name` | `corrected_temperature.npy`. **Pass it explicitly** |
| `--debiased-name` | `corrected_temperature_debiased.npy`. **Pass it explicitly** |
| `--percentile` | 10 |
| `--proxy-classes` | `wall,ceiling,column` |
| `--thermocouple C` | validation only: reports the residual, not used for the offset |
| `--interactive` | drag a rectangle on a plain interior wall (matplotlib window) |
| `--apply`, `--every-n`, `--limit`, `--out-name` | |

```powershell
& $L estimate_offset.py --session-dir $S --air-temp 20.5 --thermocouple 22.19 `
     --corrected-name corrected_temperature.npy --apply --debiased-name corrected_temperature_debiased.npy
```

Paper sessions, read from their `offset_report.json` (previous stored-settings
input; neutral input: 4.104 / 4.260 / 4.201 °C, see the note at the top):

| Session | Method | T_air | Offset | RTD | Residual |
|---|---|---|---|---|---|
| A1 painted metal | `ade_class_pooling` (62 frames) | 20.5 | 4.644 °C | 22.19 | 0.027 |
| A9 glass | `manual_roi` (`--interactive`, 1 frame) | 21.0 | 4.863 °C | 22.9 | 1.316 |
| A10 aluminium | `manual_roi` (`--interactive`, 1 frame) | 21.0 | 4.804 °C | 23.09 | 1.817 |

## Utilities

```powershell
py main.py --thermal 34.2 --distance 5.2 --emissivity 0.93 --humidity 50 --air-temp 21 --flir-image frame_R.jpg
py main.py --thermal apparent.npy --distance-map distance.npy --emissivity-map emissivity.npy --humidity 50 --air-temp 21 --flir-image frame_R.jpg --out corrected.npy
py main.py --thermal 34.2 --distance 5.2 --emissivity 0.93 --humidity 50 --air-temp 21 --radiance-model t4
py -m pytest tests -q
py ThermalData.py --folder C:\path\to\flir_session --frame 3 --out apparent.npy --show
```
