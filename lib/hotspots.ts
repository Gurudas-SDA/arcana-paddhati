// Numbered pictures: where each printed number's object sits on the image.
// Data only (data/hotspots.json): to link another picture with its numbered
// list, add an entry for its file name — no code change needed.
//
// Per image: natural size (w, h) and, per number, the object's ellipse
// (x, y = centre; rx, ry = radii) and optionally the printed label's position
// (lx, ly). All values are in % of the image width (x, rx, lx) or height
// (y, ry, ly), so they survive resizing of the picture.
import data from "@/data/hotspots.json";

export interface Hotspot {
  x: number;
  y: number;
  rx: number;
  ry: number;
  lx?: number;
  ly?: number;
}

export interface HotspotImage {
  w: number;
  h: number;
  spots: Record<string, Hotspot>;
}

const IMAGES = data as Record<string, HotspotImage>;

/** Hotspot data of an image (by file name), or undefined. */
export function hotspotsFor(src: string | undefined): HotspotImage | undefined {
  return src ? IMAGES[src] : undefined;
}

/** Picture numbers named by a list label: "4" -> ["4"], "4, 5" -> ["4", "5"]. */
export function labelNumbers(label: string | undefined): string[] {
  return (label ?? "").split(/[^0-9]+/).filter(Boolean);
}
