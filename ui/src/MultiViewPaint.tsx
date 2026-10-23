import { useEffect, useRef, useState, type ReactElement } from "react";
import { api, fileUrl, waitJob, type Meta } from "./api";
import { onEvent } from "./events";
import { Compare } from "./Compare";
import { LocalRuntimeStatus } from "./LocalRuntimeStatus";
import { AutomaticFinish } from "./AutomaticFinish";
import { AuthoringWorkspace } from "./AuthoringWorkspace";
import { MaskEditor, type Selection } from "./PaintSelection";
import { multiViewApi, type PaintAction, type PaintRecipe, type PaintSession } from "./multi-view-api";
import "./multi-view-paint.css";

type Props = Readonly<{ asset: string; version: Meta; versions: readonly Meta[] }>;
const EMPTY_SELECTION: Selection = { mode: "brush", strokes: [] };
const INITIAL_RECIPE: PaintRecipe = { model: "fibo2-turbo", prompt: "", materials: "", style: "", preserve: "Keep the mesh silhouette, camera framing and material boundaries unchanged.",
  seed: 24031, denoise: 0.35, conditioning: "preserve_structure", style_image: null, feather: 0, moss_steps: 8 };

export function MultiViewPaint(props: Props): ReactElement | null {
  const [enabled, setEnabled] = useState(false);
  const [sessions, setSessions] = useState<readonly PaintSession[]>([]);
  const [current, setCurrent] = useState<PaintSession | null>(null);
  const [recipe, setRecipe] = useState<PaintRecipe>(INITIAL_RECIPE);
  const [dirty, setDirty] = useState(false);
  const [authoringDirty, setAuthoringDirty] = useState(false);
  const [authoringBusy, setAuthoringBusy] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [viewId, setViewId] = useState("v00");
  const [selection, setSelection] = useState<Selection>(EMPTY_SELECTION);
  const [selectedGroups, setSelectedGroups] = useState<readonly string[]>([]);
  const [facesText, setFacesText] = useState("");
  const [initialPick, setInitialPick] = useState<"off" | "add" | "remove">("off");
  const [groupDrafts, setGroupDrafts] = useState<Readonly<Record<string, string>>>({});
  const [compare, setCompare] = useState<readonly string[]>([]);
  const [compareOpen, setCompareOpen] = useState(false);
  const compareDialog = useRef<HTMLDialogElement>(null);
  const [showSheetMask, setShowSheetMask] = useState(false);
  const [panelSize, setPanelSize] = useState(192);
  const key = `effigy:multi-view:${props.asset}`;
  const paintingBusy = busy || current?.active !== null && current?.active !== undefined;
  const locked = paintingBusy || authoringBusy;
  const canSelect = selection.mode === "all" || selection.strokes.length > 0 || !!selection.faces?.ids.length;

  const accept = (next: PaintSession, loadRecipe = false): void => {
    setCurrent(next);
    setSessions((previous) => [...previous.filter((s) => s.id !== next.id), next]);
    if (loadRecipe) { setRecipe(next.recipe); setDirty(false); }
    try { localStorage.setItem(key, next.id); }
    catch (failure: unknown) { console.error("Could not remember paint session", failure); }
  };
  const perform = (operation: () => Promise<void>): void => {
    setBusy(true); setError("");
    void operation().catch((failure: unknown) => { console.error("Multi-view painting failed", failure); setError(String(failure)); }).finally(() => { setBusy(false); });
  };

  useEffect(() => {
    let active = true;
    void multiViewApi.enabled().then(async (available) => {
      if (!active || !available) return;
      setEnabled(true);
      const all = (await multiViewApi.list(props.asset)).filter((s) => s.purpose !== "finish");
      if (!active) return;
      setSessions(all);
      const id = localStorage.getItem(key);
      const chosen = all.find((s) => s.id === id) ?? all.at(-1);
      if (chosen) { setCurrent(chosen); setRecipe(chosen.recipe); return; }
      const existing = await api.asset(props.asset);
      if (!active || !existing.asset.appearance) return;
      const appearance = existing.asset.appearance;
      setRecipe({ ...INITIAL_RECIPE, materials: appearance.materials, style: appearance.style, preserve: appearance.preserve,
        model: appearance.model === "krea-genesis" ? "krea-genesis" : "fibo2-turbo" });
    }).catch((failure: unknown) => { if (active) setError(String(failure)); });
    return () => { active = false; };
  }, [props.asset, key]);

  useEffect(() => {
    if (!current || dirty) return;
    setRecipe(current.recipe);
  }, [current, dirty]);

  useEffect(() => {
    if (!compareOpen) { compareDialog.current?.close(); return; }
    compareDialog.current?.showModal();
  }, [compareOpen]);

  useEffect(() => {
    if (!current?.active) return;
    let stopped = false;
    let timeout: ReturnType<typeof setTimeout> | undefined;
    const id = current.id, job = current.active.job, action = current.active.action;
    const refresh = async (): Promise<void> => {
      try {
        const [next, progress] = await Promise.all([multiViewApi.get(props.asset, id), multiViewApi.progress(job).catch((failure: unknown) => {
          console.warn("Previous job status unavailable", failure); return "Reopened saved painting session.";
        })]);
        if (stopped) return;
        setCurrent(next); setStatus(progress);
        if (!next.active) setSessions((previous) => [...previous.filter((s) => s.id !== next.id), next]);
        if (!next.active && !next.error && action === "preview" && next.preview) {
          window.location.hash = `/asset/${props.asset}?version=${next.preview}`;
        }
        if (!next.active && !next.error && action === "apply" && next.applied) {
          window.location.hash = `/asset/${props.asset}?version=${next.applied}`;
        }
        if (next.active) timeout = setTimeout(() => { void refresh(); }, 2000);
      } catch (failure: unknown) {
        if (!stopped) setError(`Could not refresh the session: ${String(failure)}. Reload when the server is available.`);
      }
    };
    void refresh();
    return () => { stopped = true; if (timeout !== undefined) clearTimeout(timeout); };
  }, [props.asset, current?.id, current?.active?.job]);

  useEffect(() => {
    if (!current || current.active) return;
    let active = true;
    void multiViewApi.get(props.asset, current.id).then((next) => {
      if (active) setCurrent(next);
    }).catch((failure: unknown) => { if (active) setError(String(failure)); });
    return () => { active = false; };
  }, [props.asset, current?.id, props.versions.length]);

  useEffect(() => {
    if (!current) return;
    let active = true;
    const id = current.id;
    const unsubscribe = onEvent((event: string, data: unknown) => {
      if (typeof data !== "object" || data === null) return;
      const reconnect = event === "connection" && "ok" in data && data.ok === true;
      const assetJob = event === "job" && "asset_id" in data && data.asset_id === props.asset;
      if (!reconnect && !assetJob) return;
      void multiViewApi.get(props.asset, id).then((next) => {
        if (!active) return;
        setCurrent((previous) => previous?.id === next.id && previous.revision <= next.revision ? next : previous);
        setSessions((previous) => [...previous.filter((session) => session.id !== next.id), next]);
      }).catch((failure: unknown) => { if (active) setError(`Could not refresh painting progress: ${String(failure)}`); });
    });
    return () => { active = false; unsubscribe(); };
  }, [props.asset, current?.id]);

  useEffect(() => {
    if (current || busy || initialPick === "off") return;
    const viewer = window.__viewer;
    if (!viewer) { setError("Open the mesh before selecting its faces."); return; }
    const ids = facesText.trim() ? facesText.split(/[\s,]+/).map(Number) : [];
    if (ids.some((id) => !Number.isSafeInteger(id) || id < 0)) return;
    const problem = viewer.setPaintFaces(ids, (id) => {
      const next = new Set(ids);
      if (initialPick === "remove") next.delete(id); else next.add(id);
      setFacesText([...next].sort((a, b) => a - b).join(", "));
    });
    if (problem) setError(problem);
    return () => { viewer.setPaintFaces([], null); };
  }, [current, busy, initialPick, facesText, props.version.version]);

  if (!enabled) return null;
  const view = current?.views.find((v) => v.id === viewId) ?? current?.views[0];
  const ready = !!current?.capture;
  const whole = current?.strategy !== "pairs";
  const maskRefreshNeeded = ready && whole && current?.permission_projection !== "same_face_all_selected_v2";
  const pending = current?.groups.filter((g) => !current.excluded.includes(g.id) && !current.results[g.id]?.valid) ?? [];
  const inputReady = !![recipe.materials, recipe.style, recipe.prompt].join("").trim();
  const generationReason = locked ? "A painting operation is running." : !ready ? "Capture a view set first." : dirty ? "Save the changed recipe first."
    : authoringDirty ? "Save the authoring contract first."
    : current?.authoring?.profile.method !== undefined && current.authoring.profile.method !== "generated" ? "Use Build masked reconstruction in Surface authoring for this method."
    : current?.authoring && current.sampling_profile_revision !== current.authoring.revision ? "Refresh camera masks for the saved authoring contract."
    : current?.authoring?.profile.sampling.mode === "detail" && !current.sampling?.detail_admitted ? "Capture is undersampled. Select a smaller surface region, or explicitly choose a style study."
    : maskRefreshNeeded ? "Refresh the saved camera masks before generating." : current?.limitation ? current.limitation : Object.keys(groupDrafts).length ? "Save the instructions first." : !inputReady ? "Describe the materials or requested change." : "";
  const previewReason = locked ? "A painting operation is running." : authoringDirty ? "Save the authoring contract first." : dirty ? "Save the changed recipe first." : Object.keys(groupDrafts).length ? "Save the pair instructions first." : !ready ? "Capture a view set first." : pending.length ? `Generate or exclude ${pending.length} remaining groups.` : "";
  const applyReason = locked ? "A painting operation is running." : authoringDirty ? "Save the authoring contract first." : dirty ? "Save the changed recipe and rebuild the preview." : Object.keys(groupDrafts).length ? "Save the pair instructions and rebuild the preview." : !current?.preview ? "Build and review a combined preview first." : current.applied_preview === current.preview ? `Already applied as ${current.applied}. Open the existing version below.` : "";
  const act = (action: PaintAction, extra: Partial<Parameters<typeof multiViewApi.action>[2]> = {}): void => {
    if (!current) return;
    perform(async () => { accept(await multiViewApi.action(props.asset, current.id, { revision: current.revision, action, ...extra })); setSelection(EMPTY_SELECTION); });
  };
  const editRecipe = (changes: Partial<PaintRecipe>): void => { setRecipe((value) => ({ ...value, ...changes })); setDirty(true); };
  const openVersion = (version: string): void => { window.location.hash = `/asset/${props.asset}?version=${version}`; };
  const comparisonCandidates = sessions.filter((s) => s.source === current?.source && s.strategy !== "pairs")
    .flatMap((s) => s.candidates.filter((c) => c.status === "complete").map((candidate) => ({ session: s, candidate })));
  const comparedMeshes = comparisonCandidates.filter(({ candidate }) => compare.includes(candidate.id))
    .map(({ candidate }) => props.versions.find((version) => version.version === candidate.preview))
    .filter((version): version is Meta => version !== undefined);
  const reuseCapture = async (): Promise<void> => {
    if (!current) throw new Error("Choose a captured session first");
    if (authoringDirty) throw new Error("Save the authoring contract before creating a comparison");
    const strategy = recipe.model === "syncmvd" ? "synchronized" : "whole_sheet";
    const size = recipe.model === "moss-turbo" && current.strategy !== "pairs" ? current.panel_size : 512;
    let next = await multiViewApi.create(props.asset, current.source, recipe, view?.view.yaw ?? 0, null,
      current.strategy === "pairs" || size !== current.panel_size
        ? { strategy, panel_size: size, ...(current.mask_version ? { selection_source: current.mask_version } : {}) }
        : { strategy, panel_size: size, reuse_session: current.id });
    if (current.authoring) next = await multiViewApi.saveAuthoring(props.asset, next, current.authoring.profile);
    accept(next, true); setSelectedGroups([]); setGroupDrafts({});
  };

  return <><AutomaticFinish asset={props.asset} version={props.version} versions={props.versions} selectionSource={current?.mask_version ?? null} authoringSession={current} authoringDirty={authoringDirty} />
    {current && <AuthoringWorkspace key={`${props.asset}:${current.id}`} asset={props.asset} displayedVersion={props.version.version} current={current} versions={props.versions} locked={paintingBusy} onChange={accept} onDirtyChange={setAuthoringDirty} onBusyChange={setAuthoringBusy} />}
    <details className="multi-view-paint" open>
    <summary>Multi-view paint</summary>
    <p>Select mesh regions once, generate with context across the complete view set, then review and apply one protected texture.</p>
    <ol className="mv-stages"><li>1. Select &amp; capture</li><li>2. Generate complete view set</li><li>3. Review &amp; apply</li></ol>
    {error && <p role="alert">{error}</p>}
    {authoringBusy && <p role="status">Surface authoring is busy. Finish or cancel preparation before changing the painting session.</p>}
    {current?.error && <p role="alert">Last attempt: {current.error}</p>}
    {current?.limitation && <p role="alert">{current.limitation}. Create a new comparison session to use a newly supported layout; historical sessions remain fixed.</p>}
    <div className="row">
      <label>Saved painting session<select disabled={locked || dirty || authoringDirty} value={current?.id ?? ""} onChange={(event) => {
        const id = event.target.value;
        if (!id) { setCurrent(null); setSelectedGroups([]); setGroupDrafts({}); return; }
        const cached = sessions.find((s) => s.id === id);
        if (cached) accept(cached, true);
        perform(async () => { accept(await multiViewApi.get(props.asset, id), true); setSelectedGroups([]); setGroupDrafts({}); setSelection(EMPTY_SELECTION); });
      }}><option value="">New session from {props.version.version}</option>{sessions.map((s) => <option key={s.id} value={s.id}>{props.versions.find((v) => v.version === s.capture)?.label ?? s.source} / {s.recipe.model} / {s.id.slice(0, 6)}</option>)}</select></label>
      {current && <button disabled={locked || dirty || authoringDirty} onClick={() => { setCurrent(null); setSelectedGroups([]); setGroupDrafts({}); setSelection(EMPTY_SELECTION); }}>New session from this mesh</button>}
      <button disabled={locked || dirty || Object.keys(groupDrafts).length > 0} onClick={() => { perform(async () => {
        const all = (await multiViewApi.list(props.asset)).filter((s) => s.purpose !== "finish");
        setSessions(all);
        const refreshed = all.find((s) => s.id === current?.id);
        if (refreshed) accept(refreshed, true);
      }); }}>Reload sessions</button>
    </div>
    {current && <p>Fixed source: <a href={`#/asset/${props.asset}?version=${current.source}`}>{current.source}</a>. This session never overwrites that version.</p>}
    {current && <p>Generation strategy: {current.strategy === "pairs" ? "Historical paired sheets" : current.strategy === "synchronized" ? "Shared-texture synchronized diffusion" : "One complete fixed view sheet"}.</p>}
    <details open={!current}><summary>Shared appearance and model</summary>
      <label>Model<select disabled={locked} value={recipe.model} onChange={(event) => {
        const model = event.target.value;
        if (model !== "fibo2-turbo" && model !== "krea-genesis" && model !== "moss-turbo" && model !== "syncmvd") return;
        editRecipe({ model, style_image: null, ...(!current && model === "moss-turbo" ? { moss_steps: panelSize === 192 ? 4 : panelSize === 256 ? 6 : 8 } : {}) });
      }}><option value="fibo2-turbo">FIBO 2 Edit Turbo</option><option value="krea-genesis">Krea2 Genesis (NVFP4 weights)</option>
        <option value="moss-turbo">MOSS Turbo v2 - experimental image-to-image</option><option value="syncmvd">SyncMVD - synchronized normal conditioning</option></select></label>
      {recipe.model === "moss-turbo" && <>
        <label>Pixels per camera view<select value={current?.panel_size ?? panelSize} disabled={locked || !!current} onChange={(event) => {
          const size = Number(event.target.value);
          if (![192, 256, 384, 512].includes(size)) return;
          setPanelSize(size); editRecipe({ moss_steps: size === 192 ? 4 : size === 256 ? 6 : 8 });
        }}><option value={192}>192 - fast whole-set draft</option><option value={256}>256 - balanced draft</option><option value={384}>384 - more detail</option><option value={512}>512 - original comparison</option></select></label>
        {current && <p className="muted">Camera size is fixed for this session. Start a new session to change it; existing results remain available.</p>}
        <label>MOSS sampling steps<select value={recipe.moss_steps} disabled={locked} onChange={(event) => {
          const steps = Number(event.target.value);
          if (steps !== 4 && steps !== 6 && steps !== 8) return;
          editRecipe({ moss_steps: steps });
        }}><option value={4}>4 - sheets near 1024 square</option><option value={6}>6 - medium sheets</option><option value={8}>8 - larger sheets</option></select></label>
      </>}
      <label>Materials<textarea rows={3} value={recipe.materials} disabled={locked} onChange={(event) => { editRecipe({ materials: event.target.value }); }} /></label>
      <label>Painted style<textarea rows={2} value={recipe.style} disabled={locked} onChange={(event) => { editRecipe({ style: event.target.value }); }} /></label>
      <label>Keep unchanged<textarea rows={2} value={recipe.preserve} disabled={locked} onChange={(event) => { editRecipe({ preserve: event.target.value }); }} /></label>
      <label>{recipe.model === "fibo2-turbo" ? "Requested change" : "Describe the resulting painted surfaces"}<textarea rows={4} value={recipe.prompt} disabled={locked} onChange={(event) => { editRecipe({ prompt: event.target.value }); }} /></label>
      {recipe.model === "fibo2-turbo" ? <>
        <label>Editing approach<select value={recipe.conditioning} disabled={locked} onChange={(event) => { editRecipe({ conditioning: event.target.value === "blank_region" ? "blank_region" : "preserve_structure", style_image: null }); }}>
          <option value="preserve_structure">Restyle while retaining captured structure</option><option value="blank_region">Replace selected detail</option>
        </select></label>
        {recipe.conditioning === "preserve_structure" && <label>Optional style reference<select value={recipe.style_image ?? ""} disabled={locked} onChange={(event) => { editRecipe({ style_image: event.target.value || null }); }}>
          <option value="">Use captured appearance</option>{props.versions.filter((v) => v.outputs.image && v.step !== "paint_set").map((v) => <option key={v.version} value={v.version}>{v.label ?? v.version}</option>)}
        </select></label>}
        {props.version.step === "reference" && props.version.outputs.image && <button disabled={locked} onClick={() => {
          editRecipe({ style_image: props.version.version, conditioning: "preserve_structure" });
        }}>Use displayed image as painting reference</button>}
        <p className="muted">Four steps. The complete sheet provides context; exact mask compositing protects unselected pixels. A reference image guides appearance without replacing mesh geometry.</p>
      </> : <>
        <label>Image-to-image strength: {recipe.denoise.toFixed(2)}<input type="range" min="0.1" max="0.8" step="0.05" disabled={locked} value={recipe.denoise} onChange={(event) => { editRecipe({ denoise: Number(event.target.value) }); }} /></label>
        <p className="muted">{recipe.model === "syncmvd" ? "Thirty global updates. All views contribute before each shared texture update; normal conditioning guides structure." :
          recipe.model === "moss-turbo" ? `${recipe.moss_steps} Euler steps with the installed Turbo v2 LoRA and differential masking. Smaller panels trade fine detail for speed; the mesh atlas is unchanged.` :
          "Eight Euler steps with differential masking. Uses the installed Genesis NVFP4 weights; this does not claim native FP4 acceleration."}</p>
      </>}
      <label>Seed<input type="number" min="0" disabled={locked} value={recipe.seed} onChange={(event) => { editRecipe({ seed: Number(event.target.value) }); }} /></label>
      <label>Selection edge blend: {recipe.feather} pixels<input type="range" min="0" max="16" disabled={locked} value={recipe.feather} onChange={(event) => { editRecipe({ feather: Number(event.target.value) }); }} /></label>
      {current && <button disabled={locked || !dirty} onClick={() => { perform(async () => {
        if (recipe.model !== current.recipe.model) { await reuseCapture(); return; }
        accept(await multiViewApi.update(props.asset, current, { recipe }), true);
      }); }}>{recipe.model !== current?.recipe.model ? "Create comparison with selected model" : "Save shared recipe"}</button>}
      {current?.capture && <button disabled={locked} onClick={() => { perform(reuseCapture); }}>
        {current.strategy === "pairs" ? "Start full-view painting from this selection" : "New comparison using these captures"}</button>}
      {dirty && current && <p role="status">Recipe changes invalidate generated groups. Save before generating again.</p>}
    </details>
    {!current && <>
      <p>Choose faces on the mesh before capturing, or leave the selection empty to capture all surfaces.</p>
      <div className="row">
        <button disabled={locked} aria-pressed={initialPick === "add"} onClick={() => { setInitialPick("add"); }}>Add faces on mesh</button>
        <button disabled={locked} aria-pressed={initialPick === "remove"} onClick={() => { setInitialPick("remove"); }}>Remove faces on mesh</button>
        <button disabled={locked || initialPick === "off"} onClick={() => { setInitialPick("off"); }}>Finish face selection</button>
        <button disabled={locked || !facesText} onClick={() => { setFacesText(""); }}>Clear initial selection</button>
      </div>
      <label>Selected triangle IDs (optional; blank selects the whole mesh)<input disabled={locked} value={facesText} onChange={(event) => { setFacesText(event.target.value); }} placeholder="48, 75, 84" /></label>
    </>}
    {!ready && <button className="mv-primary" disabled={locked || !inputReady} onClick={() => {
      perform(async () => {
        let session = current;
        if (!session) {
          const faces = facesText.trim() ? facesText.split(/[\s,]+/).map(Number) : null;
          if (faces?.some((n) => !Number.isSafeInteger(n) || n < 0)) throw new Error("Triangle IDs must be nonnegative whole numbers");
          session = await multiViewApi.create(props.asset, props.version.version, recipe, window.__viewer?.view().yaw ?? 0, faces,
            { strategy: recipe.model === "syncmvd" ? "synchronized" : "whole_sheet", panel_size: recipe.model === "moss-turbo" ? panelSize : 512 });
          accept(session, true);
        }
        accept(await multiViewApi.action(props.asset, session.id, { revision: session.revision, action: "capture" }));
      });
    }}>Capture view set</button>}
    {!inputReady && !ready && <p role="status">Enter a material description or requested change before capturing.</p>}
    {current?.active && <div role="status" className="mv-progress"><p>{status || current.active.action}</p><button onClick={() => { const job = current.active?.job; if (job) perform(async () => { await multiViewApi.cancel(job); accept(await multiViewApi.get(props.asset, current.id)); }); }}>Cancel this batch</button></div>}
    {ready && current && view && <>
      <h4>Shared mesh selection</h4>
      <p>Green means paint here. Mark a region, then add or remove it from the shared selection; every view updates.</p>
      {current.coverage && <p><strong>Saved selection: {current.coverage.selected.toLocaleString()} texture pixels.</strong> Marks and triangle picks below are pending changes to that saved mask.</p>}
      {maskRefreshNeeded && <div role="status">
        <p>These saved camera masks use older edge sampling. Refresh keeps your mesh selection and camera captures, and fixes false holes along triangle edges. Previous images and meshes stay in history; this session will need a new candidate and preview.</p>
        <button disabled={locked} onClick={() => { act("select", { selection_mode: "refresh" }); }}>Refresh camera masks</button>
      </div>}
      {current.mask_overlay && <div className="row">
        <button disabled={props.version.version !== current.source} onClick={() => { perform(async () => {
          if (!window.__viewer || !current.mask_overlay) throw new Error("Open this session's source mesh first");
          await window.__viewer.setAtlasOverlay(fileUrl(props.asset, current.mask_overlay, "selection_atlas.png"));
        }); }}>Show shared mask on mesh</button>
        <button onClick={() => { perform(async () => { await window.__viewer?.setAtlasOverlay(null); }); }}>Show painted material</button>
      </div>}
      <div className="row"><label>Captured camera<select value={view.id} disabled={locked} onChange={(event) => { setViewId(event.target.value); setSelection(EMPTY_SELECTION); }}>
        {current.views.map((v) => <option key={v.id} value={v.id}>{v.id}: yaw {Math.round(v.view.yaw)}, tilt {Math.round(v.view.pitch)} ({v.texels} texels)</option>)}
      </select></label><button disabled={!props.version.outputs.mesh} title={!props.version.outputs.mesh ? "Open the fixed source mesh or a combined preview first" : "Move to this recorded projection camera"}
        onClick={() => { window.__viewer?.restoreCapturedView(view.view); }}>Show this camera on mesh</button></div>
      <MaskEditor key={`${current.id}:${view.id}:${current.mask_version}`} asset={props.asset} revision={current.geometry_revision}
        image={fileUrl(props.asset, current.mask_version ?? "", `overlays/${view.id}.png`)}
        faceImage={fileUrl(props.asset, current.capture ?? "", `faces/${view.id}.png`)} selection={selection} onChange={setSelection} />
      <div className="row">
        <button disabled={locked || !canSelect} onClick={() => { act("select", { view_id: view.id, selection, selection_mode: "add" }); }}>Add marked area</button>
        <button disabled={locked || !canSelect} onClick={() => { act("select", { view_id: view.id, selection, selection_mode: "erase" }); }}>Remove marked area</button>
        <button disabled={locked || !selection.faces?.ids.length} onClick={() => { act("select", { selection, selection_mode: "faces" }); }}>Use these faces only</button>
        <button disabled={locked} onClick={() => { act("select", { selection_mode: "all" }); }}>Select all surfaces</button>
        <button disabled={locked} onClick={() => { act("select", { selection_mode: "clear" }); }}>Clear shared selection</button>
      </div>
      {current.coverage && <p>{current.coverage.visible.toLocaleString()} selected texels visible; {current.coverage.unseen.toLocaleString()} unseen texels stay unchanged.
        {current.coverage.unpaired_views.length > 0 && ` Unpaired cameras: ${current.coverage.unpaired_views.join(", ")}.`}</p>}
      {whole ? <>
        <h4>Generate complete view set</h4>
        <p>One candidate contains every camera in this layout. Regeneration creates another complete candidate; panels from different generations are never mixed.</p>
        {current.groups[0]?.layout && <>
          <p>{current.groups[0].views.length} cameras, {current.groups[0].layout.width} x {current.groups[0].layout.height} context sheet, {current.panel_size} pixels per camera. The mesh atlas stays unchanged.</p>
          <button aria-pressed={showSheetMask} onClick={() => { setShowSheetMask(!showSheetMask); }}>{showSheetMask ? "Show captured colour" : "Show paint permission on sheet"}</button>
          <div className="mv-sheet" style={{ gridTemplateColumns: `repeat(${current.groups[0].layout.width / current.panel_size}, minmax(0, 1fr))` }} aria-label="Exact registered camera sheet">
            {Array.from({ length: current.groups[0].layout.width * current.groups[0].layout.height / current.panel_size ** 2 }, (_, i) => {
              const panel = current.groups[0]?.layout?.panels[i];
              return panel ? <div key={panel.camera_id} title={`${panel.camera_id}: x ${panel.x}, y ${panel.y}`}>
                <img src={fileUrl(props.asset, showSheetMask ? current.mask_version ?? "" : current.capture ?? "", `${showSheetMask ? "overlays" : "views"}/${panel.camera_id}.png`)} alt={`Registered ${panel.camera_id}`} />
                <span>{panel.camera_id}</span></div> : <div key={`blank-${i}`} aria-label="Blank context cell" />;
            })}
          </div>
        </>}
        <div className="row mv-run-actions">
          <button disabled={locked || !current.groups.length} onClick={() => { act("diagnostic"); }}>Check mask projection</button>
          <button className="mv-primary" disabled={!!generationReason || !pending.length} onClick={() => { act("generate"); }}>Generate complete view set</button>
          <button disabled={!!generationReason || !current.groups.length} onClick={() => { act("generate", { regenerate: true }); }}>Generate another complete candidate</button>
        </div>
        {current.diagnostic && <p>Projection diagnostic: <a href={`#/asset/${props.asset}?version=${current.diagnostic}`}>inspect green paint permission on the mesh</a>. This diagnostic cannot be applied as an art candidate.</p>}
        {generationReason && <p role="status">{generationReason}</p>}
        {!generationReason && !pending.length && <p role="status">Current candidate is complete. Build its combined preview or generate another complete candidate.</p>}
        {current.results.complete && <a href={fileUrl(props.asset, current.results.complete.version, "image.png")} target="_blank" rel="noreferrer">
          <img className="mv-review" src={fileUrl(props.asset, current.results.complete.version, "image.png")} alt="Generated complete camera sheet" /></a>}
        <details><summary>Compare complete candidates</summary>
          <p>Select up to two results to compare their baked meshes. Successful generation alone does not establish consistent stone scale or mortar.</p>
          <button disabled={comparedMeshes.length !== 2} title={comparedMeshes.length !== 2 ? "Select two candidates with completed combined bakes." : "Orbit both meshes together at full size."}
            onClick={() => { setCompareOpen(true); }}>Compare baked meshes side by side</button>
          {comparisonCandidates.map(({ session: s, candidate: c }) => <label key={c.id}>
            <input type="checkbox" checked={compare.includes(c.id)} disabled={!compare.includes(c.id) && compare.length >= 2} onChange={(event) => {
              setCompare((previous) => event.target.checked ? [...previous, c.id] : previous.filter((id) => id !== c.id));
            }} />{s.recipe.model} / {c.version} / denoise {c.recipe.denoise}{c.excluded ? " / excluded from Apply" : ""}</label>)}
          <div className="mv-comparison">{comparisonCandidates.filter(({ candidate: c }) => compare.includes(c.id)).map(({ session: s, candidate: c }) => <article key={c.id}>
            <h5>{s.recipe.model}: {c.version}</h5>
            <img src={fileUrl(props.asset, c.preview ?? c.version, c.preview ? "review.png" : "image.png")} alt={`Candidate ${c.version}`} />
            {c.preview ? <><button onClick={() => { openVersion(c.preview ?? c.version); }}>Inspect baked mesh</button>
              <a href={fileUrl(props.asset, c.preview, "turntable.gif")} target="_blank" rel="noreferrer">360 preview</a></> : <p>Combined bake not built yet.</p>}
            <button disabled={locked || c.excluded} title={c.excluded ? "Restore this candidate before choosing it." : ""} onClick={() => { perform(async () => {
              const latest = await multiViewApi.get(props.asset, s.id);
              accept(await multiViewApi.update(props.asset, latest, { candidate_version: c.version }), true);
            }); }}>Select this complete candidate</button>
            <button disabled={locked} onClick={() => { perform(async () => {
              const latest = await multiViewApi.get(props.asset, s.id);
              const reviewed = await multiViewApi.update(props.asset, latest, { candidate_review: { version: c.version, excluded: !c.excluded } });
              setSessions((previous) => [...previous.filter((session) => session.id !== reviewed.id), reviewed]);
              if (current.id === reviewed.id) accept(reviewed, true);
            }); }}>{c.excluded ? "Restore candidate for review" : "Exclude candidate from Apply"}</button>
          </article>)}</div>
        </details>
      </> : <>
      <h4>Edit overlapping view pairs</h4>
      <p>Two fixed views per sheet. Select one pair for an initial style check, then generate remaining pairs.</p>
      <div className="row mv-run-actions">
        <button className="mv-primary" disabled={!!generationReason || !selectedGroups.length} onClick={() => { act("generate", { groups: selectedGroups }); }}>Generate selected groups</button>
        <button disabled={!!generationReason || !pending.length} onClick={() => { act("generate"); }}>Generate remaining groups</button>
        <button disabled={!!generationReason || !selectedGroups.length} onClick={() => { act("generate", { groups: selectedGroups, regenerate: true }); }}>Regenerate selected groups</button>
      </div>
      {generationReason && <p role="status">{generationReason}</p>}
      {!generationReason && !selectedGroups.length && <p role="status">Check one or more view pairs to enable Generate selected groups.</p>}
      <div className="mv-groups">{current.groups.map((group) => {
        const result = current.results[group.id], excluded = current.excluded.includes(group.id);
        return <article key={group.id} className={excluded ? "mv-excluded" : ""}>
          <label><input type="checkbox" disabled={locked || excluded} checked={selectedGroups.includes(group.id)} onChange={(event) => {
            setSelectedGroups((previous) => event.target.checked ? [...previous, group.id] : previous.filter((id) => id !== group.id));
          }} />{group.views.join(" + ")}</label>
          <p>{excluded ? "Excluded" : result?.valid ? "Candidate ready" : result ? "Needs regeneration" : "Not generated"} / {group.overlap_texels.toLocaleString()} shared texels</p>
          {result ? <a href={fileUrl(props.asset, result.version, "image.png")} target="_blank" rel="noreferrer"><img loading="lazy" src={fileUrl(props.asset, result.version, "image.png")} alt={`Generated views ${group.views.join(" and ")}`} /></a>
            : <div className="mv-pair">{group.views.map((id) => <img key={id} loading="lazy" src={fileUrl(props.asset, current.capture ?? "", `views/${id}.png`)} alt={`Captured view ${id}`} />)}</div>}
          <details><summary>Instructions for this pair</summary><label>Optional instruction<textarea rows={2} disabled={locked} value={groupDrafts[group.id] ?? current.group_instructions[group.id] ?? ""}
            onChange={(event) => { const value = event.target.value; setGroupDrafts((previous) => ({ ...previous, [group.id]: value })); }} /></label>
          <button disabled={locked || groupDrafts[group.id] === undefined} onClick={() => { perform(async () => {
            const instruction = groupDrafts[group.id];
            if (instruction === undefined) return;
            accept(await multiViewApi.update(props.asset, current, { group_instructions: { [group.id]: instruction } }));
            setGroupDrafts((previous) => { const next = { ...previous }; delete next[group.id]; return next; });
          }); }}>Save pair instruction</button></details>
          <button disabled={locked} onClick={() => { perform(async () => {
            const next = excluded ? current.excluded.filter((id) => id !== group.id) : [...current.excluded, group.id];
            accept(await multiViewApi.update(props.asset, current, { excluded: next }));
            if (!excluded) setSelectedGroups((previous) => previous.filter((id) => id !== group.id));
          }); }}>{excluded ? "Include pair" : "Exclude pair"}</button>
        </article>;
      })}</div>
      </>}
      <h4>Combined texture preview</h4>
      <button className="mv-primary" disabled={!!previewReason} onClick={() => { act("preview"); }}>Build combined preview</button>
      {previewReason && <p role="status">{previewReason}</p>}
      {current.preview && <>
        <img className="mv-review" src={fileUrl(props.asset, current.preview, "review.png")} alt="Combined texture around all eight sides of the mesh" />
        <div className="row"><button onClick={() => { openVersion(current.source); }}>Show before</button><button onClick={() => { if (current.preview) openVersion(current.preview); }}>Review combined mesh in 3D</button>
          <a href={fileUrl(props.asset, current.preview, "turntable.gif")} target="_blank" rel="noreferrer">Open 360 preview</a></div>
        <button className="mv-primary" disabled={locked || dirty || props.version.version !== current.preview}
          title={props.version.version !== current.preview ? "Open the combined preview in 3D and frame the join first." : "Capture this assembled texture with editable seam suggestions."}
          onClick={() => { perform(async () => {
            if (!window.__viewer || !current.preview) throw new Error("Open and frame the combined preview first");
            const requestedRoute = window.location.hash;
            const submitted = await api.run(props.asset, "paint", current.preview, {
              op: "capture", view: window.__viewer.view(), size: 1024, heal: true,
              appearance: { revision: 0, materials: current.recipe.materials, style: current.recipe.style,
                preserve: current.recipe.preserve, model: "krea-genesis", denoise: 0.3, steps: 8 },
            });
            const completed = await waitJob(submitted.job_id);
            if (completed.status !== "done" || !completed.version) throw new Error(completed.error?.message ?? "Heal capture did not complete");
            if (window.location.hash !== requestedRoute) return;
            openVersion(completed.version);
          }); }}>Heal seams from this view</button>
        <p className="muted">Frame a join on the assembled mesh first. This starts a full-context masked edit using Genesis; review and erase unwanted suggested areas before generating.</p>
        <details><summary>Inspect projection boundaries</summary>
          <p>Open the combined mesh, then inspect coloured ownership or red disagreement directly on its surfaces.</p>
          <div className="row">
            <button disabled={props.version.version !== current.preview && props.version.version !== current.applied} onClick={() => { perform(async () => {
              if (!window.__viewer || !current.preview) throw new Error("Open the combined preview first");
              await window.__viewer.setAtlasOverlay(fileUrl(props.asset, current.preview, "owners.png"));
            }); }}>Show view ownership on mesh</button>
            <button disabled={props.version.version !== current.preview && props.version.version !== current.applied} onClick={() => { perform(async () => {
              if (!window.__viewer || !current.preview) throw new Error("Open the combined preview first");
              await window.__viewer.setAtlasOverlay(fileUrl(props.asset, current.preview, "disagreement.png"));
            }); }}>Show disagreement on mesh</button>
            <button onClick={() => { perform(async () => { await window.__viewer?.setAtlasOverlay(null); }); }}>Restore painted material</button>
          </div>
          <div className="mv-pair"><img src={fileUrl(props.asset, current.preview, "owners.png")} alt="View ownership atlas" /><img src={fileUrl(props.asset, current.preview, "disagreement.png")} alt="Disagreement atlas" /></div>
        </details>
        <p>Inspect joins and material scale on the mesh before applying. The existing atlas size and geometry are retained.</p>
      </>}
      <button className="mv-primary" disabled={!!applyReason} onClick={() => { act("apply"); }}>Apply texture</button>
      {applyReason && <p role="status">{applyReason}</p>}
      {current.applied && <p>Applied as <a href={`#/asset/${props.asset}?version=${current.applied}`}>{current.applied}</a>. Open it and start a new session to heal remaining seams.</p>}
      <LocalRuntimeStatus />
    </>}
    <dialog className="mv-compare-dialog" ref={compareDialog} aria-label="Compare painted candidates" onCancel={() => { setCompareOpen(false); }}>
      {compareOpen && comparedMeshes.length === 2 && <Compare asset={props.asset} versions={[...props.versions]} shown={comparedMeshes[0]!} other={comparedMeshes[1]!}
        onClose={() => { setCompareOpen(false); }} />}
    </dialog>
  </details></>;
}
