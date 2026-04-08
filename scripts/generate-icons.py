"""
Generate app icons from the conch shell source image (6.png).

Steps:
  1. Open source image
  2. Rotate 90° clockwise (conch is vertical in source, horizontal in book)
  3. Crop whitespace
  4. Pad to square with transparent background
  5. Generate: favicon.ico, apple-touch-icon.png (180), icon-192.png, icon-512.png
"""

from pathlib import Path
from PIL import Image

PROJECT = Path(__file__).resolve().parent.parent
SRC = PROJECT / "public" / "book-preview" / "image" / "6.png"
PUBLIC = PROJECT / "public"
APP = PROJECT / "app"

def main():
    img = Image.open(SRC).convert("RGBA")
    print(f"Original size: {img.size}")

    # 1. Rotate 90° clockwise
    img = img.rotate(-90, expand=True)
    print(f"After rotation: {img.size}")

    # 2. Crop whitespace (using alpha + near-white detection)
    # Get bounding box of non-white/non-transparent content
    bbox = get_content_bbox(img)
    if bbox:
        img = img.crop(bbox)
        print(f"After crop: {img.size}")
    else:
        print("WARNING: Could not detect content bounds, skipping crop")

    # 3. Pad to square
    w, h = img.size
    side = max(w, h)
    # Add 5% padding
    padding = int(side * 0.05)
    canvas_size = side + 2 * padding
    square = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    offset_x = (canvas_size - w) // 2
    offset_y = (canvas_size - h) // 2
    square.paste(img, (offset_x, offset_y), img)
    print(f"Square canvas: {square.size}")

    # 4. Generate icons
    # icon-512.png
    icon_512 = square.copy()
    icon_512 = icon_512.resize((512, 512), Image.LANCZOS)
    icon_512.save(PUBLIC / "icon-512.png")
    print("Saved icon-512.png")

    # icon-192.png
    icon_192 = square.copy()
    icon_192 = icon_192.resize((192, 192), Image.LANCZOS)
    icon_192.save(PUBLIC / "icon-192.png")
    print("Saved icon-192.png")

    # apple-touch-icon.png (180x180, white background for Apple)
    apple = square.copy()
    apple = apple.resize((180, 180), Image.LANCZOS)
    apple_bg = Image.new("RGBA", (180, 180), (253, 248, 240, 255))  # #FDF8F0 cream bg
    apple_bg.paste(apple, (0, 0), apple)
    apple_bg = apple_bg.convert("RGB")
    apple_bg.save(PUBLIC / "apple-touch-icon.png")
    print("Saved apple-touch-icon.png")

    # favicon.ico (multi-size: 16, 32, 48)
    sizes = [16, 32, 48]
    ico_images = []
    for s in sizes:
        ico_img = square.copy()
        ico_img = ico_img.resize((s, s), Image.LANCZOS)
        ico_images.append(ico_img)

    ico_images[0].save(
        PUBLIC / "favicon.ico",
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=ico_images[1:],
    )
    print("Saved favicon.ico (16, 32, 48)")

    # Also copy to app/favicon.ico for Next.js
    ico_images[0].save(
        APP / "favicon.ico",
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=ico_images[1:],
    )
    print("Saved app/favicon.ico")

    print("\nDone! All icons generated.")


def get_content_bbox(img: Image.Image):
    """Find bounding box of actual drawn content (non-white, non-transparent pixels)."""
    pixels = img.load()
    w, h = img.size
    min_x, min_y, max_x, max_y = w, h, 0, 0

    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            # Skip transparent or near-white pixels
            if a < 30:
                continue
            if r > 240 and g > 240 and b > 240:
                continue
            # This pixel has content
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)

    if min_x >= max_x or min_y >= max_y:
        return None
    return (min_x, min_y, max_x + 1, max_y + 1)


if __name__ == "__main__":
    main()
