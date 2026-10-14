// The pixel editor's animation side (M57, research 15 §5.6): the frames strip under the canvas, and the frames and
// animations (Aseprite's tags) in the panel. Every change here is one undo step of the editor's Doc.
import { useEffect, useRef, useState } from "react";
import type { Doc, PixelEd, Tag } from "./Editor";

/** Does the animation loop (Aseprite's `repeat` "1": it plays once, as an attack or a hit). */
export const loops = (t: Tag) => String(t.repeat ?? "0") !== "1";

/** The animation frame i plays in: its tag's [from, to, loops], or every frame, looping. */
export function span(d: Doc, i: number): [number, number, boolean] {
  const t = d.tags.find((t) => t.from <= i && i <= t.to);
  return t ? [t.from, t.to, loops(t)] : [0, d.names.length - 1, true];
}

/** A name unlike the others, `base_1`, `base_2`, …: a frame's name is its file's, and an animation's must be unique. */
export function fresh(names: string[], base: string) {
  const b = base.slice(0, 56);
  for (let k = 1; ; k++) if (!names.includes(`${b}_${k}`)) return `${b}_${k}`;
}

/** A frame put after frame c: a tag holding c grows by it, the later ones move on. */
export function insert(d: Doc, c: number, name: string, frame: Uint8ClampedArray, ms: number): Doc {
  const put = <X,>(a: X[], x: X) => [...a.slice(0, c + 1), x, ...a.slice(c + 1)];
  return {
    names: put(d.names, name),
    frames: put(d.frames, frame),
    ms: put(d.ms, ms),
    tags: d.tags.map((t) => ({ ...t, from: t.from > c ? t.from + 1 : t.from, to: t.to >= c ? t.to + 1 : t.to })),
  };
}

/** Frame i gone: the tags close up, and a tag that held only it goes with it. */
export function remove(d: Doc, i: number): Doc {
  const cut = <X,>(a: X[]) => a.filter((_, k) => k !== i);
  return {
    names: cut(d.names),
    frames: cut(d.frames),
    ms: cut(d.ms),
    tags: d.tags.map((t) => ({ ...t, from: t.from > i ? t.from - 1 : t.from, to: t.to >= i ? t.to - 1 : t.to })).filter((t) => t.from <= t.to),
  };
}

/** Frames i and j change places; the tags stay on their positions (Aseprite's way). */
export function swap(d: Doc, i: number, j: number): Doc {
  const sw = <X,>(a: X[]) => a.map((x, k) => (k === i ? a[j] : k === j ? a[i] : x));
  return { names: sw(d.names), frames: sw(d.frames), ms: sw(d.ms), tags: d.tags };
}

function Thumb({ data, w, h }: { data: Uint8ClampedArray; w: number; h: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => ref.current!.getContext("2d")!.putImageData(new ImageData(new Uint8ClampedArray(data), w, h), 0, 0), [data, w, h]);
  return <canvas ref={ref} width={w} height={h} className="frame-thumb" aria-hidden />;
}

/** The frames under the canvas: a thumbnail each, its duration; a bar over the frames of an animation, its name on
 * the first, and on the last where it goes next (↻ back to its first frame, ⇥ it stops there). */
export function FramesStrip({ ed }: { ed: PixelEd }) {
  const d = ed.doc!;
  const s = ed.sheet!;
  return (
    <div className="picture-strip frames-strip" role="group" aria-label="Frames">
      {d.names.map((name, i) => {
        const first = d.tags.find((t) => t.from === i);
        const last = d.tags.find((t) => t.to === i);
        return (
          <button
            key={name}
            className={d.tags.some((t) => t.from <= i && i <= t.to) ? "tagged" : undefined}
            aria-pressed={ed.frame === i}
            aria-label={`Frame ${i + 1}: ${name}, ${d.ms[i]} ms`}
            title={name}
            onClick={() => (ed.setPlaying(false), ed.setFrame(i))}
          >
            <span className="frame-note">{first?.name ?? " "}</span>
            <Thumb data={d.frames[i]} w={s.w} h={s.h} />
            <span className="frame-note">
              {i + 1} · {d.ms[i]} ms{last ? (loops(last) ? " ↻" : " ⇥") : ""}
            </span>
          </button>
        );
      })}
    </div>
  );
}

/** A field that is one undo step when left (Enter or a click elsewhere), not one per key; Escape, or a value `commit`
 * refuses (false), puts the old one back. */
function Field({ commit, value, ...rest }: { commit: (v: string) => boolean; value: string | number } & Omit<React.InputHTMLAttributes<HTMLInputElement>, "value">) {
  const [v, setV] = useState(String(value));
  useEffect(() => setV(String(value)), [value]);
  return (
    <input
      {...rest}
      value={v}
      onChange={(e) => setV(e.target.value)}
      onBlur={() => v !== String(value) && !commit(v) && setV(String(value))}
      onKeyDown={(e) => (e.key === "Enter" ? e.currentTarget.blur() : e.key === "Escape" ? setV(String(value)) : null)}
    />
  );
}

/** The panel's frames and animations: add, duplicate, delete and move the shown frame, its duration; the tags. */
export function FramesPanel({ ed }: { ed: PixelEd }) {
  const d = ed.doc!;
  const s = ed.sheet!;
  const i = ed.frame;
  const n = d.names.length;
  const edit = (next: Doc, frame = i) => (ed.edit(() => next), ed.setFrame(frame), true);
  const setTag = (k: number, t: Partial<Tag>) => edit({ ...d, tags: d.tags.map((x, j) => (j === k ? { ...x, ...t } : x)) });
  const frameOptions = d.names.map((name, j) => (
    <option key={name} value={j}>
      {j + 1}
    </option>
  ));
  return (
    <details open>
      <summary>Frames and animations</summary>
      <div>
        <div className="row">
          <button className="small" onClick={() => edit(insert(d, i, fresh(d.names, "frame"), new Uint8ClampedArray(s.w * s.h * 4), d.ms[i]), i + 1)}>
            Add a frame
          </button>
          <button className="small" onClick={() => edit(insert(d, i, fresh(d.names, `${d.names[i]}_copy`), d.frames[i], d.ms[i]), i + 1)}>
            Duplicate
          </button>
          <button className="small" disabled={n < 2} onClick={() => edit(remove(d, i), Math.min(i, n - 2))}>
            Delete
          </button>
          <button className="small" disabled={i === 0} onClick={() => edit(swap(d, i, i - 1), i - 1)} title="Move this frame one to the left">
            ◀ Move
          </button>
          <button className="small" disabled={i === n - 1} onClick={() => edit(swap(d, i, i + 1), i + 1)} title="Move this frame one to the right">
            Move ▶
          </button>
        </div>
        <label>
          Frame {i + 1}'s duration (ms)
          <Field
            type="number"
            min={1}
            max={60000}
            value={d.ms[i]}
            commit={(v) => {
              const ms = Math.round(Number(v));
              return ms >= 1 && ms <= 60000 && edit({ ...d, ms: d.ms.map((x, j) => (j === i ? ms : x)) });
            }}
          />
        </label>
        <fieldset>
          <legend>Animations</legend>
          {d.tags.length === 0 && <p className="muted">None yet: the frames play as one loop. Give each move its own (Godot plays them by name).</p>}
          {d.tags.map((t, k) => (
            <div className="row" key={k}>
              <Field
                aria-label={`Animation ${k + 1}'s name`}
                value={t.name}
                commit={(v) => !!v.trim() && v.trim() !== t.name && !d.tags.some((x) => x.name === v.trim()) && setTag(k, { name: v.trim() })}
                style={{ width: "9em" }}
              />
              <select aria-label={`Animation ${k + 1}'s first frame`} value={t.from} onChange={(e) => setTag(k, { from: Number(e.target.value), to: Math.max(t.to, Number(e.target.value)) })}>
                {frameOptions}
              </select>
              to
              <select aria-label={`Animation ${k + 1}'s last frame`} value={t.to} onChange={(e) => setTag(k, { to: Number(e.target.value), from: Math.min(t.from, Number(e.target.value)) })}>
                {frameOptions}
              </select>
              <label className="check">
                <input type="checkbox" checked={loops(t)} onChange={(e) => setTag(k, { repeat: e.target.checked ? "0" : "1" })} /> Loop
              </label>
              <button className="small" onClick={() => edit({ ...d, tags: d.tags.filter((_, j) => j !== k) })}>
                Remove
              </button>
            </div>
          ))}
          <button
            className="small"
            onClick={() => {
              const [from, to] = d.tags.length ? [i, i] : [0, n - 1]; // the first one: every frame
              edit({ ...d, tags: [...d.tags, { name: fresh(d.tags.map((t) => t.name), "animation"), from, to, direction: "forward", repeat: "0" }] });
            }}
          >
            Add an animation
          </button>
        </fieldset>
      </div>
    </details>
  );
}
