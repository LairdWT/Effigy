// The 2D track's viewer (research 15 §5.1, M50/M51): a picture, a set of pictures or a sprite sheet. Pixel art is
// shown in whole pixels (a whole-number zoom, no smoothing); transparency shows as a checkerboard. A sheet plays under
// the 3D viewer's own time bar (anim/Transport), driven by SheetClock.
import { useEffect, useMemo, useRef, useState } from "react";
import { fileUrl, type Meta } from "../api";
import { Transport, useFrame, useTransportKeys, type Clock } from "../anim/Transport";

export type SheetData = {
  frames: { filename?: string; frame: { x: number; y: number; w: number; h: number }; duration: number }[];
  meta: { frameTags?: { name: string; from: number; to: number }[] };
};

/** A version's set of pictures (concepts op image), in order. */
export const pictureKeys = (v: Meta) =>
  Object.keys(v.outputs)
    .filter((k) => /^image_\d+$/.test(k))
    .sort((a, b) => +a.slice(6) - +b.slice(6));
export const isSheet = (v: Meta) => !!(v.outputs.sheet && v.outputs.data);
/** What the 2D check and exports take (M53, M54): a sheet, or a seamless tile. */
export const is2D = (v: Meta) => isSheet(v) || !!v.outputs.tile || !!v.outputs.layers;
const crisp = (v: Meta) => v.step === "pixelize" || v.step === "sprites"; // drawn on a pixel grid
const ZOOMS = [0, 1, 2, 4, 8, 16]; // 0: fit the view
const still = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** A sheet's frames as the time the Transport bar reads and sets: frame k shows from k / fps, looping. */
export class SheetClock implements Clock {
  private base = 0;
  private t0 = performance.now();
  private paused = still();
  private rate = 1;
  constructor(
    private n: number,
    private perSecond: number,
  ) {}
  fps() {
    return this.perSecond;
  }
  duration() {
    return Math.max(this.n - 1, 1) / this.perSecond; // the last frame's start: Transport's last frame number
  }
  time() {
    const t = this.paused ? this.base : this.base + ((performance.now() - this.t0) / 1000) * this.rate;
    return t % (this.n / this.perSecond);
  }
  frame() {
    return Math.min(this.n - 1, Math.round(this.time() * this.perSecond));
  }
  play() {
    this.t0 = performance.now();
    this.paused = false;
  }
  pause() {
    this.base = this.time();
    this.paused = true;
  }
  seek(t: number) {
    this.base = t;
    this.t0 = performance.now();
  }
  isPaused() {
    return this.paused;
  }
  setSpeed(s: number) {
    this.base = this.time();
    this.t0 = performance.now();
    this.rate = s;
  }
}

function useBox() {
  const ref = useRef<HTMLDivElement>(null);
  const [box, setBox] = useState({ w: 800, h: 600 });
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setBox({ w: el.clientWidth - 16, h: el.clientHeight - 16 }));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, box] as const;
}

/** The zoom a picture of w × h is drawn at: the chosen one, or the fit (whole numbers for pixel art). */
function zoomOf(z: number, w: number, h: number, box: { w: number; h: number }, pixel: boolean) {
  if (z) return z;
  const fit = Math.min(box.w / w, box.h / h);
  if (fit < 1) return fit;
  return pixel ? Math.floor(fit) : 1;
}

/** A sheet's data and image, loaded once per version. */
function useSheet(asset: string, v: Meta) {
  const [data, setData] = useState<SheetData | null>(null);
  const [img, setImg] = useState<HTMLImageElement | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!isSheet(v)) return;
    let live = true;
    setData(null);
    setImg(null);
    fetch(fileUrl(asset, v.version, v.outputs.data))
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`${v.outputs.data}: ${r.status}`))))
      .then((d) => live && setData(d), (e) => live && setError(String(e.message ?? e)));
    const im = new Image();
    im.onload = () => live && setImg(im);
    im.src = fileUrl(asset, v.version, v.outputs.sheet);
    return () => {
      live = false;
    };
  }, [asset, v.version]);
  return { data, img, error };
}

export function PixelView(props: { asset: string; version: Meta; picked: string; onPick: (key: string) => void }) {
  const v = props.version;
  const [zoom, setZoom] = useState(0);
  const [tag, setTag] = useState(-1); // -1: every frame of the sheet
  const [repeat, setRepeat] = useState(3); // a tile (M54): 3 × 3, so its seams would show
  const [depthView, setDepthView] = useState(false); // a depth version (M55): its picture or its depth
  // a layers version: "scroll" (all of them, moving), a layer's output key on its own, or "bands"
  const [layerView, setLayerView] = useState("scroll");
  useEffect(() => setLayerView("scroll"), [v.version]);
  const layerKeys = Object.keys(v.outputs)
    .filter((k) => /^layer_\d+$/.test(k))
    .sort((a, b) => +a.slice(6) - +b.slice(6));
  const [ref, box] = useBox();
  const sheet = useSheet(props.asset, v);
  useEffect(() => setTag(-1), [v.version]);
  const keys = pictureKeys(v);
  const file = keys.length ? v.outputs[props.picked] ?? v.outputs[keys[0]] : v.outputs.image;
  const tags = sheet.data?.meta.frameTags ?? [];
  const [from, to] = sheet.data ? (tag >= 0 && tags[tag] ? [tags[tag].from, tags[tag].to] : [0, sheet.data.frames.length - 1]) : [0, 0];
  const n = to - from + 1;
  const perSecond = 1000 / (sheet.data?.frames[from]?.duration || 83);
  const clock = useMemo(() => new SheetClock(n, perSecond), [v.version, from, n, perSecond]);
  const playing = isSheet(v) && !!sheet.data && !!sheet.img && n > 1;
  // the 3D view's own frame: the toolbar floats at the top, the time bar (or the pictures) at the bottom, the stage
  // between them, so Fit never puts the picture under either
  const bottom = playing ? 72 : keys.length > 1 ? 104 : 12;
  return (
    <div className="preview pixel-view">
      <div className="pixel-stage checker" ref={ref} style={{ paddingTop: 56, paddingBottom: bottom }}>
        {v.outputs.layers && layerView === "scroll" ? (
          <Parallax asset={props.asset} version={v} zoom={zoom} box={{ w: box.w, h: box.h - 56 - bottom }} />
        ) : v.outputs.layers || (v.outputs.depth && depthView) ? (
          <Picture
            src={fileUrl(props.asset, v.version, v.outputs.layers ? v.outputs[layerView] : v.outputs.preview)}
            zoom={zoom}
            box={{ w: box.w, h: box.h - 56 - bottom }}
            pixel={false}
          />
        ) : v.outputs.tile ? (
          <Tiled src={fileUrl(props.asset, v.version, v.outputs.tile)} zoom={zoom} box={{ w: box.w, h: box.h - 56 - bottom }} pixel={crisp(v)} repeat={repeat} />
        ) : isSheet(v) ? (
          sheet.error ? (
            <p className="error">Could not read the sheet: {sheet.error}</p>
          ) : sheet.data && sheet.img ? (
            <Sheet data={sheet.data} img={sheet.img} from={from} clock={clock} zoom={zoom} box={{ w: box.w, h: box.h - 56 - bottom }} />
          ) : (
            <p className="muted">Loading…</p>
          )
        ) : file ? (
          <Picture src={fileUrl(props.asset, v.version, file)} zoom={zoom} box={{ w: box.w, h: box.h - 56 - bottom }} pixel={crisp(v)} />
        ) : (
          <p className="muted">{v.step === "brief" ? "The pictures appear here." : "This version has no picture."}</p>
        )}
      </div>
      <div className="toolbar" role="group" aria-label="View">
        {v.outputs.depth &&
          [false, true].map((d) => (
            <button key={String(d)} aria-pressed={depthView === d} onClick={() => setDepthView(d)}>
              {d ? "Depth" : "Picture"}
            </button>
          ))}
        {v.outputs.layers && (
          <select aria-label="Show" value={layerView} onChange={(e) => setLayerView(e.target.value)}>
            <option value="scroll">All layers, scrolling</option>
            {layerKeys.map((k, i) => (
              <option key={k} value={k}>
                {i === 0 ? "The farthest layer alone" : i === layerKeys.length - 1 ? "The nearest layer alone" : `Layer ${i + 1} alone`}
              </option>
            ))}
            <option value="bands">Bands</option>
          </select>
        )}
        {v.outputs.tile &&
          [3, 1].map((n) => (
            <button key={n} aria-pressed={repeat === n} onClick={() => setRepeat(n)}>
              {n > 1 ? `Repeated ${n} × ${n}` : "One tile"}
            </button>
          ))}
        {playing && tags.length > 0 && (
          <select aria-label="Animation" value={tag} onChange={(e) => setTag(Number(e.target.value))}>
            <option value={-1}>All frames</option>
            {tags.map((t, k) => (
              <option key={t.name + k} value={k}>
                Play: {t.name}
              </option>
            ))}
          </select>
        )}
        {ZOOMS.map((z) => (
          <button key={z} aria-pressed={zoom === z} onClick={() => setZoom(z)}>
            {z ? `${z}×` : "Fit"}
          </button>
        ))}
      </div>
      {playing && <SheetBar clock={clock} />}
      {/* the 3D view's stats line, where its time bar is not up */}
      {!playing && keys.length <= 1 && <Stats asset={props.asset} version={v} file={file} sheet={sheet.data} />}
      {keys.length > 1 && (
        <div className="picture-strip" role="group" aria-label="Pictures">
          {keys.map((k, i) => (
            <button key={k} aria-pressed={(v.outputs[props.picked] ? props.picked : keys[0]) === k} onClick={() => props.onPick(k)}>
              <img src={fileUrl(props.asset, v.version, v.outputs[k])} alt={`picture ${i + 1}`} />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function Stats(props: { asset: string; version: Meta; file?: string; sheet: SheetData | null }) {
  const [size, setSize] = useState<[number, number] | null>(null);
  const url = props.file ? fileUrl(props.asset, props.version.version, props.file) : "";
  useEffect(() => {
    if (props.sheet || !url) return;
    const im = new Image();
    im.onload = () => setSize([im.naturalWidth, im.naturalHeight]);
    im.src = url;
  }, [url, !!props.sheet]);
  const f = props.sheet?.frames[0]?.frame;
  const n = props.sheet?.frames.length ?? 0;
  const colors = props.version.metrics?.colors;
  const text = f ? `${n} frame${n === 1 ? "" : "s"} · ${f.w} × ${f.h} px` : size ? `${size[0]} × ${size[1]} px` : "";
  return text ? <span id="stats">{text}{colors ? ` · ${colors} colours` : ""}</span> : null;
}

function SheetBar(props: { clock: SheetClock }) {
  useTransportKeys(props.clock); // Space, ←/→, Home/End as in the 3D viewer
  return (
    <div className="timebar">
      <Transport viewer={props.clock} />
    </div>
  );
}

function Picture(props: { src: string; zoom: number; box: { w: number; h: number }; pixel: boolean }) {
  const [size, setSize] = useState<[number, number] | null>(null);
  const z = size ? zoomOf(props.zoom, size[0], size[1], props.box, props.pixel) : 1;
  return (
    <img
      className="pixel-picture"
      src={props.src}
      alt="the picture"
      onLoad={(e) => setSize([e.currentTarget.naturalWidth, e.currentTarget.naturalHeight])}
      style={size ? { width: size[0] * z, height: size[1] * z, imageRendering: z >= 1 && props.pixel ? "pixelated" : "auto" } : { maxWidth: "100%" }}
    />
  );
}

/** Parallax layers (M55) stacked far to near and scrolled back and forth by a pretend camera: layer k moves by the
 * camera's move times its scroll_scale. The camera range slider takes over when touched; Play resumes. */
function Parallax(props: { asset: string; version: Meta; zoom: number; box: { w: number; h: number } }) {
  const v = props.version;
  const [layers, setLayers] = useState<{ file: string; scroll_scale: number }[] | null>(null);
  const [size, setSize] = useState<[number, number] | null>(null);
  const [x, setX] = useState(0); // the camera's move, as a share of the picture's width
  const [playing, setPlaying] = useState(!still());
  useEffect(() => {
    fetch(fileUrl(props.asset, v.version, v.outputs.layers))
      .then((r) => r.json())
      .then(setLayers, () => setLayers([]));
  }, [props.asset, v.version]);
  useEffect(() => {
    if (!playing) return;
    const t0 = performance.now() - x * 8000;
    let id = 0;
    const tick = (now: number) => {
      const p = ((now - t0) / 8000) % 2; // 8 s across, 8 s back
      setX(p < 1 ? p : 2 - p);
      id = requestAnimationFrame(tick);
    };
    id = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(id);
  }, [playing]);
  if (!layers) return <p className="muted">Loading…</p>;
  // the view shows the picture's middle 70 %: the camera moves 30 % of its width, the edges never show
  const z = size ? zoomOf(props.zoom, size[0] * 0.7, size[1], props.box, false) : 1;
  const [w, h] = size ? [size[0] * z, size[1] * z] : [0, 0];
  return (
    <div className="stack" style={{ alignItems: "center" }}>
      <div className="parallax" role="img" aria-label={`${layers.length} parallax layers, scrolling`} style={{ width: w * 0.7, height: h }}>
        {layers.map((d, k) => (
          <img
            key={d.file}
            src={fileUrl(props.asset, v.version, d.file)}
            alt=""
            onLoad={k === 0 ? (e) => setSize([e.currentTarget.naturalWidth, e.currentTarget.naturalHeight]) : undefined}
            style={{ width: w || undefined, height: h || undefined, transform: `translateX(${-(0.15 + (x - 0.5) * 0.3 * d.scroll_scale) * w}px)` }}
          />
        ))}
      </div>
      <div className="row">
        <button onClick={() => setPlaying((p) => !p)}>{playing ? "Pause" : "Play"}</button>
        <input type="range" aria-label="Camera" min={0} max={1} step={0.001} value={x} onChange={(e) => (setPlaying(false), setX(Number(e.target.value)))} />
      </div>
    </div>
  );
}

/** A seamless tile laid `repeat` × `repeat` times (a CSS background, so the browser does the repeating): an edge that
 * does not meet shows as a line through the middle. */
function Tiled(props: { src: string; zoom: number; box: { w: number; h: number }; pixel: boolean; repeat: number }) {
  const [size, setSize] = useState<[number, number] | null>(null);
  useEffect(() => {
    const im = new Image();
    im.onload = () => setSize([im.naturalWidth, im.naturalHeight]);
    im.src = props.src;
  }, [props.src]);
  if (!size) return <p className="muted">Loading…</p>;
  const n = props.repeat;
  const z = zoomOf(props.zoom, size[0] * n, size[1] * n, props.box, props.pixel);
  const [w, h] = [size[0] * z, size[1] * z];
  return (
    <div
      className="pixel-picture tiled"
      role="img"
      aria-label={n > 1 ? `the tile, repeated ${n} × ${n}` : "the tile"}
      style={{
        width: w * n,
        height: h * n,
        backgroundImage: `url("${props.src}")`,
        backgroundSize: `${w}px ${h}px`,
        imageRendering: z >= 1 && props.pixel ? "pixelated" : "auto",
      }}
    />
  );
}

/** The sheet's frame at the clock's time, redrawn every animation frame, in whole pixels. */
function Sheet(props: { data: SheetData; img: HTMLImageElement; from: number; clock: SheetClock; zoom: number; box: { w: number; h: number } }) {
  useFrame();
  const k = props.from + props.clock.frame();
  const f = props.data.frames[k];
  const z = zoomOf(props.zoom, f.frame.w, f.frame.h, props.box, true);
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const c = canvas.current;
    if (!c) return;
    c.width = Math.max(1, Math.round(f.frame.w * z));
    c.height = Math.max(1, Math.round(f.frame.h * z));
    const ctx = c.getContext("2d")!;
    ctx.imageSmoothingEnabled = z < 1;
    ctx.clearRect(0, 0, c.width, c.height);
    ctx.drawImage(props.img, f.frame.x, f.frame.y, f.frame.w, f.frame.h, 0, 0, c.width, c.height);
  });
  // its own size in CSS too: the app's canvas rule stretches a canvas to its box (the 3D view's)
  const w = Math.max(1, Math.round(f.frame.w * z));
  const h = Math.max(1, Math.round(f.frame.h * z));
  return <canvas ref={canvas} className="sheet-canvas" style={{ width: w, height: h }} aria-label={`frame ${k + 1}`} data-frame={k} />;
}
