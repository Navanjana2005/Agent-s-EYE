import time
from dataclasses import dataclass, field


@dataclass
class Element:
    id: int
    type: str            # YOLO class name, or "text" for OCR-only text
    text: str
    bbox: tuple          # x1, y1, x2, y2 in SCREEN pixels
    conf: float
    source: str = "vision"   # later: "uia" for UI Automation elements

    @property
    def center(self):
        return ((self.bbox[0] + self.bbox[2]) // 2, (self.bbox[1] + self.bbox[3]) // 2)


@dataclass
class ScreenState:
    frame_id: int
    width: int
    height: int
    elements: list
    timestamp: float = field(default_factory=time.time)
    cached: bool = False
    elapsed_ms: float = 0.0
    left: int = 0
    top: int = 0


@dataclass
class Detection:         # raw YOLO output, frame coordinates
    bbox: tuple
    conf: float
    label: str


@dataclass
class TextBox:           # raw OCR output, frame coordinates
    bbox: tuple
    text: str
    conf: float