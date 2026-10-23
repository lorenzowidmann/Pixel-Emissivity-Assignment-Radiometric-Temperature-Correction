"""Radiance <-> temperature conversion.

Two models share one interface (temperatures in deg C at the interface,
numpy-vectorized, NaN where the inverse is undefined):

- PlanckRadianceModel: the camera's own Planck calibration, the default of
  correct_session.py / main.py. With T in kelvin,

      S(T) = R1 / (R2*(exp(B/T) - F)) - O
      T    = B / ln( R1 / (R2*(S + O)) + F )

  R1, R2, B, F, O are read from the FLIR radiometric JPEG metadata via flyr
  (from_flir_image). The sign of O follows flyr 5.1.0 (thermogram.py,
  `plancked`): O is *subtracted* in S(T); O itself is stored as a signed int
  and is negative on this camera.
- StefanBoltzmannModel: radiation proportional to the 4th power of the
  absolute temperature, the approximation used before the Planck constants
  were read. Kept for comparison (--radiance-model t4); RadianceModel is a
  backward-compatible alias of it.
"""

import numpy as np

ZERO_C = 273.15  # 0 deg C in Kelvin

PLANCK_KEYS = ("planck_r1", "planck_r2", "planck_b", "planck_f", "planck_o")


class StefanBoltzmannModel:
    """T^4 radiance model. Temperatures are in deg C at the interface."""

    name = "t4"

    def radiance(self, temp_c):
        """Relative radiance W(T) for temperature(s) in deg C."""
        t_k = np.asarray(temp_c, dtype=float) + ZERO_C
        return t_k**4

    def temperature(self, w):
        """Inverse W^-1: temperature(s) in deg C from relative radiance."""
        w = np.asarray(w, dtype=float)
        w = np.where(w > 0, w, np.nan)
        return w**0.25 - ZERO_C


RadianceModel = StefanBoltzmannModel  # backward-compatible name


class PlanckRadianceModel:
    """FLIR Planck calibration. Temperatures are in deg C at the interface,
    the signal is in the camera's raw units."""

    name = "planck"

    def __init__(self, r1: float, r2: float, b: float, f: float, o: float):
        self.r1 = float(r1)
        self.r2 = float(r2)
        self.b = float(b)
        self.f = float(f)
        self.o = float(o)

    @classmethod
    def from_flir_image(cls, path):
        """Constants from the metadata of a full FLIR radiometric JPEG."""
        import flyr

        try:
            meta = flyr.unpack(str(path)).metadata
        except Exception as exc:
            raise ValueError(
                f"Cannot read FLIR metadata from {path} (stripped copy?): {exc}"
            ) from exc
        missing = [k for k in PLANCK_KEYS if k not in meta]
        if missing:
            raise ValueError(f"{path}: FLIR metadata lacks {', '.join(missing)}")
        return cls(*(meta[k] for k in PLANCK_KEYS))

    def constants(self) -> dict:
        return dict(zip(PLANCK_KEYS, (self.r1, self.r2, self.b, self.f, self.o)))

    def radiance(self, temp_c):
        """Raw signal S(T) for temperature(s) in deg C."""
        t_k = np.asarray(temp_c, dtype=float) + ZERO_C
        t_k = np.where(t_k > 0, t_k, np.nan)
        return self.r1 / (self.r2 * (np.exp(self.b / t_k) - self.f)) - self.o

    def temperature(self, signal):
        """Inverse S^-1: temperature(s) in deg C from raw signal."""
        s = np.asarray(signal, dtype=float) + self.o
        with np.errstate(divide="ignore", invalid="ignore"):
            arg = self.r1 / (self.r2 * np.where(s > 0, s, np.nan)) + self.f
            arg = np.where(arg > 1, arg, np.nan)
            return self.b / np.log(arg) - ZERO_C
