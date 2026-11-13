"""Per-pixel uncertainty u(T) of the corrected temperature, with the emissivity
treated as an uncertain quantity (a distribution over candidate materials).

For every frame of one session, the corrected temperature is recomputed with the
pipeline's own functions (radiometric_correction/radiometric: Planck model,
correct_temperature, transmittance) and the per-session offset that
estimate_offset.py --apply subtracted. The script never changes the corrected
temperature: it checks that it reproduces corrected_temperature_neutral_debiased
and stops otherwise.

Emissivity distribution per segment (segments.json of the consensus material map):
    p_m   = CLIP scores in top_k, renormalised (scores after the category prior).
            If the applied (consensus) material is not in top_k, it is added with
            p = consensus agreement and the CLIP scores are scaled by (1 - agreement).
            Optional --confusion CSV (evaluate.py output, rows = predicted, columns =
            ground truth): p_true(m) = sum_j p_clip(j) P(true m | pred j) for the
            predicted classes present in the matrix; CLIP as-is for the others.
            Candidates whose correction is not plausible (correct_session.py rule:
            >= 99 % of the segment's pixels in [t-min, t-max]) are dropped.
    eps_m = lookup emissivity; u_m from the table's emissivity range (rectangular).
    u_eps^2 = sum_m p_m [ u_m^2 + (T_m - T_corr)^2 ]   (second moment about the
            reported T_corr, which is the value the pipeline keeps)

Other inputs (same values as uncertainty_mc.py), linearised by central differences:
    T_air ±0.5 K R (T_refl and T_atm follow it, bias recomputed), T_refl - T_air ±1 K R,
    tau from RH 30-70 % R (pixel and wall), NETD 0.05 K N, wall percentile
    (p15 - p5)/2 R, wall emissivity ±0.025 R.
    Wall model as in uncertainty_mc.py: the wall's apparent temperature is
    back-computed from reference_c with eps_wall and the tau at the RTD-pixel distance.
    u_c = RSS of all terms; u_sys = RSS without NETD (used for voxels, see
    voxel_uncertainty.py).

Outputs (existing files are never overwritten unless --overwrite):
    <session-dir>/emissivity_map/<stem>/uncertainty_map_neutral.npy    u_c [K]
    <session-dir>/emissivity_map/<stem>/uncertainty_sys_neutral.npy    u_c without NETD
    <session-dir>/emissivity_map/<stem>/uncertainty_netd_neutral.npy   NETD term
    <session-dir>/emissivity_map/<stem>/uncertainty_gate_flag_neutral.npy   (--uncertainty-gate)
    <out-dir>/examined_frame_<stem>_components.npz    every term, examined frame
    <out-dir>/uncertainty_summary.json

Usage:
    py uncertainty_map.py --session-dir ...\\RawSignalResult\\work\\A1
        --flir-dir ...\\RawSignalResult\\neutral_npy\\session_A1_rot180
        --material-map-dir ...\\Zed\\20260911_094055\\fullrate\\material_map_consensus
        --run-dir ...\\RawSignalResult\\runs\\A1 --uncertainty-gate
"""

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "radiometric_correction"))
from radiometric import PlanckRadianceModel, correct_temperature, transmittance  # noqa: E402
from radiometric.radiance import PLANCK_KEYS  # noqa: E402

DEFAULT_TABLE = REPO / "emissivity" / "emissivity_table.csv"
SQ3 = np.sqrt(3.0)
SQ12 = np.sqrt(12.0)
TERMS = ("eps", "T_air", "T_refl", "tau", "NETD", "offset_percentile", "eps_wall")


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--session-dir", required=True, help="RawSignalResult\\work\\<S> (sync_manifest.json, emissivity_map/)")
    p.add_argument("--flir-dir", required=True, help="neutral rot180 .npy folder")
    p.add_argument("--material-map-dir", required=True, help="material_map_consensus of the session")
    p.add_argument("--run-dir", required=True, help="RawSignalResult\\runs\\<S> (offset_report_neutral.json, extracts.json)")
    p.add_argument("--out-dir", default=None, help="default <run-dir>\\uncertainty")
    p.add_argument("--tag", default="neutral", help="suffix of the pipeline files (default neutral)")
    p.add_argument("--table", default=str(DEFAULT_TABLE))
    p.add_argument("--confusion", default=None, help="confusion CSV from evaluate.py (rows predicted, cols true)")
    # input uncertainties, same defaults as uncertainty_mc.py
    p.add_argument("--h-air", type=float, default=0.5, help="half-width T_air [K]")
    p.add_argument("--h-refl", type=float, default=1.0, help="half-width T_refl - T_air [K]")
    p.add_argument("--rh-range", type=float, nargs=2, default=[30.0, 70.0], help="RH range [%%] for tau")
    p.add_argument("--netd", type=float, default=0.05, help="NETD std [K]")
    p.add_argument("--eps-wall", type=float, default=0.94)
    p.add_argument("--h-eps-wall", type=float, default=0.025)
    p.add_argument("--t-min", type=float, default=-20.0)
    p.add_argument("--t-max", type=float, default=80.0)
    p.add_argument("--min-plausible-frac", type=float, default=0.99)
    # gate
    p.add_argument("--uncertainty-gate", action="store_true",
                   help="evaluate the uncertainty-based low-emissivity gate (analysis only; T_corr unchanged)")
    p.add_argument("--gate-max-u", type=float, default=1.0, help="accept a low-eps material only if u(T) < this [K]")
    p.add_argument("--low-emissivity-max", type=float, default=0.5)
    p.add_argument("--what-if", nargs="*", default=[], metavar="MATERIAL",
                   help="u(T) on the RTD segment of the examined frame if MATERIAL were the call (p = 1)")
    p.add_argument("--overwrite", action="store_true", help="replace this script's own outputs")
    return p.parse_args()


def load_table(path):
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            lo, hi = (float(x) for x in r["emissivity_range"].split("-"))
            out[r["material"]] = (float(r["emissivity"]), lo, hi)
    return out


def load_confusion(path):
    """{predicted: {true: P(true | predicted)}} from an evaluate.py confusion CSV."""
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    cols = rows[0][1:]
    out = {}
    for r in rows[1:]:
        counts = np.array([float(x or 0) for x in r[1:]])
        if counts.sum() > 0:
            out[r[0]] = dict(zip(cols, counts / counts.sum()))
    return out


class Model:
    """T_corr as a function of every uncertain input (pipeline functions)."""

    def __init__(self, consts, T_air, rh, offset, wall_ref_c, eps_wall, d_wall):
        self.m = PlanckRadianceModel(*(consts[k] for k in PLANCK_KEYS))
        self.T_air, self.rh, self.offset = T_air, rh, offset
        self.eps_wall, self.d_wall = eps_wall, d_wall
        tw = transmittance(d_wall, rh, T_air)
        self.T_app_wall = self.t_app(wall_ref_c, eps_wall, tw, T_air, T_air)
        self.bias_nom = self.bias()

    def t_obj(self, T_app, eps, tau, T_refl, T_atm):
        return correct_temperature(T_app, eps, tau, T_refl, T_atm, model=self.m)

    def t_app(self, T_obj, eps, tau, T_refl, T_atm):
        m = self.m
        return m.temperature(eps * tau * m.radiance(T_obj) + (1 - eps) * tau * m.radiance(T_refl)
                             + (1 - tau) * m.radiance(T_atm))

    def bias(self, d_air=0.0, d_refl=0.0, rh=None, d_epsw=0.0):
        Ta = self.T_air + d_air
        tw = transmittance(self.d_wall, self.rh if rh is None else rh, self.T_air)
        return float(self.t_obj(self.T_app_wall, self.eps_wall + d_epsw, tw, Ta + d_refl, Ta)) - Ta

    def t_corr(self, T_app, eps, tau, d_air=0.0, d_refl=0.0, tau_rh=None, rh=None, d_epsw=0.0, d_netd=0.0):
        Ta = self.T_air + d_air
        t = tau if tau_rh is None else tau_rh
        T_obj = self.t_obj(T_app + d_netd, eps, t, Ta + d_refl, Ta)
        return T_obj - self.offset - (self.bias(d_air, d_refl, rh, d_epsw) - self.bias_nom)

    def components(self, T_app, eps, tau, tau_lo, tau_hi, a):
        """Standard uncertainties [K] of every term except eps (and the percentile constant)."""
        rh_lo, rh_hi = a.rh_range
        f = lambda **kw: self.t_corr(T_app, eps, tau, **kw)  # noqa: E731
        return {
            "T_air": np.abs(f(d_air=a.h_air) - f(d_air=-a.h_air)) / (2 * SQ3),
            "T_refl": np.abs(f(d_refl=a.h_refl) - f(d_refl=-a.h_refl)) / (2 * SQ3),
            "tau": np.abs(f(tau_rh=tau_hi, rh=rh_hi) - f(tau_rh=tau_lo, rh=rh_lo)) / SQ12,
            "NETD": np.abs(f(d_netd=a.netd) - f(d_netd=-a.netd)) / 2,
            "eps_wall": np.abs(f(d_epsw=a.h_eps_wall) - f(d_epsw=-a.h_eps_wall)) / (2 * SQ3),
        }


def candidate_probs(seg, table, confusion):
    """[(material, p)] sorted by p, and whether the applied material was added."""
    clip = {}
    for m, c in seg.get("top_k", []):
        if m in table:
            clip[m] = clip.get(m, 0.0) + float(c)
    if confusion:
        cal = {}
        for j, pj in clip.items():
            row = confusion.get(j)
            if row is None:
                cal[j] = cal.get(j, 0.0) + pj
            else:
                for m, q in row.items():
                    if m in table and q > 0:
                        cal[m] = cal.get(m, 0.0) + pj * q
        allowed = seg.get("allowed_materials")
        if allowed:
            cal = {m: v for m, v in cal.items() if m in allowed} or cal
        clip = cal
    tot = sum(clip.values())
    p = {m: v / tot for m, v in clip.items()} if tot > 0 else {}
    applied = seg["top_material"]
    added = applied not in p
    if added:
        agree = float((seg.get("consensus") or {}).get("agreement", 1.0 if not p else 0.5))
        p = {m: v * (1 - agree) for m, v in p.items()}
        p[applied] = agree if p else 1.0
    return sorted(p.items(), key=lambda kv: -kv[1]), added


def eps_term(model, T_app, tau, T_corr, cands, table, a):
    """u_eps [K] over the given pixels, the candidates kept, and per-candidate T."""
    per = []
    for m, pm in cands:
        e, lo, hi = table[m]
        T_obj = model.t_obj(T_app, e, tau, model.T_air, model.T_air)
        frac = float(np.mean((T_obj >= a.t_min) & (T_obj <= a.t_max)))
        if frac < a.min_plausible_frac:
            continue
        T_m = T_obj - model.offset
        u_m = np.abs(model.t_obj(T_app, lo, tau, model.T_air, model.T_air)
                     - model.t_obj(T_app, hi, tau, model.T_air, model.T_air)) / SQ12
        per.append((m, pm, T_m, u_m))
    if not per:
        return np.full(T_app.shape, np.nan), [], []
    w = np.array([q for _m, q, _t, _u in per])
    w = w / w.sum()
    second = sum(wi * (u ** 2 + (t - T_corr) ** 2) for wi, (_m, _q, t, u) in zip(w, per))
    kept = [(m, float(wi)) for wi, (m, *_r) in zip(w, per)]
    return np.sqrt(second), kept, per


def stats(v):
    v = np.asarray(v, dtype=float)
    v = v[np.isfinite(v)]
    if not v.size:
        return None
    return {"median": round(float(np.median(v)), 4), "p95": round(float(np.percentile(v, 95)), 4),
            "max": round(float(v.max()), 4), "n": int(v.size)}


def main():
    a = parse_args()
    session = Path(a.session_dir)
    emis = session / "emissivity_map"
    flir = Path(a.flir_dir)
    matdir = Path(a.material_map_dir)
    run = Path(a.run_dir)
    out = Path(a.out_dir) if a.out_dir else run / "uncertainty"
    tag = a.tag
    table = load_table(a.table)
    confusion = load_confusion(a.confusion) if a.confusion else None

    ex = json.loads((run / "extracts.json").read_text(encoding="utf-8"))
    off = json.loads((run / f"offset_report_{tag}.json").read_text(encoding="utf-8"))
    px = ex["rtd_pixel"]
    examined = px["frame"]
    rx, ry = px["pixel_xy_matlab_1based"]
    rtd_rc = (ry - 1, rx - 1)
    T_rtd = off.get("thermocouple_c")
    pct = off["offset_by_percentile_c"]
    u_pct = (pct["p15"] - pct["p5"]) / 2.0 / SQ3

    manifest = json.loads((session / "sync_manifest.json").read_text(encoding="utf-8"))
    stems = [Path(t["flir"]["file"]).stem for t in manifest["triplets"]]
    stems = [s for s in stems if (emis / s / f"corrected_temperature_{tag}_debiased.npy").exists()]
    if not stems:
        sys.exit(f"no corrected_temperature_{tag}_debiased.npy under {emis}")

    names = [f"uncertainty_map_{tag}.npy", f"uncertainty_sys_{tag}.npy", f"uncertainty_netd_{tag}.npy"]
    if a.uncertainty_gate:
        names.append(f"uncertainty_gate_flag_{tag}.npy")
    targets = [emis / s / n for s in stems for n in names]
    targets += [out / "uncertainty_summary.json", out / f"examined_frame_{examined}_components.npz"]
    existing = [t for t in targets if t.exists()]
    if existing and not a.overwrite:
        sys.exit(f"{len(existing)} output file(s) already exist (e.g. {existing[0]}); pass --overwrite "
                 "to replace this script's own outputs")
    out.mkdir(parents=True, exist_ok=True)

    rep0 = json.loads((emis / stems[0] / f"correction_report_{tag}.json").read_text(encoding="utf-8"))
    cond = rep0["conditions"]
    T_air, rh = float(cond["air_temp_c"]), float(cond["humidity_pct"])
    if abs(float(cond["reflected_temp_c"]) - T_air) > 1e-9:
        sys.exit("reflected temperature != air temperature in the correction report: not supported")
    d_wall = float(px["distance_m"])

    all_u, all_usys, all_term = [], [], {k: [] for k in TERMS}
    by_mat, by_ade = {}, {}
    max_check, offsets = 0.0, []
    n_seg = n_added = n_eps_mismatch = n_seg_nocand = 0
    gate_rows, examined_info, rtd_info, what_if = [], None, None, []

    for stem in stems:
        fdir = emis / stem
        rep = json.loads((fdir / f"correction_report_{tag}.json").read_text(encoding="utf-8"))
        consts = rep["radiance_model"]
        corr = np.load(fdir / f"corrected_temperature_{tag}.npy").astype(np.float64)
        deb = np.load(fdir / f"corrected_temperature_{tag}_debiased.npy").astype(np.float64)
        offset = float(np.nanmedian(corr - deb))
        offsets.append(offset)
        model = Model(consts, T_air, rh, offset, off["reference_c"], a.eps_wall, d_wall)

        T_app = np.load(flir / f"{stem.replace('_R', '')}.npy").astype(np.float64)
        dist = np.load(fdir / "distance.npy").astype(np.float64)
        sid_map = np.load(fdir / "segment_id.npy")
        eps_used = np.load(fdir / f"emissivity_used_{tag}.npy").astype(np.float64)
        segs = {int(s["id"]): s for s in
                json.loads((matdir / stem / "segments.json").read_text(encoding="utf-8"))["segments"]}

        tau = transmittance(dist, rh, T_air)
        tau_lo = transmittance(dist, a.rh_range[0], T_air)
        tau_hi = transmittance(dist, a.rh_range[1], T_air)
        valid = np.isfinite(deb)

        T_corr = model.t_corr(T_app, eps_used, tau)
        diff = np.abs(T_corr - deb)[valid]
        max_check = max(max_check, float(diff.max()) if diff.size else 0.0)

        terms = model.components(T_app, eps_used, tau, tau_lo, tau_hi, a)
        terms["offset_percentile"] = np.full(T_app.shape, u_pct)
        terms["eps"] = np.full(T_app.shape, np.nan)
        flag = np.zeros(T_app.shape, dtype=np.uint8)
        seg_records = []

        for sid in np.unique(sid_map):
            sid = int(sid)
            mask = (sid_map == sid) & valid
            seg = segs.get(sid)
            if seg is None or not mask.any():
                continue
            n_seg += 1
            cands, added = candidate_probs(seg, table, confusion)
            n_added += added
            applied = seg["top_material"]
            if applied in table and abs(table[applied][0] - float(np.median(eps_used[mask]))) > 1e-6:
                n_eps_mismatch += 1
            u_eps, kept, per = eps_term(model, T_app[mask], tau[mask], T_corr[mask], cands, table, a)
            if not kept:
                n_seg_nocand += 1
            terms["eps"][mask] = u_eps
            u_other = np.sqrt(sum(terms[k][mask] ** 2 for k in TERMS if k != "eps"))
            seg_u = np.sqrt(u_eps ** 2 + u_other ** 2)
            seg_records.append({
                "segment_id": sid, "ade": seg.get("ade"), "applied": applied,
                "applied_added_to_topk": added, "n_pixels": int(mask.sum()),
                "p": [(m, round(q, 4)) for m, q in kept],
                "T_m_median_c": {m: round(float(np.median(t)), 3) for m, _q, t, _u in per},
                "u_eps_median_k": round(float(np.median(u_eps)), 4),
                "u_c_median_k": round(float(np.median(seg_u)), 4),
            })

            if a.uncertainty_gate:
                # same ranking for both rules: candidates by p (before the plausibility drop,
                # as the gates in the pipeline see the ranking)
                fixed = next((m for m, _q in cands if table[m][0] >= a.low_emissivity_max), None)
                unc, rejected = None, []
                for m, _q in cands:
                    e, lo, hi = table[m]
                    if e >= a.low_emissivity_max:
                        unc = m
                        break
                    tm = model.components(T_app[mask], e, tau[mask], tau_lo[mask], tau_hi[mask], a)
                    um = np.abs(model.t_obj(T_app[mask], lo, tau[mask], T_air, T_air)
                                - model.t_obj(T_app[mask], hi, tau[mask], T_air, T_air)) / SQ12
                    u_low = float(np.median(np.sqrt(um ** 2 + u_pct ** 2 + sum(v ** 2 for v in tm.values()))))
                    if u_low < a.gate_max_u:
                        unc = m
                        break
                    rejected.append((m, round(u_low, 3)))
                if rejected:
                    flag[mask] = 1
                has_low = any(table[m][0] < a.low_emissivity_max for m, _q in cands)
                gate_rows.append({"frame": stem, "segment_id": sid, "has_low_eps_candidate": has_low,
                                  "fixed_rule": fixed, "uncertainty_rule": unc,
                                  "changed": fixed != unc, "rejected_low_eps": rejected})

        u_c = np.sqrt(sum(terms[k] ** 2 for k in TERMS))
        u_sys = np.sqrt(sum(terms[k] ** 2 for k in TERMS if k != "NETD"))
        for arr in (u_c, u_sys, terms["NETD"]):
            arr[~valid] = np.nan
        for k in TERMS:
            terms[k][~valid] = np.nan

        np.save(fdir / names[0], u_c.astype(np.float32))
        np.save(fdir / names[1], u_sys.astype(np.float32))
        np.save(fdir / names[2], terms["NETD"].astype(np.float32))
        if a.uncertainty_gate:
            np.save(fdir / names[3], flag)

        all_u.append(u_c[valid].astype(np.float32))
        all_usys.append(u_sys[valid].astype(np.float32))
        for k in TERMS:
            all_term[k].append(terms[k][valid].astype(np.float32))
        for s in seg_records:
            mask = (sid_map == s["segment_id"]) & valid
            by_mat.setdefault(s["applied"], []).append(u_c[mask].astype(np.float32))
            by_ade.setdefault(s["ade"] or "?", []).append(u_c[mask].astype(np.float32))

        if stem == examined:
            np.savez_compressed(out / f"examined_frame_{stem}_components.npz",
                                u_c=u_c.astype(np.float32), u_sys=u_sys.astype(np.float32),
                                T_corr=T_corr.astype(np.float32),
                                **{f"u_{k}": terms[k].astype(np.float32) for k in TERMS})
            r, c = rtd_rc
            rsid = int(sid_map[r, c])
            T_px = float(T_corr[r, c])
            u_px = float(u_c[r, c])
            rtd_info = {
                "frame": stem, "pixel_rc_0based": [r, c], "segment_id": rsid,
                "T_corr_c": round(T_px, 4), "T_corr_pipeline_c": round(float(deb[r, c]), 4),
                "T_rtd_c": T_rtd, "error_k": round(T_px - T_rtd, 4) if T_rtd is not None else None,
                "u_c_k": round(u_px, 4), "U_k2_k": round(2 * u_px, 4),
                "within_2u": bool(abs(T_px - T_rtd) <= 2 * u_px) if T_rtd is not None else None,
                "components_k": {k: round(float(terms[k][r, c]), 4) for k in TERMS},
                "segment": next((s for s in seg_records if s["segment_id"] == rsid), None),
            }
            examined_info = {
                "frame": stem, "u_c": stats(u_c), "segments": seg_records,
                "components_median_k": {k: stats(terms[k])["median"] for k in TERMS},
            }
            mask = (sid_map == rsid) & valid
            for mname in a.what_if:
                e, lo, hi = table[mname]
                Tm = model.t_corr(T_app[mask], e, tau[mask])
                tm = model.components(T_app[mask], e, tau[mask], tau_lo[mask], tau_hi[mask], a)
                um = np.abs(model.t_obj(T_app[mask], lo, tau[mask], T_air, T_air)
                            - model.t_obj(T_app[mask], hi, tau[mask], T_air, T_air)) / SQ12
                uu = np.sqrt(um ** 2 + u_pct ** 2 + sum(v ** 2 for v in tm.values()))
                k_px = (int(np.searchsorted(np.flatnonzero(mask.ravel()), r * mask.shape[1] + c))
                        if mask[r, c] else None)
                what_if.append({
                    "material": mname, "emissivity": e, "range": [lo, hi],
                    "segment_id": rsid, "n_pixels": int(mask.sum()),
                    "T_corr_rtd_px_c": round(float(Tm[k_px]), 3) if k_px is not None else None,
                    "u_c_rtd_px_k": round(float(uu[k_px]), 3) if k_px is not None else None,
                    "error_vs_rtd_k": round(float(Tm[k_px]) - T_rtd, 3) if k_px is not None and T_rtd else None,
                    "T_corr_segment_median_c": round(float(np.nanmedian(Tm)), 3),
                    "u_c_segment_median_k": round(float(np.nanmedian(uu)), 3),
                    "components_rtd_px_k": ({"eps_lookup": round(float(um[k_px]), 3),
                                             **{k: round(float(v[k_px]), 3) for k, v in tm.items()},
                                             "offset_percentile": round(u_pct, 3)} if k_px is not None else None),
                    "uncertainty_gate": "accept" if float(np.nanmedian(uu)) < a.gate_max_u else "reject",
                    "fixed_gate_0.5": "accept" if e >= a.low_emissivity_max else "reject",
                })
        print(f"{stem}: u_c median {np.nanmedian(u_c):.3f} K, max {np.nanmax(u_c):.3f} K, "
              f"check |dT| {diff.max() if diff.size else 0:.2e}")

    if max_check > 1e-3:
        sys.exit(f"recomputed T_corr differs from corrected_temperature_{tag}_debiased by {max_check:.4f} K")

    cat = lambda xs: np.concatenate(xs) if xs else np.array([])  # noqa: E731
    summary = {
        "schema": "uncertainty_map/v1",
        "generated_by": "UncertaintyAnalysis/uncertainty_map.py",
        "command": " ".join(sys.argv),
        "session": run.name,
        "settings": {k: v for k, v in vars(a).items()},
        "conditions": {"T_air_c": T_air, "rh_pct": rh, "T_refl_c": T_air, "offset_applied_c": round(offsets[0], 5),
                       "offset_spread_over_frames_c": round(max(offsets) - min(offsets), 6),
                       "wall_reference_c": off["reference_c"], "wall_tau_distance_m": d_wall,
                       "u_offset_percentile_k": round(u_pct, 4)},
        "eps_distribution": {
            "source": "CLIP top_k of segments.json (after category prior), renormalised" +
                      (f"; calibrated with confusion {a.confusion}" if confusion else "; no confusion calibration"),
            "n_segments": n_seg, "n_applied_added_to_topk": n_added,
            "n_segments_eps_used_differs_from_table": n_eps_mismatch,
            "n_segments_without_plausible_candidate": n_seg_nocand,
        },
        "check_max_abs_diff_vs_pipeline_k": max_check,
        "n_frames": len(stems),
        "rtd_pixel": rtd_info,
        "examined_frame": examined_info,
        "session_u_c": stats(cat(all_u)),
        "session_u_sys": stats(cat(all_usys)),
        "session_components": {k: stats(cat(v)) for k, v in all_term.items()},
        "by_material": {m: stats(cat(v)) for m, v in sorted(by_mat.items())},
        "by_ade": {m: stats(cat(v)) for m, v in sorted(by_ade.items())},
        "what_if": what_if,
    }
    if a.uncertainty_gate:
        summary["gate"] = {
            "rule": f"low-eps (< {a.low_emissivity_max}) material accepted only if median u(T) < {a.gate_max_u} K",
            "n_segments": len(gate_rows),
            "n_with_low_eps_candidate": sum(r["has_low_eps_candidate"] for r in gate_rows),
            "n_changed_vs_fixed_0.5": sum(r["changed"] for r in gate_rows),
            "n_flagged": sum(bool(r["rejected_low_eps"]) for r in gate_rows),
            "changed": [r for r in gate_rows if r["changed"] or r["rejected_low_eps"]],
        }
    (out / "uncertainty_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"\nsession u_c {summary['session_u_c']}; check max |dT| {max_check:.2e} K")
    if rtd_info:
        print(f"RTD pixel: T_corr {rtd_info['T_corr_c']} C, u_c {rtd_info['u_c_k']} K, "
              f"e {rtd_info['error_k']} K, within 2u: {rtd_info['within_2u']}")
    print(f"wrote {out / 'uncertainty_summary.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
