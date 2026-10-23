"""Planck radiance model: round trip and agreement with the T^4 model.

Run from radiometric_correction/:  py -m pytest tests -q
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from radiometric import (  # noqa: E402
    PlanckRadianceModel,
    RadianceModel,
    StefanBoltzmannModel,
    correct_temperature,
)

# Synthetic constants of the same order as a FLIR microbolometer calibration.
SYNTHETIC = [
    (15000.0, 0.05, 1400.0, 1.0, -500),
    (20000.0, 0.06, 1500.0, 1.2, 300),
]


@pytest.mark.parametrize("constants", SYNTHETIC)
def test_round_trip(constants):
    model = PlanckRadianceModel(*constants)
    t = np.linspace(-30.0, 120.0, 301)
    np.testing.assert_allclose(model.temperature(model.radiance(t)), t, rtol=0, atol=1e-6)


@pytest.mark.parametrize("constants", SYNTHETIC)
def test_planck_vs_t4_correction(constants):
    args = dict(apparent_temp=26.83, emissivity=0.94, tau=0.98,
                reflected_temp=20.5, air_temp=20.5)
    t_planck = correct_temperature(**args, model=PlanckRadianceModel(*constants))
    t_t4 = correct_temperature(**args, model=StefanBoltzmannModel())
    assert abs(t_planck - t_t4) < 0.01


def test_invalid_signal_is_nan():
    model = PlanckRadianceModel(*SYNTHETIC[0])
    o = SYNTHETIC[0][4]
    t = model.temperature(np.array([-o - 1.0, -o, model.radiance(20.0)]))
    assert np.isnan(t[0]) and np.isnan(t[1])
    assert t[2] == pytest.approx(20.0, abs=1e-6)


def test_radiance_model_alias():
    assert RadianceModel is StefanBoltzmannModel
