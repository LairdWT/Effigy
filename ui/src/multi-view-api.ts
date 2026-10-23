import type { Selection } from "./PaintSelection";
import { fileUrl } from "./api";

export type PaintRecipe = Readonly<{
  model: "fibo2-turbo" | "krea-genesis" | "moss-turbo" | "syncmvd"; prompt: string; materials: string; style: string; preserve: string;
  seed: number; denoise: number; conditioning: "preserve_structure" | "blank_region"; style_image: string | null; feather: number;
  moss_steps: number;
}>;
export type PaintView = Readonly<{ id: string; texels: number; view: Readonly<{ yaw: number; pitch: number; center: [number, number, number]; extent: number }> }>;
export type PaintLayout = Readonly<{ version: number; width: number; height: number; panels: readonly Readonly<{ camera_id: string; x: number; y: number; width: number; height: number }>[] }>;
export type PaintGroup = Readonly<{ id: string; views: readonly string[]; overlap_texels: number; layout: PaintLayout | null }>;
export type PaintStrategy = "pairs" | "whole_sheet" | "synchronized";
export type PaintCandidate = Readonly<{ id: string; version: string; status: string; recipe: PaintRecipe; preview: string | null; mask_version: string; excluded: boolean }>;
export type SourceRole = "original" | "accepted" | "working" | "preferred" | "appearance" | "donor" | "rejected";
export type AuthoringMethod = "generated" | "registered_source" | "blender_brush";
export type MaterialIntent = Readonly<{ id: string; identity: string; faces: readonly number[] | null; palette: string; feature_scale: string; marks: string; preserve: string }>;
export type AuthoringProfile = Readonly<{
  schema_version: 1;
  preparation: Readonly<{ source: string; geometry_revision: string; uv_profile: "padded_islands" | "line_art_square"; atlas_size: number; gutter_pixels: number; pack_rotation: 90 }>;
  sources: readonly Readonly<{ role: SourceRole; version: string; note: string }>[];
  materials: readonly MaterialIntent[];
  sampling: Readonly<{ mode: "detail" | "study"; minimum_samples: number; density_per_metre: number | null; metres_per_unit: number | null; viewing_distance_units: number | null; native_display_pixels: number }>;
  method: AuthoringMethod; operation: "refine_current" | "restore_source" | "restyle";
  style: string; observation: string; preservation: string; submission_budget: number;
}>;
export type AuthoringState = Readonly<{ revision: number; profile: AuthoringProfile; preferred: string | null; accepted: string | null;
  preview: string | null; published: string | null; published_candidate: string | null; submissions: readonly Readonly<{ count: number; key: string }>[];
  handoff: string | null; heal_mask: string | null }>;
export type SamplingReport = Readonly<{ detail_admitted: boolean; reachable_texels: number; unreachable_texels: number;
  undersampled_texels: number; minimum_axis_p10_p50_p90: readonly number[] }>;
export type PreparationReport = Readonly<{ triangles: number; atlas_size: number; bit_depth: number; uv_shells: number;
  degenerate_uv_faces: number; occupancy: number; overlap_check: string; uv_squares: string;
  texels_per_asset_unit_p10_p50_p90: readonly number[];
  exact_clearance: Readonly<{ disposition: string; minimum_island_pixels: number | null; minimum_border_pixels: number | null;
    meets_requested_gap: boolean | null; reason: string | null; overlapping_island_pairs: number | null }> }>;
export type PaintSession = Readonly<{
  authoring: AuthoringState | null; sampling: SamplingReport | null; sampling_profile_revision: number | null;
  purpose: "paint" | "finish";
  id: string; revision: number; source: string; geometry_revision: string; recipe: PaintRecipe; panel_size: number;
  capture: string | null; mask_version: string | null; preview: string | null; applied: string | null; applied_preview: string | null;
  selection_source: string | null;
  retained_versions: readonly string[];
  mask_overlay: string | null;
  permission_projection: string | null;
  diagnostic: string | null;
  strategy: PaintStrategy; candidates: readonly PaintCandidate[]; limitation: string | null;
  views: readonly PaintView[]; groups: readonly PaintGroup[]; excluded: readonly string[];
  results: Readonly<Record<string, Readonly<{ version: string; valid: boolean }>>>;
  group_instructions: Readonly<Record<string, string>>;
  active: Readonly<{ job: string; action: string }> | null; error: string | null;
  coverage: Readonly<{ selected: number; visible: number; unseen: number; unpaired_views: readonly string[] }> | null;
  finishing: Readonly<{ plan: string; run: string | null; preview: string | null; applied: string | null; status: string;
    unaddressed_pairs: number | null; unreachable_pairs: number | null;
    progress: Readonly<{ stage: string; completed: number; retained: number; rejected: number; corrections: number }> | null }> | null;
}>;
export type PaintAction = "capture" | "select" | "generate" | "preview" | "apply" | "diagnostic" | "finish_plan" | "finish" | "finish_apply";
export type PaintActionRequest = Readonly<{
  revision: number; action: PaintAction; groups?: readonly string[]; regenerate?: boolean;
  view_id?: string; selection?: Selection; selection_mode?: "add" | "erase" | "all" | "clear" | "faces" | "refresh";
  finish_options?: Readonly<{ max_patches: number; correction_budget: number; protected_faces: readonly number[] }>;
}>;

function object(value: unknown): Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) throw new Error("Invalid painting response");
  return value as Record<string, unknown>;
}
function text(value: unknown): string {
  if (typeof value !== "string") throw new Error("Painting response is missing text");
  return value;
}
function number(value: unknown): number {
  if (typeof value !== "number" || !Number.isFinite(value)) throw new Error("Painting response is missing a number");
  return value;
}
function array(value: unknown): readonly unknown[] {
  if (!Array.isArray(value)) throw new Error("Painting response is missing a list");
  return value;
}
function nullable(value: unknown): string | null { return value === null ? null : text(value); }

function authoring(value: unknown): AuthoringState | null {
  if (value == null) return null;
  const a = object(value), p = object(a.profile), prep = object(p.preparation), sample = object(p.sampling);
  if (p.schema_version !== 1 || !["generated", "registered_source", "blender_brush"].includes(text(p.method))) throw new Error("Unsupported authoring method");
  if (!["refine_current", "restore_source", "restyle"].includes(text(p.operation))) throw new Error("Unsupported authoring operation");
  if (prep.uv_profile !== "padded_islands" && prep.uv_profile !== "line_art_square") throw new Error("Unknown UV profile");
  if (sample.mode !== "detail" && sample.mode !== "study") throw new Error("Unknown sampling mode");
  if (prep.pack_rotation !== 90) throw new Error("Unsupported pack rotation");
  const sources = array(p.sources).map((raw) => {
    const s = object(raw), role = text(s.role);
    if (!["original", "accepted", "working", "preferred", "appearance", "donor", "rejected"].includes(role)) throw new Error("Unknown source role");
    return { role: role as SourceRole, version: text(s.version), note: text(s.note) };
  });
  const materials = array(p.materials).map((raw): MaterialIntent => {
    const m = object(raw);
    return { id: text(m.id), identity: text(m.identity), faces: m.faces === null ? null : array(m.faces).map(number),
      palette: text(m.palette), feature_scale: text(m.feature_scale), marks: text(m.marks), preserve: text(m.preserve) };
  });
  return { revision: number(a.revision), preferred: nullable(a.preferred ?? null), accepted: nullable(a.accepted ?? null),
    preview: nullable(a.preview ?? null), published: nullable(a.published ?? null),
    published_candidate: nullable(a.published_candidate ?? null),
    handoff: nullable(a.handoff ?? null), heal_mask: nullable(a.heal_mask ?? null),
    submissions: array(a.submissions).map((raw) => { const s = object(raw); return { count: number(s.count), key: text(s.key) }; }),
    profile: { schema_version: 1, preparation: { source: text(prep.source), geometry_revision: text(prep.geometry_revision),
      uv_profile: prep.uv_profile, atlas_size: number(prep.atlas_size), gutter_pixels: number(prep.gutter_pixels), pack_rotation: 90 },
      sources, materials, method: p.method as AuthoringMethod, operation: p.operation as AuthoringProfile["operation"],
      sampling: { mode: sample.mode, minimum_samples: number(sample.minimum_samples),
        density_per_metre: sample.density_per_metre == null ? null : number(sample.density_per_metre),
        metres_per_unit: sample.metres_per_unit == null ? null : number(sample.metres_per_unit),
        viewing_distance_units: sample.viewing_distance_units == null ? null : number(sample.viewing_distance_units),
        native_display_pixels: number(sample.native_display_pixels) }, style: text(p.style), observation: text(p.observation),
      preservation: text(p.preservation), submission_budget: number(p.submission_budget) } };
}

function sampling(value: unknown): SamplingReport | null {
  if (value == null) return null;
  const s = object(value);
  if (typeof s.detail_admitted !== "boolean") throw new Error("Invalid sampling admission");
  return { detail_admitted: s.detail_admitted, reachable_texels: number(s.reachable_texels), unreachable_texels: number(s.unreachable_texels),
    undersampled_texels: number(s.undersampled_texels), minimum_axis_p10_p50_p90: array(s.minimum_axis_p10_p50_p90).map(number) };
}

function layout(value: unknown): PaintLayout | null {
  if (value === undefined || value === null) return null;
  const l = object(value);
  return { version: number(l.version), width: number(l.width), height: number(l.height), panels: array(l.panels).map((value) => {
    const p = object(value);
    return { camera_id: text(p.camera_id), x: number(p.x), y: number(p.y), width: number(p.width), height: number(p.height) };
  }) };
}

function recipe(value: unknown): PaintRecipe {
  const r = object(value);
  if (r.model !== "fibo2-turbo" && r.model !== "krea-genesis" && r.model !== "moss-turbo" && r.model !== "syncmvd") throw new Error("Unknown painting model");
  if (r.conditioning !== "preserve_structure" && r.conditioning !== "blank_region") throw new Error("Unknown editing approach");
  return { model: r.model, prompt: text(r.prompt), materials: text(r.materials), style: text(r.style), preserve: text(r.preserve),
    seed: number(r.seed), denoise: number(r.denoise), conditioning: r.conditioning, style_image: nullable(r.style_image), feather: number(r.feather), moss_steps: number(r.moss_steps ?? 8) };
}

function session(value: unknown): PaintSession {
  const r = object(value);
  const strategy = r.strategy ?? "pairs";
  if (strategy !== "pairs" && strategy !== "whole_sheet" && strategy !== "synchronized") throw new Error("Unknown generation strategy");
  const active = r.active === null ? null : object(r.active);
  const coverage = r.coverage === undefined ? null : object(r.coverage);
  const finish = r.finishing === undefined || r.finishing === null ? null : object(r.finishing);
  const finishProgress = finish?.progress === undefined || finish.progress === null ? null : object(finish.progress);
  const results = Object.fromEntries(Object.entries(object(r.results)).map(([id, raw]) => {
    const result = object(raw);
    if (typeof result.valid !== "boolean") throw new Error("Invalid candidate state");
    return [id, { version: text(result.version), valid: result.valid }];
  }));
  const views = array(r.views).map((raw): PaintView => {
    const row = object(raw), camera = object(row.view), center = array(camera.center).map(number);
    if (center.length !== 3) throw new Error("Invalid captured camera");
    return { id: text(row.id), texels: number(row.texels), view: { yaw: number(camera.yaw), pitch: number(camera.pitch),
      center: [number(center[0]), number(center[1]), number(center[2])], extent: number(camera.extent) } };
  });
  return { id: text(r.id), revision: number(r.revision), source: text(r.source), geometry_revision: text(r.geometry_revision), recipe: recipe(r.recipe),
    authoring: authoring(r.authoring), sampling: sampling(r.sampling), sampling_profile_revision: r.sampling_profile_revision == null ? null : number(r.sampling_profile_revision),
    purpose: r.purpose === "finish" ? "finish" : "paint", selection_source: nullable(r.selection_source ?? null),
    retained_versions: array(r.retained_versions ?? [r.source]).map(text),
    finishing: finish === null ? null : { plan: text(finish.plan), run: nullable(finish.run), preview: nullable(finish.preview),
      applied: nullable(finish.applied), status: text(finish.status),
      unaddressed_pairs: finish.unaddressed_pairs == null ? null : number(finish.unaddressed_pairs),
      unreachable_pairs: finish.unreachable_pairs == null ? null : number(finish.unreachable_pairs),
      progress: finishProgress === null ? null : {
        stage: text(finishProgress.stage ?? "working"), completed: number(finishProgress.completed ?? 0),
        retained: number(finishProgress.retained ?? finishProgress.accepted ?? 0), rejected: number(finishProgress.rejected ?? 0), corrections: number(finishProgress.corrections ?? 0) } },
    strategy, panel_size: number(r.panel_size ?? (strategy === "pairs" ? 704 : 512)), limitation: nullable(r.limitation ?? null),
    candidates: array(r.candidates ?? []).map((value) => { const c = object(value); return {
      id: text(c.id), version: text(c.version), status: text(c.status), recipe: recipe(c.recipe),
      mask_version: text(c.mask_version), preview: nullable(c.preview), excluded: c.excluded === true,
    }; }),
    capture: nullable(r.capture), mask_version: nullable(r.mask_version), preview: nullable(r.preview), applied: nullable(r.applied),
    applied_preview: nullable(r.applied_preview ?? null),
    mask_overlay: nullable(r.mask_overlay ?? null),
    permission_projection: nullable(r.permission_projection ?? null),
    diagnostic: nullable(r.diagnostic ?? null),
    views, results, excluded: array(r.excluded).map(text), error: nullable(r.error),
    group_instructions: Object.fromEntries(Object.entries(r.group_instructions === undefined ? {} : object(r.group_instructions)).map(([key, value]) => [key, text(value)])),
    groups: array(r.groups).map((raw) => { const g = object(raw); return { id: text(g.id), views: array(g.views).map(text), overlap_texels: number(g.overlap_texels), layout: layout(g.layout) }; }),
    active: active === null ? null : { job: text(active.job), action: text(active.action) },
    coverage: coverage === null ? null : { selected: number(coverage.selected), visible: number(coverage.visible), unseen: number(coverage.unseen), unpaired_views: array(coverage.unpaired_views).map(text) } };
}

async function request(path: string, method = "GET", body?: object): Promise<unknown> {
  const response = await fetch(path, { method, headers: { "Content-Type": "application/json" }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
  const data: unknown = await response.json();
  if (!response.ok) {
    const error = object(object(data).error);
    throw new Error(text(error.message));
  }
  return data;
}
const base = (asset: string): string => `/api/assets/${encodeURIComponent(asset)}/paint-sessions`;

export const multiViewApi = {
  preparationReport: async (asset: string, version: string): Promise<PreparationReport> => {
    const r = object(await request(fileUrl(asset, version, "preparation.json")));
    const c = object(r.exact_clearance);
    return { triangles: number(r.triangles), atlas_size: number(r.atlas_size), bit_depth: number(r.bit_depth), uv_shells: number(r.uv_shells),
      degenerate_uv_faces: number(r.degenerate_uv_faces), occupancy: number(r.occupancy), overlap_check: text(r.overlap_check), uv_squares: text(r.uv_squares),
      texels_per_asset_unit_p10_p50_p90: array(r.texels_per_asset_unit_p10_p50_p90).map(number),
      exact_clearance: { disposition: text(c.disposition), minimum_island_pixels: c.minimum_island_pixels == null ? null : number(c.minimum_island_pixels),
        minimum_border_pixels: c.minimum_border_pixels == null ? null : number(c.minimum_border_pixels), meets_requested_gap: typeof c.meets_requested_gap === "boolean" ? c.meets_requested_gap : null,
        reason: nullable(c.reason ?? null), overlapping_island_pairs: c.overlapping_island_pairs == null ? null : number(c.overlapping_island_pairs) } };
  },
  saveAuthoring: async (asset: string, current: PaintSession, profile: AuthoringProfile): Promise<PaintSession> =>
    session(await request(`${base(asset)}/${current.id}/authoring`, "PUT", { revision: current.revision, profile })),
  authoringAction: async (asset: string, current: PaintSession, action: "reconstruct" | "publish" | "handoff" | "heal_mask" | "heal_mask:shells" | "reconstruct_heal"): Promise<PaintSession> =>
    session(object(await request(`${base(asset)}/${current.id}/authoring/actions`, "POST", { revision: current.revision, action })).session),
  reviewAuthoring: async (asset: string, current: PaintSession, version: string, verdict: "preferred" | "accepted" | "rejected", note: string): Promise<PaintSession> =>
    session(await request(`${base(asset)}/${current.id}/authoring/reviews`, "POST", { revision: current.revision,
      review: { version, verdict, reviewer: "owner", note, profile_revision: current.authoring?.revision } })),
  prepare: async (asset: string, source: string, operation: "inspect" | "pack" | "unwrap", gutter: number, scale: number): Promise<string> =>
    text(object(await request(`/api/assets/${asset}/steps/uv_context`, "POST", { parent: source, params: { op: "prepare", operation, gutter_pixels: gutter, uv_scale: scale } })).job_id),
  job: async (id: string): Promise<Readonly<{ status: string; version: string | null; message: string }>> => {
    const j = object(await request(`/api/jobs/${id}`)), e = j.error == null ? null : object(j.error);
    return { status: text(j.status), version: nullable(j.version ?? null), message: e ? text(e.message) : typeof j.text === "string" ? j.text : text(j.status) };
  },
  pullBlender: async (asset: string, version: string): Promise<string> =>
    text(object(await request(`/api/assets/${asset}/blender/pull`, "POST", { version })).version),
  enabled: async (): Promise<boolean> => {
    const response = await fetch("/api/multi-view");
    if (!response.ok) return false;
    const data: unknown = await response.json();
    return object(data).enabled === true;
  },
  list: async (asset: string): Promise<readonly PaintSession[]> => array(await request(base(asset))).map(session),
  get: async (asset: string, id: string): Promise<PaintSession> => session(await request(`${base(asset)}/${id}`)),
  create: async (asset: string, source: string, value: PaintRecipe, yaw: number, faces: readonly number[] | null,
    options: Readonly<{ strategy?: PaintStrategy; reuse_session?: string; selection_source?: string; panel_size?: number }> = {}): Promise<PaintSession> =>
    session(await request(base(asset), "POST", { source, recipe: value, front_yaw: yaw, faces, ...options })),
  update: async (asset: string, current: PaintSession, fields: Readonly<{ recipe?: PaintRecipe; excluded?: readonly string[]; group_instructions?: Readonly<Record<string, string>>; candidate_version?: string; candidate_review?: Readonly<{ version: string; excluded: boolean }> }>): Promise<PaintSession> =>
    session(await request(`${base(asset)}/${current.id}`, "PATCH", { revision: current.revision, ...fields })),
  action: async (asset: string, id: string, body: PaintActionRequest): Promise<PaintSession> =>
    session(object(await request(`${base(asset)}/${id}/actions`, "POST", body)).session),
  cancel: async (job: string): Promise<void> => { await request(`/api/jobs/${job}/cancel`, "POST"); },
  progress: async (job: string): Promise<string> => {
    const result = object(await request(`/api/jobs/${job}`));
    return typeof result.text === "string" && result.text ? result.text : text(result.status);
  },
};
