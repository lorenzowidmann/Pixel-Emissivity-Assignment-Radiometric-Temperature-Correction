"""Per-voxel uncertainty u_c, added as columns to the session's voxel map.

Runs the pipeline's own voxel code (emissivity/voxel_consensus.py --stage thermal,
same bag, voxel size, projection and NaN mask as the voxel_map_<tag> run) twice,
on the per-pixel maps written by uncertainty_map.py:
    uncertainty_sys_<tag>.npy   -> mean u_sys per voxel  (T_air, T_refl, tau, offset,
                                   wall emissivity, emissivity: correlated within a
                                   voxel, NOT reduced by averaging)
    uncertainty_netd_<tag>.npy  -> mean NETD term per voxel, divided by sqrt(n_obs)
and joins them with <run-dir>/voxel_map_<tag>/thermal_voxels.csv on (x, y, z):
    u_c = sqrt(u_sys^2 + (u_netd_px / sqrt(n_obs))^2)
The voxel set and n_obs must be identical to thermal_voxels.csv (checked).

Outputs (in <out-dir>, default <run-dir>/uncertainty; never overwritten unless --overwrite):
    voxel_usys/, voxel_unetd/      raw voxel_consensus.py outputs (t_mean_c = mean u)
    thermal_voxels_u.csv           thermal_voxels.csv + u_sys_k, u_netd_k, u_c_k
    voxel_summary.json             distribution, by material, RTD voxel(s)

Usage:
    py voxel_uncertainty.py --session-dir ...\\RawSignalResult\\work\\A1 --bag ...\\Lidar\\rosbag2_...
        --material-map-dir ...\\material_map_consensus --run-dir ...\\RawSignalResult\\runs\\A1
        --rtd-voxels ...\\RawSignalResult\\rtd_voxels.json --session A1
"""

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
VOXEL_CONSENSUS = REPO / "emissivity" / "voxel_consensus.py"


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--session-dir", required=True)
    p.add_argument("--bag", required=True)
    p.add_argument("--material-map-dir", required=True)
    p.add_argument("--run-dir", required=True)
    p.add_argument("--rtd-voxels", required=True, help="RawSignalResult\\rtd_voxels.json")
    p.add_argument("--session", required=True, help="key in rtd_voxels.json (A1, A9, A10)")
    p.add_argument("--out-dir", default=None)
    p.add_argument("--tag", default="neutral")
    p.add_argument("--voxel", type=float, default=0.20)
    p.add_argument("--radius", type=float, default=0.5, help="RTD neighbourhood radius [m]")
    p.add_argument("--skip-passes", action="store_true", help="reuse existing voxel_usys/voxel_unetd")
    p.add_argument("--overwrite", action="store_true")
    return p.parse_args()


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def key_of(row):
    return (row["x"], row["y"], row["z"])


def stats(v):
    v = np.asarray(v, dtype=float)
    v = v[np.isfinite(v)]
    if not v.size:
        return None
    return {"median": round(float(np.median(v)), 4), "p95": round(float(np.percentile(v, 95)), 4),
            "max": round(float(v.max()), 4), "n": int(v.size)}


def group(rows, T_rtd):
    """n_obs-weighted mean T of several voxels and its u_c (u_sys correlated, NETD over all samples)."""
    n = np.array([r["n_obs"] for r in rows], dtype=float)
    w = n / n.sum()
    T = float(np.sum(w * [r["t_mean_c"] for r in rows]))
    u_sys = float(np.sum(w * [r["u_sys_k"] for r in rows]))
    netd_px = np.array([r["u_netd_k"] * np.sqrt(r["n_obs"]) for r in rows])
    u_netd = float(np.sum(n * netd_px) / n.sum() / np.sqrt(n.sum()))
    u_c = float(np.hypot(u_sys, u_netd))
    e = T - T_rtd
    return {"n_voxels": len(rows), "n_obs": int(n.sum()), "T_c": round(T, 3), "u_c_k": round(u_c, 4),
            "U_k2_k": round(2 * u_c, 4), "error_k": round(e, 3), "within_2u": bool(abs(e) <= 2 * u_c),
            "T_min_c": round(min(r["t_mean_c"] for r in rows), 3),
            "T_max_c": round(max(r["t_mean_c"] for r in rows), 3)}


def main():
    a = parse_args()
    session = Path(a.session_dir)
    run = Path(a.run_dir)
    out = Path(a.out_dir) if a.out_dir else run / "uncertainty"
    tag = a.tag
    base_csv = run / f"voxel_map_{tag}" / "thermal_voxels.csv"
    outs = [out / "thermal_voxels_u.csv", out / "voxel_summary.json"]
    passes = {"usys": f"uncertainty_sys_{tag}.npy", "unetd": f"uncertainty_netd_{tag}.npy"}
    if not a.skip_passes:
        outs += [out / f"voxel_{k}" for k in passes]
    existing = [p for p in outs if p.exists()]
    if existing and not a.overwrite:
        sys.exit(f"already exists: {existing[0]} (pass --overwrite, or --skip-passes to reuse the voxel passes)")
    out.mkdir(parents=True, exist_ok=True)

    commands = []
    for k, name in passes.items():
        cmd = [sys.executable, str(VOXEL_CONSENSUS), "--stage", "thermal", "--session-dir", str(session),
               "--bag", a.bag, "--voxel", str(a.voxel), "--emissivity-map-dir", str(session / "emissivity_map"),
               "--material-map-dir", a.material_map_dir, "--corrected-name", name,
               "--out-dir", str(out / f"voxel_{k}")]
        commands.append(" ".join(f'"{c}"' if " " in c else c for c in cmd))
        if a.skip_passes:
            continue
        print(f"voxel pass {k}: {name}")
        with open(out / f"log_voxel_{k}.txt", "w", encoding="utf-8") as log:
            rc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT).returncode
        if rc:
            sys.exit(f"voxel_consensus.py failed for {name}, see {out / f'log_voxel_{k}.txt'}")

    base = read_csv(base_csv)
    usys = {key_of(r): r for r in read_csv(out / "voxel_usys" / "thermal_voxels.csv")}
    unetd = {key_of(r): r for r in read_csv(out / "voxel_unetd" / "thermal_voxels.csv")}
    keys = [key_of(r) for r in base]
    if set(keys) != set(usys) or set(keys) != set(unetd):
        sys.exit(f"voxel sets differ: base {len(keys)}, u_sys {len(usys)}, u_netd {len(unetd)}")
    bad_n = sum(r["n_obs"] != usys[key_of(r)]["n_obs"] or r["n_obs"] != unetd[key_of(r)]["n_obs"] for r in base)
    if bad_n:
        sys.exit(f"n_obs differs on {bad_n} voxel(s)")

    rows = []
    for r in base:
        k = key_of(r)
        n = int(r["n_obs"])
        u_sys = float(usys[k]["t_mean_c"])
        u_netd = float(float(unetd[k]["t_mean_c"]) / np.sqrt(n))
        rows.append({**r, "u_sys_k": round(u_sys, 4), "u_netd_k": round(u_netd, 5),
                     "u_c_k": round(float(np.hypot(u_sys, u_netd)), 4)})
    with open(out / "thermal_voxels_u.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # numeric view for the summary
    num = [{"x": float(r["x"]), "y": float(r["y"]), "z": float(r["z"]), "t_mean_c": float(r["t_mean_c"]),
            "n_obs": int(r["n_obs"]), "material": r["material"], "u_sys_k": r["u_sys_k"],
            "u_netd_k": r["u_netd_k"], "u_c_k": r["u_c_k"]} for r in rows]
    for r in num:
        r["key"] = tuple(int(round(c / a.voxel - 0.5)) for c in (r["x"], r["y"], r["z"]))
    by_key = {r["key"]: r for r in num}
    u_all = np.array([r["u_c_k"] for r in num])
    mats = sorted({r["material"] for r in num})

    rtd = json.loads(Path(a.rtd_voxels).read_text(encoding="utf-8"))[a.session]
    off = json.loads((run / f"offset_report_{tag}.json").read_text(encoding="utf-8"))
    T_rtd = off["thermocouple_c"]
    p_rtd = np.array(rtd["rtd_world_xyz"])
    vk = tuple(rtd["voxel_key"])
    d = {r["key"]: float(np.linalg.norm(np.array([r["x"], r["y"], r["z"]]) - p_rtd)) for r in num}
    nearest = min(num, key=lambda r: d[r["key"]])
    neigh = [by_key[(vk[0] + i, vk[1] + j, vk[2] + k)] for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1)
             if (vk[0] + i, vk[1] + j, vk[2] + k) in by_key]
    within = [r for r in num if d[r["key"]] <= a.radius]

    def one(r):
        e = r["t_mean_c"] - T_rtd
        return {"key": list(r["key"]), "material": r["material"], "n_obs": r["n_obs"], "T_c": r["t_mean_c"],
                "distance_to_rtd_m": round(d[r["key"]], 3), "u_sys_k": r["u_sys_k"], "u_netd_k": r["u_netd_k"],
                "u_c_k": r["u_c_k"], "U_k2_k": round(2 * r["u_c_k"], 4), "error_k": round(e, 3),
                "within_2u": bool(abs(e) <= 2 * r["u_c_k"])}

    top = sorted(num, key=lambda r: -r["u_c_k"])[:10]
    summary = {
        "schema": "voxel_uncertainty/v1",
        "generated_by": "UncertaintyAnalysis/voxel_uncertainty.py",
        "command": " ".join(sys.argv),
        "voxel_pass_commands": commands,
        "session": a.session,
        "n_voxels": len(num),
        "checks": {"same_voxel_set": True, "same_n_obs": True},
        "T_rtd_c": T_rtd,
        "u_c": stats(u_all),
        "u_sys": stats([r["u_sys_k"] for r in num]),
        "u_netd": stats([r["u_netd_k"] for r in num]),
        "by_material": {m: stats([r["u_c_k"] for r in num if r["material"] == m]) for m in mats},
        "largest_u": [{"key": list(r["key"]), "material": r["material"], "n_obs": r["n_obs"],
                       "T_c": r["t_mean_c"], "u_c_k": r["u_c_k"]} for r in top],
        "rtd": {
            "voxel_key": list(vk),
            "rtd_voxel": one(by_key[vk]) if vk in by_key else None,
            "nearest_voxel": one(nearest),
            "neighbourhood_3x3x3": group(neigh, T_rtd) if neigh else None,
            f"within_{a.radius}m": group(within, T_rtd) if within else None,
        },
    }
    (out / "voxel_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"{len(num)} voxels, u_c {summary['u_c']}")
    print(f"RTD voxel {vk}: {summary['rtd']['rtd_voxel']}")
    print(f"wrote {out / 'thermal_voxels_u.csv'}, {out / 'voxel_summary.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
