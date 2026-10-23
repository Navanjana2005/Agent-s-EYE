from .schema import Element


def merge(dets, texts, left=0, top=0, row_px=25, line_px=12):
    """YOLO boxes + OCR text -> numbered Elements in screen coordinates.
    Each text goes to the smallest YOLO box containing its center;
    text outside every box becomes its own 'text' element."""
    cells = [{"bbox": d.bbox, "type": d.label, "conf": d.conf, "texts": []} for d in dets]
    loose = []

    for t in texts:
        cx, cy = (t.bbox[0] + t.bbox[2]) / 2, (t.bbox[1] + t.bbox[3]) / 2
        best, best_area = None, None
        for c in cells:
            x1, y1, x2, y2 = c["bbox"]
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                area = (x2 - x1) * (y2 - y1)
                if best is None or area < best_area:
                    best, best_area = c, area
        if best is not None:
            best["texts"].append(t)
        else:
            loose.append({"bbox": t.bbox, "type": "text", "conf": t.conf, "texts": [t]})

    out = []
    for c in cells + loose:
        # words on the same visual line sorted left-to-right
        ts = sorted(c["texts"], key=lambda t: (int((t.bbox[1] + t.bbox[3]) / 2) // line_px, t.bbox[0]))
        x1, y1, x2, y2 = c["bbox"]
        out.append(Element(
            id=0, type=c["type"], text=" ".join(t.text for t in ts),
            bbox=(int(x1 + left), int(y1 + top), int(x2 + left), int(y2 + top)),
            conf=float(c["conf"]),
        ))

    # reading order: rows of ~row_px, then left-to-right
    out.sort(key=lambda e: (e.center[1] // row_px, e.center[0]))
    for i, e in enumerate(out, start=1):
        e.id = i
    return out