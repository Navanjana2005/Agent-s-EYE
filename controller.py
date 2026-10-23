from typing import Callable

ALLOWED_KEYS = {"enter", "tab", "esc", "backspace", "up", "down", "left", "right",
                "pageup", "pagedown", "home", "end", "win", "space"}
RISKY_WORDS = ("delete", "remove", "pay", "buy", "purchase", "uninstall",
               "format", "shutdown", "send", "confirm order")


def cli_approve(msg: str) -> bool:
    return input(f"\n⚠️  APPROVAL NEEDED: {msg} [y/N]: ").strip().lower() == "y"


def _err(reason, **kw):
    return {"ok": False, "reason": reason, **kw}


class ActionController:
    def __init__(self, eye, backend, min_conf=0.35, approve: Callable = cli_approve):
        self.eye, self.backend = eye, backend
        self.min_conf, self.approve = min_conf, approve

    def click(self, element_id: int, frame_id: int):
        st = self.eye.latest()
        if st is None:
            return _err("NO_FRESH_OBSERVATION", hint="call observe_screen first")
        if frame_id != st.frame_id:
            return _err("STALE_FRAME", latest_frame_id=st.frame_id, hint="observe_screen again")
        el = next((e for e in st.elements if e.id == element_id), None)
        if el is None:
            return _err("NO_SUCH_ELEMENT")
        if el.conf < self.min_conf:
            return _err("LOW_CONFIDENCE", conf=el.conf)
        x, y = el.center
        if not (0 <= x < st.width and 0 <= y < st.height):
            return _err("OUT_OF_BOUNDS")
        if any(w in el.text.lower() for w in RISKY_WORDS):
            if not self.approve(f"click '{el.text}'"):
                return _err("USER_DENIED")
        self.backend.click(x, y)
        self.eye.invalidate()          # screen changed -> must observe again
        return {"ok": True, "action": "click", "target": el.text, "note": "NOT verified yet"}

    def type_text(self, text: str):
        if not text or len(text) > 500:
            return _err("BAD_TEXT_LENGTH")
        self.backend.type(text)
        self.eye.invalidate()
        return {"ok": True, "action": "type", "note": "NOT verified yet"}

    def press_key(self, key: str):
        key = key.lower()
        if key not in ALLOWED_KEYS:
            return _err("KEY_NOT_ALLOWED", allowed=sorted(ALLOWED_KEYS))
        self.backend.press(key)
        self.eye.invalidate()
        return {"ok": True, "action": "press", "key": key, "note": "NOT verified yet"}

    def scroll(self, amount: int):
        self.backend.scroll(max(-20, min(20, int(amount))))
        self.eye.invalidate()
        return {"ok": True, "action": "scroll", "note": "NOT verified yet"}


class PyAutoGUIBackend:      # real backend, not used in the first test
    def __init__(self):
        import pyautogui
        pyautogui.FAILSAFE = True   # mouse to a corner = emergency stop
        self.p = pyautogui

    def click(self, x, y): self.p.click(x, y)
    def type(self, text): self.p.write(text, interval=0.02)
    def press(self, key): self.p.press(key)
    def scroll(self, amount): self.p.scroll(amount * 100)