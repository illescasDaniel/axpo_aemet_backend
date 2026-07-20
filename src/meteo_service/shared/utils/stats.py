from collections.abc import Iterable
from statistics import mean


def optional_mean(values: Iterable[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return mean(present) if present else None
