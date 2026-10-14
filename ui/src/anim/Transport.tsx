// M37a: Blender's transport over the viewer's playing clip: play/pause (Space), a frame back or on (←/→), the start and
// end (Home/End), the frame scrubbed or typed, slow motion. The playhead redraws every animation frame.
import { useEffect, useState } from "react";
import type { Viewer } from "../viewer/Viewer";

/** What the bar drives: the 3D viewer's playing clip, or a 2D sheet (pixel/View's SheetClock). */
export type Clock = Pick<Viewer, "fps" | "duration" | "time" | "pause" | "seek" | "isPaused" | "play" | "setSpeed">;

export function useFrame(): void {
  const [, redraw] = useState(0);
  useEffect(() => {
    let id = requestAnimationFrame(function loop() {
      redraw((x) => x + 1);
      id = requestAnimationFrame(loop);
    });
    return () => cancelAnimationFrame(id);
  }, []);
}
export function useTransportKeys(v: Clock, onStep?: (frame: number) => void) {
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).closest?.("input:not([type=range]),textarea,select,button")) return;
      const fps = v.fps();
      const last = Math.round(v.duration() * fps);
      const now = Math.round(v.time() * fps);
      const go = (f: number) => (v.pause(), v.seek(Math.min(Math.max(f, 0), last) / fps), onStep?.(Math.min(Math.max(f, 0), last)));
      if (e.key === " ") v.isPaused() ? v.play() : v.pause();
      else if (e.key === "ArrowLeft") go(now - 1);
      else if (e.key === "ArrowRight") go(now + 1);
      else if (e.key === "Home") go(0);
      else if (e.key === "End") go(last);
      else return;
      e.preventDefault();
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [v, onStep]);
}
export function Transport(props: { viewer: Clock; children?: React.ReactNode }) {
  const v = props.viewer;
  const [speed, setSpeed] = useState(1);
  useFrame();
  const fps = v.fps();
  const last = Math.max(1, Math.round(v.duration() * fps));
  const f = Math.min(last, Math.round(v.time() * fps));
  const go = (n: number) => (v.pause(), v.seek(Math.min(Math.max(n, 0), last) / fps));
  return (
    <div className="transport" role="group" aria-label="Time">
      {/* an editor's glyphs: a bare triangle is Play alone (Next frame showed the same ▶ while paused) */}
      <button aria-label="First frame" title="Home" onClick={() => go(0)}>
        |◀◀
      </button>
      <button aria-label="Previous frame" title="←" onClick={() => go(f - 1)}>
        ◀|
      </button>
      <button className="play" aria-label={v.isPaused() ? "Play" : "Pause"} title="Space" onClick={() => (v.isPaused() ? v.play() : v.pause())}>
        {v.isPaused() ? "▶" : "❚❚"}
      </button>
      <button aria-label="Next frame" title="→" onClick={() => go(f + 1)}>
        |▶
      </button>
      <button aria-label="Last frame" title="End" onClick={() => go(last)}>
        ▶▶|
      </button>
      {props.children ?? <input type="range" aria-label="Frame" min={0} max={last} value={f} onChange={(e) => go(+e.target.value)} />}
      <label className="frame">
        <span className="tb-head">Frame</span>
        <input type="number" aria-label="Frame number" min={0} max={last} value={f} onChange={(e) => Number.isFinite(+e.target.value) && go(+e.target.value)} />
        <span>
          / {last} · {(f / fps).toFixed(2)} s
        </span>
      </label>
      <label className="speed">
        <span className="tb-head">Speed</span>
        <select aria-label="Playback speed" value={speed} onChange={(e) => (setSpeed(+e.target.value), v.setSpeed(+e.target.value))}>
          <option value={1}>1×</option>
          <option value={0.5}>0.5×</option>
          <option value={0.25}>0.25×</option>
        </select>
      </label>
    </div>
  );
}
