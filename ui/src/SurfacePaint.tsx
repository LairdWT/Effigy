import { useEffect, useRef, useState, type ReactElement } from "react";
import { api, fileUrl, type Appearance, type Meta } from "./api";
import { useBusy, useUnsaved } from "./hooks";
import { ReferenceModelSelect } from "./ReferenceModels";
import { ancestors, hasGlb } from "./workflow";
import "./surface-paint.css";

import { MaskEditor, type Point, type Stroke, type Selection } from "./PaintSelection";

type Chain = (asset: string, parent: string | null, steps: [string, object][]) => Promise<string | null>;
type Props = Readonly<{ asset: string; version: Meta; versions: Meta[]; chain: Chain }>;
type Draft = Readonly<{ kind: "empty" }> | Readonly<{ kind: "saved"; value: Record<string, unknown> }> | Readonly<{ kind: "error"; message: string }>;

function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function loadDraft(key: string): Draft {
  try {
    const text = localStorage.getItem(key);
    if (text === null) return { kind: "empty" };
    const value: unknown = JSON.parse(text);
    if (!record(value)) return { kind: "error", message: "Saved paint draft is invalid; enter the recipe again." };
    return { kind: "saved", value };
  } catch (error: unknown) {
    console.error("Could not read the surface-paint draft", error);
    return { kind: "error", message: "Could not read the saved paint draft. Unsaved edits remain in this tab only." };
  }
}

function savedSelection(value: unknown): Selection {
  if (value === undefined) return { mode: "brush", strokes: [] };
  const invalid: Selection = { mode: "brush", strokes: [] };
  if (!record(value) || !["all", "brush", "seams"].includes(String(value.mode)) || !Array.isArray(value.strokes)) return invalid;
  if (value.strokes.length > 256) return invalid;
  const strokes: Stroke[] = [];
  let count = 0;
  for (const row of value.strokes as unknown[]) {
    if (!record(row) || !["paint", "erase", "lasso", "erase-lasso"].includes(String(row.tool)) ||
      typeof row.radius !== "number" || !Number.isFinite(row.radius) || row.radius < 0.002 || row.radius > 0.25 ||
      !Array.isArray(row.points) || row.points.length < 1 || row.points.length > 4096) return invalid;
    const points: Point[] = [];
    for (const point of row.points as unknown[]) {
      if (!Array.isArray(point) || point.length !== 2 ||
        !point.every((n: unknown) => typeof n === "number" && Number.isFinite(n) && n >= 0 && n <= 1)) return invalid;
      points.push([Number(point[0]), Number(point[1])]);
    }
    count += points.length;
    if (count > 30000) return invalid;
    strokes.push({ tool: row.tool as Stroke["tool"], radius: row.radius, points });
  }
  const faces = value.faces;
  if (faces !== undefined && (!record(faces) || typeof faces.revision !== "string" || !Array.isArray(faces.ids) ||
    !faces.ids.every((id: unknown) => Number.isInteger(id) && Number(id) >= 0))) return invalid;
  return { mode: value.mode === "all" ? "all" : value.mode === "seams" ? "seams" : "brush", strokes, ...(faces ? { faces: faces as Selection["faces"] } : {}) };
}

function imageUrl(asset: string, version: Meta, output = "image"): string {
  return fileUrl(asset, version.version, version.outputs[output]);
}

export function SurfacePaint(props: Props): ReactElement | null {
  const line = ancestors(props.versions, props.version);
  const capture = props.version.step === "paint" && props.version.params.op === "apply" ? undefined
    : line.find((v) => v.step === "paint" && v.params.op === "capture");
  const source = capture ? props.versions.find((v) => v.version === capture.parent) : props.version;
  const candidate = props.version.step === "reference" && props.version.parent === capture?.version ? props.version : null;
  const available = hasGlb(props.version) || !!capture;
  if (!available || !source) return null;
  return <PaintWorkspace key={`${props.asset}/${props.version.version}`} {...props} source={source} capture={capture ?? null} candidate={candidate} />;
}

function PaintWorkspace(props: Props & Readonly<{ source: Meta; capture: Meta | null; candidate: Meta | null }>): ReactElement {
  const seamReady = ancestors(props.versions, props.source).some((version) => typeof version.outputs.owners === "string");
  const draftKey = `effigy:surface-paint:${props.asset}:${props.candidate?.version ?? props.capture?.version ?? props.source.version}`;
  const [draft] = useState<Draft>(() => loadDraft(draftKey));
  const saved = draft.kind === "saved" ? draft.value : props.candidate?.params
    ?? (record(props.source.metrics.paint_settings) ? props.source.metrics.paint_settings : undefined);
  const recordedRecipe = draft.kind === "saved" || props.candidate !== null;
  const [model, setModel] = useState(typeof saved?.model === "string" ? saved.model : "krea-genesis");
  const [prompt, setPrompt] = useState(typeof saved?.view_prompt === "string" ? saved.view_prompt : typeof saved?.prompt === "string" ? saved.prompt : "");
  const [denoise, setDenoise] = useState(typeof saved?.denoise === "number" ? saved.denoise : 0.35);
  const [steps, setSteps] = useState(typeof saved?.steps === "number" ? saved.steps : 8);
  const [paintMode, setPaintMode] = useState(saved?.paint_mode === "full_view" ? "full_view" : "masked");
  const [promptScope, setPromptScope] = useState(saved?.prompt_scope === "match_capture" || (!recordedRecipe && props.capture?.params.heal === true) ? "match_capture" : "shared_style");
  const [conditioning, setConditioning] = useState(saved?.conditioning === "blank_region" ? "blank_region" : "preserve_structure");
  const [styleImage, setStyleImage] = useState(typeof saved?.style_image === "string" ? saved.style_image : "");
  const [samplerFeather, setSamplerFeather] = useState(typeof saved?.mask_feather === "number" ? saved.mask_feather : 0);
  const [appearance, setAppearance] = useState<Appearance>({
    revision: 0, materials: "", style: "", preserve: "", model: "krea-genesis", denoise: 0.35, steps: 8,
  });
  const [appearanceReady, setAppearanceReady] = useState(false);
  const [appearanceBaseRevision, setAppearanceBaseRevision] = useState(0);
  const edited = useRef(false);
  const materialText = useRef<HTMLTextAreaElement>(null);
  const [suggestion, setSuggestion] = useState(props.version.step === "describe" ? String(props.version.metrics.description ?? "") : "");
  const [materialRange, setMaterialRange] = useState<readonly [number, number]>([0, 0]);
  const [seed, setSeed] = useState(typeof saved?.seed === "number" || typeof saved?.seed === "string" ? String(saved.seed) : "");
  const [strength, setStrength] = useState(1);
  const [feather, setFeather] = useState(0);
  const previewBlended = props.candidate?.params.paint_mode === "masked" && Number(props.candidate.params.mask_feather ?? 8) > 0;
  const [selection, setSelection] = useState<Selection>(() => saved?.paint_mask ? savedSelection(saved.paint_mask)
    : props.capture?.outputs.seam_mask ? { mode: "seams", strokes: [] } : { mode: "brush", strokes: [] });
  const [presetReady, setPresetReady] = useState(false);
  const [maskPresent, setMaskPresent] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState(draft.kind === "error" ? draft.message : "");
  const [notice, setNotice] = useState("");
  const [busy, run] = useBusy();
  const changeAppearance = (field: "materials" | "style" | "preserve", value: string): void => {
    edited.current = true; setAppearance((previous) => ({ ...previous, [field]: value })); setDirty(true);
  };
  const instructionModel = model === "qwen-edit" || model === "fibo2-turbo";
  const exactPrompt = promptScope === "match_capture" ? prompt
    : [appearance.materials, appearance.style, instructionModel ? appearance.preserve : "", prompt].filter((part) => part.trim()).join("\n\n");
  useEffect(() => {
    let active = true;
    api.asset(props.asset).then(({ asset }) => {
      if (!active) return;
      setAppearanceReady(true);
      setAppearanceBaseRevision(asset.appearance?.revision ?? 0);
      if (edited.current) return;
      if (saved && !record(saved.appearance)) {
        setNotice("Legacy full prompt preserved. Load shared appearance explicitly if you want to combine it with this recipe.");
        return;
      }
      const snapshot = saved?.appearance ?? props.capture?.metrics.appearance ?? props.source.metrics.appearance ?? asset.appearance;
      if (!record(snapshot) || typeof snapshot.materials !== "string" || typeof snapshot.style !== "string" || typeof snapshot.preserve !== "string") return;
      const inherited = snapshot as Appearance;
      setAppearance(inherited);
      if (!saved) { setModel(inherited.model); setDenoise(inherited.denoise); setSteps(inherited.steps); }
    }).catch((failure: unknown) => { if (active) setError(String(failure)); });
    return () => { active = false; };
  }, [props.asset]);
  useUnsaved(`${props.asset}-surface-paint`, dirty && !busy);
  const validSeed = seed === "" || (Number.isSafeInteger(Number(seed)) && Number(seed) >= 0 && Number(seed) < 2 ** 53);
  const validMask = maskPresent && (!selection.faces || (selection.faces.ids.length > 0 && selection.faces.revision === props.capture?.metrics.geometry_revision))
    && (selection.mode === "all" || (selection.mode === "seams" && presetReady) || selection.strokes.some((stroke) => stroke.tool === "paint" || stroke.tool === "lasso"))
    && selection.strokes.reduce((total, stroke) => total + stroke.points.length, 0) <= 30000;
  const generateDisabledReason = busy ? "A painting operation is running."
    : model === "fibo2-turbo" && paintMode !== "masked" ? "Choose incremental masked painting for FIBO."
    : !appearanceReady ? "Loading this asset's appearance..."
    : !validMask ? "Select the area to paint below: add a green brush, lasso or triangle selection."
    : !exactPrompt.trim() ? "Enter an appearance or edit instruction before generating."
    : !validSeed ? "Enter a nonnegative whole-number seed, or leave it blank."
    : !Number.isInteger(steps) || steps < 1 || steps > 50 ? "Steps must be between 1 and 50."
    : paintMode === "masked" && model === "qwen-edit" ? "Choose Krea or FLUX for incremental masking, or switch Qwen to full-view editing."
    : "";
  const size = props.capture ? Number(props.capture.metrics.size) : 1024;
  const perform = (action: () => Promise<unknown>): void => {
    void run(async () => {
      setError("");
      try { await action(); }
      catch (failure: unknown) {
        console.error("Surface paint operation failed", failure);
        setError(failure instanceof Error ? failure.message : String(failure));
      }
    });
  };
  const generate = (): void => perform(async () => {
    if (!props.capture) throw new Error("Capture a mesh view first");
    const chosenSeed = seed === "" ? Math.floor(Math.random() * 2 ** 31) : Number(seed);
    await props.chain(props.asset, props.capture.version, [["reference", {
      op: "edit", model, prompt: exactPrompt, view_prompt: prompt,
      prompt_scope: promptScope,
      appearance: { ...appearance, model, denoise, steps }, count: 1, seed: chosenSeed, steps, width: size, height: size,
      paint_mask: selection, ...(!instructionModel ? { denoise } : {}),
      ...(model === "fibo2-turbo" ? { conditioning, ...(conditioning === "preserve_structure" && styleImage ? { style_image: styleImage } : {}) } : {}),
      paint_mode: paintMode, ...(paintMode === "masked" ? { mask_feather: samplerFeather } : {}),
    }]]);
  });
  const project = (): void => perform(async () => {
    if (!props.candidate) throw new Error("Generate a projection preview first");
    await props.chain(props.asset, props.source.version, [["paint", { op: "apply", image: props.candidate.version, mask: selection, strength, feather: previewBlended ? 0 : feather, texture_size: "keep" }]]);
  });
  return <details className="surface-paint" id="surface-paint" open>
    <summary>Projection painting</summary>
    <p>Capture this mesh, select an area, generate a preview, then project it onto the texture. After projecting, capture another angle to continue from the updated mesh.</p>
    {props.capture && <div className="paint-run-actions" aria-label="Projection painting actions">
      {generateDisabledReason && <p role="status">{generateDisabledReason}</p>}
      <button className="primary" type="button" disabled={!!generateDisabledReason} title={generateDisabledReason || undefined} onClick={generate}>
        {busy ? "Working..." : "1. Generate projection preview"}
      </button>
      <button className={props.candidate ? "primary" : ""} type="button" disabled={busy || !props.candidate || !validMask} onClick={project}>2. Project onto mesh</button>
      <p>{props.candidate ? "Preview ready below. Review it, then project to create a mesh version." : "Generate runs the model. Your mesh changes only after Project onto mesh."}</p>
    </div>}
    <p className="muted">One static mesh with a unique square base-colour atlas. Use a baked static copy for multiple materials or animation.</p>
    {error && <p className="error" role="alert">{error}</p>}
    {notice && <p role="status">{notice}</p>}
    <details><summary>Appearance shared across views</summary>
      <label>Materials and palette<textarea ref={materialText} rows={3} value={appearance.materials}
        onSelect={(e) => setMaterialRange([e.currentTarget.selectionStart, e.currentTarget.selectionEnd])}
        onChange={(e) => changeAppearance("materials", e.target.value)} /></label>
      <label>Desired style<textarea rows={2} value={appearance.style} onChange={(e) => changeAppearance("style", e.target.value)} /></label>
      <label>Features to preserve<textarea rows={2} value={appearance.preserve} onChange={(e) => changeAppearance("preserve", e.target.value)} /></label>
      <button type="button" disabled={busy || !appearanceReady} onClick={() => perform(async () => {
        const result = await api.saveAppearance(props.asset, { ...appearance, revision: appearanceBaseRevision, model, denoise, steps });
        setAppearance(result); setAppearanceBaseRevision(result.revision); if (!props.capture) setDirty(false);
        setNotice(`Appearance revision ${result.revision} saved for new views.`);
      })}>Use for this asset</button>
      <button type="button" disabled={busy} onClick={() => perform(async () => {
        const result = await api.asset(props.asset);
        if (!result.asset.appearance) { setNotice("No shared appearance has been saved yet."); return; }
        edited.current = true;
        setAppearance(result.asset.appearance); setAppearanceBaseRevision(result.asset.appearance.revision);
        setModel(result.asset.appearance.model); setDenoise(result.asset.appearance.denoise); setSteps(result.asset.appearance.steps);
        if (!props.capture) setDirty(false);
        setNotice("Current shared appearance loaded. This view's instructions and selection remain.");
      })}>Load current shared appearance</button>
      <button type="button" disabled={busy} onClick={() => {
        const previous = props.versions.filter((v) => v.step === "reference" && typeof v.params.prompt === "string").at(-1);
        if (!previous) { setNotice("No previous painting recipe in this asset."); return; }
        edited.current = true;
        const snapshot = previous.params.appearance;
        if (record(snapshot) && typeof snapshot.materials === "string") {
          setAppearance(snapshot as Appearance);
          setPrompt(String(previous.params.view_prompt ?? ""));
        } else if (props.capture) { setPrompt(String(previous.params.prompt)); }
        else { setAppearance((current) => ({ ...current, materials: String(previous.params.prompt) })); }
        setNotice(`Recipe text loaded from ${previous.version}. Review view-specific details before saving shared appearance.`);
        setDirty(true);
      }}>Use previous recipe</button>
    </details>
    {!props.capture && <>
      <p>Orbit and frame the surface in the 3D viewer. Capture creates a fixed, unlit square view for painting.</p>
      {dirty && <p role="status">Save shared appearance with "Use for this asset" before capturing another view.</p>}
      <button type="button" disabled={busy || !appearanceReady || dirty} onClick={() => perform(async () => {
        if (!window.__viewer) throw new Error("The 3D viewer is not ready");
        await props.chain(props.asset, props.source.version, [["paint", { op: "capture", view: window.__viewer.view(), size: 1024 }]]);
      })}>Capture view for painting</button>
      <button type="button" disabled={busy || !appearanceReady || !seamReady} title={!seamReady ? "This mesh has no combined projection history. Use a normal capture and manual selection." : undefined} onClick={() => perform(async () => {
        if (!window.__viewer) throw new Error("The 3D viewer is not ready");
        await props.chain(props.asset, props.source.version, [["paint", {
          op: "capture", view: window.__viewer.view(), size: 1024, heal: true,
          appearance: { ...appearance, model, denoise, steps },
        }]]);
      })}>Capture seam-heal view</button>
      <p className="muted">Seam suggestions use the combined projection history. Ordinary capture remains available for a manually painted mask.</p>
      {props.version.step === "paint" && props.version.params.op === "apply" &&
        <img className="paint-comparison" src={imageUrl(props.asset, props.version, "comparison")} alt="Mesh before and after applying the painted view" />}
      {props.version.outputs.review && <details><summary>Inspect the repair around the whole mesh</summary>
        <img className="paint-comparison" src={imageUrl(props.asset, props.version, "review")} alt="Repaired mesh from eight angles" />
        {props.version.outputs.turntable && <a href={imageUrl(props.asset, props.version, "turntable")} target="_blank" rel="noreferrer">Open repaired mesh360 preview</a>}
      </details>}
    </>}
    {props.capture && <>
      <p className="muted">Fixed view from version {props.source.version}. Orbiting now does not change its projection.</p>
      {props.capture.outputs.seam_mask && <p role="status">Seam-heal capture: the entire assembled mesh remains in context. Green is an editable suggestion, not an accepted repair. Erase good details before generating.</p>}
      <label>Appearance intent<select value={promptScope} onChange={(event) => { setPromptScope(event.target.value); setDirty(true); }}>
        <option value="match_capture">Repair: match the captured appearance</option>
        <option value="shared_style">Restyle: use shared materials and style</option>
      </select></label>
      {promptScope === "match_capture" && <p className="muted">The capture supplies the existing look. Only this view's repair wording is sent; shared appearance remains saved and editable.</p>}
      {promptScope === "match_capture" && <button type="button" disabled={busy || !appearanceReady} onClick={() => {
        setPrompt(instructionModel
          ? "Repair the selected texture join. Continue the surrounding pattern, color, material scale and brushwork through it. Keep the existing shape and all other details unchanged."
          : "The selected surface has a continuous version of the surrounding texture, with matching color, material scale, pattern and brushwork across the join.");
        setDirty(true);
      }}>Use repair wording</button>}
      <details open={!!suggestion}><summary>Optional: suggest a description</summary>
      <button type="button" disabled={busy || !appearanceReady} onClick={() => perform(async () => {
        localStorage.setItem(`effigy:surface-paint:${props.asset}:${props.capture!.version}`,
          JSON.stringify({ model, prompt: exactPrompt, view_prompt: prompt, appearance, denoise, steps, seed, paint_mask: selection, paint_mode: paintMode, mask_feather: samplerFeather, conditioning, style_image: styleImage, prompt_scope: promptScope }));
        setDirty(false);
        await props.chain(props.asset, props.capture!.version, [["describe", {}]]);
      })}>Suggest description from this view</button>
      <p className="muted">Uses local Q3.5-9B OpusGLM Q8 and its vision projector. Suggestions describe observed pixels; your desired style stays separate.</p>
      {suggestion && <section aria-label="Proposed observed description">
        <label>Observed description - review before applying<textarea rows={6} value={suggestion} onChange={(e) => setSuggestion(e.target.value)} /></label>
        <button type="button" onClick={() => { changeAppearance("materials", [appearance.materials, suggestion].filter(Boolean).join("\n\n")); setSuggestion(""); }}>Append to materials</button>
        <button type="button" disabled={materialRange[0] === materialRange[1]} onClick={() => {
          changeAppearance("materials", appearance.materials.slice(0, materialRange[0]) + suggestion + appearance.materials.slice(materialRange[1]));
          setSuggestion("");
        }}>Replace selected material text</button>
        <button type="button" onClick={() => setSuggestion("")}>Discard suggestion</button>
      </section>}
      </details>
      <label>Painting method<select value={paintMode} onChange={(e) => { setPaintMode(e.target.value); setDirty(true); }}>
        <option value="masked">Incremental: generate only inside the mask</option>
        <option value="full_view">Restyle the full view, then project the selection</option>
      </select></label>
      <p>{model === "fibo2-turbo" ? "FIBO receives the captured image and edit instructions; green limits the pixels composited into the preview and mesh."
        : paintMode === "masked" ? "The full captured image stays in context. Only the green selection is denoised; the rest of the preview stays unchanged. Use brush, lasso or faces to extend your painted area." : "The model can change the whole image. Only the selected area is projected onto the mesh."}</p>
      {model === "fibo2-turbo" && <>
        <label>FIBO edit approach<select value={conditioning} onChange={(e) => { setConditioning(e.target.value); setDirty(true); }}>
          <option value="preserve_structure">Retain the full capture</option><option value="blank_region">Blank selected detail for replacement</option>
        </select></label>
        <p>FIBO edits from image context; the mask protects final pixels. Genesis and MOSS also use differential masked denoising.</p>
        {conditioning === "preserve_structure" && <label>Style reference<select value={styleImage} onChange={(e) => { setStyleImage(e.target.value); setDirty(true); }}>
          <option value="">None</option>{props.versions.filter((v) => v.outputs.image && v.step !== "paint").map((v) => <option key={v.version} value={v.version}>{v.version}</option>)}
        </select></label>}
      </>}
      {props.candidate && props.candidate.params.paint_mode !== "masked" && <p role="status">This older preview was generated across the full view. Generate a new preview to use incremental masking.</p>}
      <MaskEditor asset={props.asset} revision={typeof props.capture.metrics.geometry_revision === "string" ? props.capture.metrics.geometry_revision : undefined}
        seamMask={props.capture.outputs.seam_mask ? imageUrl(props.asset, props.capture, "seam_mask") : undefined} onPresetReady={setPresetReady} onMaskPresence={setMaskPresent}
        faceImage={props.capture.outputs.face_ids ? imageUrl(props.asset, props.capture, "face_ids") : undefined}
        image={imageUrl(props.asset, props.capture)} selection={selection} onChange={(value) => { setSelection(value); setDirty(true); }} />
      {!validMask && <p role="status">Paint a selection before continuing. Selections are limited to 256 strokes and 30000 points.</p>}
      <ReferenceModelSelect value={model} mode="edit" onChange={(value) => { edited.current = true; setModel(value); setSteps(value === "fibo2-turbo" || value === "moss-turbo" ? 4 : value.startsWith("krea") ? 8 : value === "flux-ghibli" ? 30 : 20); setDirty(true); }} />
      {paintMode === "masked" && model === "qwen-edit" && <p role="alert">Incremental masked generation currently supports Krea and FLUX. Choose Krea2 Genesis, or explicitly switch to full-view editing for Qwen.</p>}
      <label>This view: appearance or requested change
        <textarea rows={6} value={prompt} onChange={(e) => { setPrompt(e.target.value); setDirty(true); }}
          placeholder={!instructionModel ? "Describe the visible materials, painted shapes, palette and finish of the resulting view." : "Describe the change, then name the visible features to preserve."} />
      </label>
      <details><summary>Exact prompt sent to the model</summary><textarea readOnly rows={5} value={exactPrompt} /></details>
      <p className="muted">{model === "fibo2-turbo" ? "FIBO uses four steps and an edit instruction. Its style reference is optional."
        : model === "moss-turbo" ? "MOSS uses the installed Turbo v2 LoRA and a description of the resulting surfaces. Four steps suit a1024-square view."
        : model === "krea-genesis" ? "Krea2 Genesis image-to-image uses the captured texture and your resulting-appearance description. No FLUX LoRAs are attached." : model === "flux-ghibli"
        ? "FLUX describes the resulting image. Ghibli 0.7 is loaded locally; denoise controls how far it departs from the captured texture."
        : "Qwen accepts edit instructions. The selection protects texture pixels during application, not through preservation prose."}</p>
      {!instructionModel && <label>Image-to-image strength (denoise): {denoise.toFixed(2)}
        <input type="range" min="0.1" max="0.9" step="0.05" value={denoise} onChange={(e) => { setDenoise(Number(e.target.value)); setDirty(true); }} /></label>}
      {paintMode === "masked" && <label>Generation edge blend: {samplerFeather} pixels inward
        <input type="range" min="0" max="32" step="1" value={samplerFeather} onChange={(e) => { setSamplerFeather(Number(e.target.value)); setDirty(true); }} /></label>}
      <div className="row">
        <label>Steps<input disabled={model === "fibo2-turbo"} type="number" min="1" max="50" value={steps} onChange={(e) => { setSteps(Number(e.target.value)); setDirty(true); }} /></label>
        <label>Seed (blank for random)<input value={seed} inputMode="numeric" onChange={(e) => { setSeed(e.target.value); setDirty(true); }} /></label>
      </div>
      <button type="button" disabled={busy} onClick={() => {
        try {
          localStorage.setItem(draftKey, JSON.stringify({ model, prompt: exactPrompt, view_prompt: prompt, appearance, denoise, steps, seed, paint_mask: selection, paint_mode: paintMode, mask_feather: samplerFeather, conditioning, style_image: styleImage, prompt_scope: promptScope }));
          setDirty(false);
          setError("");
          setNotice("Draft saved in this browser. Generated candidates also retain their recipe in asset history.");
        } catch (failure: unknown) {
          console.error("Could not save the surface-paint draft", failure);
          setError("Could not save the draft. Keep this tab open or copy the prompt before leaving.");
        }
      }}>Save painting draft</button>
      {props.candidate && <>
        <div className="paint-pair">
          <figure><img src={imageUrl(props.asset, props.capture)} alt="Original captured view" /><figcaption>Captured texture</figcaption></figure>
          <figure><img src={imageUrl(props.asset, props.candidate)} alt="Generated candidate, not yet applied" /><figcaption>Candidate - not applied</figcaption></figure>
        </div>
        <p><a href={imageUrl(props.asset, props.capture)} target="_blank" rel="noreferrer">Full-size capture</a>
          {" / "}<a href={imageUrl(props.asset, props.candidate)} target="_blank" rel="noreferrer">Full-size candidate</a></p>
        <label>Texture size<select value="keep" disabled><option value="keep">Keep existing atlas ({String(props.capture.metrics.texture_size)} square)</option></select></label>
        <label>Apply strength: {strength.toFixed(2)}<input type="range" min="0.05" max="1" step="0.05" value={strength} onChange={(e) => setStrength(Number(e.target.value))} /></label>
        {previewBlended ? <p className="muted">The preview already contains its edge blend. Projection adds no second blend.</p>
          : <label>Inward mask edge blend: {feather} pixels<input type="range" min="0" max="32" step="1" value={feather} onChange={(e) => setFeather(Number(e.target.value))} /></label>}
        <p className="muted">You can narrow the mask before projecting. To expand beyond this preview's generated area, select the larger area and generate again. Projection uses this capture's camera.</p>
        <p className="muted">Creates a new mesh version. Unseen surfaces, unselected texels, alpha and other material maps remain; small adjacent atlas gutters are refreshed.</p>
      </>}
    </>}
  </details>;
}
