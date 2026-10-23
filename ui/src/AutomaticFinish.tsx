import { useEffect, useRef, useState, type ReactElement } from "react";
import { fileUrl, type Meta } from "./api";
import { Compare } from "./Compare";
import { onEvent } from "./events";
import { multiViewApi, type PaintRecipe, type PaintSession } from "./multi-view-api";

type Props = Readonly<{ asset: string; version: Meta; versions: readonly Meta[]; selectionSource: string | null; authoringSession: PaintSession | null; authoringDirty: boolean }>;

export function AutomaticFinish(props: Props): ReactElement {
  const [sessions, setSessions] = useState<readonly PaintSession[]>([]);
  const [current, setCurrent] = useState<PaintSession | null>(null);
  const [model, setModel] = useState<"fibo2-turbo" | "krea-genesis">("fibo2-turbo");
  const [selectionSource, setSelectionSource] = useState("");
  const [protectedFaces, setProtectedFaces] = useState("");
  const [budget, setBudget] = useState(3);
  const [correction, setCorrection] = useState(true);
  const [seed, setSeed] = useState(24060);
  const [denoise, setDenoise] = useState(0.35);
  const [conditioning, setConditioning] = useState<PaintRecipe["conditioning"]>("preserve_structure");
  const [instruction, setInstruction] = useState("");
  const [appearance, setAppearance] = useState<Pick<PaintRecipe, "materials" | "style" | "preserve">>({
    materials: "", style: "", preserve: "Keep captured material and architecture.",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [compare, setCompare] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const key = `effigy:automatic-finish:${props.asset}`;
  const locked = busy || !!current?.active;
  const finish = current?.finishing;
  const preview = props.versions.find((v) => v.version === finish?.preview);
  const source = props.versions.find((v) => v.version === current?.source);

  const accept = (value: PaintSession): void => {
    setCurrent(value);
    setSessions((old) => [...old.filter((s) => s.id !== value.id), value]);
    try { localStorage.setItem(key, value.id); }
    catch (failure: unknown) { console.warn("Could not remember finishing session", failure); }
  };
  const perform = (operation: () => Promise<void>): void => {
    setBusy(true); setError("");
    void operation().catch((failure: unknown) => { console.error("Finishing failed", failure); setError(String(failure)); })
      .finally(() => { setBusy(false); });
  };
  useEffect(() => {
    let live = true;
    void multiViewApi.list(props.asset).then((all) => {
      if (!live) return;
      const saved = all.filter((s) => s.purpose === "finish");
      setSessions(saved);
      const remembered = localStorage.getItem(key);
      setCurrent(saved.find((s) => s.id === remembered) ?? saved.filter((s) => s.source === props.version.version).at(-1) ?? null);
    }).catch((failure: unknown) => { if (live) setError(String(failure)); });
    return () => { live = false; };
  }, [props.asset, key]);
  useEffect(() => {
    if (!current?.active) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const id = current.id, job = current.active.job;
    const refresh = async (): Promise<void> => {
      try {
        const next = await multiViewApi.get(props.asset, id);
        if (stopped) return;
        setCurrent(next);
        const message = await multiViewApi.progress(job).catch(() => "Reopened saved finishing work.");
        if (stopped) return;
        setStatus(message);
        if (next.active) timer = setTimeout(() => { void refresh(); }, 2000);
        else setSessions((old) => [...old.filter((s) => s.id !== next.id), next]);
      } catch (failure: unknown) {
        if (!stopped) setError(`Could not refresh finishing: ${String(failure)}. Reload the saved pass after the server returns.`);
      }
    };
    void refresh();
    return () => { stopped = true; if (timer !== undefined) clearTimeout(timer); };
  }, [props.asset, current?.id, current?.active?.job]);
  useEffect(() => {
    if (compare) dialog.current?.showModal(); else dialog.current?.close();
  }, [compare]);
  useEffect(() => {
    if (!current) return;
    let live = true;
    const id = current.id;
    const unsubscribe = onEvent((event: string, data: unknown) => {
      if (typeof data !== "object" || data === null) return;
      const reconnect = event === "connection" && "ok" in data && data.ok === true;
      const relatedJob = event === "job" && "asset_id" in data && data.asset_id === props.asset;
      if (!reconnect && !relatedJob) return;
      void multiViewApi.get(props.asset, id).then((next) => {
        if (!live) return;
        setCurrent((previous) => previous?.id === next.id && previous.revision <= next.revision ? next : previous);
        setSessions((old) => [...old.filter((s) => s.id !== next.id), next]);
      }).catch((failure: unknown) => { if (live) setError(`Could not refresh finishing state: ${String(failure)}`); });
    });
    return () => { live = false; unsubscribe(); };
  }, [props.asset, current?.id]);

  const plan = (): void => perform(async () => {
    const faces = protectedFaces.trim() ? protectedFaces.trim().split(/[\s,]+/).map(Number) : [];
    if (faces.some((value) => !Number.isSafeInteger(value) || value < 0)) throw new Error("Protected faces need non-negative triangle IDs");
    if (!Number.isSafeInteger(seed) || seed < 0) throw new Error("Choose a non-negative integer seed");
    const recipe: PaintRecipe = { ...appearance, model, prompt: instruction,
      seed, denoise, conditioning, style_image: null, feather: 0, moss_steps: 8 };
    let created = await multiViewApi.create(props.asset, props.version.version, recipe, window.__viewer?.view().yaw ?? 0, null,
      { strategy: "whole_sheet", panel_size: 512, ...(selectionSource ? { selection_source: selectionSource } : {}) });
    const authoring = props.authoringSession?.authoring;
    if (authoring) {
      if (created.geometry_revision !== props.authoringSession?.geometry_revision) throw new Error("The saved material regions belong to different geometry. Select its prepared mesh before finishing.");
      const profile = authoring.profile;
      created = await multiViewApi.saveAuthoring(props.asset, created, { ...profile, method: "generated", operation: "refine_current",
        preparation: { ...profile.preparation, source: created.source, geometry_revision: created.geometry_revision },
        sources: [...profile.sources.filter((s) => s.role !== "working"), { role: "working", version: created.source, note: "Explicit finishing source" }],
        submission_budget: budget + (correction ? 1 : 0) });
    }
    accept(await multiViewApi.action(props.asset, created.id, { revision: created.revision, action: "finish_plan",
      finish_options: { max_patches: budget, correction_budget: correction ? 1 : 0, protected_faces: faces } }));
  });
  const action = (name: "finish" | "finish_apply"): void => {
    if (!current) return;
    perform(async () => { accept(await multiViewApi.action(props.asset, current.id, { revision: current.revision, action: name })); });
  };
  const newPass = (): void => {
    if (locked) return;
    if (!current) { setError(""); setStatus(""); return; }
    const recipe = current.recipe;
    if (recipe.model !== "fibo2-turbo" && recipe.model !== "krea-genesis") {
      setError("This recipe is not supported by automatic finishing."); return;
    }
    setModel(recipe.model); setInstruction(recipe.prompt); setSeed(recipe.seed);
    setDenoise(recipe.denoise); setConditioning(recipe.conditioning);
    setAppearance({ materials: recipe.materials, style: recipe.style, preserve: recipe.preserve });
    setSelectionSource(current.finishing?.plan ?? current.mask_version ?? current.selection_source ?? "");
    setProtectedFaces(""); setError(""); setCurrent(null);
    setStatus("Copied the model, appearance, seed and saved paint permission. The saved mask must match this mesh.");
  };
  return <details className="multi-view-paint">
    <summary>Finish seams automatically</summary>
    <p>Plan visible joins, repair them from the latest assembled mesh, then review one finished draft. Full captured views provide context; only the permitted surface changes.</p>
    {props.authoringSession?.authoring && !current && <p>Copies the saved material regions, sampling floor and appearance contract. This new pass allows at most {budget + (correction ? 1 : 0)} model calls. It keeps the selected source immutable.</p>}
    {error && <p role="alert">{error}</p>}
    {current?.error && <p role="alert">Last attempt: {current.error}</p>}
    <label>Saved finishing pass<select disabled={locked} value={current?.id ?? ""} onChange={(event) => {
      const selected = sessions.find((s) => s.id === event.target.value);
      if (selected) accept(selected); else newPass();
    }}><option value="">New pass from {props.version.version}</option>
      {sessions.map((s) => <option key={s.id} value={s.id}>{s.source} / {s.recipe.model} / {s.id.slice(0, 6)}</option>)}
    </select></label>
    <div className="row"><button disabled={locked} onClick={newPass}>New pass from this mesh</button>
      <button disabled={busy} onClick={() => { perform(async () => {
        const all = (await multiViewApi.list(props.asset)).filter((s) => s.purpose === "finish");
        setSessions(all);
        const saved = all.find((s) => s.id === current?.id);
        if (saved) accept(saved);
      }); }}>Reload finishing passes</button></div>
    {current && <p>Fixed source: <a href={`#/asset/${props.asset}?version=${current.source}`}>{current.source}</a>. Repairs remain a draft until Apply.</p>}
    {!current && <>
      <label>Repair model<select value={model} disabled={locked} onChange={(event) => {
        if (event.target.value === "fibo2-turbo" || event.target.value === "krea-genesis") setModel(event.target.value);
      }}><option value="fibo2-turbo">FIBO2 Edit Turbo INT8 - 4 steps</option><option value="krea-genesis">Krea2 Genesis NVFP4 - 8 steps</option></select></label>
      <label>Permitted surface<select value={selectionSource} disabled={locked} onChange={(event) => setSelectionSource(event.target.value)}>
        <option value="">All supported surfaces</option>{props.versions.filter((v) => !!v.outputs.mask).map((v) =>
          <option key={v.version} value={v.version}>{v.label || v.version}</option>)}
      </select></label>
      <button disabled={locked || !props.selectionSource} onClick={() => setSelectionSource(props.selectionSource ?? "")}>Use the current multi-view selection</button>
      <label>Protected triangle IDs<input value={protectedFaces} disabled={locked} onChange={(event) => setProtectedFaces(event.target.value)} placeholder="Optional, comma-separated" /></label>
      <div className="row"><label>Patch budget<select value={budget} disabled={locked} onChange={(event) => setBudget(Number(event.target.value))}>
        {[1, 2, 3].map((count) => <option key={count} value={count}>{count}</option>)}</select></label>
        <label>Seed<input type="number" min="0" step="1" value={seed} disabled={locked} onChange={(event) => setSeed(Number(event.target.value))} /></label></div>
      <label><input type="checkbox" checked={correction} disabled={locked} onChange={(event) => setCorrection(event.target.checked)} />Allow one diagnosed correction for the entire pass</label>
      {model === "krea-genesis" && <label>Denoise: {denoise.toFixed(2)}<input type="range" min="0.1" max="0.75" step="0.05" value={denoise} disabled={locked} onChange={(event) => setDenoise(Number(event.target.value))} /></label>}
      {model === "fibo2-turbo" && <label>Repair guidance<select value={conditioning} disabled={locked} onChange={(event) => {
        if (event.target.value === "preserve_structure" || event.target.value === "blank_region") setConditioning(event.target.value);
      }}><option value="preserve_structure">Keep existing forms</option><option value="blank_region">Rebuild damaged detail</option></select></label>}
      <label>Optional repair direction<textarea value={instruction} disabled={locked} onChange={(event) => setInstruction(event.target.value)} placeholder="Leave blank to match the captured materials and brushwork." /></label>
      <button className="mv-primary" disabled={locked || props.authoringDirty || !props.version.outputs.mesh} onClick={plan}>1. Plan seam repairs</button>
      {props.authoringDirty && <p>Save the authoring contract before planning a new finishing pass.</p>}
      {!props.version.outputs.mesh && <p>Select a saved mesh version first.</p>}
    </>}
    {current?.active && <div role="status"><p>{status || current.active.action}</p><button onClick={() => {
      const job = current.active?.job;
      if (job) perform(async () => { await multiViewApi.cancel(job); accept(await multiViewApi.get(props.asset, current.id)); });
    }}>Cancel finishing</button></div>}
    {finish && <>
      <img className="mv-review" src={fileUrl(props.asset, finish.plan, "review.png")} alt="Automatically planned repair cameras and green permitted regions" />
      <p><a href={fileUrl(props.asset, finish.plan, "plan.json")} target="_blank" rel="noreferrer">View coverage and unresolved regions</a>. Camera frames stay fixed. Each repair sees the latest draft; no model switching or soft overlap blend.</p>
      {finish.progress && <p>{finish.progress.stage}: {finish.progress.completed} completed, {finish.progress.retained} technically retained, {finish.progress.rejected} rejected, {finish.progress.corrections} correction used.</p>}
      <button className="mv-primary" disabled={locked || !!finish.preview} onClick={() => action("finish")}>
        {finish.run && !finish.preview ? "2. Resume automatic finishing" : "2. Run automatic finishing"}</button>
      {finish.preview && <>
        <p>Draft complete. Numeric checks retain or reject obvious regressions; inspect material continuity before applying.</p>
        {finish.unaddressed_pairs !== null && <p>{finish.unaddressed_pairs} detected seam pairs remain unaddressed; {finish.unreachable_pairs ?? 0} pairs were unreachable. A retained repair still needs visual review.</p>}
        <a href={fileUrl(props.asset, finish.preview, "finish.json")} target="_blank" rel="noreferrer">Inspect repair decisions and measurements</a>
        <img className="mv-review" src={fileUrl(props.asset, finish.preview, "review.png")} alt="Finished draft viewed around the entire mesh" />
        <div className="row"><button onClick={() => { window.location.hash = `/asset/${props.asset}?version=${finish.preview}`; }}>Review draft in 3D</button>
          <button disabled={!preview || !source} onClick={() => setCompare(true)}>Compare before and after</button>
          <a href={fileUrl(props.asset, finish.preview, "turntable.gif")} target="_blank" rel="noreferrer">Open 360 review</a></div>
        <button className="mv-primary" disabled={locked || !!finish.applied || finish.progress?.retained === 0} onClick={() => action("finish_apply")}>3. Apply finished texture</button>
        {finish.progress?.retained === 0 && <p>No repair was retained. The source is unchanged; there is nothing to apply.</p>}
        {finish.applied && <p>Applied: <a href={`#/asset/${props.asset}?version=${finish.applied}`}>{finish.applied}</a>. Source remains unchanged.</p>}
      </>}
    </>}
    <dialog className="mv-compare-dialog" ref={dialog} aria-label="Compare finishing draft" onCancel={() => setCompare(false)}>
      {compare && preview && source && <Compare asset={props.asset} versions={[...props.versions]} shown={preview} other={source} onClose={() => setCompare(false)} />}
    </dialog>
  </details>;
}
