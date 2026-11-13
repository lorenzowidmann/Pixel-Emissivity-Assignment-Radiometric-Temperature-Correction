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
