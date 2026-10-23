import { useEffect, useRef, useState, type PointerEvent, type ReactElement } from "react";

export type Point = readonly [number, number];
export type Stroke = Readonly<{ tool: "paint" | "erase" | "lasso" | "erase-lasso"; radius: number; points: readonly Point[] }>;
export type Selection = Readonly<{
  mode: "all" | "brush" | "seams"; strokes: readonly Stroke[];
  faces?: Readonly<{ revision: string; ids: readonly number[] }>;
}>;
type Props = Readonly<{
  image: string; faceImage?: string; revision?: string; asset: string;
  seamMask?: string; onPresetReady?: (ready: boolean) => void;
  onMaskPresence?: (present: boolean) => void;
  selection: Selection; onChange: (value: Selection) => void; onClose?: () => void;
  history?: Readonly<{ change: (value: Selection) => void; undo: () => void; redo: () => void; canUndo: boolean; canRedo: boolean }>;
}>;

export function MaskEditor(props: Props): ReactElement {
  const canvas = useRef<HTMLCanvasElement>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const pixels = useRef<ImageData | null>(null);
  const maskHasPixels = useRef(false);
  const drag = useRef<Stroke | null>(null);
  const [pending, setPending] = useState<Stroke | null>(null);
  const [tool, setTool] = useState<Stroke["tool"] | "face-add" | "face-remove">("paint");
  const [radius, setRadius] = useState(0.02);
  const [zoom, setZoom] = useState(1);
  const [hover, setHover] = useState<number | null>(null);
  const [undo, setUndo] = useState<Selection[]>([]);
  const [redo, setRedo] = useState<Selection[]>([]);
  const [name, setName] = useState("");
  const [message, setMessage] = useState("");
  const [rasterReady, setRasterReady] = useState(false);
  const [seamCanvas, setSeamCanvas] = useState<HTMLCanvasElement | null>(null);
  const [triangle, setTriangle] = useState("");
  const [expanded, setExpanded] = useState(false);
  const [keyboardX, setKeyboardX] = useState(0.5);
  const [keyboardY, setKeyboardY] = useState(0.5);
  const [vertices, setVertices] = useState<Point[]>([]);
  const faceMode = tool === "face-add" || tool === "face-remove";
  useEffect(() => {
    let active = true;
    setSeamCanvas(null); props.onPresetReady?.(false);
    if (!props.seamMask) return;
    const image = new Image();
    image.onload = () => {
      if (!active) return;
      const guide = document.createElement("canvas"); guide.width = image.width; guide.height = image.height;
      const context = guide.getContext("2d");
      if (!context) { setMessage("Cannot display the seam mask. Use a manual selection."); return; }
      context.drawImage(image, 0, 0);
      const data = context.getImageData(0, 0, guide.width, guide.height);
      let count = 0;
      for (let i = 0; i < data.data.length; i += 4) {
        const alpha = data.data[i]; count += alpha > 0 ? 1 : 0;
        data.data[i] = 73; data.data[i + 1] = 222; data.data[i + 2] = 155; data.data[i + 3] = alpha;
      }
      context.putImageData(data, 0, 0); setSeamCanvas(guide); props.onPresetReady?.(count > 0);
      if (!count) setMessage("No visible seam was suggested. Add a brush, lasso or triangle selection.");
    };
    image.onerror = () => { if (active) setMessage("Could not load the suggested mask. Reload the capture or choose a manual selection."); };
    image.src = props.seamMask;
    return () => { active = false; };
  }, [props.seamMask, props.onPresetReady]);
  const change = (value: Selection): void => {
    if (props.history) { props.history.change(value); return; }
    setUndo((previous) => [...previous.slice(-99), props.selection]); setRedo([]); props.onChange(value);
  };
  const history = props.history ?? {
    change, canUndo: undo.length > 0, canRedo: redo.length > 0,
    undo: () => {
      const previous = undo.at(-1); if (!previous) return;
      setRedo((r) => [...r, props.selection]); props.onChange(previous); setUndo(undo.slice(0, -1));
    },
    redo: () => {
      const next = redo.at(-1); if (!next) return;
      setUndo((r) => [...r, props.selection]); props.onChange(next); setRedo(redo.slice(0, -1));
    },
  };
  const chooseFace = (id: number): void => {
    if (!props.revision || id < 0) return;
    const ids = new Set(props.selection.faces?.ids ?? []);
    if (tool === "face-remove") ids.delete(id); else ids.add(id);
    const emptyPixels = !maskHasPixels.current;
    const startFromFace = emptyPixels && tool === "face-add";
    change({ ...props.selection, mode: startFromFace ? "all" : props.selection.mode, strokes: startFromFace ? [] : props.selection.strokes,
      faces: { revision: props.revision, ids: [...ids].sort((a, b) => a - b) } });
  };
  useEffect(() => {
    pixels.current = null; setRasterReady(false);
    if (!props.faceImage) return;
    let active = true;
    const image = new Image();
    image.onload = () => {
      if (!active) return;
      const buffer = document.createElement("canvas");
      buffer.width = image.width; buffer.height = image.height;
      const context = buffer.getContext("2d");
      if (!context) return;
      context.drawImage(image, 0, 0);
      pixels.current = context.getImageData(0, 0, image.width, image.height); setRasterReady(true);
    };
    image.onerror = () => { if (active) setMessage("Face map unavailable. Capture this view again to select triangles."); };
    image.src = props.faceImage;
    return () => { active = false; };
  }, [props.faceImage]);
  useEffect(() => {
    const viewer = window.__viewer;
    if (!viewer || !faceMode || !props.revision || expanded) return;
    const problem = viewer.setPaintFaces(props.selection.faces?.ids ?? [], chooseFace);
    if (problem) setMessage(problem);
    return () => { viewer.setPaintFaces([], null); };
  }, [faceMode, tool, props.selection, props.revision, expanded]);
  useEffect(() => {
    const ctx = canvas.current?.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, 1024, 1024); ctx.globalCompositeOperation = "source-over"; ctx.fillStyle = "#49de9b";
    if (props.selection.mode === "all") ctx.fillRect(0, 0, 1024, 1024);
    if (props.selection.mode === "seams" && seamCanvas) { ctx.imageSmoothingEnabled = false; ctx.drawImage(seamCanvas, 0, 0, 1024, 1024); }
    for (const stroke of pending ? [...props.selection.strokes, pending] : props.selection.strokes) {
      ctx.globalCompositeOperation = stroke.tool === "erase" || stroke.tool === "erase-lasso" ? "destination-out" : "source-over";
      ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.lineWidth = stroke.radius * 2048; ctx.strokeStyle = "#49de9b";
      ctx.beginPath();
      stroke.points.forEach(([x, y], index) => { if (index === 0) ctx.moveTo(x * 1024, y * 1024); else ctx.lineTo(x * 1024, y * 1024); });
      if (stroke.tool === "lasso" || stroke.tool === "erase-lasso") { ctx.closePath(); ctx.fill(); }
      else {
        ctx.stroke();
        for (const [x, y] of stroke.points) { ctx.beginPath(); ctx.arc(x * 1024, y * 1024, stroke.radius * 1024, 0, Math.PI * 2); ctx.fill(); }
      }
    }
    const raster = pixels.current;
    if (props.selection.faces) {
      if (!raster || props.selection.faces.revision !== props.revision) ctx.clearRect(0, 0, 1024, 1024);
      else {
        const boundary = document.createElement("canvas"); boundary.width = raster.width; boundary.height = raster.height;
        const context = boundary.getContext("2d")!;
        const image = context.createImageData(raster.width, raster.height);
        const ids = new Set(props.selection.faces.ids);
        for (let i = 0; i < raster.data.length; i += 4) {
          const id = raster.data[i] + 256 * raster.data[i + 1] + 65536 * raster.data[i + 2] - 1;
          image.data[i + 3] = ids.has(id) ? 255 : 0;
        }
        context.putImageData(image, 0, 0); ctx.globalCompositeOperation = "destination-in";
        ctx.imageSmoothingEnabled = false; ctx.drawImage(boundary, 0, 0, 1024, 1024);
      }
    }
    ctx.globalCompositeOperation = "source-over";
    if (props.onMaskPresence || faceMode) {
      const maskPixels = ctx.getImageData(0, 0, 1024, 1024).data;
      let present = false;
      for (let i = 3; i < maskPixels.length; i += 4) { if (maskPixels[i] > 0) { present = true; break; } }
      maskHasPixels.current = present;
      props.onMaskPresence?.(present);
    }
    if (raster && hover !== null && faceMode) {
      const highlight = document.createElement("canvas"); highlight.width = raster.width; highlight.height = raster.height;
      const context = highlight.getContext("2d")!; const image = context.createImageData(raster.width, raster.height);
      for (let i = 0; i < raster.data.length; i += 4) {
        if (raster.data[i] + 256 * raster.data[i + 1] + 65536 * raster.data[i + 2] - 1 !== hover) continue;
        image.data[i] = 255; image.data[i + 1] = 190; image.data[i + 3] = 220;
      }
      context.putImageData(image, 0, 0); ctx.drawImage(highlight, 0, 0, 1024, 1024);
    }
  }, [props.selection, pending, rasterReady, hover, faceMode, props.revision, seamCanvas, props.onMaskPresence]);
  const point = (e: PointerEvent<HTMLCanvasElement>): Point => {
    const box = e.currentTarget.getBoundingClientRect();
    return [Math.max(0, Math.min(1, (e.clientX - box.left) / box.width)), Math.max(0, Math.min(1, (e.clientY - box.top) / box.height))];
  };
  const faceAt = ([x, y]: Point): number => {
    const raster = pixels.current;
    if (!raster) return -1;
    const offset = (Math.min(raster.height - 1, Math.floor(y * raster.height)) * raster.width + Math.min(raster.width - 1, Math.floor(x * raster.width))) * 4;
    return raster.data[offset] + 256 * raster.data[offset + 1] + 65536 * raster.data[offset + 2] - 1;
  };
  const commit = (): void => {
    const stroke = drag.current; drag.current = null; setPending(null);
    if (!stroke || (stroke.tool.includes("lasso") && stroke.points.length < 3)) return;
    change({ ...props.selection, strokes: [...props.selection.strokes, stroke] });
  };
  return <section className="paint-mask" aria-label="Texture write selection">
    <button type="button" onClick={props.onClose ?? (() => { setExpanded(true); dialog.current?.showModal(); })}>{props.onClose ? "Done selecting" : "Enlarge selection editor"}</button>
    <p><strong>Green = paint here. Clear = keep unchanged.</strong> Add marks where you want new paint. Erase removes areas from the paint mask.</p>
    <label>Paint region<select value={props.selection.mode} onChange={(e) => change({ ...props.selection, mode: e.target.value === "all" ? "all" : e.target.value === "seams" ? "seams" : "brush", strokes: [] })}>
      <option value="brush">Only the mask I paint</option><option value="all">Entire visible surface (inside any triangle boundary)</option>
      {props.seamMask && <option value="seams">Suggested seams, with my additions and erasures</option>}
    </select></label>
    {props.selection.mode === "all" && !props.selection.faces && <p role="status">The whole visible surface is selected. Use Clear paint mask to paint only specific spots.</p>}
    <label>Selection tool<select value={tool} onChange={(e) => setTool(e.target.value as typeof tool)}>
      <option value="paint">Paint mask: add</option><option value="erase">Paint mask: erase</option><option value="lasso">Lasso: add paint area</option><option value="erase-lasso">Lasso: remove paint area</option>
      <option value="face-add" disabled={!rasterReady}>Triangles: add paint area (image or 3D)</option><option value="face-remove" disabled={!rasterReady}>Triangles: remove paint area</option>
    </select></label>
    <div className="row">
      <label>Zoom<input type="range" min="1" max="8" step="0.5" value={zoom} onChange={(e) => setZoom(Number(e.target.value))} /></label>
      <label>Brush radius<input type="range" min="0.002" max="0.2" step="0.002" value={radius} onChange={(e) => setRadius(Number(e.target.value))} /></label>
      <button type="button" disabled={!history.canUndo} onClick={history.undo}>Undo selection</button>
      <button type="button" disabled={!history.canRedo} onClick={history.redo}>Redo selection</button>
    </div>
    <div className="paint-pan" tabIndex={0} aria-label="Scrollable zoomed capture">
      <div className="paint-canvas" style={{ width: `${zoom * 100}%`, maxWidth: "none" }}>
        <img src={props.image} alt="Fixed captured surface" />
        <canvas ref={canvas} width={1024} height={1024} aria-label="Draw texture selection" tabIndex={0}
          onPointerDown={(e) => {
            if (faceMode) { chooseFace(faceAt(point(e))); return; }
            if (props.selection.strokes.length >= 256) return;
            e.currentTarget.setPointerCapture(e.pointerId);
            drag.current = { tool, radius, points: [point(e)] }; setPending(drag.current);
          }}
          onPointerMove={(e) => {
            if (faceMode) { const id = faceAt(point(e)); setHover(id >= 0 ? id : null); return; }
            if (!drag.current || drag.current.points.length >= 4096) return;
            drag.current = { ...drag.current, points: [...drag.current.points, point(e)] }; setPending(drag.current);
          }}
          onPointerLeave={() => setHover(null)} onPointerUp={commit} onPointerCancel={commit} onLostPointerCapture={commit} />
      </div>
    </div>
    <p className="muted">Scroll to pan while zoomed. Green marks writable areas, inside the optional triangle boundary. Blue triangle hover is only a preview. Only front-visible surface pixels can be painted.</p>
    <div className="row">
      <button type="button" onClick={() => change({ mode: "brush", strokes: [] })}>Clear paint mask</button>
      <button type="button" onClick={() => change({ mode: props.selection.mode === "seams" ? "seams" : props.selection.strokes.length ? props.selection.mode : "brush", strokes: props.selection.strokes })}>Remove triangle boundary</button>
    </div>
    <details><summary>Keyboard brush and lasso positions</summary>
      <label>Horizontal position<input type="number" min="0" max="1" step="0.001" value={keyboardX} onChange={(e) => setKeyboardX(Number(e.target.value))} /></label>
      <label>Vertical position<input type="number" min="0" max="1" step="0.001" value={keyboardY} onChange={(e) => setKeyboardY(Number(e.target.value))} /></label>
      <button type="button" disabled={faceMode || !Number.isFinite(keyboardX) || !Number.isFinite(keyboardY) || keyboardX < 0 || keyboardX > 1 || keyboardY < 0 || keyboardY > 1 || props.selection.strokes.length >= 256}
        onClick={() => {
          if (faceMode) return;
          if (tool === "lasso" || tool === "erase-lasso") { setVertices([...vertices.slice(-4095), [keyboardX, keyboardY]]); return; }
          change({ ...props.selection, strokes: [...props.selection.strokes, { tool, radius, points: [[keyboardX, keyboardY]] }] });
        }}>{tool.includes("lasso") ? `Add lasso vertex (${vertices.length})` : "Add brush mark"}</button>
      <button type="button" disabled={vertices.length < 3 || (tool !== "lasso" && tool !== "erase-lasso")} onClick={() => {
        if (tool !== "lasso" && tool !== "erase-lasso") return;
        change({ ...props.selection, strokes: [...props.selection.strokes, { tool, radius, points: vertices }] }); setVertices([]);
      }}>Close lasso</button>
    </details>
    {props.revision && <details><summary>Named triangle selection ({props.selection.faces?.ids.length ?? 0} selected)</summary>
      <label>Triangle ID<input value={triangle} onChange={(e) => setTriangle(e.target.value)} /></label>
      <button type="button" disabled={!faceMode || !/^\d+$/.test(triangle)} onClick={() => chooseFace(Number(triangle))}>Apply triangle tool</button>
      <label>Selection name<input value={name} maxLength={80} onChange={(e) => setName(e.target.value)} /></label>
      <button type="button" disabled={!name.trim() || !props.selection.faces?.ids.length} onClick={() => {
        try { localStorage.setItem(`effigy:faces:${props.asset}:${name.trim()}`, JSON.stringify(props.selection.faces)); setMessage("Triangle selection saved. Pixel strokes stay with this view."); }
        catch (error) { setMessage(String(error)); }
      }}>Save named selection</button>
      <button type="button" disabled={!name.trim()} onClick={() => {
        try {
          const value = JSON.parse(localStorage.getItem(`effigy:faces:${props.asset}:${name.trim()}`) ?? "null");
          if (value?.revision !== props.revision || !Array.isArray(value?.ids) || !value.ids.every((id: unknown) => Number.isInteger(id) && Number(id) >= 0)) throw new Error("Selection unavailable or geometry/UV revision changed. Select triangles again.");
          change({ ...props.selection, mode: !maskHasPixels.current ? "all" : props.selection.mode,
            strokes: !maskHasPixels.current ? [] : props.selection.strokes, faces: value }); setMessage("Triangle boundary loaded for this geometry.");
        } catch (error) { setMessage(String(error)); }
      }}>Load named selection</button>
    </details>}
    {message && <p role="status">{message}</p>}
    {!props.onClose && <dialog className="paint-dialog" ref={dialog} aria-label="Enlarged texture selection" onClose={() => setExpanded(false)}>
      {expanded && <MaskEditor {...props} history={history} onClose={() => dialog.current?.close()} />}
    </dialog>}
  </section>;
}
