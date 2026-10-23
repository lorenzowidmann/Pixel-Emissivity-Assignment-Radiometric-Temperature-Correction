# radiometric_correction/radiometric/ (package)

Pure array maths, imported by `../correct_session.py` and `../main.py`. No CLI.

| Module | What |
|---|---|
| `atmosphere.py` | `water_vapour_content(RH, T_air)` (g/m³) and `transmittance(d, RH, T_air)`: the FLIR/LOWTRAN double exponential in √d. Vectorised, so `d` can be the per-pixel LiDAR distance map; d ≤ 0 or NaN gives NaN. |
| `radiance.py` | S(T) and its inverse, °C at the interface. `PlanckRadianceModel(r1, r2, b, f, o)`: FLIR Planck calibration (paper Eq. 3/4, O subtracted as in flyr), `from_flir_image(path)` reads the constants from an original `*_R.jpg`; NaN where the inverse is undefined. `StefanBoltzmannModel`: T⁴ approximation (`RadianceModel` is an alias). |
| `correction.py` | `correct_temperature(apparent, ε, τ, T_refl, T_air, model=None)`: inverts Eq. 1 (Eq. 2) and converts back to °C. `model=None` is T⁴; the CLIs pass the Planck model. |
| `io_maps.py` | `.npy`/`.csv` map I/O, `lookup_emissivity`, default table `../../emissivity/emissivity_table.csv`. Used by `main.py` / `ThermalData.py`. |
| `sensors.py` | Hardware stubs that raise `NotImplementedError`. Unused. |
