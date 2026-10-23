"""
eye_interface.py

The contract between the agent and its "eye", plus a fake eye for testing
without YOLO/OCR.

Any eye (MockEye or the real AgentsEye) must provide:
    observe()    -> ScreenState      fresh capture with a new frame_id
    latest()     -> ScreenState|None last observation; None once an action has happened
    invalidate()                     called by the controller after every action
"""
import time

from agents_eye.schema import Element, ScreenState   # light import: no torch needed


class MockEye:
    """Fake screen: a tiny search page whose state changes when MockBackend acts."""

    def __init__(self):
        self._frame = 0
        self._latest = None
        self.stage = "home"       # home | results
        self.query = ""
        self.focused = False

    # ---- the "real" UI at this moment (independent of any snapshot) ----
    def elements(self):
        if self.stage == "home":
            return [
                Element(1, "text", "Mock Search", (800, 100, 1100, 150), 0.95),
                Element(2, "input", self.query or "Search the web", (700, 300, 1200, 350), 0.91),
                Element(3, "button", "Search", (1220, 300, 1320, 350), 0.88),
            ]
        return [
            Element(1, "text", f"Results for: {self.query}", (300, 100, 900, 140), 0.93),
            Element(2, "text", f"{self.query} - Official Tutorial", (300, 200, 900, 240), 0.90),
            Element(3, "text", f"{self.query} - Beginner Guide", (300, 280, 900, 320), 0.89),
        ]

    # ---- eye interface ----
    def observe(self, force=False):
        self._frame += 1
        self._latest = ScreenState(
            frame_id=self._frame,
            width=1920,
            height=1080,
            elements=self.elements(),
            timestamp=time.time(),
        )
        return self._latest

    def latest(self):
        return self._latest

    def invalidate(self):
        self._latest = None

    # ---- helpers matching AgentsEye, so gui_tools could use either ----
    def get_element(self, element_id):
        st = self._latest
        return next((e for e in st.elements if e.id == element_id), None) if st else None

    def find_element(self, query, limit=5):
        st = self._latest
        if not st:
            return []
        q = query.lower().strip()
        return [e for e in st.elements if q in e.text.lower()][:limit]

    def verify_text(self, text):
        st = self.observe()
        hits = [e for e in st.elements if text.lower() in e.text.lower()]
        return {"found": bool(hits), "frame_id": st.frame_id,
                "matches": [e.text for e in hits[:3]]}


class MockBackend:
    """Stands in for PyAutoGUI: changes MockEye's state instead of moving the mouse."""

    def __init__(self, eye: MockEye):
        self.eye = eye

    def click(self, x, y):
        for e in self.eye.elements():
            x1, y1, x2, y2 = e.bbox
            if x1 <= x <= x2 and y1 <= y <= y2:
                if e.type == "input":
                    self.eye.focused = True
                elif e.type == "button" and e.text == "Search" and self.eye.query:
                    self.eye.stage = "results"

    def type(self, text):
        if self.eye.focused:
            self.eye.query += text

    def press(self, key):
        if key == "enter" and self.eye.focused and self.eye.query:
            self.eye.stage = "results"

    def scroll(self, amount):
        pass