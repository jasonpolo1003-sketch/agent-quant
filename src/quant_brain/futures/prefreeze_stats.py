"""Pre-freeze inference plumbing for synthetic paired daily series only.

This module reads no files and never accesses licensed or held-out data. The
bootstrap is a proposed method pending statistical freeze review.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence


def stationary_indices(n_days: int, length: int, *, mean_block: int, seed: int) -> list[int]:
    """Circular stationary bootstrap; continuation probability = 1 - 1/L."""
    if n_days < 1 or length < 1 or mean_block < 1:
        raise ValueError("positive sample, path length, and mean block required")
    rng = random.Random(seed)
    index = rng.randrange(n_days)
    result: list[int] = []
    for _ in range(length):
        if result:
            index = rng.randrange(n_days) if rng.random() < 1 / mean_block else (index + 1) % n_days
        result.append(index)
    return result


def paired_one_sided_bootstrap(
    strategy: Sequence[float],
    controls: Sequence[float],
    *,
    seed: int,
    replicates: int = 999,
    mean_block: int = 5,
) -> dict[str, float | bool]:
    """Upper-tail test of paired mean > 0, resampling null-centered days.

    `controls` is ONE prespecified daily aggregate of the controls, not 500
    independent observations. This routine is for synthetic pipeline tests
    until its null construction and selection treatment are approved.
    """
    if len(strategy) != len(controls) or len(strategy) < 2:
        raise ValueError("paired series need equal length >= 2")
    if replicates < 19:
        raise ValueError("too few resamples")
    if any(not math.isfinite(float(x)) for x in (*strategy, *controls)):
        raise ValueError("nonfinite input")
    differences = [float(a) - float(b) for a, b in zip(strategy, controls)]
    observed = math.fsum(differences) / len(differences)
    null_centered = [x - observed for x in differences]
    exceedances = 0
    for i in range(replicates):
        indices = stationary_indices(
            len(differences), len(differences), mean_block=mean_block, seed=seed + i
        )
        mean = math.fsum(null_centered[j] for j in indices) / len(indices)
        exceedances += mean >= observed - 1e-12
    p_value = (exceedances + 1) / (replicates + 1)
    return {"observed_difference": observed, "p_value": p_value, "reject_at_005": p_value < 0.05}
