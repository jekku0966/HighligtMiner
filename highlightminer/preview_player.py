"""Self-contained local preview player with explicit playhead mark events."""
from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

_player = components.declare_component(
    "highlightminer_preview_marks", path=str(Path(__file__).with_name("preview_component"))
)


@st.cache_data(max_entries=2, show_spinner=False)
def _preview_data(path: str, size: int, modified_ns: int) -> str:
    # Only the generated lightweight clip is embedded, never the source VOD.
    return "data:video/mp4;base64," + base64.b64encode(Path(path).read_bytes()).decode("ascii")


def preview_player(path: Path, *, token: str, key: str, duration: float, ack: str | None = None,
                   disabled: bool = False):
    stat = path.stat()
    return _player(src=_preview_data(str(path), stat.st_size, stat.st_mtime_ns),
                   token=token, duration=duration, ack=ack, disabled=disabled, key=key, default=None)
