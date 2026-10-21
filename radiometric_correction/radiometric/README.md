# radiometric_correction/radiometric/ (package)

Pure array maths, imported by `../correct_session.py` and `../main.py`. No CLI.

| Module | What |
|---|---|
| `atmosphere.py` | `water_vapour_content(RH, T_air)` (g/m³) and `transmittance(d, RH, T_air)`: the FLIR/LOWTRAN double exponential in √d. Vectorised, so `d` can be the per-pixel LiDAR distance map; d ≤ 0 or NaN gives NaN. |
| `radiance.py` | `RadianceModel`: S(T) and its inverse. **Implemented as T⁴ (Stefan–Boltzmann)**, not the Planck form with R1, R2, B, F, O of paper Eq. 3/4. The class boundary is meant for swapping in a Planck model. |
| `correction.py` | `correct_temperature(apparent, ε, τ, T_refl, T_air, model=None)`: inverts Eq. 1 (Eq. 2) and converts back to °C. |
| `io_maps.py` | `.npy`/`.csv` map I/O, `lookup_emissivity`, default table `../../emissivity/emissivity_table.csv`. Used by `main.py` / `ThermalData.py`. |
| `sensors.py` | Hardware stubs that raise `NotImplementedError`. Unused. |
