import { useEffect, useState, type ReactElement } from "react";
import { api, fileUrl, type Meta } from "./api";
import { Compare } from "./Compare";
import { multiViewApi, type AuthoringMethod, type AuthoringProfile, type MaterialIntent, type PaintSession, type PreparationReport } from "./multi-view-api";

type Props = Readonly<{ asset: string; displayedVersion: string; current: PaintSession; versions: readonly Meta[]; locked: boolean; onChange: (session: PaintSession) => void; onDirtyChange: (dirty: boolean) => void; onBusyChange: (busy: boolean) => void }>;
type Job = Readonly<{ id: string; message: string; version: string | null; running: boolean; operation: "inspect" | "pack" | "unwrap" }>;

function initialProfile(current: PaintSession, versions: readonly Meta[]): AuthoringProfile {
  if (current.authoring) return current.authoring.profile;
  const source = versions.find((v) => v.version === current.source);
  const atlas = typeof source?.metrics.texture_size === "number" ? source.metrics.texture_size : 1024;
  return { schema_version: 1, preparation: { source: current.source, geometry_revision: current.geometry_revision,
    uv_profile: "padded_islands", atlas_size: atlas, gutter_pixels: 4, pack_rotation: 90 },
    sources: [{ role: "original", version: current.source, note: "Initial source for this session" },
      { role: "working", version: current.source, note: "Prepared source" }],
    materials: [{ id: "surface", identity: current.recipe.materials || "Captured source materials", faces: null,
      palette: "", feature_scale: "Retain feature proportions relative to the captured mesh", marks: "", preserve: current.recipe.preserve }],
    sampling: { mode: "detail", minimum_samples: 1, density_per_metre: null, metres_per_unit: null, viewing_distance_units: null, native_display_pixels: 1024 },
    method: "generated", operation: "refine_current", style: current.recipe.style, observation: "", preservation: current.recipe.preserve, submission_budget: 3 };
}

export function AuthoringWorkspace(props: Props): ReactElement {
  const [profile, setProfile] = useState<AuthoringProfile>(() => initialProfile(props.current, props.versions));
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [scale, setScale] = useState(1);
  const [job, setJob] = useState<Job | null>(null);
  const [note, setNote] = useState("");
  const [reviewVersion, setReviewVersion] = useState("");
  const [compare, setCompare] = useState(false);
  const [faces, setFaces] = useState("");
  const [materialIndex, setMaterialIndex] = useState(0);
  const [inspection, setInspection] = useState<PreparationReport | null>(null);
  const [shellZone, setShellZone] = useState<boolean>(false);
  const working = busy || job?.running === true;
  const locked = props.locked || working;
  const source = props.versions.find((v) => v.version === props.current.source);
  const currentRevision = props.current.authoring?.revision ?? 0;
  const donor = profile.sources.find((s) => s.role === "donor")?.version ?? "";
  const draft = props.current.authoring?.preview ?? props.current.preview;
  const reviewable = props.versions.filter((v) => v.outputs.mesh && props.current.retained_versions.includes(v.version));
  const chosen = reviewable.find((v) => v.version === (reviewVersion || draft));
  const saved = props.current.authoring !== null && !dirty;
  const published = props.current.authoring?.preview != null && props.current.authoring.published_candidate === props.current.authoring.preview;
  const material = profile.materials[materialIndex] ?? profile.materials[0];
  const samplingMeshVisible = props.displayedVersion === props.current.source;

  useEffect(() => { props.onDirtyChange(dirty); }, [dirty, props.onDirtyChange]);
  useEffect(() => { props.onBusyChange(working); }, [working, props.onBusyChange]);
  useEffect(() => () => { props.onBusyChange(false); props.onDirtyChange(false); }, [props.onBusyChange, props.onDirtyChange]);

  useEffect(() => {
    const next = initialProfile(props.current, props.versions);
    setProfile(next); setDirty(false); setMaterialIndex(0); setFaces(next.materials[0].faces?.join(", ") ?? ""); setReviewVersion("");
  }, [props.current.id, currentRevision]);

  useEffect(() => {
    if (!job?.running) return;
    let live = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const refresh = async (): Promise<void> => {
      try {
        const next = await multiViewApi.job(job.id);
        if (!live) return;
        if (!["queued", "running", "done", "failed", "cancelled"].includes(next.status)) {
          throw new Error(`Unknown preparation status ${next.status}; waiting for a confirmed job state`);
        }
        setError("");
        const running = next.status === "running" || next.status === "queued";
        if (next.status === "done" && next.version && job.operation !== "inspect") {
          const id = await multiViewApi.prepare(props.asset, next.version, "inspect", profile.preparation.gutter_pixels, 1);
          if (live) setJob({ id, message: "Measuring prepared UV layout", version: next.version, running: true, operation: "inspect" });
          return;
        }
        if (next.status === "done" && next.version) {
          const report = await multiViewApi.preparationReport(props.asset, next.version);
          if (!live) return;
          setInspection(report);
        }
        setJob({ ...job, message: next.message, version: next.version, running });
        if (running) timer = setTimeout(() => { void refresh(); }, 2000);
      } catch (failure: unknown) {
        if (!live) return;
        console.warn("Preparation progress unavailable; retaining the active job", failure);
        setError(`Progress unavailable: ${String(failure)}. The job remains active; reconnecting automatically.`);
        timer = setTimeout(() => { void refresh(); }, 5000);
      }
    };
    void refresh();
    return () => { live = false; if (timer) clearTimeout(timer); };
  }, [job?.id, job?.running]);

  const perform = (operation: () => Promise<void>): void => {
    setBusy(true); setError("");
    void operation().catch((failure: unknown) => { console.error("Surface authoring failed", failure); setError(String(failure)); }).finally(() => setBusy(false));
  };
  const edit = (change: Partial<AuthoringProfile>): void => { setProfile((p) => ({ ...p, ...change })); setDirty(true); };
  const editMaterial = (change: Partial<MaterialIntent>): void => edit({ materials: profile.materials.map((m, i) => i === materialIndex ? { ...m, ...change } : m) });
  const materialDraft = (): readonly MaterialIntent[] => {
    const parsed = faces.trim() ? faces.split(/[\s,]+/).map(Number) : null;
    if (parsed?.some((n) => !Number.isInteger(n) || n < 0)) throw new Error("Material faces must be nonnegative integer IDs");
    if (parsed && new Set(parsed).size !== parsed.length) throw new Error("Material face IDs must be unique");
    return profile.materials.map((m, i) => i === materialIndex ? { ...m, faces: parsed } : m);
  };
  const chooseMaterial = (index: number, add = false): void => {
    try {
      const materials = materialDraft();
      const next = add ? [...materials, { ...material, id: `material_${materials.length + 1}`, faces: null }] : materials;
      edit({ materials: next }); setMaterialIndex(index); setFaces(next[index].faces?.join(", ") ?? ""); setError("");
    } catch (failure: unknown) { setError(String(failure)); }
  };
  const save = async (): Promise<void> => {
    const next = { ...profile, materials: materialDraft() };
    props.onChange(await multiViewApi.saveAuthoring(props.asset, props.current, next)); setDirty(false);
  };
  const prepare = (operation: "inspect" | "pack" | "unwrap"): void => perform(async () => {
    const id = await multiViewApi.prepare(props.asset, props.current.source, operation, profile.preparation.gutter_pixels, scale);
    setInspection(null); setJob({ id, message: "Queued preparation", version: null, running: true, operation });
  });
  const selectDonor = (version: string): void => edit({ sources: [...profile.sources.filter((s) => s.role !== "donor"),
    ...(version ? [{ role: "donor" as const, version, note: "Explicit source for masked reconstruction" }] : [])] });
  const review = (verdict: "preferred" | "accepted" | "rejected"): void => perform(async () => {
    const version = reviewVersion || draft;
    if (!version || !note.trim()) throw new Error("Choose a mesh and enter your review note");
    props.onChange(await multiViewApi.reviewAuthoring(props.asset, props.current, version, verdict, note));
    setStatus(`Recorded ${verdict} for ${version}.`);
  });

  return <section className="multi-view-paint" aria-label="Surface authoring workspace">
    <h3>Surface authoring</h3>
    <ol className="mv-stages"><li>Source &amp; prepare</li><li>Select &amp; capture</li><li>Author</li><li>Review &amp; publish</li></ol>
    <p>Prepared source: <strong>{props.current.source}</strong>. Geometry: {props.current.geometry_revision}. Preferred: {props.current.authoring?.preferred ?? "none"}. Owner accepted: {props.current.authoring?.accepted ?? "none"}.</p>
    {error && <p role="alert">{error}</p>}{status && <p role="status">{status}</p>}
    <details><summary>1. Blender and UV preparation</summary>
      <p>Inspect first. Unwrap and packing create a separate prepared revision; existing paint sessions keep their source.</p>
      <label>Required island gap (pixels)<input type="number" min="1" max="64" value={profile.preparation.gutter_pixels} disabled={locked}
        onChange={(e) => edit({ preparation: { ...profile.preparation, gutter_pixels: Number(e.target.value) } })} /></label>
      <label>Declared atlas size<select value={profile.preparation.atlas_size} disabled={locked} onChange={(e) => edit({ preparation: { ...profile.preparation, atlas_size: Number(e.target.value) } })}>
        {[128, 256, 512, 1024, 2048, 4096].map((size) => <option key={size} value={size}>{size}</option>)}</select></label>
      <label>UV profile<select value={profile.preparation.uv_profile} disabled={locked} onChange={(e) => edit({ preparation: { ...profile.preparation, uv_profile: e.target.value === "line_art_square" ? "line_art_square" : "padded_islands" } })}>
        <option value="padded_islands">Padded material islands</option><option value="line_art_square">Declared square line-art layout</option></select></label>
      <label>Explicit UV scale before packing<input type="number" min="0.5" max="1" step="0.01" value={scale} disabled={locked} onChange={(e) => setScale(Number(e.target.value))} /></label>
      <p>90-degree rotations, no flips. UV Squares is unavailable on the current Blender API. Nonconstant secondary maps require a separately qualified rebake.</p>
      <div className="row"><button type="button" disabled={locked} onClick={() => prepare("inspect")}>Inspect UVs</button>
        <button type="button" disabled={locked} onClick={() => prepare("pack")}>Pack with UVPackmaster</button>
        <button type="button" disabled={locked} onClick={() => prepare("unwrap")}>ZenUV unwrap and pack</button></div>
      <div className="row"><button type="button" disabled={locked} onClick={() => perform(async () => {
        await api.blenderOpen(props.asset, props.current.source); setStatus(`Opened ${props.current.source} in the isolated Blender session.`);
      })}>Open working copy in Blender</button>
      <button type="button" disabled={locked} onClick={() => perform(async () => {
        const version = await multiViewApi.pullBlender(props.asset, props.current.source);
        selectDonor(version); setStatus(`Saved Blender return ${version}. Save the donor binding before reconstruction. Changed geometry requires a new session.`);
      })}>Pull Blender changes as donor</button></div>
      {job && <p role="status">{job.message} {job.version && <a href={`#/asset/${props.asset}?version=${job.version}`}>Open prepared result {job.version}</a>}</p>}
      {job?.running && <button type="button" onClick={() => perform(async () => { await multiViewApi.cancel(job.id); })}>Cancel preparation</button>}
      {inspection && <div role="status"><p>{inspection.triangles} triangles; {inspection.uv_shells} UV islands; {inspection.atlas_size}px / {inspection.bit_depth}-bit atlas; {(inspection.occupancy * 100).toFixed(1)}% occupied.</p>
        <p>{inspection.degenerate_uv_faces} degenerate UV triangles. {inspection.overlap_check}. Exact island overlap pairs: {inspection.exact_clearance.overlapping_island_pairs ?? "not measured"}.</p>
        <p>Measured island gap: {inspection.exact_clearance.minimum_island_pixels?.toFixed(3) ?? "not applicable"}px; border: {inspection.exact_clearance.minimum_border_pixels?.toFixed(3) ?? "not measured"}px. Clearance: {inspection.exact_clearance.disposition}. {inspection.exact_clearance.reason}</p>
        <p>Texels per asset unit, p10 / median / p90: {inspection.texels_per_asset_unit_p10_p50_p90.map((n) => n.toFixed(1)).join(" / ")}. Metres require the measured scale below.</p>
        <p>UV Squares: {inspection.uv_squares}.</p></div>}
    </details>
    <details open={!saved}><summary>2. Appearance and source contract</summary>
      <label>Method<select value={profile.method} disabled={locked} onChange={(e) => edit({ method: e.target.value as AuthoringMethod })}>
        <option value="generated">Local model edit</option><option value="registered_source">Registered source reconstruction</option><option value="blender_brush">Native Blender brush return</option></select></label>
      <label>Intent<select value={profile.operation} disabled={locked} onChange={(e) => edit({ operation: e.target.value as AuthoringProfile["operation"] })}>
        <option value="refine_current">Refine current appearance</option><option value="restore_source">Restore registered source inside selection</option><option value="restyle">Restyle selected surface</option></select></label>
      <label>Original source<select disabled={locked} value={profile.sources.find((s) => s.role === "original")?.version} onChange={(e) => edit({ sources: profile.sources.map((s) => s.role === "original" ? { ...s, version: e.target.value } : s) })}>
        {props.versions.filter((v) => v.outputs.mesh).map((v) => <option key={v.version}>{v.version}</option>)}</select></label>
      <label>Registered donor<select disabled={locked} value={donor} onChange={(e) => selectDonor(e.target.value)}><option value="">No donor</option>
        {props.versions.filter((v) => v.outputs.mesh).map((v) => <option key={v.version}>{v.version}</option>)}</select></label>
      <label>Material region<select value={materialIndex} disabled={locked} onChange={(e) => chooseMaterial(Number(e.target.value))}>
        {profile.materials.map((m, i) => <option key={m.id} value={i}>{m.id}</option>)}</select></label>
      <button type="button" disabled={locked || profile.materials.length >= 64} onClick={() => chooseMaterial(profile.materials.length, true)}>Add material region</button>
      <label>Material identity<textarea disabled={locked} value={material.identity} onChange={(e) => editMaterial({ identity: e.target.value })} /></label>
      <label>Material face IDs (blank means whole selected surface)<input disabled={locked} value={faces} onChange={(e) => { setFaces(e.target.value); setDirty(true); }} /></label>
      <label>Feature size relative to the source<textarea disabled={locked} value={material.feature_scale} onChange={(e) => editMaterial({ feature_scale: e.target.value })} /></label>
      <label>Palette<input disabled={locked} value={material.palette} onChange={(e) => editMaterial({ palette: e.target.value })} /></label>
      <label>Brush marks and direction<input disabled={locked} value={material.marks} onChange={(e) => editMaterial({ marks: e.target.value })} /></label>
      <label>Shared style<textarea disabled={locked} value={profile.style} onChange={(e) => edit({ style: e.target.value })} /></label>
      <label>Preserve<textarea disabled={locked} value={profile.preservation} onChange={(e) => edit({ preservation: e.target.value })} /></label>
      <label>Source observations<textarea disabled={locked} value={profile.observation} onChange={(e) => edit({ observation: e.target.value })} /></label>
      <label>Capture purpose<select disabled={locked} value={profile.sampling.mode} onChange={(e) => edit({ sampling: { ...profile.sampling, mode: e.target.value === "study" ? "study" : "detail" } })}>
        <option value="detail">Detail-qualified painting</option><option value="study">Low-resolution style study</option></select></label>
      <label>Minimum camera samples per atlas texel<input type="number" min="1" max="4" step="0.25" disabled={locked} value={profile.sampling.minimum_samples} onChange={(e) => edit({ sampling: { ...profile.sampling, minimum_samples: Number(e.target.value) } })} /></label>
      <label>Measured metres per asset unit (blank = unknown)<input type="number" min="0.000001" step="any" disabled={locked} value={profile.sampling.metres_per_unit ?? ""} onChange={(e) => edit({ sampling: { ...profile.sampling, metres_per_unit: e.target.value ? Number(e.target.value) : null } })} /></label>
      <label>Declared texels per metre (requires measured scale)<input type="number" min="1" disabled={locked} value={profile.sampling.density_per_metre ?? ""} onChange={(e) => edit({ sampling: { ...profile.sampling, density_per_metre: e.target.value ? Number(e.target.value) : null } })} /></label>
      <label>Finite model-call budget<input type="number" min="1" max="12" disabled={locked} value={profile.submission_budget} onChange={(e) => edit({ submission_budget: Number(e.target.value) })} /></label>
      <button type="button" disabled={locked || saved} onClick={() => perform(save)}>Save authoring contract</button>
      {dirty && <p>Save changes before authoring. Existing candidates remain in history.</p>}
    </details>
    {props.current.sampling && <div role="status"><p>{props.current.sampling.detail_admitted ? "Capture sampling meets the declared floor." : "Capture is undersampled for detail painting."} {props.current.sampling.undersampled_texels} undersampled texels; {props.current.sampling.unreachable_texels} unreachable texels stay unchanged.</p>
      <p>Small / median / large sampling ratios: {props.current.sampling.minimum_axis_p10_p50_p90.map((n) => n.toFixed(2)).join(" / ")}. Orange: undersampled. Purple: unreachable. Green: adequate.</p>
      {props.current.mask_version && <details><summary>Sampling atlas</summary><img alt="Sampling coverage on the UV atlas" width="320" src={fileUrl(props.asset, props.current.mask_version, "sampling.png")} /></details>}
      <div className="row"><button type="button" disabled={locked || !samplingMeshVisible || !props.current.mask_version} onClick={() => perform(async () => {
        if (!window.__viewer || !props.current.mask_version) throw new Error("Open the session source mesh before showing sampling");
        await window.__viewer.setAtlasOverlay(fileUrl(props.asset, props.current.mask_version, "sampling.png"));
      })}>Show sampling on mesh</button><button type="button" onClick={() => perform(async () => { await window.__viewer?.setAtlasOverlay(null); })}>Restore painted material</button></div>
      {!samplingMeshVisible && <p><a href={`#/asset/${props.asset}?version=${props.current.source}`}>Open the session source</a> to inspect its sampling overlay.</p>}
    </div>}
    {saved && props.current.capture && props.current.sampling_profile_revision !== currentRevision && <button type="button" disabled={locked} onClick={() => perform(async () => {
      props.onChange(await multiViewApi.action(props.asset, props.current.id, { revision: props.current.revision, action: "select", selection_mode: "refresh" }));
    })}>Refresh camera masks and sampling</button>}
    {profile.method !== "generated" && <div><h4>3. Build a protected {profile.method === "blender_brush" ? "brush" : "source"} draft</h4>
      <p>{profile.method === "blender_brush" ? "Paint the copied mesh in Blender, then Pull it as the donor. Reconstruction copies only RGB inside the saved selection." : "Use a registered mesh with matching triangle positions. The selected surface receives its source colour without a model."}</p>
      <button type="button" disabled={locked || !saved || !donor || !props.current.mask_version} onClick={() => perform(async () => { props.onChange(await multiViewApi.authoringAction(props.asset, props.current, "reconstruct")); })}>Build masked reconstruction</button>
      {(!saved || !donor || !props.current.mask_version) && <p>Requires a saved contract, donor mesh and captured surface selection.</p>}
      <button type="button" disabled={locked || !saved || !props.current.authoring?.preview || published} onClick={() => perform(async () => { props.onChange(await multiViewApi.authoringAction(props.asset, props.current, "publish")); })}>Publish reviewed draft by reference</button>
      {published && <p>Already published as <a href={`#/asset/${props.asset}?version=${props.current.authoring?.published}`}>{props.current.authoring?.published}</a>. Reopening it creates no copy.</p>}
    </div>}
    <details><summary>Hand-paint handoff and seam heal</summary>
      <p>Export guide renders, face IDs, cameras, UV layout and permission for hand painting. Density stays undeclared unless the contract records a measured scale and a declared density.</p>
      <button type="button" disabled={locked || !saved} onClick={(): void => perform(async (): Promise<void> => { props.onChange(await multiViewApi.authoringAction(props.asset, props.current, "handoff")); })}>Export hand-paint handoff</button>
      {props.current.authoring?.handoff && <p>Latest handoff: <a href={`#/asset/${props.asset}?version=${props.current.authoring.handoff}`}>{props.current.authoring.handoff}</a>.</p>}
      <label><input type="checkbox" checked={shellZone} disabled={locked} onChange={(event: Readonly<{ target: HTMLInputElement }>): void => setShellZone(event.target.checked)} />Use UV shell borders (fallback when no writer ownership exists)</label>
      <button type="button" disabled={locked || !saved} onClick={(): void => perform(async (): Promise<void> => { props.onChange(await multiViewApi.authoringAction(props.asset, props.current, shellZone ? "heal_mask:shells" : "heal_mask")); })}>Mark seam-heal zone</button>
      {props.current.authoring?.heal_mask && <p>Saved seam-heal zone: <a href={`#/asset/${props.asset}?version=${props.current.authoring.heal_mask}`}>{props.current.authoring.heal_mask}</a>.</p>}
      <button type="button" disabled={locked || !saved || profile.method === "generated" || !donor || !props.current.mask_version || !props.current.authoring?.heal_mask} onClick={(): void => perform(async (): Promise<void> => { props.onChange(await multiViewApi.authoringAction(props.asset, props.current, "reconstruct_heal")); })}>Reconstruct seam heal</button>
      {(profile.method === "generated" || !donor || !props.current.authoring?.heal_mask) && <p>Seam-heal reconstruction requires a brush or registered-source method, a donor mesh and a saved seam-heal zone.</p>}
    </details>
    <details><summary>4. Review and appearance acceptance</summary>
      <p>Model calls reserved: {props.current.authoring?.submissions.reduce((total, s) => total + s.count, 0) ?? 0}/{profile.submission_budget}. Technical retention does not accept appearance.</p>
      <label>Review mesh<select value={reviewVersion || draft || ""} disabled={locked} onChange={(e) => setReviewVersion(e.target.value)}><option value="">Choose a result</option>
        {reviewable.map((v) => <option key={v.version}>{v.version}</option>)}</select></label>
      {chosen && <a href={`#/asset/${props.asset}?version=${chosen.version}`}>Inspect {chosen.version} in 3D</a>}
      {chosen?.outputs.image && !chosen.outputs.image.startsWith("@") && <div className="row">
        <img alt="Baked review sheet" width="480" src={fileUrl(props.asset, chosen.version, chosen.outputs.image)} />
        {chosen.outputs.comparison && !chosen.outputs.comparison.startsWith("@") && <img alt="Source beside result at four review yaws" width="480" src={fileUrl(props.asset, chosen.version, chosen.outputs.comparison)} />}
      </div>}
      <button type="button" disabled={!chosen || !source} onClick={() => setCompare(true)}>Compare source and result</button>
      <label>Your visual review<textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Material scale, seams, detail and protected areas" /></label>
      <div className="row"><button type="button" disabled={locked || !saved || !chosen || !note.trim()} onClick={() => review("preferred")}>Mark preferred</button>
        <button type="button" disabled={locked || !saved || !chosen || !note.trim()} onClick={() => review("rejected")}>Reject appearance</button>
        <button type="button" disabled={locked || !saved || !chosen || !note.trim()} onClick={() => review("accepted")}>Accept appearance</button></div>
    </details>
    {compare && chosen && source && <Compare asset={props.asset} versions={[...props.versions]} shown={chosen} other={source} onClose={() => setCompare(false)} />}
  </section>;
}
