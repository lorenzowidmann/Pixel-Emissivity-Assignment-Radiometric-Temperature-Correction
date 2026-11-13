"""Monte Carlo uncertainty of the corrected temperature at the RTD pixel.

Propagates the input uncertainties through the radiometric inversion and the
wall-based sensor-offset correction (GUM Supplement 1), for the sessions used
in the paper (door A1, glass A9 by default).

Model, per Monte Carlo draw:
    T_obj  = inversion(T_app + noise, eps, tau, T_refl, T_air)
    T_wall = inversion(T_app_wall,    eps_wall, tau, T_refl, T_air)
    bias   = T_wall + percentile_shift - T_air
    T_corr = T_obj - bias
with T_refl = T_air + d_refl. The wall's apparent temperature T_app_wall is
back-computed from the offset report (reference_c = corrected wall
temperature at the chosen percentile), assuming the same tau as the RTD pixel.

The Planck model and the inversion (Eq. 2) are imported from the pipeline
(../radiometric_correction/radiometric), not duplicated: PlanckRadianceModel
and correct_temperature are exactly what correct_session.py uses.

Inputs read for each session from <runs-dir>/<session>/:
    extracts.json                 rtd_pixel (T_app, eps_used, tau, T_corr), bias_applied_c
    offset_report_neutral.json    air_temp_c, reference_c, offset_by_percentile_c, thermocouple_c
    examined_frame_*/correction_report_neutral.json   Planck constants R1, R2, B, F, O

Notes:
    - extracts.json stores values rounded to 4 decimals, so the model T_corr can
      differ from the pipeline's by ~0.001 K.
    - One random generator is shared by all sessions (seeded once), so running a
      session alone gives slightly different Monte Carlo noise than in a batch.

Usage:
    py uncertainty_mc.py --runs-dir ...\\RawSignalResult\\runs
    py uncertainty_mc.py --runs-dir ... --sessions A1 A9 --h-air 0.5 --out results.json
"""

import argparse
import glob
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "radiometric_correction"))
from radiometric import PlanckRadianceModel, correct_temperature  # noqa: E402
from radiometric.radiance import PLANCK_KEYS  # noqa: E402


def make_model(consts):
    """Inversion (pipeline's correct_temperature) and its forward counterpart
    (Eq. 1, no pipeline equivalent), both on the session's Planck model."""
    m = PlanckRadianceModel(*(consts[k] for k in PLANCK_KEYS))

    def t_obj(T_app, eps, tau, T_refl, T_atm):
        return correct_temperature(T_app, eps, tau, T_refl, T_atm, model=m)

    def t_app(T_obj, eps, tau, T_refl, T_atm):
        return m.temperature(eps * tau * m.radiance(T_obj) + (1 - eps) * tau * m.radiance(T_refl)
                             + (1 - tau) * m.radiance(T_atm))

    return t_obj, t_app


def load_session(runs_dir: Path, session: str):
    d = runs_dir / session
    ex = json.loads((d / "extracts.json").read_text(encoding="utf-8"))
    off = json.loads((d / "offset_report_neutral.json").read_text(encoding="utf-8"))
    rep_path = sorted(glob.glob(str(d / "examined_frame_*" / "correction_report_neutral.json")))
    if not rep_path:
        raise FileNotFoundError(f"no correction_report_neutral.json under {d}")
    rep = json.loads(Path(rep_path[0]).read_text(encoding="utf-8"))
    return ex, off, rep["radiance_model"]


def run_session(name, ex, off, consts, a, rng):
    t_obj, t_app = make_model(consts)
    px = ex["rtd_pixel"]
    T_app, eps, tau = px["T_app"], px["eps_used"], px["tau"]
    T_air = off["air_temp_c"]
    T_wall = off["reference_c"]
    bias_rep = ex["bias_applied_c"]
    pct = off["offset_by_percentile_c"]
    half_pct = (pct["p15"] - pct["p5"]) / 2.0
    T_app_wall = t_app(T_wall, a.eps_wall, tau, T_air, T_air)

    def model(d_eps=0.0, d_epsw=0.0, d_refl=0.0, d_tau=0.0, d_air=0.0, d_netd=0.0, d_pct=0.0):
        Ta = T_air + d_air
        Tr = Ta + d_refl
        t = tau + d_tau
        To = t_obj(T_app + d_netd, eps + d_eps, t, Tr, Ta)
        Tw = t_obj(T_app_wall, a.eps_wall + d_epsw, t, Tr, Ta)
        bias = Tw + d_pct - Ta
        return To - bias

    base = float(model())
    N = a.n
    inputs = {
        "eps_surface": ("d_eps", "R", a.h_eps),
        "eps_wall": ("d_epsw", "R", a.h_eps),
        "T_refl": ("d_refl", "R", a.h_refl),
        "tau": ("d_tau", "R", a.h_tau),
        "T_air": ("d_air", "R", a.h_air),
        "NETD": ("d_netd", "N", a.netd),
        "offset_percentile": ("d_pct", "R", half_pct),
    }

    def draw(kind, w):
        return rng.uniform(-w, w, N) if kind == "R" else rng.normal(0.0, w, N)

    contrib = {}
    for key, (arg, kind, w) in inputs.items():
        contrib[key] = float(np.std(model(**{arg: draw(kind, w)}) - base))
    y = model(**{arg: draw(kind, w) for arg, kind, w in inputs.values()})
    uc = float(np.std(y))
    lo, hi = np.percentile(y, [2.5, 97.5])

    # emissivity contribution vs. surface-to-surroundings difference (door-like geometry)
    eps_vs_dT = {}
    for dT in a.delta_t:
        To = T_air + dT
        Ta_syn = t_app(To, eps, tau, T_air, T_air)
        eps_vs_dT[str(dT)] = float(np.std(t_obj(Ta_syn, eps + draw("R", a.h_eps), tau, T_air, T_air) - To))

    return {
        "session": name,
        "T_corr_model_c": base,
        "T_corr_pipeline_c": px["T_corr"],
        "T_corr_model_minus_pipeline_c": base - (px["T_obj_after_eps"] - bias_rep),
        "rtd_c": off.get("thermocouple_c"),
        "half_width_offset_percentile_c": half_pct,
        "contributions_k": contrib,
        "u_combined_k": uc,
        "U_expanded_k2_k": 2 * uc,
        "interval_95_c": [float(lo), float(hi)],
        "eps_contribution_vs_dT_k": eps_vs_dT,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--runs-dir", required=True, help="RawSignalResult\\runs")
    p.add_argument("--sessions", nargs="+", default=["A1", "A9"])
    p.add_argument("--n", type=int, default=400_000, help="Monte Carlo draws")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--eps-wall", type=float, default=0.94, help="lookup emissivity of the wall (paint)")
    p.add_argument("--h-eps", type=float, default=0.025, help="half-width of eps (rectangular)")
    p.add_argument("--h-refl", type=float, default=1.0, help="half-width of T_refl - T_air [K]")
    p.add_argument("--h-tau", type=float, default=0.0035, help="half-width of tau (RH 30-70 %%)")
    p.add_argument("--h-air", "--u-air", dest="h_air", type=float, default=0.5,
                   help="half-width of the rectangular air thermometer error [K], "
                        "u = h/sqrt(3) (--u-air is a legacy alias; check datasheet)")
    p.add_argument("--netd", type=float, default=0.05, help="camera NETD, std [K] (check datasheet)")
    p.add_argument("--delta-t", type=float, nargs="+", default=[6.0, 20.0])
    p.add_argument("--out", default=None, help="optional JSON output")
    a = p.parse_args()

    rng = np.random.default_rng(a.seed)
    runs = Path(a.runs_dir)
    results = []
    for s in a.sessions:
        ex, off, consts = load_session(runs, s)
        r = run_session(s, ex, off, consts, a, rng)
        results.append(r)
        print(f"== {s}: T_corr model {r['T_corr_model_c']:.3f} C (pipeline {r['T_corr_pipeline_c']:.3f}), RTD {r['rtd_c']}")
        for k, v in r["contributions_k"].items():
            print(f"   {k:18s} {v:.3f} K")
        print(f"   u_c = {r['u_combined_k']:.3f} K   U(k=2) = {r['U_expanded_k2_k']:.2f} K   "
              f"95% [{r['interval_95_c'][0]:.2f}, {r['interval_95_c'][1]:.2f}] C")
        print("   eps contribution vs dT:", {k: round(v, 3) for k, v in r["eps_contribution_vs_dT_k"].items()})
    if a.out:
        Path(a.out).write_text(json.dumps({"settings": vars(a), "results": results}, indent=1), encoding="utf-8")
        print("written", a.out)


if __name__ == "__main__":
    main()
