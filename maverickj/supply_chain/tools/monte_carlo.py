from __future__ import annotations

import statistics

import numpy as np


def run_monte_carlo(mean: float, std_dev: float, simulations: int = 1000) -> dict:
    """Simple normal-demand Monte Carlo summary."""
    if simulations <= 0:
        raise ValueError("simulations must be > 0")
    if std_dev < 0:
        raise ValueError("std_dev must be >= 0")

    samples = np.random.normal(loc=mean, scale=std_dev, size=simulations)
    p50 = float(np.percentile(samples, 50))
    p95 = float(np.percentile(samples, 95))
    stockout_threshold = mean * 1.15
    overstock_threshold = mean * 0.85
    stockout_prob = float(np.mean(samples > stockout_threshold))
    overstock_prob = float(np.mean(samples < overstock_threshold))
    return {
        "simulations": simulations,
        "sample_mean": round(float(statistics.fmean(samples.tolist())), 2),
        "p50": round(p50, 2),
        "p95": round(p95, 2),
        "stockout_probability": round(stockout_prob, 4),
        "overstock_probability": round(overstock_prob, 4),
        "thresholds": {
            "stockout_threshold": round(stockout_threshold, 2),
            "overstock_threshold": round(overstock_threshold, 2),
        },
    }

