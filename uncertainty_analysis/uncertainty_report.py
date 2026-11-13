"""Print the uncertainty report (for the paper section) from the outputs of
uncertainty_map.py and voxel_uncertainty.py, and save the same text.

Reads <runs-dir>/<session>/uncertainty/{uncertainty_summary,voxel_summary}.json
and the benchmark labels (emissivity/ground_truth/ground_truth_m2f.csv).

Usage:
    py uncertainty_report.py --runs-dir ...\\RawSignalResult\\runs
    py uncertainty_report.py --runs-dir ... --sessions A1 A9 A10 --out ...\\uncertainty_report.txt
"""

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GT = REPO / "emissivity" / "ground_truth" / "ground_truth_m2f.csv"
LABEL = {"A1": "door, painted metal", "A9": "window, glass", "A10": "aluminum plate"}
TERMS = ("eps", "T_air", "T_refl", "tau", "NETD", "offset_percentile", "eps_wall")


def fmt_stats(s):
    return f"median {s['median']:.3f}  p95 {s['p95']:.3f}  max {s['max']:.3f} K" if s else "n/a"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--runs-dir", required=True)
    p.add_argument("--sessions", nargs="+", default=["A1", "A9", "A10"])
    p.add_argument("--ground-truth", default=str(GT))
    p.add_argument("--out", default=None, help="default <runs-dir>\\uncertainty_report.txt")
    p.add_argument("--overwrite", action="store_true")
    a = p.parse_args()
    runs = Path(a.runs_dir)
    out = Path(a.out) if a.out else runs / "uncertainty_report.txt"
    if out.exists() and not a.overwrite:
        sys.exit(f"{out} exists (pass --overwrite)")

    S = {s: json.loads((runs / s / "uncertainty" / "uncertainty_summary.json").read_text(encoding="utf-8"))
         for s in a.sessions}
    V = {s: json.loads((runs / s / "uncertainty" / "voxel_summary.json").read_text(encoding="utf-8"))
         for s in a.sessions}
    with open(a.ground_truth, newline="", encoding="utf-8") as f:
        gt = [r for r in csv.DictReader(f) if r["status"] == "labeled"]
    gt_counts = Counter(r["ground_truth"] for r in gt)

    L = []
    w = L.append
    first = S[a.sessions[0]]["settings"]
    w("=" * 78)
    w("UNCERTAINTY OF THE CORRECTED TEMPERATURE: PER PIXEL AND PER VOXEL")
    w("=" * 78)

    w("\n1. EMISSIVITY AS AN UNCERTAIN QUANTITY")
    w("Each segment gets a distribution over candidate materials m with probability p_m and")
    w("lookup emissivity eps_m (emissivity_table.csv). p_m = the CLIP scores stored in")
    w("segments.json (top_k, the 3 best materials after the category prior), renormalised.")
    w("When voxel consensus applied a material that is not in top_k, it is added with")
    w("p = consensus agreement and the CLIP scores are scaled by (1 - agreement).")
    w("Candidates whose correction is implausible (correct_session.py rule) are dropped.")
    w("For each candidate, T_m is computed with the pipeline's own inversion and offset.")
    w("  u_eps^2 = sum_m p_m [u_m^2 + (T_m - T_corr)^2],  u_m = |T(eps_lo) - T(eps_hi)|/sqrt(12)")
    w("(eps_lo..eps_hi = table range of material m, rectangular; the second moment is taken")
    w("about the reported T_corr, which is not changed).")
    w("\nConfusion matrix: NOT APPLIED. The benchmark predictions (session 20260730_161223,")
    w("run material_map_m2f) are not on this machine: searched GroundTruthFiles,")
    w("AcquistionGroundTruth and C:\\Users\\loren. ground_truth_m2f.csv holds only the")
    w("reference labels, so P(true | predicted) cannot be built. The calibration is")
    w("implemented (uncertainty_map.py --confusion confusion_prior-on.csv from evaluate.py).")
    w(f"Benchmark reference labels ({len(gt)} labelled regions): " +
      ", ".join(f"{m} {n}" for m, n in gt_counts.most_common()))
    w("Paper's summary for that benchmark (prior on): accuracy 0.696, macro F1 0.771,")
    w("0 regions with |d_eps| > 0.10; the confusions are among eps 0.90-0.95 non-metals.")
    w("Applied materials in A1/A9/A10:")
    for s in a.sessions:
        mats = sorted(S[s]["by_material"])
        e = S[s]["eps_distribution"]
        w(f"  {s}: applied {', '.join(mats)}; {e['n_segments']} segment-frames, "
          f"{e['n_applied_added_to_topk']} with the consensus material added to top_k")
    w("\nOther inputs (same as uncertainty_mc.py), linearised per pixel:")
    w(f"  T_air +-{first['h_air']} K R, T_refl - T_air +-{first['h_refl']} K R, tau from RH "
      f"{first['rh_range'][0]:.0f}-{first['rh_range'][1]:.0f} % R (per-pixel distance),")
    w(f"  NETD {first['netd']} K N, wall percentile (p15 - p5)/2 R, wall eps {first['eps_wall']} "
      f"+-{first['h_eps_wall']} R.")
    w("Voxels: mean of u_sys over the voxel's samples (not reduced) + NETD/sqrt(n_obs).")

    w("\n2. RTD LOCATION, PER SESSION")
    for s in a.sessions:
        r = S[s]["rtd_pixel"]
        v = V[s]["rtd"]
        w(f"\n{s} ({LABEL.get(s, '')}), T_RTD {r['T_rtd_c']} C, T_air {S[s]['conditions']['T_air_c']} C, "
          f"offset {S[s]['conditions']['offset_applied_c']:.3f} K")
        seg = r["segment"]
        w(f"  RTD pixel {r['frame']} rc {r['pixel_rc_0based']}: ADE {seg['ade']}, applied {seg['applied']}, "
          f"p = {', '.join(f'{m} {q:.3f}' for m, q in seg['p'])}")
        w(f"    T_corr {r['T_corr_c']:.3f} C  u_c {r['u_c_k']:.3f} K  U(k=2) {r['U_k2_k']:.2f} K  "
          f"e = T_corr - T_RTD {r['error_k']:+.3f} K  |e| <= 2u: {'yes' if r['within_2u'] else 'NO'}")
        w("    contributions [K]: " + ", ".join(f"{k} {r['components_k'][k]:.3f}" for k in TERMS))
        rv = v["rtd_voxel"]
        if rv:
            w(f"  RTD voxel {rv['key']} ({rv['material']}, n_obs {rv['n_obs']}): T {rv['T_c']:.3f} C  "
              f"u_c {rv['u_c_k']:.3f} K (u_sys {rv['u_sys_k']:.3f}, NETD/sqrt(n) {rv['u_netd_k']:.4f})  "
              f"e {rv['error_k']:+.3f} K  |e| <= 2u: {'yes' if rv['within_2u'] else 'NO'}")
        else:
            w(f"  RTD voxel {v['voxel_key']}: no voxel (no LiDAR return at the RTD point)")
        nv = v["nearest_voxel"]
        if not rv or nv["key"] != rv["key"]:
            w(f"  nearest voxel {nv['key']} ({nv['material']}, {nv['distance_to_rtd_m']} m, n_obs {nv['n_obs']}): "
              f"T {nv['T_c']:.3f} C  u_c {nv['u_c_k']:.3f} K  e {nv['error_k']:+.3f} K  "
              f"|e| <= 2u: {'yes' if nv['within_2u'] else 'NO'}")
        for name, g in v.items():
            if name in ("voxel_key", "rtd_voxel", "nearest_voxel") or not g:
                continue
            w(f"  {name} ({g['n_voxels']} voxels, n_obs-weighted): T {g['T_c']:.3f} C "
              f"[{g['T_min_c']:.2f}, {g['T_max_c']:.2f}]  u_c {g['u_c_k']:.3f} K  e {g['error_k']:+.3f} K  "
              f"|e| <= 2u: {'yes' if g['within_2u'] else 'NO'}")

    w("\n3. DISTRIBUTION OF u(T)")
    for s in a.sessions:
        x = S[s]
        w(f"\n{s}: examined frame {x['examined_frame']['frame']}: {fmt_stats(x['examined_frame']['u_c'])}")
        w(f"    all {x['n_frames']} frames (pixels): {fmt_stats(x['session_u_c'])}")
        w(f"    voxel map ({V[s]['n_voxels']} voxels): {fmt_stats(V[s]['u_c'])}")
        w("    session medians per term [K]: " +
          ", ".join(f"{k} {x['session_components'][k]['median']:.3f}" for k in TERMS))
        w("    per-term p95 [K]: " + ", ".join(f"{k} {x['session_components'][k]['p95']:.3f}" for k in TERMS))
        bm = sorted(((m, st) for m, st in x["by_material"].items() if st), key=lambda t: -t[1]["p95"])
        w("    by applied material (pixels, sorted by p95): " +
          "; ".join(f"{m} {st['median']:.3f}/{st['p95']:.3f}/{st['max']:.3f}" for m, st in bm))
        ba = sorted(((m, st) for m, st in x["by_ade"].items() if st and st["n"] > 1000), key=lambda t: -t[1]["p95"])[:5]
        w("    surfaces (ADE class, >1000 px) with largest p95: " +
          "; ".join(f"{m} {st['median']:.3f}/{st['p95']:.3f}/{st['max']:.3f}" for m, st in ba))
        vm = sorted(((m, st) for m, st in V[s]["by_material"].items() if st), key=lambda t: -t[1]["p95"])
        w("    voxels by material (median/p95/max): " +
          "; ".join(f"{m or '-'} {st['median']:.3f}/{st['p95']:.3f}/{st['max']:.3f}" for m, st in vm))
        segs = sorted(x["examined_frame"]["segments"], key=lambda t: -t["u_c_median_k"])[:3]
        w("    examined frame, segments with largest median u_c: " +
          "; ".join(f"#{t['segment_id']} {t['ade']}/{t['applied']} {t['u_c_median_k']:.3f} K "
                    f"(u_eps {t['u_eps_median_k']:.3f}, p {t['p'][0][0]} {t['p'][0][1]:.2f})" for t in segs))

    if "A10" in S:
        x = S["A10"]
        r = x["rtd_pixel"]
        seg = r["segment"]
        w("\n4. A10 ALUMINUM PLATE")
        w(f"  The plate is segmented as ADE '{seg['ade']}' (its prior group allows no bare metal). CLIP top_k "
          f"after the prior: {', '.join(f'{m} {q:.3f}' for m, q in seg['p'])}; consensus applied "
          f"{seg['applied']} (eps 0.92).")
        w(f"  As corrected: u_c at the RTD pixel {r['u_c_k']:.3f} K (u_eps {r['components_k']['eps']:.3f}), "
          f"segment median {seg['u_c_median_k']:.3f} K; e {r['error_k']:+.3f} K.")
        w("  The pipeline never offered aluminum, so neither gate saw it. What-if, p = 1:")
        for wi in x["what_if"]:
            c = wi["components_rtd_px_k"]
            w(f"   {wi['material']} (eps {wi['emissivity']}, range {wi['range'][0]}-{wi['range'][1]}): "
              f"T_corr {wi['T_corr_rtd_px_c']:.2f} C (e {wi['error_vs_rtd_k']:+.2f} K), "
              f"u_c {wi['u_c_rtd_px_k']:.2f} K (segment median {wi['u_c_segment_median_k']:.2f})")
            w("      terms: " + ", ".join(f"{k} {v:.3f}" for k, v in c.items()))
            w(f"      uncertainty gate (u < {first['gate_max_u']} K): {wi['uncertainty_gate'].upper()};  "
              f"fixed gate (eps >= {first['low_emissivity_max']}): {wi['fixed_gate_0.5'].upper()}")

    w("\n5. UNCERTAINTY GATE vs FIXED eps >= 0.5")
    for s in a.sessions:
        g = S[s].get("gate")
        if not g:
            w(f"  {s}: gate not evaluated")
            continue
        w(f"  {s}: {g['n_segments']} segment-frames, {g['n_with_low_eps_candidate']} with a low-eps candidate, "
          f"{g['n_changed_vs_fixed_0.5']} changed, {g['n_flagged']} flagged")
    w("  With the category prior on, no stored candidate has eps < 0.5, so the two rules")
    w("  agree everywhere on these sessions. The gate only matters without the prior, or")
    w("  for classes whose prior group permits a bare metal.")

    w("\n6. FILES WRITTEN")
    w("  per frame, next to corrected_temperature_neutral_debiased.npy in")
    w("  RawSignalResult\\work\\<S>\\emissivity_map\\<stem>\\: uncertainty_map_neutral.npy (u_c),")
    w("  uncertainty_sys_neutral.npy, uncertainty_netd_neutral.npy, uncertainty_gate_flag_neutral.npy")
    w("  RawSignalResult\\runs\\<S>\\uncertainty\\: uncertainty_summary.json,")
    w("  examined_frame_<stem>_components.npz, thermal_voxels_u.csv, voxel_summary.json,")
    w("  voxel_usys\\, voxel_unetd\\ (voxel_consensus.py outputs), log_voxel_*.txt")
    w(f"  {out}")
    w("\nCOMMANDS (light env C:\\venvs\\sensorfusion, run from PaperEmissivityCorrection\\)")
    def clean(cmd):
        parts = [x for x in cmd.split() if x not in ("--skip-passes", "--overwrite")]
        return "& $L " + " ".join(parts)
    w(r'  $L = "C:\venvs\sensorfusion\Scripts\python.exe"; $env:PYTHONDONTWRITEBYTECODE = 1')
    for s in a.sessions:
        w(f"  {clean(S[s]['command'])}")
        w(f"  {clean(V[s]['command'])}")
    w(f"  {clean(' '.join(sys.argv))}")
    w("  (voxel passes inside voxel_uncertainty.py: " + V[a.sessions[0]]["voxel_pass_commands"][0] + " ...)")

    w("\n7. ASSUMPTIONS AND WHAT COULD NOT BE DONE")
    w("  - No confusion-matrix calibration (benchmark predictions not available); p_m = CLIP scores.")
    w("  - Only the top 3 CLIP scores are stored; the remaining mass (median 0, at most 0.22) is ignored.")
    w("  - The consensus material, when missing from top_k, gets p = consensus agreement.")
    w("  - Lookup uncertainty of each material = its table range, rectangular.")
    w("  - u_eps is the second moment about the reported T_corr, not about the mixture mean.")
    w("  - Linearised propagation (central differences); for eps >= 0.9 this matches the")
    w("    Monte Carlo of uncertainty_mc.py at the RTD pixel (A9: 0.315 K both).")
    w("  - Wall model as in uncertainty_mc.py: one wall pixel with eps 0.94 at the RTD-pixel")
    w("    distance for tau; T_atm = T_air; tau's dependence on T_air ignored.")
    w("  - T_air +-0.5 K and NETD 0.05 K are assumed (datasheets not checked); the RTD")
    w("    uncertainty is not included in u_c.")
    w("  - Voxels: all terms except NETD fully correlated within a voxel (mean of u_sys).")
    w("  - A9 has no voxel at the RTD point (glass returns no LiDAR); nearest/neighbourhood voxels")
    w("    are window-frame voxels, not glass.")
    w("  - The uncertainty gate could not be exercised on real low-eps candidates: with the prior,")
    w("    none exists in A1/A9/A10. A10 is a what-if with aluminum forced as the call.")

    text = "\n".join(L)
    print(text)
    out.write_text(text + "\n", encoding="utf-8")
    print(f"\n(saved to {out})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
