"""Validate playhead marks against the exact preview that produced them."""
from __future__ import annotations

import math


def marked_bounds(event: object, *, token: str, preview_start: float,
                  preview_end: float, start: float, end: float,
                  source_duration: float) -> tuple[float, float]:
    if not isinstance(event, dict) or event.get("token") != token:
        raise ValueError("This mark belongs to an older preview. Try again.")
    position = event.get("position")
    if isinstance(position, bool) or not isinstance(position, (int, float)):
        raise ValueError("The player has no valid position yet.")
    if not math.isfinite(position) or not 0 <= position <= preview_end - preview_start:
        raise ValueError("The playhead must stay inside the current preview.")
    boundary = round(preview_start + position, 3)
    boundary = min(preview_end, max(preview_start, boundary))
    if event.get("action") == "in":
        start = boundary
    elif event.get("action") == "out":
        end = boundary
    else:
        raise ValueError("Unknown preview mark.")
    if not all(math.isfinite(v) for v in (start, end, source_duration)):
        raise ValueError("Clip boundaries must be finite.")
    if not 0 <= start < end <= source_duration or end - start < 0.1 - 1e-9:
        raise ValueError("Mark not applied: the end must be at least 0.1 seconds after the start and inside the VOD.")
    return start, end
