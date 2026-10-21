# radiometric_correction/

Per-pixel correction of the FLIR apparent temperature (paper §II, §IV-C) and
the per-session sensor bias (§IV-E). Light env (`requirements.txt`).

```
S_tot = ε τ S_obj + (1−ε) τ S_refl + (1−τ) S_atm                (Eq. 1)
S_obj = [S_tot − (1−ε) τ S_refl − (1−τ) S_atm] / (ε τ)           (Eq. 2)
T_corr = T_obj − ΔT_bias,   ΔT_bias = T_FLIR(ref. surface) − T_air   (§IV-C, Eq. 5)
```

- **ε**: per pixel, from `../emissivity/project_to_flir.py` (`emissivity_map/<stem>/`).
- **τ**: per pixel, from the LiDAR distance (`distance.npy`), RH and T_air.
  `radiometric/atmosphere.py` implements the FLIR/LOWTRAN double-exponential
  model in √d.
- **T_refl**: approximated by T_air (`--reflected-temp` omitted).

> ⚠️ **Radiance model differs from the paper.** `radiometric/radiance.py`
> implements S(T) as the Stefan–Boltzmann **T⁴** law (in K). It does not use the
> camera's Planck calibration S(T) = R1 / (R2 (e^{B/T} − F)) + O of Eq. 3/4,
> and `correct_session.py` uses this default. Not changed here: reported in the
> extraction log.

| File | What |
|---|---|
| `correct_session.py` | Batch correction of a synced session, with a physical-plausibility retry: if a segment's material gives temperatures outside `[--t-min, --t-max]`, the next CLIP candidate is tried. A segment where no candidate is plausible becomes NaN. |
| `estimate_offset.py` | ΔT_bias from a surface at air temperature: the `--percentile` (10) of corrected pixels of interior wall/ceiling/column regions (ADE class), or of a hand-picked patch (`--interactive`). `--apply` writes the debiased maps. |
| `main.py` | Single-frame CLI (map or scalar mode) on the same `radiometric/` code. Utility, not part of the paper pipeline. |
| `ThermalData.py` | Reads apparent temperature from FLIR `*_R.jpg` with `flyr` (stats, single frame, hover viewer, `--out` .npy/.csv). Utility. |
| `radiometric/` | Package: `atmosphere.py` (ω, τ), `radiance.py` (S↔T), `correction.py` (`correct_temperature`, Eq. 2 + inverse), `io_maps.py` (map I/O, default table `../emissivity/emissivity_table.csv`), `sensors.py` (unused hardware stubs). |
| [`matlab/`](matlab) | Figures and the before/after voxel table. |

## `correct_session.py`

**Inputs:**
- `--session-dir`: ZED `fullrate/` with `sync_manifest.json`;
- **`<session>/emissivity_map/<stem>/`**: a fixed name, no flag (`distance.npy`, `segment_id.npy`);
- `--material-map-dir/<stem>/segments.json` (default `<session>/material_map`;
  the paper used `material_map_consensus`);
- `--flir-dir`: rot180 `<stem>.npy` apparent temperature (°C).

**Outputs**, in `emissivity_map/<stem>/`:
- `--out-name` (default `corrected_temperature.npy`);
- `emissivity_used.npy`;
- `correction_report.json`: conditions, per-segment decisions, retries.

| Flag | Default |
|---|---|
| `--humidity` | required. The paper used **50** (assumed) |
| `--air-temp` | required (20.5 / 21.0 / 21.0 °C) |
| `--reflected-temp` | = air temperature |
| `--table` | `../emissivity/emissivity_table.csv` |
| `--t-min` / `--t-max` | −20 / 80 °C |
| `--min-plausible-frac` | 0.99 |
| `--min-emissivity` | 0.5 |
| `--allow-low-emissivity` | off |
| `--every-n`, `--limit` | |

```powershell
& $L correct_session.py --session-dir $S --flir-dir $F --humidity 50 --air-temp 20.5 --material-map-dir $S\material_map_consensus
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

Paper sessions, read from their `offset_report.json`:

| Session | Method | T_air | Offset | RTD | Residual |
|---|---|---|---|---|---|
| A1 painted metal | `ade_class_pooling` (62 frames) | 20.5 | 4.644 °C | 22.19 | 0.027 |
| A9 glass | `manual_roi` (`--interactive`, 1 frame) | 21.0 | 4.863 °C | 22.9 | 1.316 |
| A10 aluminium | `manual_roi` (`--interactive`, 1 frame) | 21.0 | 4.804 °C | 23.09 | 1.817 |

## Utilities

```powershell
py main.py --thermal 34.2 --distance 5.2 --emissivity 0.93 --humidity 50 --air-temp 21
py main.py --thermal apparent.npy --distance-map distance.npy --emissivity-map emissivity.npy --humidity 50 --air-temp 21 --out corrected.npy
py ThermalData.py --folder C:\path\to\flir_session --frame 3 --out apparent.npy --show
```
