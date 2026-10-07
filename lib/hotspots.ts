// Numbered pictures: where each printed number's object sits on the image.
// Data only (data/hotspots.json): to link another picture with its numbered
// list, add an entry for its file name — no code change needed.
//
// Per image: natural size (w, h) and, per number, the object's ellipse
// (x, y = centre; rx, ry = radii) and optionally the printed label's position
// (lx, ly). All values are in % of the image width (x, rx, lx) or height
// (y, ry, ly), so they survive resizing of the picture. The highlight itself
// uses the per-object pixel mask ("mask") when present, the ellipse otherwise.
import data from "@/data/hotspots.json";

export interface Hotspot {
  x: number;
  y: number;
  rx: number;
  ry: number;
  lx?: number;
  ly?: number;
  /** Position [x%, y%] of a number drawn over the picture where the picture
   *  itself has no printed number (emblem: 2.1–2.6, 10–12; «1» moved clear
   *  of the hexagon — Reader v7.1). */
  tag?: number[];
  /** Per-object alpha mask (public/images/hotspots/<file>), built by
   * scripts/build_hotspot_masks.py: exactly this object + its number. */
  mask?: string;
}

export interface HotspotImage {
  w: number;
  h: number;
  spots: Record<string, Hotspot>;
  /** Polygons ([x%, y%] points) that are no tap target at all (the Deities). */
  inert?: number[][][];
  /** Text (outside the numbered list) linked to a spot: per spot number, the
   *  exact Sanskrit phrases — a verse line or an inline ⟦mantra⟧ — whose tap
   *  lights it (Reader v7.8: the crown, «vāsudevāya mūrdhani» /
   *  «oṁ vāsudevāya namaḥ»). Matched in every language that gives them in IAST. */
  text?: Record<string, string[]>;
}

const IMAGES = data as Record<string, HotspotImage>;

/** Hotspot data of an image (by file name), or undefined. */
export function hotspotsFor(src: string | undefined): HotspotImage | undefined {
  return src ? IMAGES[src] : undefined;
}

/** Picture numbers named by a list label: "4" -> ["4"], "4, 5" -> ["4", "5"], "2.1" -> ["2.1"] (a sub-point). */
export function labelNumbers(label: string | undefined): string[] {
  return (label ?? "").match(/\d+(?:\.\d+)*/g) ?? [];
}

/** Spot number linked to this phrase of the picture's text links, or null. */
export function linkedSpot(data: HotspotImage | undefined, phrase: string): string | null {
  if (!data?.text) return null;
  const p = phrase.trim().normalize("NFC");
  for (const [n, list] of Object.entries(data.text)) {
    if (list.some((x) => x.normalize("NFC") === p)) return n;
  }
  return null;
}
