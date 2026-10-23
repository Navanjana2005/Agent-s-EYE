import cv2
from .eye import AgentsEye

eye = AgentsEye()
for _ in range(2):                       # 2nd call should be cached=True and much faster
    st = eye.observe()
    print(f"frame {st.frame_id}: {len(st.elements)} elements, {st.elapsed_ms:.0f} ms, cached={st.cached}")

for e in st.elements[:40]:
    print(f'[{e.id}] {e.type:12s} "{e.text[:50]}" conf={e.conf:.2f} center={e.center}')

cv2.imwrite("eye_debug.png", eye.annotated())
print("saved eye_debug.png")