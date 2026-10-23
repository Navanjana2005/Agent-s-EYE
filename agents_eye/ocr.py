import warnings
import cv2
from .schema import TextBox

warnings.filterwarnings("ignore", category=UserWarning, module="torch.utils.data")


class OCR:
    def __init__(self, gpu=False, min_conf=0.30, max_width=1280, langs=("en",)):
        import easyocr
        self.reader = easyocr.Reader(list(langs), gpu=gpu)
        self.min_conf, self.max_width = min_conf, max_width

    def read(self, frame):
        h, w = frame.shape[:2]
        scale = min(1.0, self.max_width / w)       # downscale = much faster
        img = cv2.resize(frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else frame
        out = []
        for pts, text, conf in self.reader.readtext(img):
            text = text.strip()
            if conf < self.min_conf or not text:
                continue
            xs = [float(p[0]) / scale for p in pts]
            ys = [float(p[1]) / scale for p in pts]
            out.append(TextBox((min(xs), min(ys), max(xs), max(ys)), text, float(conf)))
        return out