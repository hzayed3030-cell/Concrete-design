import sys
sys.stdout.reconfigure(encoding='utf-8')
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_beam_polygon(ax, p1, p2, b_m, label="", rft_label="", is_steel_layout=False):
    x1, y1 = p1
    x2, y2 = p2
    L = math.hypot(x2 - x1, y2 - y1)
    if L < 0.1: return
    
    dx = (x2 - x1) / L
    dy = (y2 - y1) / L
    nx = -dy * (b_m / 2.0)
    ny = dx * (b_m / 2.0)
    
    poly_pts = [
        [x1 + nx, y1 + ny],
        [x2 + nx, y2 + ny],
        [x2 - nx, y2 - ny],
        [x1 - nx, y1 - ny]
    ]
    
    if is_steel_layout:
        edge_col = "#1e3a8a"
        face_col = "rgba(30, 58, 138, 0.12)"
        poly = patches.Polygon(poly_pts, closed=True, facecolor="#eff6ff", edgecolor=edge_col, lw=2.0, zorder=6, linestyle="--")
        ax.add_patch(poly)
        # Rebar lines along beam
        rnx = -dy * (b_m / 4.0)
        rny = dx * (b_m / 4.0)
        ax.plot([x1 + rnx, x2 + rnx], [y1 + rny, y2 + rny], color="#dc2626", lw=1.8, zorder=7)
        ax.plot([x1 - rnx, x2 - rnx], [y1 - rny, y2 - rny], color="#1e40af", lw=1.8, zorder=7)
    else:
        edge_col = "#0369a1"
        poly = patches.Polygon(poly_pts, closed=True, facecolor="#e0f2fe", edgecolor=edge_col, lw=1.8, zorder=6)
        ax.add_patch(poly)
        ax.plot([x1, x2], [y1, y2], color="#0284c7", lw=1.2, linestyle=":", zorder=7)
        
    # Text label at midpoint
    mx = (x1 + x2) / 2.0
    my = (y1 + y2) / 2.0
    
    # Calculate angle of rotation
    angle_deg = math.degrees(math.atan2(dy, dx))
    if angle_deg > 90:
        angle_deg -= 180
    elif angle_deg < -90:
        angle_deg += 180
        
    txt = rft_label if is_steel_layout and rft_label else label
    if txt:
        ax.text(
            mx, my, txt,
            color="#0f172a", fontsize=9.5, weight="bold",
            ha="center", va="center", rotation=angle_deg,
            bbox=dict(boxstyle="round,pad=0.25", facecolor="#ffffff", edgecolor=edge_col, lw=1.2, alpha=0.92),
            zorder=8
        )

print("Beam polygon drawing logic defined successfully!")
