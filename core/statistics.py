from typing import List, Optional
import math

def calc_average(pings: List[Optional[float]]) -> float:
    valid = [p for p in pings if p is not None]
    if not valid:
        return float('inf')
    return sum(valid) / len(valid)

def calc_ema(pings: List[Optional[float]], window: int = 20) -> float:
    valid = [p for p in pings if p is not None]
    if not valid:
        return float('inf')
    alpha = 2 / (window + 1)
    ema = valid[0]
    for p in valid[1:]:
        ema = ema * (1 - alpha) + p * alpha
    return ema

def calc_uniformity(pings: List[Optional[float]]) -> float:
    valid = [p for p in pings if p is not None]
    if len(valid) < 2:
        return 0.0
    pmin = min(valid)
    pmax = max(valid)
    if pmax == 0:
        return 100.0
    return (pmin / pmax) * 100.0

def calc_density(pings: List[Optional[float]]) -> float:
    valid = [p for p in pings if p is not None]
    if not valid:
        return 0.0
    avg = sum(valid) / len(valid)
    if avg == 0:
        return 100.0
    return (min(valid) / avg) * 100.0

def calc_jitter(pings: List[Optional[float]]) -> float:
    valid = [p for p in pings if p is not None]
    if len(valid) < 2:
        return 0.0
    mean = sum(valid) / len(valid)
    variance = sum((p - mean) ** 2 for p in valid) / len(valid)
    return math.sqrt(variance)

def calc_loss_percent(pings: List[Optional[float]]) -> float:
    if not pings:
        return 0.0
    total = len(pings)
    lost = sum(1 for p in pings if p is None)
    return (lost / total) * 100.0

def get_all_stats(pings: List[Optional[float]], window: int = 20) -> dict:
    return {
        'avg': calc_average(pings),
        'ema': calc_ema(pings, window),
        'uniformity': calc_uniformity(pings),
        'density': calc_density(pings),
        'jitter': calc_jitter(pings),
        'loss': calc_loss_percent(pings),
        'count': len(pings),
    }
