import pytest

from agent import _get_nvidia_api_key
from controller import ActionController
from eye_interface import MockEye, MockBackend


def make():
    eye = MockEye()
    return eye, ActionController(eye, MockBackend(eye), approve=lambda m: True)


def test_requires_observation():
    _, ctl = make()
    assert ctl.click(2, 1)["reason"] == "NO_FRESH_OBSERVATION"


def test_stale_frame_rejected():
    eye, ctl = make()
    eye.observe(); st = eye.observe()
    assert ctl.click(2, st.frame_id - 1)["reason"] == "STALE_FRAME"


def test_full_flow_and_invalidation():
    eye, ctl = make()
    st = eye.observe()
    assert ctl.click(2, st.frame_id)["ok"]
    assert ctl.click(2, st.frame_id)["reason"] == "NO_FRESH_OBSERVATION"  # must re-observe
    ctl.type_text("python tutorials")
    ctl.press_key("enter")
    texts = [e.text for e in eye.observe().elements]
    assert any("Results for: python tutorials" in t for t in texts)


def test_bad_key_blocked():
    _, ctl = make()
    assert ctl.press_key("alt+f4")["reason"] == "KEY_NOT_ALLOWED"


def test_nvidia_api_key_is_required(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="NVIDIA_API_KEY is required"):
        _get_nvidia_api_key()


def test_nvidia_api_key_is_read_from_environment(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", " test-key ")
    assert _get_nvidia_api_key() == "test-key"