// M37b/M38: the animation editor's timeline: a frame ruler (scrub, trim handles), a row per bone group opening to its
// bones, a strip where the base clip moves, diamonds for the correction keys (click, shift-click, box select, drag in
// time), foot locks as bars; or (Curves) the selected bone's correction over the frames, its keys as points dragged up
// and down. Ctrl+wheel or the slider zooms; it scrolls both ways, the names and the ruler staying. The canvases are as
// big as the view and draw what is in it.
import { useEffect, useRef, useState } from "react";

export type Row = { id: string; label: string; group: boolean; open?: boolean; keys: number[]; moving: boolean; active?: boolean };
export type Curves = {
  unit: string; // "°" or "cm"
  lines: { label: string; color: string; values: number[] }[]; // a value per base frame
  points: { id: string; f: number; values: number[] }[]; // the keys: a value per line
};
type Props = {
  frames: number; // the base clip's frames, 0 … frames-1
  frame: number; // the playhead (a base frame)
  trim: [number, number];
  rows: Row[];
  selected: string[]; // keys as "row@frame"
  spans?: Record<string, [number, number][]>; // row id → foot locks over base frames
  curves?: Curves | null; // the Curves view instead of the rows
  onFrame: (f: number) => void;
  onSelect: (keys: string[], add: boolean) => void;
  onMove: (df: number) => void; // the selected keys dragged by df frames
  onTrim: (t: [number, number]) => void;
  onRow: (id: string) => void; // a label clicked: open a group, select a bone
  onCurve?: (id: string, line: number, value: number) => void; // a key point dragged to a value (on release)
};
const ROW = 20;
const RULER = 24;
const PAD = 8;
const LABELS = 160;
const css = (v: string) => getComputedStyle(document.documentElement).getPropertyValue(v).trim() || "#888";
const nice = (span: number) => [1, 2, 5, 10, 20, 50, 100, 200].find((s) => span / s <= 8) ?? 500;

export function DopeSheet(p: Props) {
  const scroller = useRef<HTMLDivElement>(null);
  const ruler = useRef<HTMLCanvasElement>(null);
  const body = useRef<HTMLCanvasElement>(null);
  const [view, setView] = useState({ w: 600, h: 240 }); // the visible area right of the names, below the ruler
  const [scroll, setScroll] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const zoomNow = useRef(1);
  zoomNow.current = zoom;
  const [box, setBox] = useState<[number, number, number, number] | null>(null);
  const [drag, setDrag] = useState<{ df: number } | null>(null); // selected keys being dragged
  const [trimming, setTrimming] = useState<[number, number] | null>(null); // a trim handle being dragged: committed on release
  const [lifting, setLifting] = useState<{ id: string; line: number; value: number } | null>(null); // a curve point being dragged
  const trim = trimming ?? p.trim;
  const last = Math.max(p.frames - 1, 1);
  const px = ((view.w - 2 * PAD) / last) * zoom;
  const contentW = last * px + 2 * PAD;
  const curves = p.curves ?? null;
  const contentH = curves ? view.h : p.rows.length * ROW;
  const x = (f: number) => PAD + f * px - scroll.x; // canvas x of a frame
  const frameAt = (cx: number) => Math.min(last, Math.max(0, Math.round((cx + scroll.x - PAD) / px)));
  // the curves' value range: the data's, at least ±10 (° or cm), with some room
  const all = curves ? [...curves.lines.flatMap((l) => l.values), ...curves.points.flatMap((q) => q.values)] : [0];
  const lim = Math.max(10, ...all.map(Math.abs)) * 1.15; // not the dragged point's: a drag would chase its own range
  const yOf = (v: number) => view.h / 2 - (v / lim) * (view.h / 2 - 8);
  const valueAt = (cy: number) => ((view.h / 2 - cy) / (view.h / 2 - 8)) * lim;

  useEffect(() => {
    const el = scroller.current!;
    const ro = new ResizeObserver(() => setView({ w: Math.max(200, el.clientWidth - LABELS), h: Math.max(60, el.clientHeight - RULER) }));
    ro.observe(el);
    // Ctrl+wheel zooms around the frame under the cursor
    const wheel = (e: WheelEvent) => {
      if (!e.ctrlKey) return;
      e.preventDefault();
      const z = zoomNow.current;
      const nz = Math.min(Math.max(z * (e.deltaY < 0 ? 1.25 : 0.8), 1), 24);
      const w = (Math.max(200, el.clientWidth - LABELS) - 2 * PAD) / last; // a frame's width at zoom 1 (as px)
      const cx = e.clientX - el.getBoundingClientRect().left - LABELS;
      const f = (cx + el.scrollLeft - PAD) / (z * w);
      setZoom(nz);
      requestAnimationFrame(() => (el.scrollLeft = Math.max(0, f * nz * w + PAD - cx)));
    };
    el.addEventListener("wheel", wheel, { passive: false });
    return () => (ro.disconnect(), el.removeEventListener("wheel", wheel));
  }, [last]);

  // draw what is in view
  useEffect(() => {
    const dpr = window.devicePixelRatio || 1;
    const setup = (c: HTMLCanvasElement, w: number, h: number) => {
      c.width = w * dpr;
      c.height = h * dpr;
      c.style.width = `${w}px`;
      c.style.height = `${h}px`;
      const g = c.getContext("2d")!;
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
      g.clearRect(0, 0, w, h);
      return g;
    };
    const text = css("--text-2"),
      accent = css("--accent"),
      border = css("--border");
    const r = setup(ruler.current!, view.w, RULER);
    r.strokeStyle = border;
    r.beginPath();
    r.moveTo(0, RULER - 0.5);
    r.lineTo(view.w, RULER - 0.5);
    r.stroke();
    const step = [1, 2, 5, 10, 20, 50, 100].find((s) => s * px >= 50) ?? 200;
    r.fillStyle = "#00000055";
    r.fillRect(0, 0, x(trim[0]), RULER);
    r.fillRect(x(trim[1]), 0, view.w - x(trim[1]), RULER);
    r.strokeStyle = border;
    r.fillStyle = text;
    r.font = "11px system-ui";
    for (let f = Math.max(0, Math.floor(frameAt(0) / step) * step); f <= last && x(f) < view.w; f += step) {
      r.beginPath();
      r.moveTo(x(f) + 0.5, RULER - 6);
      r.lineTo(x(f) + 0.5, RULER);
      r.stroke();
      r.fillText(String(f), x(f) + 2, 11);
    }
    r.fillStyle = "#e0b040";
    for (const f of trim) {
      r.beginPath();
      r.moveTo(x(f) - 5, RULER);
      r.lineTo(x(f) + 5, RULER);
      r.lineTo(x(f), RULER - 8);
      r.fill();
    }
    const g = setup(body.current!, view.w, view.h);
    const sel = new Set(p.selected);
    if (curves) {
      // the zero line and a grid, the lines, the keys
      const st = nice(lim);
      g.font = "10px system-ui";
      for (let v = -Math.floor(lim / st) * st; v <= lim; v += st) {
        g.strokeStyle = v === 0 ? "#ffffff40" : "#ffffff12";
        g.beginPath();
        g.moveTo(0, yOf(v) + 0.5);
        g.lineTo(view.w, yOf(v) + 0.5);
        g.stroke();
        g.fillStyle = text;
        g.fillText(`${v}${curves.unit}`, 4, yOf(v) - 2);
      }
      curves.lines.forEach((l, i) => {
        g.strokeStyle = l.color;
        g.lineWidth = 1.5;
        g.beginPath();
        l.values.forEach((v, f) => (f ? g.lineTo(x(f), yOf(v)) : g.moveTo(x(f), yOf(v))));
        g.stroke();
        for (const q of curves.points) {
          const v = lifting && lifting.id === q.id && lifting.line === i ? lifting.value : q.values[i];
          g.fillStyle = sel.has(q.id) ? "#ffd84a" : l.color;
          g.beginPath();
          g.arc(x(q.f), yOf(v), 4.5, 0, 2 * Math.PI);
          g.fill();
        }
      });
    } else
      p.rows.forEach((row, i) => {
        const y = i * ROW - scroll.y;
        if (y < -ROW || y > view.h) return;
        g.fillStyle = row.active ? "#ffffff14" : i % 2 ? "#ffffff06" : "#00000000";
        g.fillRect(0, y, view.w, ROW);
        if (row.moving) {
          g.fillStyle = row.group ? "#7aa2c855" : "#7aa2c833";
          g.fillRect(x(trim[0]), y + ROW / 2 - 2, x(trim[1]) - x(trim[0]), 4);
        }
        for (const [a, b] of p.spans?.[row.id] ?? []) {
          g.fillStyle = "#5adc7a55";
          g.fillRect(x(a), y + 3, Math.max(x(b) - x(a), 2), ROW - 6);
        }
        for (const f of row.keys) {
          const cx = x(f) + (drag && sel.has(`${row.id}@${f}`) ? drag.df * px : 0);
          if (cx < -8 || cx > view.w + 8) continue;
          const cy = y + ROW / 2,
            s = row.group ? 4 : 5;
          g.fillStyle = sel.has(`${row.id}@${f}`) ? "#ffd84a" : row.group ? "#b9b9b9" : row.id.endsWith(":move") ? "#5fb8f0" : "#f0a030";
          g.beginPath();
          g.moveTo(cx, cy - s);
          g.lineTo(cx + s, cy);
          g.lineTo(cx, cy + s);
          g.lineTo(cx - s, cy);
          g.fill();
        }
      });
    g.fillStyle = "#00000055";
    g.fillRect(0, 0, x(trim[0]), view.h);
    g.fillRect(x(trim[1]), 0, view.w - x(trim[1]), view.h);
    for (const [c, h] of [
      [r, RULER],
      [g, view.h],
    ] as const) {
      c.strokeStyle = accent;
      c.lineWidth = 1.5;
      c.beginPath();
      c.moveTo(x(p.frame) + 0.5, 0);
      c.lineTo(x(p.frame) + 0.5, h);
      c.stroke();
    }
    if (box) {
      g.strokeStyle = "#ffffffaa";
      g.setLineDash([4, 3]);
      g.strokeRect(Math.min(box[0], box[2]), Math.min(box[1], box[3]), Math.abs(box[2] - box[0]), Math.abs(box[3] - box[1]));
      g.setLineDash([]);
    }
  });

  const follow = (c: HTMLCanvasElement, move: (e: PointerEvent) => void, up: () => void) => {
    const end = () => (c.removeEventListener("pointermove", move), c.removeEventListener("pointerup", end), up());
    c.addEventListener("pointermove", move);
    c.addEventListener("pointerup", end);
  };
  // the ruler: a trim handle dragged (committed on release), else scrubbing
  const onRuler = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const c = e.currentTarget;
    c.setPointerCapture(e.pointerId);
    const handle = p.trim.findIndex((f) => Math.abs(x(f) - e.nativeEvent.offsetX) < 7);
    let t: [number, number] = p.trim;
    const move = (ev: PointerEvent) => {
      const f = frameAt(ev.offsetX);
      if (handle < 0) return p.onFrame(f);
      t = handle === 0 ? [Math.min(f, p.trim[1] - 1), p.trim[1]] : [p.trim[0], Math.max(f, p.trim[0] + 1)];
      setTrimming(t);
    };
    move(e.nativeEvent);
    follow(c, move, () => {
      setTrimming(null);
      if (handle >= 0 && (t[0] !== p.trim[0] || t[1] !== p.trim[1])) p.onTrim(t);
    });
  };
  const keyAt = (cx: number, cy: number) => {
    const row = p.rows[Math.floor((cy + scroll.y) / ROW)];
    const f = row?.keys.find((k) => Math.abs(x(k) - cx) <= 6);
    return row && f !== undefined ? `${row.id}@${f}` : null;
  };
  const expand = (k: string) => {
    // a group's diamond stands for its open bones' keys at that frame
    const [id, f] = [k.slice(0, k.lastIndexOf("@")), +k.slice(k.lastIndexOf("@") + 1)];
    const i = p.rows.findIndex((r) => r.id === id);
    if (!p.rows[i]?.group) return [k];
    const kids: string[] = [];
    for (let j = i + 1; j < p.rows.length && !p.rows[j].group; j++) if (p.rows[j].keys.includes(f)) kids.push(`${p.rows[j].id}@${f}`);
    return kids.length ? kids : [k];
  };
  const onBody = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const c = e.currentTarget;
    c.setPointerCapture(e.pointerId);
    const [x0, y0] = [e.nativeEvent.offsetX, e.nativeEvent.offsetY];
    if (curves) {
      // a key point grabbed: up and down; else scrub
      for (const q of curves.points)
        for (let i = 0; i < curves.lines.length; i++)
          if (Math.hypot(x(q.f) - x0, yOf(q.values[i]) - y0) <= 7) {
            p.onSelect([q.id], false);
            let value = q.values[i];
            follow(
              c,
              (ev) => setLifting({ id: q.id, line: i, value: (value = Math.round(Math.min(Math.max(valueAt(ev.offsetY), -lim), lim) * 10) / 10) }),
              () => (setLifting(null), value !== q.values[i] && p.onCurve?.(q.id, i, value)),
            );
            return;
          }
      p.onFrame(frameAt(x0));
      follow(c, (ev) => p.onFrame(frameAt(ev.offsetX)), () => {});
      return;
    }
    const hit = keyAt(x0, y0);
    if (hit) {
      const keys = expand(hit);
      if (!keys.every((k) => p.selected.includes(k)) || e.shiftKey) p.onSelect(keys, e.shiftKey);
      let df = 0;
      follow(
        c,
        (ev) => setDrag({ df: (df = Math.round((ev.offsetX - x0) / px)) }),
        () => (setDrag(null), df && p.onMove(df)),
      );
      return;
    }
    let b: [number, number, number, number] = [x0, y0, x0, y0];
    follow(
      c,
      (ev) => setBox((b = [x0, y0, ev.offsetX, ev.offsetY])),
      () => {
        setBox(null);
        if (Math.hypot(b[2] - b[0], b[3] - b[1]) < 4) {
          if (!e.shiftKey) p.onSelect([], false);
          return p.onFrame(frameAt(x0));
        }
        const [xa, xb] = [Math.min(b[0], b[2]), Math.max(b[0], b[2])];
        const [ya, yb] = [Math.min(b[1], b[3]) + scroll.y, Math.max(b[1], b[3]) + scroll.y];
        const inside: string[] = [];
        p.rows.forEach((row, i) => {
          if (row.group || (i + 1) * ROW < ya || i * ROW > yb) return;
          for (const f of row.keys) if (x(f) >= xa && x(f) <= xb) inside.push(`${row.id}@${f}`);
        });
        p.onSelect(inside, e.shiftKey);
      },
    );
  };

  return (
    <div className="dopesheet" ref={scroller} onScroll={(e) => setScroll({ x: e.currentTarget.scrollLeft, y: e.currentTarget.scrollTop })}>
      <div className="ds-inner" style={{ width: LABELS + contentW, height: RULER + contentH }}>
        <div className="ds-view" style={{ width: LABELS + view.w, height: RULER + view.h }}>
          <div className="ds-head">
            <label className="ds-corner" title="Zoom (Ctrl+wheel over the timeline)">
              <input type="range" min={1} max={24} step={0.25} aria-label="Zoom" value={zoom} onChange={(e) => setZoom(+e.target.value)} />
            </label>
            <canvas ref={ruler} className="ds-ruler" aria-label="Frames: drag to scrub, the yellow handles trim" onPointerDown={onRuler} />
          </div>
          <div className="ds-body">
            <div className="ds-labels" style={{ transform: `translateY(${-scroll.y}px)` }}>
              {curves
                ? curves.lines.map((l) => (
                    <span key={l.label} className="ds-label" style={{ color: l.color }}>
                      {l.label} ({curves.unit})
                    </span>
                  ))
                : p.rows.map((r) => (
                    <button key={r.id} className={`ds-label${r.group ? " group" : ""}`} aria-pressed={r.active} onClick={() => p.onRow(r.id)}>
                      {r.group ? (r.open ? "▾ " : "▸ ") : ""}
                      {r.label}
                    </button>
                  ))}
            </div>
            <canvas
              ref={body}
              className="ds-rows"
              aria-label={curves ? "Curves: drag a key point up or down" : "Keys: click or drag to select, drag a key to move it"}
              onPointerDown={onBody}
            />
          </div>
        </div>
      </div>
    </div>
  );
}


/** The timeline's keys as a list the keyboard reaches (UX review 2026-10-12, UX-13: keys were pointer-only): the keyed
 * bones with a button per key frame (select it and go there; Shift adds), the selected keys a frame earlier or later,
 * X deletes them as on the timeline; in Curves, each key's values as number fields. */
export function KeyList(p: {
  rows: Row[];
  selected: string[];
  curves: Curves | null;
  onSelect: (keys: string[], add: boolean) => void;
  onSeek: (f: number) => void;
  onMove: (df: number) => void;
  onCurve: (id: string, line: number, value: number) => void;
}) {
  const keyed = p.rows.filter((r) => !r.group && r.keys.length);
  const sel = new Set(p.selected);
  const c = p.curves;
  return (
    <details className="key-list">
      <summary>Keys as a list</summary>
      {c ? (
        c.points.length ? (
          <table>
            <thead>
              <tr>
                <th>Frame</th>
                {c.lines.map((l) => (
                  <th key={l.label}>
                    {l.label} ({c.unit})
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {c.points.map((q) => (
                <tr key={q.id}>
                  <td>
                    <button className="small" onClick={() => p.onSeek(q.f)}>
                      {q.f}
                    </button>
                  </td>
                  {q.values.map((v, i) => (
                    <td key={`${q.id}:${i}:${v}`}>
                      <input
                        type="number"
                        step={0.5}
                        aria-label={`${c.lines[i].label} at frame ${q.f}`}
                        defaultValue={Math.round(v * 10) / 10}
                        onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
                        onBlur={(e) => {
                          const x = Number(e.currentTarget.value);
                          if (Number.isFinite(x) && Math.abs(x - v) > 1e-6) p.onCurve(q.id, i, x);
                        }}
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">No keys on this bone yet.</p>
        )
      ) : keyed.length ? (
        <ul>
          {keyed.map((r) => (
            <li key={r.id}>
              {r.label}:{" "}
              {r.keys.map((f) => {
                const k = `${r.id}@${f}`;
                return (
                  <button key={k} className="small" aria-pressed={sel.has(k)} aria-label={`${r.label}, frame ${f}`} onClick={(e) => (p.onSelect([k], e.shiftKey), p.onSeek(f))}>
                    {f}
                  </button>
                );
              })}
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">No correction keys yet: turn a bone, or press I, to key it at this frame.</p>
      )}
      {!c && p.selected.length > 0 && (
        <div className="row">
          <button className="small" onClick={() => p.onMove(-1)}>
            A frame earlier
          </button>
          <button className="small" onClick={() => p.onMove(1)}>
            A frame later
          </button>
          <span className="muted">{p.selected.length} selected · X deletes them</span>
        </div>
      )}
    </details>
  );
}
