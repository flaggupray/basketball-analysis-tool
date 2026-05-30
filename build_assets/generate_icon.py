"""Generate app icon for the Basketball Analyzer — a simple basketball with chart elements."""

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def create_icon(size: int = 1024) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = size * 0.08
    cx, cy = size / 2, size / 2
    r = size / 2 - margin

    # Background circle (basketball orange)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                 fill=(238, 108, 40, 255), outline=(200, 80, 20, 255),
                 width=max(2, size // 100))

    # Basketball lines
    line_w = max(2, size // 80)
    # Horizontal line
    draw.line([(cx - r * 0.85, cy), (cx + r * 0.85, cy)],
              fill=(200, 80, 20, 255), width=line_w)
    # Vertical line
    draw.line([(cx, cy - r * 0.75), (cx, cy + r * 0.75)],
              fill=(200, 80, 20, 255), width=line_w)
    # Curved lines
    for sx in [-1, 1]:
        pts = []
        for angle in range(-60, 61, 5):
            rad = math.radians(angle)
            x = cx + sx * r * 0.6 * math.cos(rad)
            y = cy + r * 0.72 * (angle / 90) * math.sin(rad)
            pts.append((x, y))
        for i in range(len(pts) - 1):
            draw.line([pts[i], pts[i + 1]],
                      fill=(200, 80, 20, 255), width=line_w)

    # Bar chart overlay (to represent analysis)
    bar_color = (30, 30, 30, 220)
    bar_w = r * 0.19
    base_y = cy + r * 0.55
    heights = [r * 0.5, r * 0.65, r * 0.35]
    for i, h in enumerate(heights):
        bx = cx + (i - 1) * bar_w * 1.3
        draw.rectangle(
            [bx - bar_w / 2, base_y - h, bx + bar_w / 2, base_y],
            fill=bar_color,
            outline=(255, 255, 255, 180),
            width=max(1, size // 300),
        )

    # Arrow pointing up (improvement)
    arrow_color = (52, 199, 89, 240)
    ax, ay = cx, cy - r * 0.65
    draw.polygon([
        (ax, ay),
        (ax - r * 0.15, ay + r * 0.22),
        (ax + r * 0.15, ay + r * 0.22),
    ], fill=arrow_color, outline=(255, 255, 255, 200),
        width=max(1, size // 200))

    return img


def main():
    root = Path(__file__).resolve().parent.parent
    assets_dir = root / "assets"
    assets_dir.mkdir(exist_ok=True)

    icon = create_icon(1024)

    # Save PNG versions at various sizes
    for sz in [1024, 512, 256, 128, 64, 32, 16]:
        resized = icon.resize((sz, sz), Image.LANCZOS)
        resized.save(assets_dir / f"icon_{sz}x{sz}.png")

    # Also save as generic icon.png
    icon_512 = icon.resize((512, 512), Image.LANCZOS)
    icon_512.save(assets_dir / "icon.png")

    print(f"Icon saved to {assets_dir}/")
    print("Next: create .icns via:")
    print(f"  mkdir -p {assets_dir}/icon.iconset")
    for sz in [16, 32, 64, 128, 256, 512]:
        print(f"  cp {assets_dir}/icon_{sz}x{sz}.png {assets_dir}/icon.iconset/icon_{sz}x{sz}.png")
        print(f"  cp {assets_dir}/icon_{sz*2}x{sz*2}.png {assets_dir}/icon.iconset/icon_{sz}x{sz}@2x.png")
    print(f"  iconutil -c icns {assets_dir}/icon.iconset -o {assets_dir}/icon.icns")


if __name__ == "__main__":
    main()
