from __future__ import annotations

from typing import Optional


def safe_div(numer: Optional[float], denom: Optional[float]) -> Optional[float]:
    if numer is None or denom is None:
        return None
    if denom == 0:
        return None
    return numer / denom


def weighted_efficiency_score(
    *,
    yprr: Optional[float],
    epa_per_target: Optional[float],
    target_share: Optional[float],
) -> Optional[float]:
    """
    Simple, explicit composite score.

    This is intentionally transparent + easy to audit; adjust weights as desired.
    """
    if yprr is None and epa_per_target is None and target_share is None:
        return None

    y = yprr or 0.0
    e = epa_per_target or 0.0
    s = target_share or 0.0
    return (0.6 * y) + (1.5 * e) + (5.0 * s)


