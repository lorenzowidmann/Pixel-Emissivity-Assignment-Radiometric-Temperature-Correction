# acquisition/rtd_reading/

Ground-truth surface temperature (paper §III-C): a four-wire Pt100 RTD fixed to
the surface, read by a National Instruments **USB-9162** through MATLAB.

The script name says `USB9126`, but the hardware is the **USB-9162** (paper and
thesis README). The name is kept so references still match.

| File | What it does |
|---|---|
| `USB9126_Pt100Reading.m` | Live-plots and records one acquisition at 2 Hz (`dq.addinput("Dev2", "ai0", "RTD")`). Saves `time_vect` and `data_vect` to `Data_DynamicCalibration/<saveName>.mat`, relative to MATLAB's current folder. |
| `read_plot_acquisitions.m` | Loads every `.mat` in `acqFolder`, rebuilds time from the 2 Hz rate, and saves one plot per file to `output/` (git-ignored). |

**Requirements:** MATLAB, **Data Acquisition Toolbox**, NI-DAQmx driver (device `Dev2`).

**Inputs/outputs:**
- `USB9126_Pt100Reading.m`: set `saveName` (default `"Acq01"`) and run. The `.mat` is written automatically.
- `read_plot_acquisitions.m`: set `acqFolder` (placeholder `C:\path\to\data\Acquisitions`). It writes `output/<name>.png`.

The RTD values used in the paper are 22.19 °C (painted metal), 22.9 °C (glass)
and 23.09 °C (aluminium). They come from `GroundTruthFiles/Dati/AcquisitionsRTD/*.mat`
(how the per-session value was taken from the series: TODO, not recorded).
