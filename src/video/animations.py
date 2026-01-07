from __future__ import annotations

import math
from typing import Callable, Tuple

# =========================================================
# TYPES
# =========================================================

Point = Tuple[int, int]
FloatPoint = Tuple[float, float]
EasingFn = Callable[[float], float]


# =========================================================
# EASING FUNCTIONS
# =========================================================


def linear(t: float) -> float:
    return t


def ease_out_cubic(t: float) -> float:
    return 1 - pow(1 - t, 3)


def ease_in_out_cubic(t: float) -> float:
    if t < 0.5:
        return 4 * t * t * t
    return 1 - pow(-2 * t + 2, 3) / 2


def ease_out_back(t: float) -> float:
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)


# =========================================================
# CORE INTERPOLATION
# =========================================================


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_point(
    start: FloatPoint,
    end: FloatPoint,
    t: float,
    easing: EasingFn = ease_out_cubic,
) -> Point:
    t = max(0.0, min(1.0, t))
    t = easing(t)
    x = lerp(start[0], end[0], t)
    y = lerp(start[1], end[1], t)
    return int(x), int(y)


# =========================================================
# SLIDE-IN ANIMATIONS
# =========================================================


def slide_from_top(
    final_pos: Point,
    progress: float,
    offset: int = 200,
    easing: EasingFn = ease_out_cubic,
) -> Point:
    start = (final_pos[0], final_pos[1] - offset)
    return lerp_point(start, final_pos, progress, easing)


def slide_from_bottom(
    final_pos: Point,
    progress: float,
    offset: int = 200,
    easing: EasingFn = ease_out_cubic,
) -> Point:
    start = (final_pos[0], final_pos[1] + offset)
    return lerp_point(start, final_pos, progress, easing)


def slide_from_left(
    final_pos: Point,
    progress: float,
    offset: int = 300,
    easing: EasingFn = ease_out_cubic,
) -> Point:
    start = (final_pos[0] - offset, final_pos[1])
    return lerp_point(start, final_pos, progress, easing)


def slide_from_right(
    final_pos: Point,
    progress: float,
    offset: int = 300,
    easing: EasingFn = ease_out_cubic,
) -> Point:
    start = (final_pos[0] + offset, final_pos[1])
    return lerp_point(start, final_pos, progress, easing)


def slide_from_angle(
    final_pos: Point,
    progress: float,
    angle_deg: float,
    distance: int = 300,
    easing: EasingFn = ease_out_cubic,
) -> Point:
    """
    Slide element in from an arbitrary angle (degrees).
    0° = from right
    90° = from bottom
    180° = from left
    270° = from top
    """
    rad = math.radians(angle_deg)
    dx = math.cos(rad) * distance
    dy = math.sin(rad) * distance
    start = (final_pos[0] + dx, final_pos[1] + dy)
    return lerp_point(start, final_pos, progress, easing)


# =========================================================
# FADE / SCALE HELPERS
# =========================================================


def fade_in(progress: float) -> int:
    """
    Returns alpha 0–255
    """
    p = max(0.0, min(1.0, progress))
    return int(255 * ease_out_cubic(p))


def scale_in(
    progress: float,
    start_scale: float = 0.85,
    end_scale: float = 1.0,
    easing: EasingFn = ease_out_back,
) -> float:
    p = max(0.0, min(1.0, progress))
    return lerp(start_scale, end_scale, easing(p))


# =========================================================
# TIMER HELPERS
# =========================================================


def countdown_value(
    total_seconds: int,
    elapsed_seconds: float,
) -> int:
    """
    Returns remaining whole seconds.
    Example: 15s → 14s → ... → 1s
    """
    remaining = total_seconds - int(elapsed_seconds)
    return max(0, remaining)


def countdown_text(
    total_seconds: int,
    elapsed_seconds: float,
) -> str:
    return f"{countdown_value(total_seconds, elapsed_seconds)}s"


# =========================================================
# STAGGERING
# =========================================================


def stagger_progress(
    global_progress: float,
    index: int,
    stagger_delay: float,
    duration: float,
) -> float:
    """
    Calculates local animation progress for staggered items.
    """
    start = index * stagger_delay
    end = start + duration

    if global_progress <= start:
        return 0.0
    if global_progress >= end:
        return 1.0

    return (global_progress - start) / duration
