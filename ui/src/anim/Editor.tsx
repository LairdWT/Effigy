// M37b/c, M38: the animation editor on an animated version. The base clip (the nearest anim version's) stays as it is; the
// user's correction layer (docs/IMPLEMENTATION.md §3.2 anim_edit) is evaluated on top and played live in the viewer; the
// dope sheet (or the curves) lies under the view (#timeline-slot), the selected bone's key, the foot locks and the clip
// tools in the panel; Save makes an anim_edit version.
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { fileUrl, type Meta } from "../api";
import { leave, useBusy, useHistory, useUnsaved } from "../hooks";
import type { Viewer } from "../viewer/Viewer";
import {
  conj,
  contacts,
  delta,
  evaluate,
  fromDegrees,
  fromThree,
  I,
  mul,
  norm,
  offset,
  positive,
  smoothed,
  toDegrees,
  toThree,
  NAME_RULE,
  nameOk,
  type Clip,
  type Key,
  type Layer,
  type Lock,
  type Offset,
  type Q,
  type V3,
} from "./clip";
import { KeyList, DopeSheet, type Curves, type Row } from "./DopeSheet";
import { Transport, useFrame, useTransportKeys } from "./Transport";

const FALLOFF = 10; // frames a new key fades in and out over
const EMPTY: Layer = {}; // one object: a clip without edits must not look changed on every render
const AXES = ["#e06464", "#6cc070", "#5a9cf0"]; // X, Y, Z in the curves
const MAX_LOCKS = 64; // anim_edit's limit
type Layers = Record<string, Layer>;
type Bone = { name: string; node: string; parent: string | null; rest: V3 }; // three.js name, glTF node name, parent's three.js name
type Base = { fps: number; base: string; clips: Record<string, { data: Clip; keep: THREE.KeyframeTrack[] }>; bones: Bone[]; groups: [string, string[]][]; sides?: [string, string] };
type Gizmo = "rotate" | "move" | "ik";

export const hasEdits = (l?: Layer) =>
  !!l &&
  (Object.values(l.keys ?? {}).some((k) => k.length) ||
    Object.values(l.offsets ?? {}).some((o) => o.length) ||
    !!l.trim ||
    (l.speed ?? 1) !== 1 ||
    !!l.loop ||
    !!l.ground ||
    !!l.in_place ||
    Object.values(l.smooth ?? {}).some((s) => s > 0) ||
    !!l.feet?.length);

/** The dope sheet's groups of glTF node names: a person's body, arms, hands and legs; a creature's middle and sides. */
export function animGroups(nodes: string[], template: string, sides?: [string, string]): [string, string[]][] {
  if (template !== "mixamo52" && sides) {
    const side = (s: string) => nodes.filter((n) => n.endsWith(s));
    return [
      ["Middle", nodes.filter((n) => !n.endsWith(sides[0]) && !n.endsWith(sides[1]))], // root, spine, head, tail
      ["Left side", side(sides[0])],
      ["Right side", side(sides[1])],
    ];
  }
  const by = (re: RegExp) => nodes.filter((n) => re.test(n));
  const groups: [string, string[]][] = [["Body", by(/^(Hips|Spine\d?|Neck|Head)$/)]];
  for (const s of ["Left", "Right"])
    groups.push([`${s} arm`, by(new RegExp(`^${s}(Shoulder|Arm|ForeArm|Hand)$`))], [`${s} hand`, by(new RegExp(`^${s}Hand.+`))], [`${s} leg`, by(new RegExp(`^${s}(UpLeg|Leg|Foot|ToeBase)$`))]);
  const seen = new Set(groups.flatMap(([, n]) => n));
  groups.push(["Other", nodes.filter((n) => !seen.has(n))]);
  return groups.filter(([, n]) => n.length);
}

// a key's id in the dope sheet: "node@frame" for a turn, "node:move@frame" for a move (an offset)
const parse = (id: string) => {
  const i = id.lastIndexOf("@");
  const n = id.slice(0, i);
  const move = n.endsWith(":move");
  return { n: move ? n.slice(0, -5) : n, f: +id.slice(i + 1), move };
};
const setIn = <T extends { f: number }>(all: Record<string, T[]> | undefined, node: string, k: T) => ({
  ...all,
  [node]: [...(all?.[node] ?? []).filter((x) => x.f !== k.f), k].sort((a, b) => a.f - b.f),
});
const setKey = (l: Layer, node: string, k: Key): Layer => ({ ...l, keys: setIn(l.keys, node, k) });
const setOffset = (l: Layer, node: string, o: Offset): Layer => ({ ...l, offsets: setIn(l.offsets, node, o) });
const dropKeys = (l: Layer, picked: string[]): Layer => {
  const keep = <T extends { f: number }>(all: Record<string, T[]> | undefined, tag: string) =>
    Object.fromEntries(
      Object.entries(all ?? {})
        .map(([n, ks]) => [n, ks.filter((k) => !picked.includes(`${n}${tag}@${k.f}`))] as const)
        .filter(([, ks]) => ks.length),
    );
  return { ...l, keys: keep(l.keys, ""), offsets: keep(l.offsets, ":move") };
};
const cm = (m: number) => Math.round(m * 1000) / 10; // metres to cm, a millimetre's precision

export function AnimEditor(props: { asset: string; version: Meta; viewer: Viewer; onSave: (clips: Layers) => Promise<unknown>; onClose: () => void }) {
  const v = props.viewer;
  const ver = props.version;
  const [ready, setReady] = useState<Base | null>(null);
  const [error, setError] = useState<string | null>(null);
  const hist = useHistory<Layers>();
  const layers = hist.h?.now ?? {};
  const [picked, setClip] = useState("");
  // the clip being edited: the picked one while it exists (undo can remove a copy), else the first base clip
  const clip = ready && (picked in ready.clips || layers[picked]?.from) ? picked : Object.keys(ready?.clips ?? {})[0] ?? "";
  const [bone, setBone] = useState<string | null>(null); // a glTF node name
  const [sel, setSel] = useState<string[]>([]); // keys as "node@frame" / "node:move@frame"
  const [open, setOpen] = useState<Set<string>>(new Set());
  const [original, setOriginal] = useState(false);
  const [frame, setFrame] = useState(0); // the base frame under the playhead
  const [mode, setMode] = useState<Gizmo>("rotate");
  const [curvesOn, setCurvesOn] = useState(false);
  const [path, setPath] = useState(false);
  const [onion, setOnion] = useState(false);
  const [found, setFound] = useState<string | null>(null); // what Find foot contacts did
  const [busy, run] = useBusy();
  const dirty = (hist.h?.past.length ?? 0) > 0; // something changed since the version was opened (what Save sends)
  useUnsaved("animation", dirty && !busy); // not while a save runs: its result opens the new version (UX-01)
  const loaded = useRef(new Map<string, THREE.AnimationClip>()); // the viewer's clips as they were: put back on close
  const added = useRef(new Set<string>());

  // the base: this version's own animations, or for an anim_edit its base's; the clips' fps; the user's earlier layer
  useEffect(() => {
    let live = true;
    (async () => {
      const get = (version: string, file: string) => fetch(fileUrl(props.asset, version, file)).then((r) => (r.ok ? r.json() : Promise.reject(new Error(`${version}/${file}: ${r.status}`))));
      const meta = await get(ver.version, ver.outputs.clips ?? "clips.json");
      const edit = ver.step === "anim_edit" ? await get(ver.version, ver.outputs.edit ?? "edit.json") : null;
      const base: string = edit?.base ?? ver.version;
      const skel = await get(ver.version, ver.outputs.skeleton ?? "skeleton.json").catch(() => ({})); // the template names the groups
      let anims: THREE.AnimationClip[];
      if (base === ver.version) anims = meta.clips.map((c: { name: string }) => v.getClip(c.name)).filter(Boolean);
      else {
        const gltf = await new GLTFLoader().loadAsync(fileUrl(props.asset, base, "rigged_anim.glb"));
        anims = gltf.animations;
        gltf.scene.traverse((o) => {
          const m = o as THREE.Mesh;
          m.geometry?.dispose();
          for (const mat of [m.material ?? []].flat() as THREE.MeshStandardMaterial[]) {
            for (const t of [mat.map, mat.normalMap, mat.roughnessMap, mat.metalnessMap, mat.aoMap, mat.emissiveMap]) t?.dispose();
            mat.dispose();
          }
        });
      }
      const bones = v.boneNames();
      const fps: number = meta.fps ?? 24;
      const clips = Object.fromEntries(anims.map((a) => [a.name, { data: fromThree(a, fps, bones), keep: a.tracks.filter((t) => t.name.endsWith(".scale")) }]));
      if (!live) return;
      const groups = animGroups(
        bones.map((b) => b.node),
        skel.template ?? "mixamo52",
        skel.sides,
      );
      setReady({ fps, base, clips, bones, groups, sides: skel.sides });
      hist.start(edit?.clips ?? {});
      const playing = v.clipName();
      setClip(playing && (clips[playing] || edit?.clips?.[playing]) ? playing : Object.keys(clips)[0]);
    })().catch((e) => live && setError((e as Error).message));
    return () => {
      live = false;
    };
  }, [props.asset, ver.version]);

  const rootOf = (c: string) => layers[c]?.from ?? c; // M44: a copy plays and edits on its source clip's samples
  const data = ready?.clips[rootOf(clip)];
  const layer = layers[clip] ?? EMPTY;
  const F = data?.data.frames ?? 1;
  const trim = layer.trim ?? [0, F - 1];
  const speed = layer.speed ?? 1;
  const evaluated = useMemo(() => data && evaluate(data.data, layer), [data, layer]);
  const three = (node: string) => ready?.bones.find((b) => b.name === node)?.name;
  const node = (name: string) => ready?.bones.find((b) => b.name === name)?.node ?? name;
  const track = (n: string) => data?.data.bones.find((b) => b.name === n);
  // a move needs a moving translation (the hips); a lock or an IK drag a bone whose parent and grandparent turn
  const canMove = (n: string | null) => !!n && !!track(n)?.translation;
  const chain = (n: string | null) => {
    const b = n ? track(n) : undefined;
    const l = b?.parent ? track(b.parent) : undefined;
    const u = l?.parent ? track(l.parent) : undefined;
    return !!(b?.rotation && l?.rotation && u?.rotation);
  };
  const gizmo: Gizmo = (mode === "move" && !canMove(bone)) || (mode === "ik" && !chain(bone)) ? "rotate" : mode;

  // the viewer plays the evaluated clip (or the original), from where it was; the motion path and the ghosts follow it
  useEffect(() => {
    if (!ready || !data || !evaluated) return;
    if (!loaded.current.has(clip) && !added.current.has(clip)) {
      const was = v.getClip(clip);
      if (was) loaded.current.set(clip, was);
      else added.current.add(clip); // a copy the viewer did not have: dropped on close
    }
    v.useClip(toThree(original ? data.data : evaluated, clip, ready.bones, data.keep));
  }, [evaluated, original, clip, ready]);
  // a copy that is gone from the layers (renamed, deleted, undone) leaves the viewer; the clip now playing was set above
  useEffect(() => {
    for (const c of added.current) if (!layers[c]) (v.dropClip(c), added.current.delete(c));
  }, [layers]);
  useEffect(() => void (ready && v.setMotionPath(path && bone ? (three(bone) ?? null) : null)), [path, bone, evaluated, original, clip, ready]);
  useEffect(() => void (ready && v.setOnion(onion ? [-6, -3, 3, 6] : null)), [onion, evaluated, original, clip, ready]);
  // put the viewer back as it was (unless it shows another model by now)
  useEffect(() => {
    const model = v.stats;
    return () => {
      if (v.stats !== model) return;
      v.setPoseEdit(null);
      v.setMotionPath(null);
      v.setOnion(null);
      for (const c of added.current) v.dropClip(c);
      for (const c of loaded.current.values()) v.useClip(c);
    };
  }, []);

  const baseFrame = () => {
    const g = Math.round(v.time() * (ready?.fps ?? 24));
    return original ? Math.min(g, F - 1) : Math.min(trim[1], trim[0] + Math.round(g * speed));
  };
  const seekBase = (f: number) => {
    v.pause();
    const out = original ? f : (Math.min(Math.max(f, trim[0]), trim[1]) - trim[0]) / speed;
    v.seek(out / (ready?.fps ?? 24));
  };
  const commit = (f: (l: Layer) => Layer) => hist.commit((all) => ({ ...all, [clip]: f(all[clip] ?? {}) }));

  // a turn in the view: the key at this frame that makes the bone look like that (the delta from the smoothed base)
  const keyTurns = (turns: Record<string, Q>) => {
    if (!data) return;
    const f = baseFrame();
    const sm = smoothed(data.data, layer);
    const ds = Object.entries(turns).flatMap(([name, q]) => {
      const n = node(name);
      const base = sm.bones.find((b) => b.name === n)?.rotation?.[f];
      return base ? [[n, positive(norm(mul(conj(base), q)))] as const] : [];
    });
    commit((l) => ds.reduce((acc, [n, d]) => setKey(acc, n, { f, q: d, falloff: l.keys?.[n]?.find((k) => k.f === f)?.falloff ?? FALLOFF }), l));
    setSel(ds.map(([n]) => `${n}@${f}`));
  };
  const onPose = (name: string, q: Q) => (keyTurns({ [name]: q }), setBone(node(name)));
  // a move in the view: the offset at this frame grows by how far the bone went
  const onMove = (name: string, from: V3, to: V3) => {
    const n = node(name);
    const f = baseFrame();
    const os = layer.offsets?.[n];
    const now = os?.length ? offset(os, f) : [0, 0, 0];
    commit((l) => setOffset(l, n, { f, v: now.map((x, i) => Math.round((x + to[i] - from[i]) * 1e5) / 1e5) as V3, falloff: os?.find((o) => o.f === f)?.falloff ?? FALLOFF }));
    setBone(n);
    setSel([`${n}:move@${f}`]);
  };
  const keyed = useMemo(
    () => [...Object.entries(layer.keys ?? {}), ...Object.entries(layer.offsets ?? {})].filter(([, ks]) => ks.some((k) => k.f === frame)).map(([n]) => three(n) ?? n),
    [layer, frame, ready],
  );
  useEffect(() => {
    if (!ready) return;
    v.setPoseEdit(original ? null : { selected: bone ? (three(bone) ?? null) : null, keyed, mode: gizmo, onSelect: (b) => setBone(node(b)), onPose, onMove, onIK: keyTurns });
  });

  // I keys the selected bone as it is now; X / Delete removes the selected keys; Ctrl+Z undoes
  useTransportKeys(v);
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).closest?.("input,textarea,select")) return;
      if (e.ctrlKey || e.metaKey) {
        if (e.key.toLowerCase() === "z") (e.preventDefault(), e.shiftKey ? hist.redo() : hist.undo());
        return;
      }
      if (e.key === "i" || e.key === "I") insertKey();
      else if (e.key === "x" || e.key === "Delete") deleteKeys();
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  });
  const insertKey = () => {
    if (!bone || original) return;
    const f = baseFrame();
    if (gizmo === "move") {
      const os = layer.offsets?.[bone];
      commit((l) => setOffset(l, bone, { f, v: os?.length ? offset(os, f) : [0, 0, 0], falloff: os?.find((o) => o.f === f)?.falloff ?? FALLOFF }));
      return setSel([`${bone}:move@${f}`]);
    }
    if (!track(bone)?.rotation) return;
    const ks = layer.keys?.[bone];
    commit((l) => setKey(l, bone, { f, q: ks?.length ? positive(delta(ks, f)) : I, falloff: ks?.find((k) => k.f === f)?.falloff ?? FALLOFF }));
    setSel([`${bone}@${f}`]);
  };
  const deleteKeys = () => {
    if (!sel.length) return;
    commit((l) => dropKeys(l, sel));
    setSel([]);
  };
  const moveKeys = (df: number) => {
    const moved: string[] = [];
    let out = dropKeys(layer, sel);
    for (const s of sel) {
      const { n, f, move } = parse(s);
      const to = Math.min(Math.max(f + df, 0), F - 1);
      const k = layer.keys?.[n]?.find((x) => x.f === f);
      const o = layer.offsets?.[n]?.find((x) => x.f === f);
      if (move && o) out = setOffset(out, n, { ...o, f: to });
      else if (!move && k) out = setKey(out, n, { ...k, f: to });
      else continue;
      moved.push(`${n}${move ? ":move" : ""}@${to}`);
    }
    commit(() => out);
    setSel(moved);
  };

  // the curves: the selected bone's turn correction in degrees (its moves in cm in Move), its keys as points; built when
  // they change, not on every frame of playback
  const curves = useMemo((): Curves | null => {
    if (!curvesOn || !bone) return null;
    const frames = Array.from({ length: F }, (_, f) => f);
    const ks = layer.keys?.[bone];
    const os = layer.offsets?.[bone];
    return gizmo === "move"
      ? {
          unit: "cm",
          lines: ["X", "Y", "Z"].map((a, i) => ({ label: a, color: AXES[i], values: frames.map((f) => (os?.length ? cm(offset(os, f)[i]) : 0)) })),
          points: (os ?? []).map((o) => ({ id: `${bone}:move@${o.f}`, f: o.f, values: o.v.map(cm) })),
        }
      : {
          unit: "°",
          lines: ["X", "Y", "Z"].map((a, i) => ({ label: a, color: AXES[i], values: frames.map((f) => (ks?.length ? toDegrees(delta(ks, f))[i] : 0)) })),
          points: (ks ?? []).map((k) => ({ id: `${bone}@${k.f}`, f: k.f, values: toDegrees(k.q) })),
        };
  }, [curvesOn, bone, gizmo, layer, F]);
  // the bones the base clip moves (a strip on their rows)
  const movingSet = useMemo(
    () =>
      new Set(
        (data?.data.bones ?? [])
          .filter((t) => !!t.translation || !!t.rotation?.some((q, f, r) => f > 0 && Math.abs(q[0] * r[f - 1][0] + q[1] * r[f - 1][1] + q[2] * r[f - 1][2] + q[3] * r[f - 1][3]) < 0.99999))
          .map((t) => t.name),
      ),
    [data],
  );

  if (error) return <p className="note warn">Could not open the animation: {error}</p>;
  if (!ready || !data) return <p className="muted">Loading the animation…</p>;

  // the dope sheet's rows: groups, their bones when open (a moving bone's moves on a row of their own)
  const moving = (n: string) => movingSet.has(n);
  const keysOf = (n: string) => (layer.keys?.[n] ?? []).map((k) => k.f);
  const movesOf = (n: string) => (layer.offsets?.[n] ?? []).map((o) => o.f);
  const locks = layer.feet ?? [];
  const spans: Record<string, [number, number][]> = {};
  for (const [g, nodes] of ready.groups)
    for (const lk of locks)
      if (nodes.includes(lk.bone)) {
        (spans[lk.bone] ??= []).push([lk.from, lk.to]);
        (spans[`g:${g}`] ??= []).push([lk.from, lk.to]);
      }
  const rows: Row[] = ready.groups.flatMap(([g, nodes]) => [
    { id: `g:${g}`, label: g, group: true, open: open.has(g), keys: [...new Set(nodes.flatMap((n) => [...keysOf(n), ...movesOf(n)]))], moving: nodes.some(moving) },
    ...(open.has(g)
      ? nodes.flatMap((n) => [
          { id: n, label: n, group: false, keys: keysOf(n), moving: moving(n), active: n === bone && gizmo !== "move" },
          ...(canMove(n) ? [{ id: `${n}:move`, label: `${n} · move`, group: false, keys: movesOf(n), moving: true, active: n === bone && gizmo === "move" }] : []),
        ])
      : []),
  ]);
  // every keyed bone, its group folded or not: the key list (UX-13) does not depend on what the timeline unfolded
  const keyRows: Row[] = ready.groups.flatMap(([, nodes]) =>
    nodes.flatMap((n) => [
      { id: n, label: n, group: false, keys: keysOf(n), moving: false },
      ...(canMove(n) ? [{ id: `${n}:move`, label: `${n} · move`, group: false, keys: movesOf(n), moving: true }] : []),
    ]),
  );
  const pick = (n: string, move: boolean) => {
    setBone(n);
    if (move) setMode("move");
    else if (mode === "move") setMode("rotate");
  };
  const onSelectKeys = (ids: string[], add: boolean) => {
    const keys = ids.flatMap((id) => {
      if (!id.startsWith("g:")) return [id];
      const [g, f] = [id.slice(2, id.lastIndexOf("@")), +id.slice(id.lastIndexOf("@") + 1)];
      return (ready.groups.find(([name]) => name === g)?.[1] ?? []).flatMap((n) => [...(keysOf(n).includes(f) ? [`${n}@${f}`] : []), ...(movesOf(n).includes(f) ? [`${n}:move@${f}`] : [])]);
    });
    setSel((s) => (add ? [...new Set([...s, ...keys])] : keys));
    if (keys[0]) pick(parse(keys[0]).n, parse(keys[0]).move);
  };

  const here = bone ? layer.keys?.[bone]?.find((k) => k.f === frame) : undefined;
  // a lock whose leg (its bone, parent, grandparent) holds the selected bone at this frame
  const heldBy = locks.find((lk) => {
    const b = track(lk.bone);
    const l = b?.parent ? track(b.parent) : undefined;
    return frame >= lk.from - lk.blend && frame <= lk.to + lk.blend && [lk.bone, b?.parent, l?.parent].includes(bone ?? undefined);
  });
  const hereMove = bone ? layer.offsets?.[bone]?.find((o) => o.f === frame) : undefined;
  const deg = here ? toDegrees(here.q) : null;
  const setDeg = (i: number, x: number) => here && commit((l) => setKey(l, bone!, { ...here, q: fromDegrees(deg!.map((d, j) => (j === i ? x : d)) as V3) }));
  const setCm = (i: number, x: number) => hereMove && commit((l) => setOffset(l, bone!, { ...hereMove, v: hereMove.v.map((d, j) => (j === i ? x / 100 : d)) as V3 }));
  const smoothOf = (g: string) => Math.max(0, ...(ready.groups.find(([name]) => name === g)?.[1] ?? []).map((n) => layer.smooth?.[n] ?? 0));
  const setSmooth = (g: string, s: number) =>
    commit((l) => ({ ...l, smooth: { ...l.smooth, ...Object.fromEntries((ready.groups.find(([name]) => name === g)?.[1] ?? []).filter((n) => track(n)?.rotation).map((n) => [n, s])) } }));
  const num = (x: string, lo: number, hi: number) => (Number.isFinite(+x) && x.trim() !== "" ? Math.min(Math.max(+x, lo), hi) : null);
  const snap = () => {
    const feet = v.feet();
    const low = v.lowest(feet.names);
    commit((l) => ({ ...l, ground: Math.round(((l.ground ?? 0) + feet.rest - low) * 1000) / 1000 }));
  };
  const edited = Object.keys(layers).filter((c) => hasEdits(layers[c]) || layers[c].from); // copies always: they exist only in the layer
  const isCopy = !!layers[clip]?.from;
  const names = (except = "") => [...Object.keys(ready?.clips ?? {}), ...Object.keys(layers)].filter((n) => n !== except);
  const ask = (msg: string, def: string, except = "") => {
    const n = window.prompt(msg, def)?.replace(/^ +| +$/g, "");
    if (!n) return null;
    if (!nameOk(n, names(except))) {
      window.alert(`${NAME_RULE}: "${n}" is not allowed or is taken.`);
      return null;
    }
    return n;
  };
  const duplicate = () => {
    let n = `${clip} copy`;
    for (let i = 2; !nameOk(n, names()); i++) n = `${clip} copy ${i}`;
    const name = ask("Name of the copy", n);
    if (!name) return;
    hist.commit((all) => ({ ...all, [name]: { ...structuredClone(all[clip] ?? {}), from: rootOf(clip) } }));
    setClip(name);
    setSel([]);
  };
  const rename = () => {
    const name = ask("New name", clip, clip);
    if (!name) return;
    hist.commit(({ [clip]: l, ...rest }) => ({ ...rest, [name]: l }));
    setClip(name);
  };
  const drop = () => {
    if (!window.confirm(`Delete the copy ${clip}?`)) return;
    const to = rootOf(clip);
    hist.commit(({ [clip]: _, ...rest }) => rest);
    setClip(to);
    setSel([]);
  };

  // the foot locks: found on the clip as edited so far, before the locks (the space they work in); a bone's rest height is
  // its own and its mirror's mean, so both sides pick the same bone of a skeleton fitted a little unevenly
  const findContacts = () => {
    const { heights } = v.feet();
    const mirror = (n: string) =>
      n.startsWith("Left") ? "Right" + n.slice(4) : n.startsWith("Right") ? "Left" + n.slice(5) : ready.sides?.map((s, i) => (n.endsWith(s) ? n.slice(0, -s.length) + ready.sides![1 - i] : "")).find(Boolean);
    const height = (b: Bone) => {
      const m = ready.bones.find((x) => x.node === mirror(b.node));
      return m ? (heights[b.name] + heights[m.name]) / 2 : heights[b.name];
    };
    const near = new Set(ready.bones.filter((b) => height(b) <= 0.2).map((b) => b.name));
    const feet = ready.bones.filter((b) => near.has(b.name) && !(b.parent && near.has(b.parent)) && !/tail/i.test(b.node) && chain(b.node)).map((b) => b.node);
    const pre = evaluate(data.data, { keys: layer.keys, offsets: layer.offsets, smooth: layer.smooth });
    const others = (layer.feet ?? []).filter((lk) => !feet.includes(lk.bone));
    const all = contacts(pre, feet);
    const room = Math.max(MAX_LOCKS - others.length, 0); // anim_edit takes 64: the longest stretches first
    const hits = [...all]
      .sort((a, b) => b.to - b.from - (a.to - a.from))
      .slice(0, room)
      .sort((a, b) => a.bone.localeCompare(b.bone) || a.from - b.from);
    commit(() => ({ ...layer, feet: [...others, ...hits] }));
    setFound(
      !feet.length
        ? "No feet found near the floor."
        : all.length
          ? `${all.length} still stretches on ${feet.join(", ")}${hits.length < all.length ? `; the ${hits.length} longest locked (${MAX_LOCKS} at most)` : ""}.`
          : `No foot stands still in this clip (${feet.join(", ")}): a walk or run in place slides its feet on purpose.`,
    );
  };
  const setLock = (i: number, lk: Lock | null) => commit((l) => ({ ...l, feet: (l.feet ?? []).flatMap((x, j) => (j !== i ? [x] : lk ? [lk] : [])) }));

  const onCurve = (id: string, i: number, x: number) => {
    const { n, f, move } = parse(id);
    const k = layer.keys?.[n]?.find((y) => y.f === f);
    const o = layer.offsets?.[n]?.find((y) => y.f === f);
    if (move && o) commit((l) => setOffset(l, n, { ...o, v: o.v.map((d, j) => (j === i ? x / 100 : d)) as V3 }));
    else if (!move && k) commit((l) => setKey(l, n, { ...k, q: fromDegrees(toDegrees(k.q).map((d, j) => (j === i ? x : d)) as V3) }));
  };

  return (
    <div className="stack anim-editor">
      <div className="row">
        <label>
          Clip{" "}
          <select aria-label="Clip to edit" value={clip} onChange={(e) => (setClip(e.target.value), setSel([]), setFound(null))}>
            {[...Object.keys(ready.clips), ...Object.keys(layers).filter((c) => layers[c].from)].map((c) => (
              <option key={c} value={c}>
                {c}
                {layers[c]?.from ? ` (copy of ${layers[c].from})` : ""}
                {hasEdits(layers[c]) ? " (edited)" : ""}
              </option>
            ))}
          </select>
        </label>
        <button className="small" onClick={duplicate}>
          Duplicate
        </button>
        {isCopy && (
          <>
            <button className="small" onClick={rename}>
              Rename
            </button>
            <button className="small" onClick={drop}>
              Delete
            </button>
          </>
        )}
        <div role="group" aria-label="Compare" className="row">
          <button aria-pressed={!original} onClick={() => setOriginal(false)}>
            Edited
          </button>
          <button aria-pressed={original} onClick={() => setOriginal(true)}>
            Original
          </button>
        </div>
      </div>
      <details>
        <summary>Help</summary>
        <ul className="muted">
        <li>Click a joint in the view (or a bone in the timeline) to select it, then turn it with the rings: that keys it at this frame.</li>
        <li>Move shifts the hips with arrows; IK drag pulls a hand or foot, the arm or leg bending to follow.</li>
        <li>A key fades in and out over its falloff, so the motion around it stays smooth. Keys are diamonds; drag them in time, or switch the timeline to Curves.</li>
        <li>Keys: Space plays, ←/→ a frame, I keys the bone as it is, X deletes the selected keys, Ctrl+Z undoes; Ctrl+wheel zooms the timeline.</li>
        <li>Timeline: Keys shows where each bone is keyed; Curves, with a bone selected, draws its turn over the clip as lines whose points you drag.</li>
        <li>Without a mouse: Keys as a list (below the Save button) selects a key, moves it a frame at a time, and in Curves edits its values.</li>
        <li>Show: Motion path draws the selected bone's track over the clip; Onion skin shows the model a few frames before (blue) and after (green).</li>
        </ul>
      </details>
      <section className="stack" aria-label="Bone">
        <h4>Bone {bone ? `· ${bone}` : ""}</h4>
        {!bone && <p className="muted">No bone selected.</p>}
        {bone && (
          <div role="group" aria-label="Gizmo" className="row">
            <button aria-pressed={gizmo === "rotate"} onClick={() => setMode("rotate")}>
              Rotate
            </button>
            <button aria-pressed={gizmo === "move"} disabled={!canMove(bone)} title={canMove(bone) ? "" : "This bone does not move in the clip"} onClick={() => setMode("move")}>
              Move
            </button>
            <button aria-pressed={gizmo === "ik"} disabled={!chain(bone)} title={chain(bone) ? "" : "Needs two turning bones above it"} onClick={() => setMode("ik")}>
              IK drag
            </button>
          </div>
        )}
        {/* why a tool is off, said where a keyboard and a touch screen see it too (UX-15) */}
        {bone && (!canMove(bone) || !chain(bone)) && (
          <p className="muted">
            {[!canMove(bone) && "Move: this bone does not move in the clip.", !chain(bone) && "IK drag: needs two turning bones above it."].filter(Boolean).join(" ")}
          </p>
        )}
        {bone && heldBy && (
          <p className="note">
            The foot lock on {heldBy.bone} (frames {heldBy.from}–{heldBy.to}) holds this leg here: a turn or IK drag on it is undone by the lock.
          </p>
        )}
        {bone && gizmo !== "move" && !here && (
          <p className="muted">
            No key at frame {frame}.{" "}
            <button className="small" onClick={insertKey} disabled={original}>
              Key it here (I)
            </button>
          </p>
        )}
        {bone && gizmo !== "move" && here && deg && (
          <>
            <div className="row" role="group" aria-label="Turn at this key">
              {(["X", "Y", "Z"] as const).map((a, i) => (
                <label key={a + frame + bone + deg[i].toFixed(1)}>{/* the value too: a curve drag or the key list changes it */}
                  {a}{" "}
                  <input
                    type="number"
                    step="1"
                    aria-label={`${a} degrees`}
                    defaultValue={deg[i].toFixed(1)}
                    style={{ width: "5em" }}
                    onBlur={(e) => {
                      const x = num(e.target.value, -180, 180);
                      if (x !== null && Math.abs(x - deg[i]) > 1e-3) setDeg(i, x);
                    }}
                    onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
                  />
                  °
                </label>
              ))}
            </div>
            <label>
              Falloff{" "}
              <input
                type="number"
                min={0}
                max={F}
                aria-label="Falloff frames"
                key={`fo${frame}${bone}`}
                defaultValue={here.falloff}
                style={{ width: "5em" }}
                onBlur={(e) => {
                  const x = num(e.target.value, 0, F);
                  if (x !== null && Math.round(x) !== here.falloff) commit((l) => setKey(l, bone, { ...here, falloff: Math.round(x) }));
                }}
              />{" "}
              frames
            </label>
            <div className="row">
              <button
                title="This turn from the first frame to the last (two equal keys at the ends)"
                onClick={() => (commit((l) => setKey(setKey(dropKeys(l, (l.keys?.[bone] ?? []).map((k) => `${bone}@${k.f}`)), bone, { f: 0, q: here.q, falloff: 0 }), bone, { f: F - 1, q: here.q, falloff: 0 })), setSel([]))}
              >
                Whole clip
              </button>
              <button onClick={() => (commit((l) => dropKeys(l, [`${bone}@${frame}`])), setSel([]))}>Delete key</button>
            </div>
          </>
        )}
        {bone && gizmo === "move" && !hereMove && (
          <p className="muted">
            No move at frame {frame}: drag the arrows in the view, or{" "}
            <button className="small" onClick={insertKey} disabled={original}>
              key it here (I)
            </button>
          </p>
        )}
        {bone && gizmo === "move" && hereMove && (
          <>
            <div className="row" role="group" aria-label="Move at this key">
              {(["X", "Y", "Z"] as const).map((a, i) => (
                <label key={a + frame + bone + hereMove.v[i]}>
                  {a}{" "}
                  <input
                    type="number"
                    step="0.5"
                    aria-label={`${a} cm`}
                    defaultValue={cm(hereMove.v[i])}
                    style={{ width: "5em" }}
                    onBlur={(e) => {
                      const x = num(e.target.value, -1000, 1000);
                      if (x !== null && Math.abs(x - cm(hereMove.v[i])) > 1e-3) setCm(i, x);
                    }}
                    onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
                  />
                  cm
                </label>
              ))}
            </div>
            <label>
              Falloff{" "}
              <input
                type="number"
                min={0}
                max={F}
                aria-label="Move falloff frames"
                key={`mfo${frame}${bone}`}
                defaultValue={hereMove.falloff}
                style={{ width: "5em" }}
                onBlur={(e) => {
                  const x = num(e.target.value, 0, F);
                  if (x !== null && Math.round(x) !== hereMove.falloff) commit((l) => setOffset(l, bone, { ...hereMove, falloff: Math.round(x) }));
                }}
              />{" "}
              frames
            </label>
            <button onClick={() => (commit((l) => dropKeys(l, [`${bone}:move@${frame}`])), setSel([]))}>Delete move</button>
          </>
        )}
        {bone && ((layer.keys?.[bone]?.length ?? 0) > 0 || (layer.offsets?.[bone]?.length ?? 0) > 0) && (
          <button
            onClick={() =>
              (commit((l) => dropKeys(l, [...(l.keys?.[bone] ?? []).map((k) => `${bone}@${k.f}`), ...(l.offsets?.[bone] ?? []).map((o) => `${bone}:move@${o.f}`)])), setSel([]))
            }
          >
            Reset bone (all its keys)
          </button>
        )}
      </section>
      <details>
        <summary>Foot locks{locks.length ? ` (${locks.length})` : ""}</summary>
        <div className="stack">
          <p className="muted">A lock holds a foot still over its frames (stops sliding); the leg bends to keep it there.</p>
          <div className="row">
            <button onClick={findContacts} disabled={original}>
              Find foot contacts
            </button>
            {bone && chain(bone) && (
              <button
                disabled={original || locks.length >= MAX_LOCKS}
                onClick={() => commit((l) => ({ ...l, feet: [...(l.feet ?? []), { bone, from: Math.max(frame - 2, 0), to: Math.min(frame + 2, F - 1), blend: Math.min(3, F) }] }))}
              >
                Lock {bone} here
              </button>
            )}
          </div>
          {found && <p className="muted">{found}</p>}
          {locks.map((lk, i) => (
            <div key={`${i}${lk.bone}${lk.from}${lk.to}${lk.blend}`} className="row" role="group" aria-label={`Lock ${i + 1}`}>
              <button className="small" onClick={() => (setBone(lk.bone), seekBase(lk.from))}>
                {lk.bone}
              </button>
              {(["from", "to", "blend"] as const).map((k) => (
                <input
                  key={k}
                  type="number"
                  min={0}
                  max={F - 1}
                  aria-label={`Lock ${i + 1} ${k}`}
                  title={k === "blend" ? "Frames it eases in and out over" : `${k === "from" ? "First" : "Last"} frame`}
                  defaultValue={lk[k]}
                  style={{ width: "3.6em" }}
                  onBlur={(e) => {
                    const x = num(e.target.value, 0, k === "blend" ? F : F - 1);
                    if (x === null || Math.round(x) === lk[k]) return;
                    const n = { ...lk, [k]: Math.round(x) };
                    if (n.from <= n.to) setLock(i, n);
                    else e.target.value = String(lk[k]); // from after to: refused
                  }}
                />
              ))}
              <button aria-label={`Remove lock ${i + 1}`} onClick={() => setLock(i, null)}>
                ✕
              </button>
            </div>
          ))}
          {locks.length > 0 && <p className="muted">Frames from, to, and the blend frames on each side.</p>}
        </div>
      </details>
      <details>
        <summary>Clip tools</summary>
        <div className="stack">
          <div className="row" role="group" aria-label="Trim">
            Trim
            {[0, 1].map((i) => (
              <input
                key={`t${i}${trim[i]}`}
                type="number"
                aria-label={i ? "Last frame" : "First frame"}
                defaultValue={trim[i]}
                style={{ width: "5em" }}
                onBlur={(e) => {
                  const x = num(e.target.value, 0, F - 1);
                  if (x === null) return;
                  const t: [number, number] = i ? [trim[0], Math.max(Math.round(x), trim[0] + 1)] : [Math.min(Math.round(x), trim[1] - 1), trim[1]];
                  commit((l) => ({ ...l, trim: t[0] === 0 && t[1] === F - 1 ? undefined : t }));
                }}
              />
            ))}
          </div>
          <label>
            Speed{" "}
            <input
              type="number"
              step="0.05"
              min={0.1}
              max={10}
              aria-label="Speed"
              key={`s${speed}`}
              defaultValue={speed}
              style={{ width: "5em" }}
              onBlur={(e) => {
                const x = num(e.target.value, 0.1, 10);
                if (x !== null && x !== speed) commit((l) => ({ ...l, speed: x === 1 ? undefined : x }));
              }}
            />
            ×
          </label>
          <label>
            Loop match{" "}
            <input
              type="number"
              min={0}
              aria-label="Loop frames"
              key={`l${layer.loop ?? 0}`}
              defaultValue={layer.loop ?? 0}
              style={{ width: "5em" }}
              onBlur={(e) => {
                const x = num(e.target.value, 0, trim[1] - trim[0]);
                if (x !== null && Math.round(x) !== (layer.loop ?? 0)) commit((l) => ({ ...l, loop: Math.round(x) || undefined }));
              }}
            />{" "}
            frames (the end blends into the start)
          </label>
          <div className="row">
            <label>
              Ground{" "}
              <input
                type="number"
                step="0.005"
                aria-label="Ground offset"
                key={`gr${layer.ground ?? 0}`}
                defaultValue={layer.ground ?? 0}
                style={{ width: "6em" }}
                onBlur={(e) => {
                  const x = num(e.target.value, -10, 10);
                  if (x !== null && x !== (layer.ground ?? 0)) commit((l) => ({ ...l, ground: x || undefined }));
                }}
              />{" "}
              m
            </label>
            <button onClick={snap}>Snap to ground</button>
          </div>
          <label className="check">
            <input type="checkbox" checked={!!layer.in_place} onChange={(e) => commit((l) => ({ ...l, in_place: e.target.checked || undefined }))} />
            In place (no travel)
          </label>
          <fieldset>
            <legend>Smoothing (steadies jitter, e.g. from video)</legend>
            {ready.groups.map(([g]) => (
              <label key={g} className="smooth-row">
                <span>{g}</span>
                <Slider value={smoothOf(g)} label={`Smooth ${g}`} onCommit={(x) => setSmooth(g, x)} />
              </label>
            ))}
          </fieldset>
        </div>
      </details>
      <div className="row">
        <button disabled={busy || !hist.h?.past.length} onClick={hist.undo}>
          Undo
        </button>
        <button disabled={busy || !hist.h?.future.length} onClick={hist.redo}>
          Redo
        </button>
      </div>
      <div className="row">
        <button
          className="primary"
          disabled={busy || !ready || !hist.h?.past.length}
          title="Saves what changed since this version was opened; with every edit undone or the last copy deleted, the base comes back as it was"
          onClick={() =>
            run(async () => {
              // what changed since the load is what to save, also when nothing is left edited: the step wants a
              // non-empty layer and starts from the base, so one base clip's empty layer is that reset (UI-002).
              // The editor closes on a new version only; a refused or failed save keeps the edits (UI-001)
              const clips = edited.length ? Object.fromEntries(edited.map((c) => [c, layers[c]])) : { [Object.keys(ready!.clips)[0]]: {} };
              if (await props.onSave(clips)) props.onClose();
            })
          }
        >
          Save as a new version
        </button>
        <button disabled={busy} onClick={() => leave() && props.onClose()}>
          Close
        </button>
        {dirty && <span className="muted">Unsaved changes</span>}
      </div>
      {edited.length > 0 && <p className="muted">Edited: {edited.join(", ")}. The original animation stays as it is.</p>}
      <KeyList rows={keyRows} selected={sel} curves={curves} onSelect={onSelectKeys} onSeek={seekBase} onMove={moveKeys} onCurve={onCurve} />
      {document.getElementById("timeline-slot") &&
        createPortal(
          <EditorTimeline
            viewer={v}
            frames={F}
            trim={trim}
            baseFrame={baseFrame}
            rows={rows}
            spans={spans}
            curves={curves}
            selected={sel}
            onFrame={setFrame}
            onSeek={seekBase}
            onSelect={onSelectKeys}
            onMove={moveKeys}
            onCurve={onCurve}
            onTrim={(t) => commit((l) => ({ ...l, trim: t[0] === 0 && t[1] === F - 1 ? undefined : t }))}
            onRow={(id) => {
              if (!id.startsWith("g:")) return pick(id.endsWith(":move") ? id.slice(0, -5) : id, id.endsWith(":move"));
              const g = id.slice(2);
              setOpen((o) => new Set(o.has(g) ? [...o].filter((x) => x !== g) : [...o, g]));
            }}
            tools={
              <>
                <div role="group" aria-label="Timeline view" className="tb-section">
                  <span className="tb-head">Timeline</span>
                  <button aria-pressed={!curvesOn} onClick={() => setCurvesOn(false)}>
                    Keys
                  </button>
                  <button aria-pressed={curvesOn} disabled={!bone} title={bone ? "" : "Select a bone first"} onClick={() => setCurvesOn(true)}>
                    Curves
                  </button>
                </div>
                <div role="group" aria-label="Show in the view" className="tb-section">
                  <span className="tb-head">Show</span>
                  <label className="check" title="The selected bone's track over the clip">
                    <input type="checkbox" checked={path} onChange={(e) => setPath(e.target.checked)} />
                    Motion path
                  </label>
                  {path && !bone && <span className="muted">select a joint</span>}
                  <label className="check" title="Ghosts of the model a few frames before (blue) and after (green)">
                    <input type="checkbox" checked={onion} onChange={(e) => setOnion(e.target.checked)} />
                    Onion skin
                  </label>
                </div>
              </>
            }
          />,
          document.getElementById("timeline-slot")!,
        )}
    </div>
  );
}

// a smoothing slider: it moves freely, the layer changes once, on release (one undo step, one evaluation)
function Slider(p: { value: number; label: string; onCommit: (x: number) => void }) {
  const [x, setX] = useState<number | null>(null);
  const done = () => x !== null && (x !== p.value && p.onCommit(x), setX(null));
  return (
    <>
      <input type="range" min={0} max={4} step={0.5} aria-label={p.label} value={x ?? p.value} onChange={(e) => setX(+e.target.value)} onPointerUp={done} onKeyUp={done} onBlur={done} />
      <span>{(x ?? p.value) ? `${x ?? p.value} frames` : "off"}</span>
    </>
  );
}

// the transport and the dope sheet under the view; the playhead follows the viewer every animation frame
function EditorTimeline(p: {
  viewer: Viewer;
  frames: number;
  trim: [number, number];
  baseFrame: () => number;
  rows: Row[];
  spans: Record<string, [number, number][]>;
  curves: Curves | null;
  selected: string[];
  tools: ReactNode;
  onFrame: (f: number) => void;
  onSeek: (f: number) => void;
  onSelect: (keys: string[], add: boolean) => void;
  onMove: (df: number) => void;
  onCurve: (id: string, line: number, value: number) => void;
  onTrim: (t: [number, number]) => void;
  onRow: (id: string) => void;
}) {
  useFrame();
  const f = p.baseFrame();
  const last = useRef(-1);
  useEffect(() => {
    if (f !== last.current) {
      last.current = f;
      p.onFrame(f);
    }
  });
  return (
    <>
      <Transport viewer={p.viewer}>
        <span className="grow" />
        {p.tools}
      </Transport>
      <DopeSheet
        frames={p.frames}
        frame={f}
        trim={p.trim}
        rows={p.rows}
        spans={p.spans}
        curves={p.curves}
        selected={p.selected}
        onFrame={p.onSeek}
        onSelect={p.onSelect}
        onMove={p.onMove}
        onCurve={p.onCurve}
        onTrim={p.onTrim}
        onRow={p.onRow}
      />
    </>
  );
}
