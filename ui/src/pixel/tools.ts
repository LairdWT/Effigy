// The pixel editor's tools (M56, research 15 §5.6): pure functions on a frame's RGBA bytes (row by row, 4 bytes a
// pixel). Each returns the points or a new array; nothing here draws on a screen.

export type Pt = [number, number];
export type Rect = { x: number; y: number; w: number; h: number };
export type Patch = { w: number; h: number; data: Uint8ClampedArray };
export type RGBA = [number, number, number, number];

export const hexRgba = (hex: string): RGBA => [parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16), parseInt(hex.slice(5, 7), 16), 255];
export const rgbaHex = (c: ArrayLike<number>) => "#" + [c[0], c[1], c[2]].map((x) => x.toString(16).padStart(2, "0")).join("");

export function pixel(data: Uint8ClampedArray, w: number, x: number, y: number): RGBA {
  const i = (y * w + x) * 4;
  return [data[i], data[i + 1], data[i + 2], data[i + 3]];
}

/** The points set to `c` (or cleared with c null), the ones outside the frame skipped; `mirror` doubles each across x. */
export function plot(data: Uint8ClampedArray, w: number, h: number, pts: Pt[], c: RGBA | null, mirror = false) {
  const out = new Uint8ClampedArray(data);
  const set = (x: number, y: number) => {
    if (x < 0 || y < 0 || x >= w || y >= h) return;
    out.set(c ?? [0, 0, 0, 0], (y * w + x) * 4);
  };
  for (const [x, y] of pts) {
    set(x, y);
    if (mirror) set(w - 1 - x, y);
  }
  return out;
}

/** Bresenham from a to b, both ends in. */
export function line([x0, y0]: Pt, [x1, y1]: Pt): Pt[] {
  const pts: Pt[] = [];
  const dx = Math.abs(x1 - x0), dy = -Math.abs(y1 - y0);
  const sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
  let err = dx + dy;
  for (;;) {
    pts.push([x0, y0]);
    if (x0 === x1 && y0 === y1) return pts;
    const e2 = 2 * err;
    if (e2 >= dy) (err += dy), (x0 += sx);
    if (e2 <= dx) (err += dx), (y0 += sy);
  }
}

/** A stroke's points with the L-corners dropped (Aseprite's pixel-perfect pencil): of three points in a row where the
 * outer two touch diagonally, the middle one goes, so a curve is one pixel thick. Repeats are dropped first. */
export function perfect(pts: Pt[]): Pt[] {
  const out: Pt[] = [];
  for (const p of pts) {
    const last = out.at(-1);
    if (last && last[0] === p[0] && last[1] === p[1]) continue;
    const prev = out.at(-2);
    if (prev && last && Math.abs(prev[0] - p[0]) === 1 && Math.abs(prev[1] - p[1]) === 1 && (prev[0] === last[0] || prev[1] === last[1])) out.pop();
    out.push(p);
  }
  return out;
}

const box = ([x0, y0]: Pt, [x1, y1]: Pt) => [Math.min(x0, x1), Math.min(y0, y1), Math.max(x0, x1), Math.max(y0, y1)];

export function rect(a: Pt, b: Pt, filled: boolean): Pt[] {
  const [l, t, r, bt] = box(a, b);
  const pts: Pt[] = [];
  for (let y = t; y <= bt; y++) for (let x = l; x <= r; x++) if (filled || x === l || x === r || y === t || y === bt) pts.push([x, y]);
  return pts;
}

/** The ellipse inside the box a-b: each row's span from the ellipse's equation; the outline is the filled shape's pixels
 * that touch one outside it, so the steep sides have no gaps. */
export function ellipse(a: Pt, b: Pt, filled: boolean): Pt[] {
  const [l, t, r, bt] = box(a, b);
  const cx = (l + r) / 2, cy = (t + bt) / 2, rx = (r - l) / 2 + 0.5, ry = (bt - t) / 2 + 0.5;
  const inside = new Set<string>();
  const pts: Pt[] = [];
  for (let y = t; y <= bt; y++) {
    const dy = (y - cy) / ry;
    const half = rx * Math.sqrt(Math.max(0, 1 - dy * dy));
    for (let x = Math.round(cx - half + 0.5); x <= Math.round(cx + half - 0.5); x++) (pts.push([x, y]), inside.add(`${x},${y}`));
  }
  if (filled) return pts;
  const has = (x: number, y: number) => inside.has(`${x},${y}`);
  return pts.filter(([x, y]) => !has(x + 1, y) || !has(x - 1, y) || !has(x, y + 1) || !has(x, y - 1));
}

const same = (data: Uint8ClampedArray, i: number, c: RGBA) =>
  (data[i + 3] === 0 && c[3] === 0) || (data[i] === c[0] && data[i + 1] === c[1] && data[i + 2] === c[2] && data[i + 3] === c[3]);

/** Fill from (x, y): the 4-connected run of its colour (`contiguous`), or every pixel of that colour in the frame. */
export function fill(data: Uint8ClampedArray, w: number, h: number, [x, y]: Pt, c: RGBA | null, contiguous: boolean) {
  if (x < 0 || y < 0 || x >= w || y >= h) return data;
  const from = pixel(data, w, x, y);
  const to: RGBA = c ?? [0, 0, 0, 0];
  if (same(data, (y * w + x) * 4, to)) return data;
  const out = new Uint8ClampedArray(data);
  if (!contiguous) {
    for (let i = 0; i < out.length; i += 4) if (same(data, i, from)) out.set(to, i);
    return out;
  }
  const stack: Pt[] = [[x, y]];
  while (stack.length) {
    const [px, py] = stack.pop()!;
    const i = (py * w + px) * 4;
    if (px < 0 || py < 0 || px >= w || py >= h || !same(out, i, from)) continue;
    out.set(to, i);
    stack.push([px + 1, py], [px - 1, py], [px, py + 1], [px, py - 1]);
  }
  return out;
}

/** A 1-px outline in `c` round the opaque pixels (the transparent ones touching them side by side). */
export function outline(data: Uint8ClampedArray, w: number, h: number, c: RGBA) {
  const out = new Uint8ClampedArray(data);
  const opaque = (x: number, y: number) => x >= 0 && y >= 0 && x < w && y < h && data[(y * w + x) * 4 + 3] > 0;
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++)
      if (!opaque(x, y) && (opaque(x + 1, y) || opaque(x - 1, y) || opaque(x, y + 1) || opaque(x, y - 1))) out.set(c, (y * w + x) * 4);
  return out;
}

/** The rectangle's pixels as a patch (clipped to the frame). */
export function copy(data: Uint8ClampedArray, w: number, h: number, r: Rect): Patch {
  const x0 = Math.max(0, r.x), y0 = Math.max(0, r.y), x1 = Math.min(w, r.x + r.w), y1 = Math.min(h, r.y + r.h);
  const pw = Math.max(0, x1 - x0), ph = Math.max(0, y1 - y0);
  const out = new Uint8ClampedArray(pw * ph * 4);
  for (let y = 0; y < ph; y++) out.set(data.subarray(((y0 + y) * w + x0) * 4, ((y0 + y) * w + x0 + pw) * 4), y * pw * 4);
  return { w: pw, h: ph, data: out };
}

/** The rectangle made transparent. */
export function clear(data: Uint8ClampedArray, w: number, h: number, r: Rect) {
  return plot(data, w, h, rect([r.x, r.y], [r.x + r.w - 1, r.y + r.h - 1], true), null);
}

/** The patch's opaque pixels put at (x, y), clipped to the frame. */
export function paste(data: Uint8ClampedArray, w: number, h: number, p: Patch, x: number, y: number) {
  const out = new Uint8ClampedArray(data);
  for (let py = 0; py < p.h; py++)
    for (let px = 0; px < p.w; px++) {
      const i = (py * p.w + px) * 4, tx = x + px, ty = y + py;
      if (p.data[i + 3] > 0 && tx >= 0 && ty >= 0 && tx < w && ty < h) out.set(p.data.subarray(i, i + 4), (ty * w + tx) * 4);
    }
  return out;
}

export function flip(p: Patch, across: "h" | "v"): Patch {
  const out = new Uint8ClampedArray(p.data.length);
  for (let y = 0; y < p.h; y++)
    for (let x = 0; x < p.w; x++) {
      const [sx, sy] = across === "h" ? [p.w - 1 - x, y] : [x, p.h - 1 - y];
      out.set(p.data.subarray((sy * p.w + sx) * 4, (sy * p.w + sx) * 4 + 4), (y * p.w + x) * 4);
    }
  return { w: p.w, h: p.h, data: out };
}

/** A quarter turn clockwise: the patch's width and height swap. */
export function rotate(p: Patch): Patch {
  const out = new Uint8ClampedArray(p.data.length);
  for (let y = 0; y < p.h; y++)
    for (let x = 0; x < p.w; x++) out.set(p.data.subarray((y * p.w + x) * 4, (y * p.w + x) * 4 + 4), (x * p.h + (p.h - 1 - y)) * 4);
  return { w: p.h, h: p.w, data: out };
}
