"""FLIR input guard: neutral .npy pass, stored-settings .npy stop the run.

The flyr reader is replaced by a fake one, so no FLIR JPEG is needed.
Run from radiometric_correction/:  py -m pytest tests -q
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import flir_input_guard as guard  # noqa: E402

STEMS = [f"20251019_1659{i:02d}_R" for i in range(5)]


def fake_reader(jpg):
    """Deterministic 'neutral' map per frame, not rotation-symmetric."""
    seed = int(Path(jpg).stem.split("_")[1])
    return 20.0 + np.arange(12, dtype=np.float64).reshape(3, 4) * 0.1 + seed % 7


@pytest.fixture
def session(tmp_path):
    jpg_dir, flir_dir = tmp_path / "orig", tmp_path / "rot180"
    jpg_dir.mkdir()
    flir_dir.mkdir()
    for s in STEMS:
        (jpg_dir / f"{s}.jpg").write_bytes(b"")
        np.save(flir_dir / f"{s.replace('_R', '')}.npy",
                np.rot90(fake_reader(jpg_dir / f"{s}.jpg"), 2).astype(np.float32))
    return jpg_dir, flir_dir


def test_neutral_input_passes(session):
    jpg_dir, flir_dir = session
    results = guard.verify_or_exit(flir_dir, STEMS, [jpg_dir], reader=fake_reader)
    assert [r[0] for r in results] == [STEMS[0], STEMS[2], STEMS[4]]   # first, middle, last
    assert all(diff == 0.0 for _, diff in results)


def test_stored_settings_input_stops(session):
    jpg_dir, flir_dir = session
    npy = flir_dir / f"{STEMS[2].replace('_R', '')}.npy"
    np.save(npy, np.load(npy) + np.float32(0.6))      # what the stored settings add
    with pytest.raises(SystemExit) as exc:
        guard.verify_or_exit(flir_dir, STEMS, [jpg_dir], reader=fake_reader)
    assert "neutral settings" in str(exc.value) and STEMS[2] in str(exc.value)


def test_allow_stored_settings_warns(session, capsys):
    jpg_dir, flir_dir = session
    npy = flir_dir / f"{STEMS[0].replace('_R', '')}.npy"
    np.save(npy, np.load(npy) + np.float32(0.6))
    guard.verify_or_exit(flir_dir, STEMS, [jpg_dir], allow_stored_settings=True, reader=fake_reader)
    assert "WARNING" in capsys.readouterr().err


def test_unrotated_input_stops(session):
    jpg_dir, flir_dir = session
    for s in STEMS:
        np.save(flir_dir / f"{s.replace('_R', '')}.npy",
                fake_reader(jpg_dir / f"{s}.jpg").astype(np.float32))
    with pytest.raises(SystemExit):
        guard.verify_or_exit(flir_dir, STEMS, [jpg_dir], reader=fake_reader)
