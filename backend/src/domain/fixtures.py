"""Seed a repeatable destructive-test pilot with batch drift and redundant channels."""

import csv
import sys
from random import Random

from .settings import COLUMNS, FEATURES, PRIORITY_RECORD, TARGET

DEMO_SEED = 20261125


def demo_rows() -> list[dict]:
    rng = Random(DEMO_SEED)
    rows = []
    for split, prefix, batches, size in (
        ("train", "T", 12, 12), ("holdout", "V", 3, 10), ("pending", "P", 2, 6),
    ):
        for order in range(1, batches + 1):
            batch = f"ZP-{prefix}{order:02d}"
            drift = rng.uniform(-0.5, 0.5)
            jaw_offset = rng.uniform(-0.07, 0.07)
            for index in range(1, size + 1):
                gap = rng.uniform(-1.5, 1.5) + drift + (0.4 if split == "pending" and order == 2 else 0)
                crimp = rng.uniform(-1.6, 1.6) - drift * 0.3
                spring = rng.uniform(-1.4, 1.4)
                micrometer = 0.8 + 0.13 * gap
                laser = micrometer + rng.uniform(-0.22, 0.22)
                readings = (
                    micrometer, 1.55 + 0.2 * crimp, 23 + 4 * spring, laser,
                    2.45 + rng.uniform(-0.06, 0.06), 0.19 + jaw_offset + rng.uniform(-0.06, 0.06),
                    10.2 + rng.uniform(-2.2, 2.2), 24 + 1.2 * drift + rng.uniform(-2, 2),
                    6.1 + rng.uniform(-0.3, 0.3),
                )
                force = 117 - 11 * gap + 9 * crimp + 6 * spring + 3 * drift + rng.uniform(-2.5, 2.5)
                row = {"id": f"{batch}-{index:02d}", "batch_id": batch, "split": split,
                       **dict(zip(FEATURES, (round(v, 4) for v in readings)))}
                row[TARGET] = None if split == "pending" else round(force, 3)
                row[PRIORITY_RECORD] = None
                rows.append(row)
    return rows


if __name__ == "__main__":
    writer = csv.DictWriter(sys.stdout, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(demo_rows())
