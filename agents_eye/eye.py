import ctypes
import difflib
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import mss
import numpy as np
import torch

from .detector import Detector
from .merge import merge
from .ocr import OCR
from .schema import ScreenState


@dataclass
class EyeConfig:
    model_path: str = "best.pt"
    imgsz: int = 960
    yolo_conf: float = 0.25
    ocr_min_conf: float = 0.30
    ocr_max_width: int = 1280
    monitor_index: int = 1        # keep 1 (primary) for now
    settle_s: float = 0.5         # wait after an action before capturing
    change_ratio: float = 0.001   # fraction of changed pixels that counts as "screen changed"


def _set_dpi_aware():
    """Make capture coordinates == click coordinates on scaled Windows displays."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class AgentsEye:
    def __init__(self, cfg: EyeConfig = None):
        _set_dpi_aware()
        self.cfg = cfg or EyeConfig()
        device = 0 if torch.cuda.is_available() else "cpu"
        print("Agent's EYE running on:", "GPU" if device == 0 else "CPU")
        model_path = Path(self.cfg.model_path).expanduser()
        if not model_path.is_absolute():
            cand_agent = Path(__file__).resolve().parents[1] / model_path
            cand_proj = Path(__file__).resolve().parents[2] / model_path
            cand_cwd = Path.cwd() / model_path
            if cand_agent.is_file():
                model_path = cand_agent
            elif cand_proj.is_file():
                model_path = cand_proj
            elif cand_cwd.is_file():
                model_path = cand_cwd
            else:
                model_path = cand_proj
        model_path = model_path.resolve()
        if not model_path.is_file():
            raise FileNotFoundError(f"YOLO model weights not found: {model_path}")
        self.detector = Detector(str(model_path), self.cfg.imgsz, self.cfg.yolo_conf, device)
        self.ocr = OCR(gpu=(device == 0), min_conf=self.cfg.ocr_min_conf,
                       max_width=self.cfg.ocr_max_width)
        self._lock = threading.Lock()
        self._frame_id = 0
        self._latest = None        # valid only until the next action
        self._last_state = None    # kept for debug drawing
        self._last_frame = None
        self._cache = None         # (signature, elements)
        self._dirty = True         # True after an action -> never reuse the cache
        self._acted_at = 0.0

    # ---------- interface used by controller / tools ----------
    def observe(self, force=False) -> ScreenState:
        with self._lock:
            if self._dirty:
                wait = self.cfg.settle_s - (time.time() - self._acted_at)
                if wait > 0:
                    time.sleep(wait)          # let the UI finish updating
            t0 = time.time()
            frame, mon = self._grab()
            sig = self._signature(frame)

            reuse = (not force and not self._dirty and self._cache is not None
                     and not self._changed(self._cache[0], sig))
            if reuse:
                elements = self._cache[1]
            else:
                dets = self.detector.detect(frame)
                texts = self.ocr.read(frame)
                elements = merge(dets, texts, mon["left"], mon["top"])
                self._cache = (sig, elements)

            self._dirty = False
            self._frame_id += 1
            st = ScreenState(self._frame_id, mon["width"], mon["height"], elements,
                             cached=reuse, elapsed_ms=(time.time() - t0) * 1000,
                             left=mon["left"], top=mon["top"])
            self._latest = self._last_state = st
            self._last_frame = frame
            return st

    def latest(self):
        return self._latest

    def invalidate(self):
        """Called by the controller after every action."""
        self._latest = None
        self._dirty = True
        self._acted_at = time.time()

    # ---------- helpers ----------
    def get_element(self, element_id):
        st = self._latest
        return next((e for e in st.elements if e.id == element_id), None) if st else None

    def find_element(self, query, limit=5):
        """Substring match first, then fuzzy (OCR makes typos)."""
        st = self._latest
        if not st:
            return []
        q, scored = query.lower().strip(), []
        for e in st.elements:
            t = e.text.lower()
            if not t:
                continue
            if q in t:
                score = 1.0 + len(q) / max(len(t), 1)      # tighter match ranks higher
            else:
                score = difflib.SequenceMatcher(None, q, t).ratio()
                if score < 0.7:
                    continue
            scored.append((score, e))
        scored.sort(key=lambda s: -s[0])
        return [e for _, e in scored[:limit]]

    def verify_text(self, text):
        """Fresh observation, then report whether `text` is visible."""
        st = self.observe()
        q = text.lower()
        hits = [e for e in st.elements if q in e.text.lower()]
        return {"found": bool(hits), "frame_id": st.frame_id, "matches": [e.text for e in hits[:3]]}

    def annotated(self):
        """Last frame with numbered boxes, for debugging."""
        st, img = self._last_state, self._last_frame
        if st is None or img is None:
            return None
        img = img.copy()
        for e in st.elements:
            x1, y1, x2, y2 = e.bbox[0] - st.left, e.bbox[1] - st.top, e.bbox[2] - st.left, e.bbox[3] - st.top
            color = (0, 200, 0) if e.text else (255, 160, 0)
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 1)
            cv2.putText(img, str(e.id), (x1, max(y1 - 3, 12)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        return img

    # ---------- internals ----------
    def _grab(self):
        ctor = getattr(mss, "MSS", None) or mss.mss
        with ctor() as sct:                      # created per call: thread-safe on Windows
            mon = dict(sct.monitors[self.cfg.monitor_index])
            frame = cv2.cvtColor(np.array(sct.grab(mon)), cv2.COLOR_BGRA2BGR)
        return frame, mon

    @staticmethod
    def _signature(frame):
        g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return cv2.resize(g, (320, 180), interpolation=cv2.INTER_AREA)

    def _changed(self, a, b):
        return (cv2.absdiff(a, b) > 25).mean() > self.cfg.change_ratio