from .schema import Detection


class Detector:
    def __init__(self, model_path, imgsz=960, conf=0.25, device="cpu"):
        from pathlib import Path
        import ultralytics.utils.downloads as ud

        # Workaround for Ultralytics bug: attempt_download_asset runs .replace("'", "")
        # which breaks file paths containing apostrophes (e.g. "The AI agent's EYE").
        orig_download = ud.attempt_download_asset
        ud.attempt_download_asset = lambda f, *a, **kw: str(f) if Path(f).is_file() else orig_download(f, *a, **kw)

        from ultralytics import YOLO
        self.model = YOLO(str(model_path))
        self.imgsz, self.conf, self.device = imgsz, conf, device

    def detect(self, frame):
        r = self.model.predict(frame, imgsz=self.imgsz, conf=self.conf,
                               device=self.device, verbose=False)[0]
        b = r.boxes
        if b is None or len(b) == 0:
            return []
        xyxy = b.xyxy.cpu().numpy()
        conf = b.conf.cpu().numpy()
        cls = b.cls.cpu().numpy().astype(int)
        return [Detection(tuple(map(float, bb)), float(c), str(r.names[int(k)]))
                for bb, c, k in zip(xyxy, conf, cls)]