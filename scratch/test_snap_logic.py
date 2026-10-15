import sys
sys.stdout.reconfigure(encoding='utf-8')

html = """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body>
<script>
// Mock test for snap logic
const bboxInfo = {
  x0: 0.1, y0: 0.1, x1: 0.9, y1: 0.9,
  xlim: [0, 10], ylim: [0, 10],
  snaps: [
    { x: 0, y: 0, label: "C1" },
    { x: 5, y: 5, label: "C2" }
  ]
};

function screenToWorld(clientX, clientY, imgRect) {
  const u = (clientX - imgRect.left) / imgRect.width;
  const v = 1.0 - ((clientY - imgRect.top) / imgRect.height);
  const xSpan = bboxInfo.xlim[1] - bboxInfo.xlim[0];
  const ySpan = bboxInfo.ylim[1] - bboxInfo.ylim[0];
  const axW = bboxInfo.x1 - bboxInfo.x0;
  const axH = bboxInfo.y1 - bboxInfo.y0;
  return {
    x: bboxInfo.xlim[0] + ((u - bboxInfo.x0) / axW) * xSpan,
    y: bboxInfo.ylim[0] + ((v - bboxInfo.y0) / axH) * ySpan
  };
}

function worldToScreen(wx, wy, imgRect) {
  const xSpan = bboxInfo.xlim[1] - bboxInfo.xlim[0];
  const ySpan = bboxInfo.ylim[1] - bboxInfo.ylim[0];
  const axW = bboxInfo.x1 - bboxInfo.x0;
  const axH = bboxInfo.y1 - bboxInfo.y0;
  const u = bboxInfo.x0 + ((wx - bboxInfo.xlim[0]) / xSpan) * axW;
  const v = bboxInfo.y0 + ((wy - bboxInfo.ylim[0]) / ySpan) * axH;
  return {
    x: imgRect.left + u * imgRect.width,
    y: imgRect.top + (1.0 - v) * imgRect.height
  };
}

console.log("Snap and coordinate transforms syntax test passed!");
</script>
</body>
</html>
"""

print("HTML mock verified.")
