// The pixel editor (M56, M57; research 15 §5.6): a sheet's frames drawn on in whole pixels, and animated. The canvas and
// the frames strip take the view's place, the tools the panel's; one stroke or frame change is one undo step. Save
// makes a pixelize op edit version with what changed; a refused save keeps the edits (UI-001), the new version closes
// the editor.
import { useEffect, useMemo, useRef, useState } from "react";
import { fileUrl, type Meta } from "../api";
import { leave, useBusy, useHistory, useUnsaved } from "../hooks";
import { readGpl } from "./Panels";
import { FramesPanel, FramesStrip, span } from "./Timeline";
import * as T from "./tools";

type Tool = "pencil" | "eraser" | "fill" | "line" | "rect" | "ellipse" | "pick" | "select";
// the tool, its name, its key (Aseprite's letters)
export const TOOLS: [Tool, string, string][] = [
  ["pencil", "Pencil", "b"],
  ["eraser", "Eraser", "e"],
  ["fill", "Fill", "g"],
  ["line", "Line", "l"],
  ["rect", "Rectangle", "u"],
  ["ellipse", "Ellipse", "o"],
  ["pick", "Pick a colour", "i"],
  ["select", "Select", "m"],
];
const ZOOMS = [2, 4, 8, 16, 24];
const MAX_SIDE = 4096; // px of canvas: a 256 px frame stops at 16×
const zooms = (w: number, h: number) => ZOOMS.filter((n) => n === 2 || n * Math.max(w, h) <= MAX_SIDE);

/** An animation: Aseprite's frame tag, `from`/`to` frame indices (`repeat` "1": it plays once). */
export type Tag = { name: string; from: number; to: number; direction?: string; repeat?: string };
/** What the editor edits, one undo step at a time: the frames in order, their names and durations, the tags. */
export type Doc = { names: string[]; frames: Uint8ClampedArray[]; ms: number[]; tags: Tag[] };
type Sheet = { w: number; h: number; palette: string[] | null; original: Doc };

async function load(asset: string, v: Meta): Promise<Sheet> {
  const data = await (await fetch(fileUrl(asset, v.version, v.outputs.data))).json();
  const img = await new Promise<HTMLImageElement>((ok, bad) => {
    const im = new Image();
    im.onload = () => ok(im);
    im.onerror = () => bad(new Error("could not read the sheet"));
    im.src = fileUrl(asset, v.version, v.outputs.sheet);
  });
  const c = document.createElement("canvas");
  [c.width, c.height] = [img.width, img.height];
  const ctx = c.getContext("2d", { willReadFrequently: true })!;
  ctx.drawImage(img, 0, 0);
  const frames = data.frames as { filename?: string; frame: T.Rect; duration?: number }[];
  const pal = v.outputs.palette ? await fetch(fileUrl(asset, v.version, v.outputs.palette)) : null;
  if (pal && !pal.ok) throw new Error(`could not read the palette (${pal.status})`);
  const palette = pal ? readGpl(await pal.text()) : null;
  return {
    w: frames[0].frame.w,
    h: frames[0].frame.h,
    palette,
    original: {
      names: frames.map((f, i) => f.filename ?? `frame_${i}`),
      frames: frames.map((f) => new Uint8ClampedArray(ctx.getImageData(f.frame.x, f.frame.y, f.frame.w, f.frame.h).data)),
      ms: frames.map((f) => f.duration ?? 100),
      tags: data.meta?.frameTags ?? [],
    },
  };
}

/** A frame as a base64 PNG (what pixelize op edit reads). */
function png(d: Uint8ClampedArray, w: number, h: number) {
  const c = document.createElement("canvas");
  [c.width, c.height] = [w, h];
  c.getContext("2d")!.putImageData(new ImageData(new Uint8ClampedArray(d), w, h), 0, 0);
  return c.toDataURL("image/png").split(",")[1];
}

const differs = (a: Uint8ClampedArray, b: Uint8ClampedArray) => a !== b && a.some((x, i) => x !== b[i]);
const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);

/** A rectangle held inside a w × h frame (a drag that left the canvas), or null when nothing of it is inside. */
export function clamp(r: T.Rect, w: number, h: number): T.Rect | null {
  const x0 = Math.max(0, r.x), y0 = Math.max(0, r.y), x1 = Math.min(w, r.x + r.w), y1 = Math.min(h, r.y + r.h);
  return x1 > x0 && y1 > y0 ? { x: x0, y: y0, w: x1 - x0, h: y1 - y0 } : null;
}

export type PixelEd = ReturnType<typeof usePixelEditor>;

/** The editor's state, held by the workspace so the view (the canvas) and the panel (the tools) share it. */
export function usePixelEditor() {
  const hist = useHistory<Doc>();
  const [target, setTarget] = useState<{ asset: string; version: Meta } | null>(null);
  const [sheet, setSheet] = useState<Sheet | null>(null);
  const [frame, setFrame] = useState(0);
  const [tool, setTool] = useState<Tool>("pencil");
  const [colour, setColour] = useState("#000000");
  const [mirror, setMirror] = useState(false);
  const [filled, setFilled] = useState(false);
  const [contiguous, setContiguous] = useState(true);
  const [zoom, setZoom] = useState(8);
  const [sel, setSel] = useState<T.Rect | null>(null);
  const [clip, setClip] = useState<T.Patch | null>(null);
  const [error, setError] = useState("");
  const [onion, setOnion] = useState(0); // the frames shown faintly each side of the shown one (0: off)
  const [playing, setPlaying] = useState(false);
  const [tick, setTick] = useState(0); // play's clock: a one-frame loop goes back to the frame it shows
  const loading = useRef<object | null>(null); // the load that counts: a Close or another start mid-load drops it
  const doc = hist.h?.now ?? null;
  const frames = doc?.frames ?? null;
  const at = doc ? Math.min(frame, doc.names.length - 1) : frame; // an undone Add leaves fewer frames
  const o = sheet?.original;
  // what Save would send: anything that differs from the version's (an undone or no-op step is not a change)
  const dirty = !!(doc && o && (!same([doc.names, doc.ms, doc.tags], [o.names, o.ms, o.tags]) || doc.frames.some((d, i) => differs(d, o.frames[i]))));
  // play: the shown frame's animation (or every frame), each frame for its own time; one that plays once stops at its end
  useEffect(() => {
    if (!playing || !doc) return;
    const [a, b, loops] = span(doc, at);
    const t = setTimeout(() => (setTick((k) => k + 1), at < b ? setFrame(at + 1) : loops ? setFrame(a) : setPlaying(false)), doc.ms[at]);
    return () => clearTimeout(t);
  }, [playing, at, doc, tick]);
  return {
    editing: !!target,
    target,
    sheet,
    doc,
    frames,
    frame: at,
    setFrame,
    onion,
    setOnion,
    playing,
    setPlaying,
    tool,
    setTool,
    colour,
    setColour,
    mirror,
    setMirror,
    filled,
    setFilled,
    contiguous,
    setContiguous,
    zoom,
    setZoom,
    sel,
    setSel,
    clip,
    setClip,
    error,
    hist,
    dirty,
    async start(asset: string, version: Meta) {
      const me = {};
      loading.current = me;
      setError("");
      setTarget({ asset, version });
      try {
        const s = await load(asset, version);
        if (loading.current !== me) return;
        setSheet(s);
        setFrame(0);
        setSel(null);
        setPlaying(false);
        // the zoom that shows a frame about 512 px wide
        setZoom(ZOOMS.filter((z) => z * s.w <= 640).at(-1) ?? 2);
        if (s.palette?.length) setColour(s.palette.find((c) => c !== "#000000") ?? s.palette[0]);
        hist.start(s.original);
      } catch (e) {
        setError(String((e as Error).message ?? e));
      }
    },
    close() {
      loading.current = null;
      setPlaying(false);
      hist.stop();
      setTarget(null);
      setSheet(null);
      setSel(null);
    },
    /** One undo step: frame `i` (default the shown one) through `f`; nothing when it changes nothing. */
    change(f: (d: Uint8ClampedArray) => Uint8ClampedArray, i = at) {
      if (!frames?.[i]) return;
      const next = f(frames[i]);
      if (differs(next, frames[i])) hist.commit((d) => ({ ...d, frames: d.frames.map((x, k) => (k === i ? next : x)) }));
    },
    /** One undo step of the frames, their order, durations or tags (Timeline.tsx). */
    edit(f: (d: Doc) => Doc) {
      if (doc && f(doc) !== doc) hist.commit(f);
    },
    /** The selection, held inside the frame. */
    select(r: T.Rect | null) {
      setSel(r && sheet ? clamp(r, sheet.w, sheet.h) : null);
    },
    /** The save's params: what differs from the version. Only the frames whose pixels changed (or a new frame with any)
     * travel, as job params land in meta.json; the order, the durations and the tags when they changed. */
    params(): Record<string, unknown> | null {
      if (!sheet || !doc || !o) return null;
      const was = new Map(o.names.map((n, i) => [n, i]));
      const frames: Record<string, string> = {};
      const durations: Record<string, number> = {};
      doc.names.forEach((n, i) => {
        const k = was.get(n);
        const d = doc.frames[i];
        if (k === undefined ? d.some((x, j) => j % 4 === 3 && x > 0) : differs(d, o.frames[k])) frames[n] = png(d, sheet.w, sheet.h);
        if (k === undefined || doc.ms[i] !== o.ms[k]) durations[n] = doc.ms[i];
      });
      const order = !same(doc.names, o.names); // the step drops the input's tags for a new order unless they are sent
      return {
        op: "edit",
        frames,
        ...(Object.keys(durations).length ? { durations } : {}),
        ...(order ? { order: doc.names } : {}),
        ...(order || !same(doc.tags, o.tags) ? { tags: doc.tags } : {}),
      };
    },
  };
}

/** The frame in whole pixels at the editor's zoom; a stroke shows while it is drawn and becomes one step when let go. */
export function EditorCanvas({ ed }: { ed: PixelEd }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [live, setShown] = useState<Uint8ClampedArray | null>(null);
  // the stroke, and what it has drawn so far in a ref too: a release can come before the last move has rendered
  const stroke = useRef<{ start: T.Pt; pts: T.Pt[]; base: Uint8ClampedArray; frame: number; move?: { patch: T.Patch; from: T.Rect } } | null>(null);
  const drawn = useRef<Uint8ClampedArray | null>(null);
  const setLive = (d: Uint8ClampedArray | null) => ((drawn.current = d), setShown(d));
  const s = ed.sheet;
  const data = live ?? ed.frames?.[ed.frame] ?? null;
  const z = ed.zoom;
  // the onion skin: the frames before in red, after in blue, fainter the farther. Put together at the frame's own size
  // once per frame shown (a stroke leaves the others as they are), then scaled once: drawn at the canvas's size each
  // move it cost 70 ms a move (128 px at 24×, 3 frames each side; docs/IMPLEMENTATION "M57")
  const onion = useMemo(() => {
    const fs = ed.frames;
    if (!s || !fs || !ed.onion || ed.playing) return null;
    const o = document.createElement("canvas");
    [o.width, o.height] = [s.w, s.h];
    const oc = o.getContext("2d")!;
    for (let k = ed.onion; k >= 1; k--)
      for (const [j, tint] of [
        [ed.frame - k, "#ff3c3c"],
        [ed.frame + k, "#3c78ff"],
      ] as const) {
        if (j < 0 || j >= fs.length) continue;
        const t = document.createElement("canvas");
        [t.width, t.height] = [s.w, s.h];
        const tc = t.getContext("2d")!;
        tc.putImageData(new ImageData(new Uint8ClampedArray(fs[j]), s.w, s.h), 0, 0);
        tc.globalCompositeOperation = "source-atop";
        tc.globalAlpha = 0.5;
        tc.fillStyle = tint;
        tc.fillRect(0, 0, s.w, s.h);
        oc.globalAlpha = 0.4 / k;
        oc.drawImage(t, 0, 0);
      }
    return o;
  }, [s, ed.frames, ed.frame, ed.onion, ed.playing]);
  useEffect(() => {
    const c = canvas.current;
    if (!c || !s || !data) return;
    [c.width, c.height] = [s.w * z, s.h * z];
    const off = document.createElement("canvas");
    [off.width, off.height] = [s.w, s.h];
    off.getContext("2d")!.putImageData(new ImageData(new Uint8ClampedArray(data), s.w, s.h), 0, 0);
    const ctx = c.getContext("2d")!;
    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, c.width, c.height);
    if (onion) ctx.drawImage(onion, 0, 0, c.width, c.height); // under the shown frame
    ctx.drawImage(off, 0, 0, c.width, c.height);
    if (z >= 8) {
      ctx.strokeStyle = "rgba(128, 128, 128, 0.25)";
      ctx.beginPath();
      for (let x = 1; x < s.w; x++) (ctx.moveTo(x * z + 0.5, 0), ctx.lineTo(x * z + 0.5, c.height));
      for (let y = 1; y < s.h; y++) (ctx.moveTo(0, y * z + 0.5), ctx.lineTo(c.width, y * z + 0.5));
      ctx.stroke();
    }
    if (ed.sel) {
      ctx.setLineDash([4, 4]);
      ctx.strokeStyle = "#fff";
      ctx.strokeRect(ed.sel.x * z + 0.5, ed.sel.y * z + 0.5, ed.sel.w * z - 1, ed.sel.h * z - 1);
      ctx.setLineDash([]);
    }
  });
  if (ed.error) return <p className="error">{ed.error}</p>;
  if (!s || !data) return <p className="muted">Loading the frames…</p>;
  const at = (e: React.PointerEvent): T.Pt => {
    const r = canvas.current!.getBoundingClientRect();
    return [Math.floor((e.clientX - r.left) / z), Math.floor((e.clientY - r.top) / z)];
  };
  const rgba = ed.tool === "eraser" ? null : T.hexRgba(ed.colour);
  const shape = (st: { start: T.Pt; pts: T.Pt[] }, p: T.Pt): T.Pt[] =>
    ed.tool === "line" ? T.line(st.start, p) : ed.tool === "rect" ? T.rect(st.start, p, ed.filled) : ed.tool === "ellipse" ? T.ellipse(st.start, p, ed.filled) : ed.tool === "pencil" ? T.perfect(st.pts) : st.pts;
  const down = (e: React.PointerEvent) => {
    if (ed.playing) return ed.setPlaying(false); // a click on a playing frame stops it there
    const p = at(e);
    const base = ed.frames![ed.frame];
    if (ed.tool === "pick") {
      const c = T.pixel(base, s.w, p[0], p[1]);
      if (c[3] > 0) ed.setColour(T.rgbaHex(c));
      return;
    }
    if (ed.tool === "fill") return ed.change((d) => T.fill(d, s.w, s.h, p, rgba, ed.contiguous));
    canvas.current!.setPointerCapture(e.pointerId);
    if (ed.tool === "select") {
      const r = ed.sel;
      if (r && p[0] >= r.x && p[1] >= r.y && p[0] < r.x + r.w && p[1] < r.y + r.h) {
        // drag inside the selection: its pixels move, the hole they leave is transparent
        stroke.current = { start: p, pts: [], base: T.clear(base, s.w, s.h, r), frame: ed.frame, move: { patch: T.copy(base, s.w, s.h, r), from: r } };
      } else stroke.current = { start: p, pts: [], base, frame: ed.frame };
      return;
    }
    stroke.current = { start: p, pts: [p], base, frame: ed.frame };
    setLive(T.plot(base, s.w, s.h, shape(stroke.current, p), rgba, ed.mirror));
  };
  const move = (e: React.PointerEvent) => {
    const st = stroke.current;
    if (!st) return;
    const p = at(e);
    if (ed.tool === "select") {
      const [dx, dy] = [p[0] - st.start[0], p[1] - st.start[1]];
      if (st.move) return setLive(T.paste(st.base, s.w, s.h, st.move.patch, st.move.from.x + dx, st.move.from.y + dy));
      const [x0, y0, x1, y1] = [Math.min(st.start[0], p[0]), Math.min(st.start[1], p[1]), Math.max(st.start[0], p[0]), Math.max(st.start[1], p[1])];
      return ed.select({ x: x0, y: y0, w: x1 - x0 + 1, h: y1 - y0 + 1 });
    }
    if (ed.tool === "pencil" || ed.tool === "eraser") st.pts.push(...T.line(st.pts.at(-1)!, p).slice(1));
    setLive(T.plot(st.base, s.w, s.h, shape(st, p), rgba, ed.mirror));
  };
  const up = (e: React.PointerEvent) => {
    const st = stroke.current;
    stroke.current = null;
    if (st?.move) {
      const [dx, dy] = [at(e)[0] - st.start[0], at(e)[1] - st.start[1]];
      ed.select({ ...st.move.from, x: st.move.from.x + dx, y: st.move.from.y + dy });
    }
    const done = drawn.current;
    if (st && done) ed.change(() => done, st.frame);
    setLive(null);
  };
  return (
    <div className="preview pixel-view">
      <div className="pixel-stage checker" style={{ paddingTop: 56, paddingBottom: 132 }}>
        <canvas
          ref={canvas}
          className="sheet-canvas pixel-edit"
          aria-label={`frame ${ed.frame + 1} of ${ed.frames!.length}, ${s.w} × ${s.h} px`}
          data-frame={ed.frame}
          style={{ width: s.w * z, height: s.h * z, cursor: ed.tool === "pick" ? "copy" : "crosshair" }}
          onPointerDown={down}
          onPointerMove={move}
          onPointerUp={up}
          onPointerCancel={up}
        />
      </div>
      <div className="toolbar" role="group" aria-label="View">
        <button aria-pressed={ed.playing} onClick={() => ed.setPlaying(!ed.playing)} title="The shown frame's animation, each frame for its time">
          {ed.playing ? "Stop" : "Play"}
        </button>
        <select aria-label="Onion skin" value={ed.onion} onChange={(e) => ed.setOnion(Number(e.target.value))}>
          <option value={0}>Onion skin off</option>
          {[1, 2, 3].map((k) => (
            <option key={k} value={k}>
              Onion skin: {k} frame{k > 1 ? "s" : ""} each side
            </option>
          ))}
        </select>
        {zooms(s.w, s.h).map((n, k) => (
          <button key={n} aria-pressed={z === n} onClick={() => ed.setZoom(n)} title={`Key ${k + 1}`}>
            {n}×
          </button>
        ))}
      </div>
      <FramesStrip ed={ed} />
    </div>
  );
}

/** The panel while editing: the tools, the palette, the selection, the frames, undo, Save and Close. */
export function EditorPanel({ ed, onSave }: { ed: PixelEd; onSave: (params: object) => Promise<unknown> }) {
  const [busy, run] = useBusy();
  useUnsaved("pixels", ed.dirty && !busy);
  const s = ed.sheet;
  // the keys: tools by letter, undo/redo, frames with , and .; not while typing in a field
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      // not while typing: a text, number or colour field; a tool's radio or a checkbox keeps the keys working
      const t = e.target;
      if (t instanceof HTMLTextAreaElement || (t instanceof HTMLElement && t.isContentEditable)) return;
      if (t instanceof HTMLInputElement && !["radio", "checkbox", "button", "range"].includes(t.type)) return;
      const k = e.key.toLowerCase();
      if ((e.ctrlKey || e.metaKey) && k === "z") return e.preventDefault(), e.shiftKey ? ed.hist.redo() : ed.hist.undo();
      if ((e.ctrlKey || e.metaKey) && k === "y") return e.preventDefault(), ed.hist.redo();
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const tool = TOOLS.find(([, , key]) => key === k);
      if (tool) return ed.setTool(tool[0]);
      const n = ed.frames?.length ?? 0;
      if (n && k === ",") return ed.setFrame((ed.frame + n - 1) % n);
      if (n && k === ".") return ed.setFrame((ed.frame + 1) % n);
      const zoom = s && /^[1-9]$/.test(k) ? zooms(s.w, s.h)[Number(k) - 1] : undefined;
      if (zoom) return ed.setZoom(zoom);
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  });
  if (!s || !ed.frames) return <p className="muted">{ed.error || "Loading the frames…"}</p>;
  const sel = ed.sel;
  const rgba = T.hexRgba(ed.colour);
  const onSel = (f: (d: Uint8ClampedArray, r: T.Rect) => Uint8ClampedArray) => sel && ed.change((d) => f(d, sel));
  const turn = (how: "h" | "v" | "r") => {
    if (!sel) return;
    const p = T.copy(ed.frames![ed.frame], s.w, s.h, sel);
    const q = how === "r" ? T.rotate(p) : T.flip(p, how);
    ed.change((d) => T.paste(T.clear(d, s.w, s.h, sel), s.w, s.h, q, sel.x, sel.y));
    if (how === "r") ed.select({ ...sel, w: q.w, h: q.h }); // a turn past the frame's edge loses what falls outside
  };
  const save = () =>
    run(async () => {
      const params = ed.params();
      if (params && (await onSave(params))) ed.close(); // a new version: done; refused: the edits stay
    });
  return (
    <>
      <section className="stack">
        <h3>Edit the pixels</h3>
        <p className="muted">
          {s.w} × {s.h} px{s.palette ? `, the version's ${s.palette.length} colours` : ""}. Save makes a new version with what changed; Close leaves this
          one as it is.
        </p>
        <fieldset>
          <legend>Tool</legend>
          <div className="choices">
            {TOOLS.map(([id, name, key]) => (
              <label key={id} className="choice">
                <input type="radio" name="pixel-tool" checked={ed.tool === id} onChange={() => ed.setTool(id)} />
                <span>{name}</span>
                <span className="muted">{key.toUpperCase()}</span>
              </label>
            ))}
          </div>
        </fieldset>
        <label className="check">
          <input type="checkbox" checked={ed.mirror} onChange={(e) => ed.setMirror(e.target.checked)} /> Mirror across the middle
        </label>
        {(ed.tool === "rect" || ed.tool === "ellipse") && (
          <label className="check">
            <input type="checkbox" checked={ed.filled} onChange={(e) => ed.setFilled(e.target.checked)} /> Filled
          </label>
        )}
        {ed.tool === "fill" && (
          <label className="check">
            <input type="checkbox" checked={ed.contiguous} onChange={(e) => ed.setContiguous(e.target.checked)} /> Only the touching area (off: every pixel of
            that colour)
          </label>
        )}
        <fieldset>
          <legend>Colour</legend>
          {s.palette ? (
            <div className="palette" role="group" aria-label="Palette">
              {s.palette.map((c) => (
                <button key={c} className="pixel-swatch" title={c} aria-label={`Colour ${c}`} aria-pressed={ed.colour === c} style={{ background: c }} onClick={() => ed.setColour(c)} />
              ))}
            </div>
          ) : (
            <input type="color" aria-label="Drawing colour" value={ed.colour} onChange={(e) => ed.setColour(e.target.value)} />
          )}
        </fieldset>
        <div className="row">
          <button className="small" onClick={() => ed.change((d) => T.outline(d, s.w, s.h, rgba))} title="A 1-px outline round the drawing, in this colour">
            Outline
          </button>
          <button className="small" disabled={!ed.hist.h?.past.length} onClick={ed.hist.undo} title="Ctrl+Z">
            Undo
          </button>
          <button className="small" disabled={!ed.hist.h?.future.length} onClick={ed.hist.redo} title="Ctrl+Y">
            Redo
          </button>
        </div>
      </section>
      <details open={!!sel || !!ed.clip}>
        <summary>Selection {sel ? `(${sel.w} × ${sel.h})` : ""}</summary>
        <div>
          <div className="row">
            <button className="small" disabled={!sel} onClick={() => turn("h")}>
              Flip ↔
            </button>
            <button className="small" disabled={!sel} onClick={() => turn("v")}>
              Flip ↕
            </button>
            <button className="small" disabled={!sel} onClick={() => turn("r")}>
              Turn 90°
            </button>
            <button className="small" disabled={!sel} onClick={() => sel && ed.setClip(T.copy(ed.frames![ed.frame], s.w, s.h, sel))}>
              Copy
            </button>
            <button
              className="small"
              disabled={!sel}
              onClick={() => sel && (ed.setClip(T.copy(ed.frames![ed.frame], s.w, s.h, sel)), onSel((d, r) => T.clear(d, s.w, s.h, r)))}
            >
              Cut
            </button>
            <button
              className="small"
              disabled={!ed.clip}
              onClick={() => {
                const c = ed.clip!;
                const [x, y] = sel ? [sel.x, sel.y] : [0, 0];
                ed.change((d) => T.paste(d, s.w, s.h, c, x, y));
                ed.select({ x, y, w: c.w, h: c.h });
              }}
            >
              Paste
            </button>
            <button className="small" disabled={!sel} onClick={() => onSel((d, r) => T.clear(d, s.w, s.h, r))}>
              Delete
            </button>
            <button className="small" disabled={!sel} onClick={() => ed.setSel(null)}>
              Deselect
            </button>
          </div>
          <p className="muted">Draw a rectangle with Select; drag inside it to move its pixels.</p>
        </div>
      </details>
      <FramesPanel ed={ed} />
      <section className="stack">
        <div className="row">
          <button className="primary" disabled={busy || !ed.dirty} onClick={save}>
            {busy ? "Saving…" : "Save as a new version"}
          </button>
          <button onClick={() => leave() && ed.close()}>Close</button>
        </div>
        {ed.dirty && <span className="muted">Unsaved changes</span>}
      </section>
    </>
  );
}
