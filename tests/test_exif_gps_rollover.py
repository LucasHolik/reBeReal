"""DMS rollover edge for the EXIF GPS rational converter."""

from __future__ import annotations

from rebereal.metadata.exif_writer import _deg_to_dms_rational


def test_just_below_integer_rolls_to_next_degree() -> None:
    d, m, s = _deg_to_dms_rational(12.9999999999)
    assert d == (13, 1)
    assert m == (0, 1)
    assert s == (0, 1000)


def test_no_rollover_for_clean_value() -> None:
    d, m, s = _deg_to_dms_rational(48.8566)
    assert d[0] == 48
    assert 0 <= m[0] < 60
    assert 0 <= s[0] < 60_000


def test_minute_only_rollover() -> None:
    # 12 deg + 59.9999... min => (12, 60, 0) raw -> (13, 0, 0) after cascade.
    deg = 12 + 59.99999999 / 60
    d, m, s = _deg_to_dms_rational(deg)
    assert d == (13, 1)
    assert m == (0, 1)
    assert s == (0, 1000)
