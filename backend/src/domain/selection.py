"""Estimate inclusion frequencies on intact historical batches and allocate collection time."""

from collections import defaultdict
from dataclasses import dataclass
from math import ceil, fsum
from random import Random

from .elastic import fit
from .settings import FEATURES, POINTS, RESAMPLE_SEED

NONZERO_TOLERANCE = 1e-6


@dataclass(frozen=True)
class Candidate:
    feature: str
    hits: int
    frequency: float
    mean_abs_coef: float
    cost: int
    status: str


def point_plan(train: list[dict], options: dict) -> tuple[list[Candidate], list[dict]]:
    grouped = defaultdict(list)
    for row in train:
        grouped[row["batch_id"]].append(row)
    batches = sorted(grouped)
    subset_size = min(len(batches) - 1, ceil(0.7 * len(batches)))
    rng = Random(RESAMPLE_SEED)
    weights = [[] for _ in FEATURES]
    trace = []
    for iteration in range(1, options["resamples"] + 1):
        members = sorted(rng.sample(batches, subset_size))
        sample = [row for batch in members for row in grouped[batch]]
        model = fit(sample, FEATURES, options["alpha"], options["l1_ratio"])
        active = []
        for feature, magnitude, weight in zip(FEATURES, weights, model.coefficients):
            magnitude.append(abs(weight))
            if abs(weight) > NONZERO_TOLERANCE:
                active.append(feature)
        trace.append({"iteration": iteration, "batch_ids": ";".join(members), "rows": len(sample),
                      "active_points": ";".join(active)})

    total = options["resamples"]
    scored = []
    for feature, magnitude in zip(FEATURES, weights):
        hits = sum(value > NONZERO_TOLERANCE for value in magnitude)
        scored.append((feature, hits, fsum(magnitude) / total, POINTS[feature][1]))
    scored.sort(key=lambda entry: (-entry[1], -round(entry[2], 8), entry[3], entry[0]))
    remaining = options["budget_seconds"]
    plan = []
    for feature, hits, impact, cost in scored:
        frequency = hits / total
        if frequency < options["min_frequency"]:
            status = "below_frequency"
        elif cost > remaining:
            status = "over_budget"
        else:
            status = "selected"
            remaining -= cost
        plan.append(Candidate(feature, hits, frequency, impact, cost, status))
    return plan, trace
