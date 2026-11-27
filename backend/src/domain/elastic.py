"""Fit standardized Elastic Net with cyclic coordinate descent on training data."""

from dataclasses import dataclass
from math import fsum, sqrt

from .settings import TARGET

MIN_SCALE = 1e-12
KKT_TOLERANCE = 1e-8
MAX_SWEEPS = 10_000


@dataclass(frozen=True)
class Fit:
    features: tuple[str, ...]
    centers: tuple[float, ...]
    scales: tuple[float, ...]
    coefficients: tuple[float, ...]
    intercept: float

    def predict(self, row: dict) -> float:
        return self.intercept + fsum(
            weight * ((row[field] - center) / scale)
            for field, center, scale, weight in zip(self.features, self.centers, self.scales, self.coefficients)
            if weight
        )


def covariance(left: list[float], right: list[float]) -> float:
    return fsum(a * b for a, b in zip(left, right)) / len(left)


def standardize(rows: list[dict], feature: str) -> tuple[float, float, list[float]]:
    center = fsum(row[feature] for row in rows) / len(rows)
    centered = [row[feature] - center for row in rows]
    scale = sqrt(covariance(centered, centered))
    column = [value / scale for value in centered] if scale > MIN_SCALE else [0.0] * len(rows)
    return center, scale, column


def soft_threshold(value: float, penalty: float) -> float:
    return max(0.0, value - penalty) if value >= 0 else min(0.0, value + penalty)


def solve(gram: list[list[float]], correlation: list[float], l1: float, l2: float) -> tuple[float, ...]:
    weights = [0.0] * len(correlation)
    for _ in range(MAX_SWEEPS):
        largest_change = 0.0
        for index, (cross, row) in enumerate(zip(correlation, gram)):
            other_points = fsum(
                value * weights[j] for j, value in enumerate(row) if j != index
            )
            partial = cross - other_points
            updated = soft_threshold(partial, l1) / (row[index] + l2)
            largest_change = max(largest_change, abs(updated - weights[index]))
            weights[index] = updated
        if largest_change <= KKT_TOLERANCE:
            gradients = (
                fsum(a * b for a, b in zip(row, weights)) + l2 * weight - cross
                for row, weight, cross in zip(gram, weights, correlation)
            )
            residual = max(
                abs(weight - soft_threshold(weight - gradient, l1))
                for weight, gradient in zip(weights, gradients)
            )
            if residual <= KKT_TOLERANCE:
                return tuple(weights)
    raise ValueError("Elastic Net 未收敛，请提高惩罚强度或降低 L1 占比后重试。")


def fit(rows: list[dict], features: tuple[str, ...], alpha: float, l1_ratio: float) -> Fit:
    intercept = fsum(row[TARGET] for row in rows) / len(rows)
    if not features:
        return Fit((), (), (), (), intercept)
    centers, scales, columns = zip(*(standardize(rows, feature) for feature in features))
    targets = [row[TARGET] - intercept for row in rows]
    gram = [[covariance(left, right) for right in columns] for left in columns]
    cross = [covariance(column, targets) for column in columns]
    weights = solve(gram, cross, alpha * l1_ratio, alpha * (1 - l1_ratio))
    return Fit(features, centers, scales, weights, intercept)
