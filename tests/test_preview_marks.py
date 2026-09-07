import pytest

from highlightminer.preview_marks import marked_bounds


def mark(action, position, **overrides):
    args = dict(token="a:1:100:130", preview_start=100.0, preview_end=130.0,
                start=100.0, end=130.0, source_duration=1000.0)
    args.update(overrides)
    return marked_bounds(dict(token="a:1:100:130", action=action, position=position), **args)


def test_marks_translate_preview_position_to_vod_and_preserve_other_boundary():
    start, end = mark("in", 4.25)
    assert (start, end) == (104.25, 130.0)
    assert mark("out", 22.5, start=start, end=end) == (104.25, 122.5)


def test_marks_use_displayed_preview_origin_after_unsaved_trim():
    assert mark("out", 25, start=110.0) == (110.0, 125.0)


@pytest.mark.parametrize("position", [None, "5", True, float("nan"), float("inf"), -1, 30.1])
def test_invalid_playhead_is_rejected(position):
    with pytest.raises(ValueError):
        mark("in", position)


@pytest.mark.parametrize("token", ["other-candidate", "a:1:105:125"])
def test_stale_candidate_or_rebuilt_preview_is_rejected(token):
    with pytest.raises(ValueError, match="older preview"):
        mark("in", 5, token=token)


@pytest.mark.parametrize("action,position", [("in", 30), ("out", 0), ("out", .099), ("unknown", 5)])
def test_invalid_ranges_and_actions_are_rejected(action, position):
    with pytest.raises(ValueError):
        mark(action, position)


def test_exact_minimum_duration_and_preview_end():
    assert mark("out", .1) == (100.0, 100.1)
    assert mark("out", 30) == (100.0, 130.0)


def test_mark_cannot_exceed_source_duration():
    with pytest.raises(ValueError):
        mark("out", 30, source_duration=125)


def test_review_mark_updates_fields_once_and_saves_source_bounds(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from streamlit.testing.v1 import AppTest
    from highlightminer import ui_mine
    from highlightminer.review import default_review

    candidate = dict(id="H001", rank=1, start=100.0, end=130.0, peak_time=110.0,
                     score=.8, reason="Reaction", audio_score=.9,
                     transcript_score=.5, chat_score=0)
    analysis = dict(duration=1000.0, work_dir=str(tmp_path), video_path="test.mp4",
                    candidates=[candidate])
    review = default_review(analysis)
    saved = []
    monkeypatch.setattr(ui_mine, "load_analysis", lambda *_: analysis)
    monkeypatch.setattr(ui_mine, "load_analysis_identity", lambda *_: {"analysis_name": "Test"})
    monkeypatch.setattr(ui_mine, "load_review", lambda *_: review)
    monkeypatch.setattr(ui_mine, "save_review", lambda *args: saved.append(dict(args[-1]["items"]["H001"])))
    monkeypatch.setattr(ui_mine, "load_active_export_batch", lambda *_: None)
    monkeypatch.setattr(ui_mine, "validate_local_video", lambda *_: tmp_path / "test.mp4")
    monkeypatch.setattr(ui_mine, "create_preview_clip", lambda *_: SimpleNamespace(path=tmp_path / "test.mp4", cleanup_failures=0))
    monkeypatch.setattr(ui_mine, "path_picker", lambda *args, **kwargs: str(tmp_path))
    monkeypatch.setattr(ui_mine, "preview_player", lambda *args, **kwargs: ui_mine.st.session_state.get("test_mark"))
    app = AppTest.from_string('''
from pathlib import Path
import streamlit as st
from highlightminer.ui_mine import _render_review
st.session_state["analysis_id"] = "analysis"
_render_review(Path("unused.db"))
''').run()
    assert not app.exception
    token = "analysis:H001:100.0:130.0"
    app.session_state["test_mark"] = dict(id="1", token=token, action="in", position=4.25)
    app.run()
    assert not app.exception
    assert not app.warning
    assert app.text_input(key="clip_start_time_analysis_H001").value == "01:44"
    app.session_state["test_mark"] = dict(id="2", token=token, action="out", position=22.5)
    app.run()
    assert app.text_input(key="clip_end_time_analysis_H001").value == "02:02"
    # An invalid mark leaves both the successful field selection and preview alone.
    app.session_state["test_mark"] = dict(id="3", token=token, action="out", position=1)
    app.run()
    assert app.warning
    assert app.text_input(key="clip_end_time_analysis_H001").value == "02:02"
    assert app.session_state["preview_bounds_analysis_H001"] == (100.0, 130.0)
    next(b for b in app.button if b.label == "💾 Save timing").click().run()
    assert saved[-1]["start"] == 104.25
    assert saved[-1]["end"] == 122.5
    # The component retains its previous value on unrelated reruns; never apply it twice.
    app.run()
    assert not app.warning
    next(b for b in app.button if b.label == "Update preview").click().run()
    assert app.session_state["preview_bounds_analysis_H001"] == (104.25, 122.5)
    app.session_state["test_mark"] = dict(id="4", token=token, action="in", position=10)
    app.run()
    assert app.warning
    assert app.text_input(key="clip_start_time_analysis_H001").value == "01:44"
    assert not app.exception
    # Manual edits replace the precise mark instead of resurrecting it on rerun.
    app.text_input(key="clip_start_time_analysis_H001").set_value("01:45.75")
    next(b for b in app.button if b.label == "Update preview").click().run()
    assert app.session_state["preview_bounds_analysis_H001"] == (105.75, 122.5)
    next(b for b in app.button if b.label == "💾 Save timing").click().run()
    assert saved[-1]["start"] == 105.75
    assert saved[-1]["end"] == 122.5
    # Replacing manually entered fractions with whole seconds must drop them.
    app.text_input(key="clip_start_time_analysis_H001").set_value("01:45")
    next(b for b in app.button if b.label == "Update preview").click().run()
    assert app.session_state["preview_bounds_analysis_H001"] == (105.0, 122.5)
    next(b for b in app.button if b.label == "💾 Save timing").click().run()
    assert saved[-1]["start"] == 105.0
    assert saved[-1]["end"] == 122.5
    app.run()
    assert not app.exception


def test_preview_component_event_protocol():
    import shutil
    import subprocess
    from pathlib import Path

    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is needed for the dependency-free component protocol smoke test")
    subprocess.run([node, str(Path(__file__).with_name("preview_component_smoke.cjs"))],
                   check=True, capture_output=True, text=True, timeout=15)
