import { useEffect, useReducer, useState, type ChangeEvent, type ReactElement } from "react";
import { api, type Meta, type ReferenceModel } from "./api";
import { useBusy } from "./hooks";
import { ancestors, hasGlb, hasImage, label } from "./workflow";

type ModelState = Readonly<{ kind: "loading" }> | Readonly<{ kind: "ready"; models: readonly ReferenceModel[] }> | Readonly<{ kind: "error"; message: string }>;
type ModelAction = Exclude<ModelState, { kind: "loading" }>;
type Chain = (asset: string, parent: string | null, steps: [string, object][]) => Promise<string | null>;

function modelState(_state: ModelState, action: ModelAction): ModelState {
  switch (action.kind) {
    case "ready": return action;
    case "error": return action;
  }
}

function useModels(): ModelState {
  const [state, dispatch] = useReducer(modelState, { kind: "loading" });
  useEffect(() => {
    let active = true;
    api.referenceModels().then(
      (models: ReferenceModel[]) => { if (active) dispatch({ kind: "ready", models }); },
      (error: unknown) => { if (active) dispatch({ kind: "error", message: String(error) }); },
    );
    return () => { active = false; };
  }, []);
  return state;
}

export function ReferenceModelSelect(props: Readonly<{
  value: string;
  onChange: (value: string) => void;
  mode: "generate" | "edit";
  scope?: "with-baseline" | "native-only";
}>): ReactElement {
  const state = useModels();
  return <label>
    Reference model
    <select value={props.value} onChange={(event: ChangeEvent<HTMLSelectElement>) => props.onChange(event.target.value)}>
      {props.scope === "with-baseline" && <option value="z-image">Z-Image Turbo (baseline)</option>}
      {state.kind === "loading" && <option disabled>Checking local models...</option>}
      {state.kind === "ready" && state.models.filter((model: ReferenceModel) => model.operations
        ? model.operations.includes(props.mode === "generate" ? "image" : "edit") : model.mode === props.mode).map((model: ReferenceModel) =>
        <option key={model.id} value={model.id} disabled={!model.available}>{model.label}{model.available ? "" : " - unavailable"}</option>)}
    </select>
    {state.kind === "error" && <span className="error">{state.message}</span>}
  </label>;
}

export function ReferenceAvailability(): ReactElement {
  const state = useModels();
  return <section>
    <h2>Reference models for meshes and textures</h2>
    <p className="muted">Choose these when creating a 3D reference, editing its appearance, or retexturing a static mesh. Shared checkpoints are read-only.</p>
    {state.kind === "loading" ? <p>Checking local models...</p> : state.kind === "error" ? <p className="error">{state.message}</p> :
      <ul>{state.models.map((model: ReferenceModel) => <li key={model.id}>{model.label}: {model.available ? "Available locally" : model.detail}</li>)}</ul>}
  </section>;
}

export function ReferenceWorkflowForm(props: Readonly<{
  mode: "generate" | "edit" | "texture";
  asset: string;
  version: Meta;
  versions: Meta[];
  chain: Chain;
}>): ReactElement {
  const editing = props.mode !== "generate";
  const [model, setModel] = useState(editing ? "qwen-edit" : "krea-anime");
  const lineage = ancestors(props.versions, props.version);
  const brief = lineage.find((version: Meta) => version.step === "brief");
  const [prompt, setPrompt] = useState(editing ? "" : String(brief?.params.prompt ?? ""));
  const [seed, setSeed] = useState("");
  const [denoise, setDenoise] = useState(0.55);
  const [textureSize, setTextureSize] = useState(1024);
  const references = props.versions.filter((version: Meta) => hasImage(version) && !hasGlb(version) &&
    ["reference", "prep", "upload", "canon"].includes(version.step));
  const textureParent = props.versions.find((version: Meta) => version.version === props.version.params.image);
  const preferred = ancestors(props.versions, textureParent ?? props.version).find((version: Meta) =>
    ["reference", "upload", "canon"].includes(version.step) && hasImage(version));
  const [reference, setReference] = useState(preferred?.version ?? references[0]?.version ?? "");
  const [busy, run] = useBusy();
  const validSeed = seed === "" || (Number.isSafeInteger(Number(seed)) && Number(seed) >= 0);
  const submit = (): void => {
    run(async () => {
      const chosenSeed = seed === "" ? Math.floor(Math.random() * 2**31) : Number(seed);
      const parent = props.mode === "texture" ? reference : props.version.version;
      const changed = await props.chain(props.asset, parent, [["reference", {
        model, op: editing ? "edit" : "image", prompt, count: 1, seed: chosenSeed,
        ...(editing && (model === "flux-ghibli" || model === "krea-genesis") ? { denoise } : {}),
      }]]);
      if (props.mode !== "texture" || changed === null) return;
      const prepared = await props.chain(props.asset, changed, [["prep", {}]]);
      if (prepared === null) return;
      await props.chain(props.asset, props.version.version, [["trellis2", {
        op: "texture", image: prepared, resolution: 1024, texture_size: textureSize, steps: 12, seed: chosenSeed,
      }]]);
    });
  };
  const title = props.mode === "texture" ? "Edit the reference and retexture this mesh" : editing ? "Edit this reference" : "Generate a local model reference";
  return <details data-mode={props.mode}>
    <summary>{title}</summary>
    <div className="stack">
      <ReferenceModelSelect value={model} onChange={setModel} mode={editing ? "edit" : "generate"} />
      {props.mode === "texture" && <label>Reference to edit<select value={reference} onChange={(event: ChangeEvent<HTMLSelectElement>) => setReference(event.target.value)}>
        {references.map((version: Meta) => <option key={version.version} value={version.version}>{version.version}: {label(version)}</option>)}
      </select></label>}
      <label>{model === "flux-ghibli" ? "Resulting appearance" : editing ? "Requested appearance change" : "Reference description"}
        <textarea rows={4} value={prompt} onChange={(event: ChangeEvent<HTMLTextAreaElement>) => setPrompt(event.target.value)}
          placeholder={model === "flux-ghibli" ? "Describe the visible materials, painted shapes, palette and finish of the resulting image." : editing ? "Keep the pose, framing and design. Change only the jacket from blue to red." : "Full-body A-pose, separated limbs, plain background and even lighting."} />
      </label>
      <label>Seed (blank for random)<input value={seed} onChange={(event: ChangeEvent<HTMLInputElement>) => setSeed(event.target.value)} inputMode="numeric" /></label>
      {editing && (model === "flux-ghibli" || model === "krea-genesis") && <label>Image-to-image strength (denoise): {denoise.toFixed(2)}
        <input type="range" min="0.1" max="0.9" step="0.05" value={denoise} onChange={(event) => setDenoise(Number(event.target.value))} /></label>}
      {props.mode === "texture" && <label>Rebuilt atlas size<select value={textureSize} onChange={(event) => setTextureSize(Number(event.target.value))}>
        <option value={1024}>1024</option><option value={2048}>2048</option><option value={4096}>4096</option>
      </select></label>}
      {props.mode === "texture" && <p className="muted">Creates an edited reference, removes its background, then transfers new textures onto this mesh's existing geometry and UVs. Use before rigging; keep the pose and framing unchanged.</p>}
      <button type="button" disabled={busy || !prompt.trim() || !validSeed || (props.mode === "texture" && !reference)} onClick={submit}>
        {busy ? "Working..." : props.mode === "texture" ? "Edit reference and apply textures" : editing ? "Create edited reference" : "Generate reference"}
      </button>
    </div>
  </details>;
}
