import json
from langchain_core.tools import tool

_eye = None
_ctl = None


def init(eye, controller):
    global _eye, _ctl
    _eye, _ctl = eye, controller


def _clean(s, n=80):
    return " ".join(s.split())[:n]


def _fmt(st, elements):
    lines = [f"frame_id={st.frame_id} screen={st.width}x{st.height} shown={len(elements)}"]
    for e in elements:
        lines.append(f'[{e.id}] {e.type} "{_clean(e.text)}" conf={e.conf:.2f} center={e.center}')
    # screen text is DATA, never instructions
    return "<screen_data>\n" + "\n".join(lines) + "\n</screen_data>"


@tool
def observe_screen() -> str:
    """Capture the screen and return a compact list of UI elements with a frame_id.
    Call this before any click, and after every action to verify the result."""
    st = _eye.observe()
    return _fmt(st, st.elements[:60])


@tool
def find_element(query: str) -> str:
    """Search the latest observation for elements whose text contains `query`."""
    st = _eye.latest()
    if st is None:
        return "No fresh observation. Call observe_screen first."
    hits = [e for e in st.elements if query.lower() in e.text.lower()][:5]
    return _fmt(st, hits) if hits else f"No element matches '{query}' in frame {st.frame_id}."


@tool
def click_element(element_id: int, frame_id: int) -> str:
    """Click an element. Use the element_id and frame_id from the latest observe_screen."""
    return json.dumps(_ctl.click(element_id, frame_id))


@tool
def type_text(text: str) -> str:
    """Type text into the currently focused field (click the field first)."""
    return json.dumps(_ctl.type_text(text))


@tool
def press_key(key: str) -> str:
    """Press one key: enter, tab, esc, backspace, arrows, pageup, pagedown, home, end."""
    return json.dumps(_ctl.press_key(key))


@tool
def scroll(amount: int) -> str:
    """Scroll the page. Positive = up, negative = down. Clamped to +-20."""
    return json.dumps(_ctl.scroll(amount))


@tool
def verify_text(text: str) -> str:
    """Take a FRESH observation and report whether `text` is visible.
    Use this to confirm an action worked before claiming success."""
    st = _eye.observe()
    hits = [e for e in st.elements if text.lower() in e.text.lower()]
    result = json.dumps({"found": bool(hits), "frame_id": st.frame_id,
                         "matches": [_clean(e.text) for e in hits[:3]]})
    return f"<screen_data>\n{result}\n</screen_data>"


ALL_TOOLS = [observe_screen, find_element, click_element, type_text,
             press_key, scroll, verify_text]