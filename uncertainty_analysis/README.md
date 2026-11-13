# UncertaintyAnalysis/

Monte Carlo uncertainty (GUM Supplement 1) of the corrected temperature at the
RTD pixel, for the validation sessions of the paper (§V; door A1 and glass A9 by
default). Light env (`requirements.txt`). The script only reads the run outputs
in `RawSignalResult\runs` and writes nothing unless `--out` is given.

```
S_obj  = [S_tot − (1−ε) τ S_refl − (1−τ) S_atm] / (ε τ)            (Eq. 2)
S(T)   = R1 / (R2 (e^{B/T} − F)) − O,   T = B / ln(R1 / (R2 (S + O)) + F)   (Eq. 3/4)
T_obj  = T(S_obj)  with  T_atm = T_air,  T_refl = T_air + δ_refl
T_wall = T(S_obj, wall)  with  ε_wall, the same τ, T_refl, T_atm
ΔT_bias = T_wall + δ_pct − T_air                                     (Eq. 5)
T_corr = T_obj − ΔT_bias
```

The Planck model and the inversion are **imported** from
`../radiometric_correction/radiometric` (`PlanckRadianceModel`,
`correct_temperature`), so the script runs the same code as
`correct_session.py`. Only the forward Eq. 1 (used to back-compute the wall's
apparent temperature from `reference_c`) is written in the script, with the
same `PlanckRadianceModel`.

Per draw, every input below is perturbed together. Each input is also perturbed
alone, and the standard deviation of the result is its contribution.
u_c = std of the full draw, U = 2 u_c, and the 95 % interval comes from the
2.5/97.5 percentiles. The model is close to linear: the contributions add in
quadrature to u_c.

## Inputs

Read from `<--runs-dir>\<session>\`:

| File | Fields used |
|---|---|
| `extracts.json` | `rtd_pixel`: `T_app`, `eps_used`, `tau`, `T_obj_after_eps`, `T_corr`; `bias_applied_c` |
| `offset_report_neutral.json` | `air_temp_c`, `reference_c` (p10 of the corrected wall pixels), `offset_by_percentile_c` (p5, p15), `thermocouple_c` |
| `examined_frame_*\correction_report_neutral.json` | `radiance_model`: R1, R2, B, F, O |

## Input uncertainties

R = rectangular (± half-width), N = normal (std). Values are those of the paper;
see [Assumptions to verify](#assumptions-to-verify).

| Input | Flag | Default | Distribution | Meaning |
|---|---|---|---|---|
| ε of the surface | `--h-eps` | ±0.025 | R | Lookup emissivity of the RTD surface (A1 painted_metal 0.94, A9 glass 0.92). About half the class range in `emissivity_table.csv`. |
| ε of the wall | `--eps-wall`, `--h-eps` | 0.94 ± 0.025 | R | Emissivity of the reference wall (paint), independent of the surface ε. |
| T_refl − T_air | `--h-refl` | ±1.0 K | R | The pipeline takes T_refl = T_air; this is the error of that approximation. |
| τ | `--h-tau` | ±0.0035 | R | Transmittance for RH 30–70 % (the pipeline assumed RH 50 %, not measured). Same perturbation on the surface and on the wall. |
| T_air | `--h-air` (alias `--u-air`) | ±0.5 K | R | Air thermometer error. **Half-width**, so u = 0.5/√3 = 0.29 K. It enters the inversion and the bias. |
| NETD | `--netd` | 0.05 K | N | Camera noise on the single RTD pixel. The wall percentile pools thousands of pixels, so no noise is applied there. |
| Wall percentile | — | ±(p15 − p5)/2 | R | Choice of the percentile used for the wall reference (A1 ±0.32 K, A9 ±0.11 K), from `offset_by_percentile_c`. |

Actual τ range for RH 30 / 50 / 70 % (`radiometric/atmosphere.py`, at the RTD
pixel distance and session air temperature):

| Session | d | τ RH 30 | τ RH 50 | τ RH 70 | half-width |
|---|---|---|---|---|---|
| A1 | 8.23 m | 0.98569 | 0.98229 | 0.97944 | 0.0031 (+0.0034 / −0.0029) |
| A9 | 1.78 m | 0.99328 | 0.99172 | 0.99043 | 0.0014 |

So ±0.0035 is slightly conservative at A1 and about 2.5× wide at A9. The effect
is negligible either way (0.003 K): the τ error is shared by the surface and the
wall and cancels in T_obj − T_wall.

Other flags: `--sessions` (default `A1 A9`), `--n` (400 000 draws), `--seed` (1),
`--delta-t` (6 20: ε contribution for a synthetic surface ΔT above air),
`--out` (JSON with settings and results).

## Usage

```powershell
$L="C:\venvs\sensorfusion\Scripts\python.exe"
& $L UncertaintyAnalysis\uncertainty_mc.py --runs-dir ..\RawSignalResult\runs
& $L UncertaintyAnalysis\uncertainty_mc.py --runs-dir ..\RawSignalResult\runs --sessions A1 A9 --h-air 0.3 --netd 0.04 --out ..\RawSignalResult\uncertainty_mc.json
```

## Expected output (defaults)

```
== A1: T_corr model 22.193 C (pipeline 22.193), RTD 22.19
   eps_surface        0.087 K
   eps_wall           0.062 K
   T_refl             0.001 K
   tau                0.003 K
   T_air              0.289 K
   NETD               0.054 K
   offset_percentile  0.184 K
   u_c = 0.363 K   U(k=2) = 0.73 K   95% [21.50, 22.87] C
   eps contribution vs dT: {'6.0': 0.09, '20.0': 0.281}
== A9: T_corr model 22.679 C (pipeline 22.678), RTD 22.9
   eps_surface        0.091 K
   eps_wall           0.064 K
   T_refl             0.012 K
   tau                0.003 K
   T_air              0.283 K
   NETD               0.054 K
   offset_percentile  0.062 K
   u_c = 0.315 K   U(k=2) = 0.63 K   95% [22.10, 23.24] C
   eps contribution vs dT: {'6.0': 0.091, '20.0': 0.287}
```

T_air dominates: it enters the bias almost 1:1. A9's residual against the RTD
(−0.22 K) is inside U. The 0.001 K gap between model and pipeline T_corr comes
from the 4-decimal rounding in `extracts.json`.

## Assumptions to verify

- **Air thermometer accuracy**: ±0.5 K rectangular is assumed. Check the
  datasheet of the thermometer used for `--air-temp` and pass `--h-air`.
- **Camera NETD**: 0.05 K is assumed (FLIR Vue Pro R, < 50 mK in the datasheet).
  Pass `--netd` if a different value applies.
- **RTD uncertainty not included**: U is the uncertainty of the corrected
  temperature only. To judge the residual against the Pt100, combine U with the
  RTD's own uncertainty (Pt100 class, DAQ).
- **Single wall pixel**: the wall reference is modelled as one pixel with
  ε_wall = 0.94 and the RTD pixel's τ. In reality A1 pools wall/ceiling/column
  pixels over 62 frames, at many distances and with per-pixel ε (paint 0.94,
  plaster 0.91, …). A9 uses a manual ROI on another frame. The ε_wall and
  percentile terms are meant to cover this.
- **Shared random generator**: one generator, seeded once, runs through all
  sessions. `--sessions A9` alone therefore gives slightly different Monte Carlo
  noise than `A1 A9` (third decimal).

---

# Per-pixel and per-voxel u(T), emissivity as an uncertain quantity

Three scripts extend the single-pixel Monte Carlo to whole frames and to the
voxel map, with the emissivity treated as a **distribution over candidate
materials** instead of a fixed lookup value.

| File | What |
|---|---|
| `uncertainty_map.py` | Per-pixel u(T) for every frame of one session, plus the uncertainty-based low-ε gate (`--uncertainty-gate`) and what-if materials (`--what-if`). |
| `voxel_uncertainty.py` | Per-voxel u_c: runs `emissivity/voxel_consensus.py --stage thermal` on the u maps, then joins with `thermal_voxels.csv`. |
| `uncertainty_report.py` | Prints the report for the paper from the per-session summaries and saves it as `uncertainty_report.txt`. |

## Model

```
p_m     CLIP scores of segments.json (top_k, after the category prior), renormalised;
        consensus material missing from top_k → added with p = consensus agreement
        optional --confusion: p_true(m) = Σ_j p_clip(j) · P(true m | pred j)
T_m     = T_obj(T_app, ε_m, τ, T_air, T_air) − ΔT_bias        (pipeline functions)
u_m     = |T(ε_lo) − T(ε_hi)| / √12                           (table range, rectangular)
u_ε²    = Σ_m p_m [u_m² + (T_m − T_corr)²]                    (about the reported T_corr)
u_c²    = u_ε² + u_Tair² + u_Trefl² + u_τ² + u_NETD² + u_pct² + u_εwall²
voxel:  u_c² = mean(u_sys)² + (mean(u_NETD) / √n_obs)²        (u_sys = u_c without NETD)
```

The other terms use the inputs of `uncertainty_mc.py`, linearised by central
differences per pixel: T_air ±0.5 K, T_refl − T_air ±1 K, τ from RH 30–70 % at
each pixel's LiDAR distance, NETD 0.05 K, wall percentile (p15 − p5)/2, wall
ε ±0.025. Candidates implausible under `correct_session.py`'s rule (≥ 99 % of
pixels in [−20, 80] °C) are dropped. **T_corr is not changed.** The script
recomputes it with the applied emissivity and stops if it differs from
`corrected_temperature_neutral_debiased.npy` by more than 1e-3 K (A1/A9/A10:
≤ 4.2e-6 K).

**Uncertainty gate** (`--uncertainty-gate`, analysis only, default off): a
candidate with ε < `--low-emissivity-max` (0.5) is accepted only if its segment
median u(T) with p = 1 is below `--gate-max-u` (1 K). Otherwise the next
candidate is taken and the pixels are flagged. Decisions are compared with the
fixed ε ≥ 0.5 rule.

## Inputs

| Flag | Content |
|---|---|
| `--session-dir` | `RawSignalResult\work\<S>`: `sync_manifest.json`, `emissivity_map\<stem>\` (`distance.npy`, `segment_id.npy`, `emissivity_used_neutral.npy`, `corrected_temperature_neutral[_debiased].npy`, `correction_report_neutral.json`) |
| `--flir-dir` | neutral rot180 `.npy` (`RawSignalResult\neutral_npy\session_<S>_rot180`) |
| `--material-map-dir` | `material_map_consensus` of the session (`segments.json`) |
| `--run-dir` | `RawSignalResult\runs\<S>`: `offset_report_neutral.json`, `extracts.json`, `voxel_map_neutral\` |
| `--rtd-voxels` (voxel script) | `RawSignalResult\rtd_voxels.json` (back-projected RTD point and voxel) |
| `--bag` (voxel script) | the session's LiDAR bag, as in the `voxel_map_neutral` run |

## Outputs (never overwritten without `--overwrite`)

- In `work\<S>\emissivity_map\<stem>\`, next to the corrected temperature:
  `uncertainty_map_neutral.npy` (u_c, K), `uncertainty_sys_neutral.npy`,
  `uncertainty_netd_neutral.npy`, and `uncertainty_gate_flag_neutral.npy` (with
  `--uncertainty-gate`).
- In `runs\<S>\uncertainty\`:
  - `uncertainty_summary.json`: RTD pixel, components, distributions, per segment p_m, gate, what-if;
  - `examined_frame_<stem>_components.npz`: every term;
  - `thermal_voxels_u.csv`: `thermal_voxels.csv` + `u_sys_k`, `u_netd_k`, `u_c_k`;
  - `voxel_summary.json`;
  - `voxel_usys\`, `voxel_unetd\` and `log_voxel_*.txt`.
- `runs\uncertainty_report.txt`.

## Usage (from `PaperEmissivityCorrection\`)

```powershell
$L="C:\venvs\sensorfusion\Scripts\python.exe"; $env:PYTHONDONTWRITEBYTECODE=1
$U="Pixel-Emissivity-Assignment-Radiometric-Temperature-Correction\UncertaintyAnalysis"
$RS="RawSignalResult"; $Z="GroundTruthFiles\Dati\Zed\20260911_105024\fullrate"
& $L $U\uncertainty_map.py --session-dir $RS\work\A10 --flir-dir $RS\neutral_npy\session_A10_rot180 --material-map-dir $Z\material_map_consensus --run-dir $RS\runs\A10 --uncertainty-gate --what-if aluminum_polished aluminum_oxidized
& $L $U\voxel_uncertainty.py --session-dir $RS\work\A10 --bag GroundTruthFiles\Dati\Lidar\rosbag2_2026_09_11-12_50_10 --material-map-dir $Z\material_map_consensus --run-dir $RS\runs\A10 --rtd-voxels $RS\rtd_voxels.json --session A10
& $L $U\uncertainty_report.py --runs-dir $RS\runs
```

A1: ZED `20260911_094055`, bag `rosbag2_2026_09_11-11_40_48`. A9: `20260911_104224`,
`rosbag2_2026_09_11-12_41_38`. A1 and A9 run without `--what-if`.

## Results (defaults)

| | RTD pixel u_c | e = T_corr − T_RTD | RTD voxel u_c (e) | pixels median / p95 | voxels median / p95 |
|---|---|---|---|---|---|
| A1 door | 0.371 K | +0.003 K | 0.373 K (−0.18 K) | 0.381 / 0.404 K | 0.379 / 0.392 K |
| A9 glass | 0.315 K | −0.222 K | no voxel; ≤ 0.5 m: 0.332 K (+1.23 K, window frame) | 0.329 / 0.368 K | 0.337 / 0.383 K |
| A10 plate | 0.332 K | −0.119 K | 0.365 K (+0.47 K); 3×3×3: 0.350 K (+0.02 K) | 0.341 / 0.399 K | 0.342 / 0.411 K |

- T_air dominates (≈ 0.29 K). The emissivity term is 0.09–0.26 K: larger where
  CLIP splits its score between materials with different ε.
- The A1 RTD pixel u_c (0.371 K) is above `uncertainty_mc.py` (0.363 K) because
  CLIP gives glass p = 0.19 on the door. A9 matches it exactly (0.315 K).
- With the prior, no stored candidate in A1/A9/A10 has ε < 0.5, so the
  uncertainty gate changes 0 segments.
- A10 what-if: polished aluminum would give u = 10.1 K and oxidized aluminum
  2.9 K. Both would be rejected by the 1 K gate as well as by the fixed rule.

## Assumptions and limits

- **No confusion-matrix calibration.** The benchmark predictions
  (`20260730_161223\material_map_m2f`) are not available. `--confusion` takes
  `evaluate.py`'s `confusion_<name>.csv` when they are.
- **Only the top 3 CLIP scores are stored.** The rest of the mass (median 0,
  at most 0.22) is ignored.
- **Wall model** as in `uncertainty_mc.py`, with τ at the RTD-pixel distance.
- **Voxel terms:** every term except NETD is treated as fully correlated
  within a voxel.
- **Not included:** the RTD's own uncertainty, and the datasheet values for
  the air thermometer and the NETD (both assumed).
