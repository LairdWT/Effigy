// M42: two versions side by side: two linked viewers and one mirrored table of what differs.
import { useEffect, useRef, useState } from "react";
import { fileUrl, type Meta } from "./api";
import { Viewer, type Stats } from "./viewer/Viewer";
import { hasGlb, hasImage, label, mainFile, source } from "./workflow";

declare global {
  interface Window {
    __compare?: Viewer[];
  }
}

/** The Checklist panel's heading from a checklist's items: passed, warnings, failed, not checked. */
function summary(items: Record<string, { status?: string }>): string {
  const n = (s: string) => Object.values(items).filter((i) => i.status === s).length;
  const unknown = Object.values(items).length - n("pass") - n("warn") - n("fail");
  return [`${n("pass")} passed`, n("warn") && `${n("warn")} warning${n("warn") === 1 ? "" : "s"}`, n("fail") && `${n("fail")} failed`, unknown && `${unknown} not checked`]
    .filter(Boolean)
    .join(" · ");
}

export function Compare(props: { asset: string; versions: Meta[]; shown: Meta; other: Meta; onClose: () => void }) {
  const [flip, setFlip] = useState(false);
  const [l, r] = flip ? [props.other, props.shown] : [props.shown, props.other];
  const sides = [l, r].map((m) => {
    const s = source(props.versions, m);
    const file = s && (hasGlb(s) || hasImage(s)) ? mainFile(s) : undefined;
    return { m, glb: s && file && hasGlb(s) ? fileUrl(props.asset, s.version, file) : null, img: s && file && !hasGlb(s) ? fileUrl(props.asset, s.version, file) : null };
  });
  const canvases = [useRef<HTMLCanvasElement>(null), useRef<HTMLCanvasElement>(null)];
  const [stats, setStats] = useState<(Stats | null)[]>([null, null]);
  const urls = sides.map((s) => s.glb).join("\n");
  useEffect(() => {
    const vs = canvases.map((c) => new Viewer(c.current!));
    window.__compare = vs;
    let off = () => {};
    let dead = false;
    setStats([null, null]);
    Promise.all(
      sides.map((s, i) =>
        s.glb
          ? vs[i].load(s.glb).then(
              (st) => (st && !dead && setStats((p) => p.map((x, j) => (j === i ? st : x))), st),
              () => null,
            )
          : null,
      ),
    ).then((done) => {
      if (!dead && done[0] && done[1]) off = vs[0].link(vs[1]);
    });
    return () => {
      dead = true;
      off();
      vs.forEach((v) => v.dispose());
      window.__compare = undefined;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- urls stands for the sides
  }, [urls]);
  useEffect(() => {
    const esc = (e: KeyboardEvent) => e.key === "Escape" && props.onClose();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [props.onClose]);

  // a side's checks: its own report when it is one, else the latest check of it; read from the checklist itself,
  // as the Checklist panel does (a fail count of 0 said "passed" over warnings; audit 2026-10-10, UI-005)
  const report = (m: Meta) => (m.step === "validate" ? m : props.versions.filter((x) => x.step === "validate" && x.parent === m.version).at(-1));
  const reports = [l, r].map((m) => report(m));
  const [checks, setChecks] = useState<string[]>(["…", "…"]);
  useEffect(() => {
    let dead = false;
    Promise.all(
      reports.map((c) =>
        !c
          ? "not checked"
          : fetch(fileUrl(props.asset, c.version, c.outputs.checklist ?? "checklist.json"))
              .then((x) => (x.ok ? x.json() : Promise.reject(new Error(String(x.status)))))
              .then((j) => summary(j.items ?? {}), () => "report unavailable"),
      ),
    ).then((t) => !dead && setChecks(t));
    return () => {
      dead = true;
    };
  }, [reports.map((c) => c?.version ?? "").join("\n")]); // the two report versions stand for the sides
  const rows: [string, (string | number)[]][] = [
    ["Triangles", stats.map((s) => s?.triangles.toLocaleString() ?? "–")],
    ["Vertices", stats.map((s) => s?.vertices.toLocaleString() ?? "–")],
    ["Meshes", stats.map((s) => s?.meshes ?? "–")],
    ["Materials", stats.map((s) => s?.materials ?? "–")],
    ["Height (m)", stats.map((s) => (s ? s.height.toFixed(2) : "–"))],
    ["Bones", stats.map((s) => s?.bones.length ?? "–")],
    ["Clips", stats.map((s) => s?.clips.length ?? "–")],
    ["Checks", checks],
    ["Licences", sides.map((s) => `${s.m.licenses?.length ?? 0}${s.m.restricted ? ", restricted" : ""}`)],
  ];
  return (
    <div className="compare" role="region" aria-label="Compare versions">
      <div className="compare-head">
        <strong>Compare</strong>
        <button className="small" onClick={() => setFlip((f) => !f)}>
          Swap
        </button>
        <button className="small" onClick={props.onClose}>
          Close
        </button>
      </div>
      <div className="compare-views">
        {sides.map((s, i) => (
          <div key={i} className="compare-side">
            <div className="compare-name">
              {s.m.label ?? label(s.m)} · {s.m.version.slice(0, 3)}
            </div>
            <div className="preview">
              <canvas ref={canvases[i]} hidden={!s.glb} aria-label={`3D preview of ${s.m.label ?? label(s.m)}`} />
              {s.img && <img className="overlay checker" src={s.img} alt="" />}
              {!s.glb && !s.img && <div className="hint">Nothing to show.</div>}
            </div>
          </div>
        ))}
      </div>
      <table className="compare-table">
        <tbody>
          {rows.map(([name, [a, b]]) => (
            <tr key={name} className={String(a) !== String(b) ? "differs" : undefined}>
              <td>{a}</td>
              <th scope="row">{name}</th>
              <td>{b}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
