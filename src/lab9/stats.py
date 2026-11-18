"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    if len(human) != len(judge):
        raise ValueError("human and judge must have equal lengths")
    h = [str(x).strip().upper() == POS for x in human]
    j = [str(x).strip().upper() == POS for x in judge]
    return {
        "tp": sum(a and b for a, b in zip(h, j)),
        "fp": sum(not a and b for a, b in zip(h, j)),
        "fn": sum(a and not b for a, b in zip(h, j)),
        "tn": sum(not a and not b for a, b in zip(h, j)),
    }


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    cm = confusion(human, judge)
    p_den, r_den = cm["tp"] + cm["fp"], cm["tp"] + cm["fn"]
    return (cm["tp"] / p_den if p_den else 0.0,
            cm["tp"] / r_den if r_den else 0.0)


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """kappa = (p_o - p_e) / (1 - p_e). Raise ValueError when undefined (p_e == 1):
    a constant judge has no signal and must FAIL calibration, not pass on a technicality."""
    if len(human) != len(judge):
        raise ValueError("human and judge must have equal lengths")
    n = len(human)
    if n == 0:
        raise ValueError("kappa is undefined for an empty sample")
    h = [str(x).strip().upper() == POS for x in human]
    j = [str(x).strip().upper() == POS for x in judge]
    observed = sum(a == b for a, b in zip(h, j)) / n
    ph, pj = sum(h) / n, sum(j) / n
    expected = ph * pj + (1 - ph) * (1 - pj)
    if expected == 1:
        raise ValueError("kappa is undefined when expected agreement is 1")
    return (observed - expected) / (1 - expected)


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Correct an observed failure rate for judge error; clip to [0, 1]."""
    denom = sensitivity + specificity - 1
    if denom <= 0:
        raise ValueError("sensitivity and specificity must have positive Youden index")
    return min(1.0, max(0.0, (observed_rate + specificity - 1) / denom))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    if len(a) != len(b):
        raise ValueError("paired samples must have equal lengths")
    if not a:
        raise ValueError("paired samples must not be empty")
    import numpy as np
    from scipy.stats import bootstrap

    aa, bb = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    delta = float(np.mean(aa - bb))
    if np.all(aa == bb):
        return 0.0, 0.0, 0.0
    result = bootstrap((aa, bb), lambda x, y, axis: np.mean(x - y, axis=axis),
                       paired=True, vectorized=True, n_resamples=n_resamples,
                       confidence_level=confidence, method="percentile",
                       rng=np.random.default_rng(rng))
    return delta, float(result.confidence_interval.low), float(result.confidence_interval.high)


def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    import math
    if n <= 0 or c < 0 or c > n or k <= 0:
        raise ValueError("require n > 0, 0 <= c <= n and k > 0")
    if k > n:
        raise ValueError("k cannot exceed n")
    return 1.0 - (math.comb(n - c, k) / math.comb(n, k))


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    import math
    if n <= 0 or c < 0 or c > n or k <= 0:
        raise ValueError("require n > 0, 0 <= c <= n and k > 0")
    if k > n:
        raise ValueError("k cannot exceed n")
    return math.comb(c, k) / math.comb(n, k)
