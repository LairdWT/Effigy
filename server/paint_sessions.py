"""Single backend owner of revisioned multi-view paint sessions."""
from __future__ import annotations

import copy
import re
import threading
import uuid
from pathlib import Path

from server import library
from server.authoring_contracts import AuthoringProfile, ReviewDecision, SourceRole
from server.finish_contracts import FinishPlan, FinishSettings
from server.library import ApiError
from server.paint_contracts import PERMISSION_PROJECTION, Strategy, joint_group

_lock = threading.RLock()
IDENTITY = re.compile(r"^[a-f0-9]{16}$")
AUTHORING_EXPORTS: tuple[str, ...] = ("handoff", "heal_mask", "heal_mask:shells")
AUTHORING_ACTIONS: dict[str, str] = {"heal_mask:shells": "heal_mask", "reconstruct_heal": "reconstruct"}


def path(asset_id: str, session_id: str) -> Path:
    root = library.asset_dir(asset_id).resolve()
    if not IDENTITY.fullmatch(session_id):
        raise ApiError(400, "bad_session", "Invalid paint session identity")
    folder = (root / "_paint_sessions" / session_id).resolve()
    if not folder.is_relative_to(root):
        raise ApiError(400, "bad_path", "Paint session escapes its asset")
    return folder / "session.json"


def _save(asset_id: str, state: dict) -> None:
    library._write(path(asset_id, state["id"]), state)


def _load(asset_id: str, session_id: str) -> dict:
    file = path(asset_id, session_id)
    if not file.is_file():
        raise ApiError(404, "not_found", "Paint session does not exist")
    state = library._read(file)
    for owner, publication, binding, parameter in (
        (state, "applied", "applied_preview", "preview"),
        (state.get("authoring"), "published", "published_candidate", "candidate"),
    ):
        if owner is None or binding in owner:
            continue
        version = owner.get(publication)
        if version is None:
            owner[binding] = None
            continue
        meta = library._read(library.version_dir(asset_id, version) / "meta.json")
        owner[binding] = meta["params"].get(parameter)
    if state.get("mask_version") is not None and state.get("permission_projection") is None:
        mask = library.version_dir(asset_id, state["mask_version"])
        manifest = library._read(library.resolve_output(mask, "manifest"))
        state["permission_projection"] = manifest.get("permission_projection", "legacy_v1")
    return state


def create(asset_id: str, source: str, recipe: dict, front_yaw: float, faces: list[int] | None,
           reuse_session: str | None = None, strategy: Strategy = "pairs", selection_source: str | None = None,
           panel_size: int = 512) -> dict:
    if panel_size not in (192, 256, 384, 512):
        raise ApiError(400, "unsupported_resolution", "Choose192,256,384 or512 pixels per camera")
    if panel_size != 512 and (strategy != "whole_sheet" or recipe["model"] != "moss-turbo"):
        raise ApiError(400, "unsupported_resolution", "Smaller camera panels currently require MOSS whole-sheet painting")
    source_dir = library.version_dir(asset_id, source)
    library.resolve_output(source_dir, "mesh")
    state = {
        "schema": 1 if strategy == "pairs" else 2, "strategy": strategy, "panel_size": 704 if strategy == "pairs" else panel_size,
        "id": uuid.uuid4().hex[:16], "revision": 0, "selection_source": selection_source,
        "source": source, "geometry_revision": library.geometry_revision(source_dir),
        "recipe": recipe, "recipe_revision": 0, "front_yaw": front_yaw,
        "initial_faces": faces, "capture": None, "mask_version": None, "mask_overlay": None,
        "views": [], "groups": [], "results": {}, "excluded": [], "group_instructions": {},
        "preview": None, "applied": None, "active": None,
        "retained_versions": [source], "error": None, "candidates": [],
    }
    with _lock:
        if selection_source is not None:
            selection_dir = library.version_dir(asset_id, selection_source)
            if library.geometry_revision(selection_dir) != state["geometry_revision"]:
                raise ApiError(409, "incompatible_selection", "Selection geometry differs from the source")
            library.resolve_output(selection_dir, "mask")
            _retain(state, selection_source)
        if recipe["style_image"] is not None:
            library.resolve_output(library.version_dir(asset_id, recipe["style_image"]), "image")
            _retain(state, recipe["style_image"])
        if reuse_session is not None:
            previous = get(asset_id, reuse_session)
            if previous["source"] != source or previous["capture"] is None or previous["active"] is not None:
                raise ApiError(409, "incompatible_session", "Reuse requires an idle captured session from the exact source")
            if (previous.get("strategy", "pairs") == "pairs") != (strategy == "pairs"):
                raise ApiError(409, "incompatible_layout", "Legacy pairs use 704 pixels. Create a new 512 capture using Selection source; the pair session remains unchanged.")
            previous_size = previous.get("panel_size", 704 if strategy == "pairs" else 512)
            if previous_size != state["panel_size"]:
                raise ApiError(409, "incompatible_resolution", "Camera size changed; create a new capture using the saved selection")
            for key in ("capture", "mask_version", "views", "groups", "coverage", "front_yaw", "initial_faces"):
                state[key] = copy.deepcopy(previous[key])
            for version in (state["capture"], state["mask_version"]):
                _retain(state, version)
            state["mask_overlay"] = previous.get("mask_overlay")
            state["permission_projection"] = previous.get("permission_projection")
            state["working_views"] = previous.get("working_views", [])
            if strategy != "pairs":
                keys = [v["id"] for v in state["views"] if v["texels"] > 0] if strategy == "synchronized" else state["working_views"]
                try:
                    state["groups"] = [joint_group(keys, strategy, state["panel_size"])]
                except ValueError as error:
                    raise ApiError(400, "unsupported_layout", str(error)) from error
        file = path(asset_id, state["id"])
        file.parent.mkdir(parents=True, exist_ok=False)
        _save(asset_id, state)
    return state


def _retain(state: dict, version: str) -> None:
    if version not in state["retained_versions"]:
        state["retained_versions"].append(version)


def _reconcile(asset_id: str, state: dict) -> bool:
    from server import jobs

    active = state["active"]
    if active is None:
        return False
    changed = False
    finishing = state.get("finishing")
    if finishing and finishing.get("run"):
        folder = library.asset_dir(asset_id) / finishing["run"]
        checkpoint = folder / "checkpoint.json"
        if checkpoint.is_file():
            record = library._read(checkpoint)
            finishing["progress"] = {key: record.get(key) for key in ("stage", "completed", "accepted", "rejected", "corrections")}
            finishing["progress"]["retained"] = record.get("retained", record.get("accepted", 0))
        receipt = folder / "finish_result.json"
        if receipt.is_file() and finishing.get("preview") is None:
            payload = library._read(receipt)
            if error := jobs._check_outputs(folder, payload):
                raise ApiError(409, "bad_finish_result", error)
            if not (folder / "meta.json").is_file():
                meta = library.write_meta(folder, state["source"], finishing["run_params"], payload)
                jobs.publish("version_created", {"asset_id": asset_id, "meta": meta})
            finishing["preview"], finishing["status"] = folder.name, "ready"
            summary = library._read(folder / "finish.json")
            finishing["unaddressed_pairs"] = summary.get("unaddressed_reachable_pairs")
            finishing["unreachable_pairs"] = summary.get("unreachable_pairs")
            _retain(state, folder.name)
            changed = True
    for group in active.get("allocated", []):
        folder = library.asset_dir(asset_id) / group["version"]
        receipt = folder / "group_result.json"
        if not receipt.is_file():
            continue
        if not (folder / "meta.json").is_file():
            payload = library._read(receipt)
            if error := jobs._check_outputs(folder, payload):
                raise ApiError(409, "bad_result", error)
            meta = library.write_meta(folder, state["source"], group["params"], payload)
            jobs.publish("version_created", {"asset_id": asset_id, "meta": meta})
        current = state["results"].get(group["id"])
        if current and current["version"] == group["version"]:
            continue
        state["results"][group["id"]] = {
            "version": group["version"], "recipe_revision": state["recipe_revision"],
            "valid": True,
        }
        for candidate in state.get("candidates", []):
            if candidate["version"] == group["version"]:
                candidate["status"] = "complete"
        _retain(state, group["version"])
        changed = True
    job = jobs.JOBS.get(active["job"])
    if job is not None and job.status in ("queued", "running"):
        return changed
    if job is None:
        state["error"] = ("The previous server stopped. Completed patches were recovered; resume missing work."
                          if active["action"] == "finish" else
                          "The previous server stopped. Completed groups were recovered; resume missing work.")
    elif job.status != "done":
        cancelled = ("Finishing was cancelled; completed patches remain available."
                     if active["action"] == "finish" else "Painting was cancelled; completed groups remain available.")
        state["error"] = (job.error or {}).get("message", cancelled)
    else:
        version = job.version
        meta = library._read(library.version_dir(asset_id, version) / "meta.json")
        _retain(state, version)
        action = active["action"]
        if action in ("capture", "select"):
            manifest = library._read(library.resolve_output(library.version_dir(asset_id, version), "manifest"))
            state["mask_version"] = version
            state["panel_size"] = manifest.get("panel_size", 704 if state.get("strategy", "pairs") == "pairs" else 512)
            state["mask_overlay"] = version if "selection_atlas" in meta["outputs"] else None
            state["views"], state["groups"] = manifest["views"], manifest["groups"]
            state["coverage"] = manifest["coverage"]
            state["sampling"] = manifest.get("sampling")
            state["sampling_profile_revision"] = meta["params"].get("authoring_revision")
            state["permission_projection"] = manifest.get("permission_projection", "legacy_v1")
            state["working_views"] = manifest.get("working_views", [])
            state["limitation"] = manifest.get("limitation")
            if action == "capture":
                state["capture"] = version
            invalid = set(meta["metrics"].get("invalidated_groups", [g["id"] for g in state["groups"]]))
            for key, result in state["results"].items():
                if key in invalid:
                    result["valid"] = False
            state["preview"] = None
            if state.get("strategy", "pairs") != "pairs":
                for result in state["results"].values():
                    result["valid"] = False
        elif action == "preview":
            state["preview"] = version
            for candidate in state.get("candidates", []):
                if candidate["version"] in [c["version"] for c in meta["params"].get("candidates", [])]:
                    candidate["preview"] = version
        elif action == "diagnostic":
            key = "source_diagnostic" if meta["params"].get("diagnostic_mode") == "source" else "diagnostic"
            state[key] = version
        elif action == "apply":
            state["applied"] = version
            state["applied_preview"] = meta["params"]["preview"]
        elif action == "finish_plan":
            if state.get("finishing"):
                state.setdefault("finish_history", []).append(state["finishing"])
            state["finishing"] = {"plan": version, "run": None, "preview": None, "applied": None,
                                  "status": "planned", "progress": None}
        elif action == "finish_apply":
            state["finishing"]["applied"] = version
        elif action == "authoring_reconstruct":
            state["authoring"]["preview"] = version
        elif action == "authoring_publish":
            state["authoring"]["published"] = version
            state["authoring"]["published_candidate"] = meta["params"]["candidate"]
        elif action == "authoring_handoff":
            state["authoring"]["handoff"] = version
        elif action == "authoring_heal_mask":
            state["authoring"]["heal_mask"] = version
        state["error"] = None
    if active["action"] == "finish" and state["finishing"].get("preview") is None:
        state["finishing"]["status"] = "interrupted"
    state["active"] = None
    for candidate in state.get("candidates", []):
        if candidate["status"] == "running":
            candidate["status"] = "interrupted"
    state["revision"] += 1
    return True


def get(asset_id: str, session_id: str) -> dict:
    with _lock:
        state = _load(asset_id, session_id)
        if _reconcile(asset_id, state):
            _save(asset_id, state)
        return copy.deepcopy(state)


def list_sessions(asset_id: str) -> list[dict]:
    folder = library.asset_dir(asset_id) / "_paint_sessions"
    if not folder.exists():
        return []
    return [get(asset_id, p.parent.name) for p in sorted(folder.glob("*/session.json"))]


def _editable(state: dict, revision: int) -> None:
    if state["active"] is not None:
        raise ApiError(409, "busy", "A session action is running; wait or cancel its job")
    if revision != state["revision"]:
        raise ApiError(409, "stale_session", "Session changed; reload it before editing")


def set_authoring(asset_id: str, session_id: str, revision: int, profile: AuthoringProfile) -> dict:
    """Opt into authoring contracts without rewriting legacy sessions."""
    with _lock:
        state: dict = get(asset_id, session_id)
        _editable(state, revision)
        if profile.preparation.source != state["source"]:
            raise ApiError(409, "different_source", "Create a new session for a different prepared source")
        if profile.preparation.geometry_revision != state["geometry_revision"]:
            raise ApiError(409, "stale_geometry", "The profile names a different geometry revision")
        for binding in profile.sources:
            folder: Path = library.version_dir(asset_id, binding.version)
            meta: dict = library._read(folder / "meta.json")
            if binding.role in (SourceRole.ORIGINAL, SourceRole.ACCEPTED, SourceRole.WORKING, SourceRole.DONOR):
                library.resolve_output(folder, "mesh")
            elif not (meta.get("outputs") or meta.get("output_refs")):
                raise ApiError(400, "missing_reference", "The named reference has no completed output")
        encoded: dict = profile.model_dump(mode="json")
        previous: dict | None = state.get("authoring")
        if previous is not None and previous["profile"] == encoded:
            return state
        profile_revision: int = 1 if previous is None else previous["revision"] + 1
        state["authoring"] = {
            "revision": profile_revision, "profile": encoded,
            "reviews": [] if previous is None else previous["reviews"],
            "submissions": [] if previous is None else previous["submissions"],
            "preferred": None if previous is None else previous.get("preferred"),
            "accepted": None if previous is None else previous.get("accepted"),
            "handoff": None if previous is None else previous.get("handoff"),
            "heal_mask": None if previous is None else previous.get("heal_mask"),
        }
        for binding in profile.sources:
            _retain(state, binding.version)
        for result in state["results"].values():
            result["valid"] = False
        state["preview"] = None
        state["sampling_profile_revision"] = None
        previous_finish = state.pop("finishing", None)
        if previous_finish is not None:
            state.setdefault("finish_history", []).append(previous_finish)
        state["revision"] += 1
        _save(asset_id, state)
        return state


def review_authoring(asset_id: str, session_id: str, revision: int, review: ReviewDecision) -> dict:
    with _lock:
        state: dict = get(asset_id, session_id)
        _editable(state, revision)
        authoring: dict | None = state.get("authoring")
        if authoring is None or review.profile_revision != authoring["revision"]:
            raise ApiError(409, "stale_profile", "Reload the authoring profile before recording this review")
        if review.version not in state["retained_versions"]:
            raise ApiError(400, "unrelated_review", "Review a mesh retained by this session")
        library.resolve_output(library.version_dir(asset_id, review.version), "mesh")
        authoring["reviews"].append(review.model_dump(mode="json"))
        if review.verdict in ("preferred", "accepted"):
            authoring[review.verdict] = review.version
        else:
            for key in ("preferred", "accepted"):
                if authoring.get(key) == review.version:
                    authoring[key] = None
        state["revision"] += 1
        _save(asset_id, state)
        return state


def _published_result(asset_id: str, state: dict, publication: str | None,
                      candidate: str | None, parameter: str) -> dict | None:
    if publication is None or candidate is None:
        return None
    folder = library.version_dir(asset_id, publication)
    meta: dict = library._read(folder / "meta.json")
    if meta.get("parent") != state["source"] or meta["params"].get(parameter) != candidate:
        return None
    library.resolve_output(folder, "mesh")
    return {"outcome": "already_converged", "job_id": None, "version": publication, "session": state}


def authoring_action(asset_id: str, session_id: str, revision: int, operation: str) -> dict:
    from server import jobs

    with _lock:
        state: dict = get(asset_id, session_id)
        _editable(state, revision)
        authoring: dict | None = state.get("authoring")
        if authoring is None or (state["mask_version"] is None and operation not in AUTHORING_EXPORTS):
            raise ApiError(409, "missing_authoring_input", "Save a profile and capture the selected surface first")
        profile = AuthoringProfile.model_validate(authoring["profile"])
        if profile.method == "generated" and operation not in AUTHORING_EXPORTS:
            raise ApiError(400, "wrong_method", "Use Generate for a model edit; select a deterministic method for reconstruction")
        params: dict = {"session_id": session_id, "source": state["source"], "mask_version": state["mask_version"],
                       "authoring_revision": authoring["revision"], "authoring_profile": authoring["profile"],
                       "method": profile.method.value, "dependencies": [state["source"], state["mask_version"]]}
        if operation == "reconstruct":
            donors = [binding.version for binding in profile.sources if binding.role == SourceRole.DONOR]
            if len(donors) != 1:
                raise ApiError(400, "missing_donor", "Register one saved donor mesh, including a Blender-painted return")
            params.update(op="reconstruct", donor=donors[0])
            params["dependencies"].append(donors[0])
        elif operation == "publish":
            candidate = authoring.get("preview")
            if candidate is None:
                raise ApiError(409, "missing_preview", "Build and review the reconstruction first")
            meta: dict = library._read(library.version_dir(asset_id, candidate) / "meta.json")
            if meta["params"].get("authoring_revision") != authoring["revision"]:
                raise ApiError(409, "stale_preview", "The reconstruction belongs to an older authoring profile")
            existing = _published_result(asset_id, state, authoring.get("published"), candidate, "candidate")
            if existing is not None:
                return existing
            params.update(op="publish", candidate=candidate)
            params["dependencies"].append(candidate)
            candidate_mask: str | None = meta["params"].get("mask_version")
            if candidate_mask is None:
                raise ApiError(409, "missing_preview_mask", "The reviewed reconstruction does not name its permission mask")
            params["mask_version"] = candidate_mask
            if candidate_mask not in params["dependencies"]:
                params["dependencies"].append(candidate_mask)
        elif operation == "handoff":
            framing: list[dict] = [{"id": row["id"], "view": row["view"]} for row in state["views"][:1]]
            params.update(op="handoff", front_yaw=state["front_yaw"], views=framing)
            params["dependencies"] = [v for v in (state["source"], state["mask_version"]) if v]
        elif operation in ("heal_mask", "heal_mask:shells"):
            heal_framing: list[dict] = [{"id": row["id"], "view": row["view"]} for row in state["views"][:1]]
            params.update(op="heal_mask", mode="shells" if operation == "heal_mask:shells" else "writers",
                          front_yaw=state["front_yaw"], views=heal_framing)
            params["dependencies"] = [state["source"]]
        elif operation == "reconstruct_heal":
            heal: str | None = authoring.get("heal_mask")
            if heal is None:
                raise ApiError(409, "missing_heal_mask", "Mark a seam-heal zone before reconstructing it")
            heal_donors: list[str] = [binding.version for binding in profile.sources if binding.role == SourceRole.DONOR]
            if len(heal_donors) != 1:
                raise ApiError(400, "missing_donor", "Register one saved donor mesh, including a Blender-painted return")
            params.update(op="reconstruct", donor=heal_donors[0], mask_version=heal)
            params["dependencies"] = [state["source"], heal, heal_donors[0]]
        else:
            raise ApiError(400, "bad_action", "Choose reconstruct, publish, handoff, heal_mask, heal_mask:shells or reconstruct_heal")
        job, _ = jobs.submit(asset_id, "uv_context", state["source"], params, start=False)
        state["active"] = {"job": job.id, "action": f"authoring_{AUTHORING_ACTIONS.get(operation, operation)}", "allocated": []}
        state["revision"] += 1
        try:
            _save(asset_id, state)
        except OSError:
            jobs.cancel(job.id)
            raise
        jobs.start_job(job)
        return {"job_id": job.id, "session": state}


def _reserve_authoring(state: dict, count: int, key: str) -> None:
    authoring = state.get("authoring")
    if authoring is None or count == 0:
        return
    if any(row["key"] == key for row in authoring["submissions"]):
        return
    used = sum(row["count"] for row in authoring["submissions"])
    budget = authoring["profile"]["submission_budget"]
    if used + count > budget:
        raise ApiError(409, "authoring_budget", f"This operation reserves {count} model calls; {used}/{budget} are already reserved. Review completed work or explicitly revise the budget, up to12.")
    authoring["submissions"].append({"key": key, "count": count, "profile_revision": authoring["revision"]})


def update(asset_id: str, session_id: str, revision: int, recipe: dict | None,
           excluded: list[str] | None, group_instructions: dict[str, str] | None = None,
           candidate_version: str | None = None, candidate_review: tuple[str, bool] | None = None) -> dict:
    with _lock:
        state = get(asset_id, session_id)
        _editable(state, revision)
        if candidate_review is not None:
            if candidate_version is not None or recipe is not None:
                raise ApiError(400, "ambiguous_candidate", "Review a candidate separately from choosing or editing it")
            version, rejected = candidate_review
            candidate = next((c for c in state.get("candidates", []) if c["version"] == version), None)
            if candidate is None or candidate["status"] != "complete":
                raise ApiError(409, "incomplete_candidate", "Only a completed candidate can be reviewed")
            candidate["excluded"] = rejected
            selected = state["results"].get("complete")
            if rejected and selected and selected["version"] == version:
                selected["valid"] = False
                state["preview"] = None
        if candidate_version is not None:
            candidate = next((c for c in state.get("candidates", []) if c["version"] == candidate_version), None)
            if candidate is None or candidate["status"] != "complete":
                raise ApiError(409, "incomplete_candidate", "Choose a completed whole-set candidate")
            if candidate.get("excluded", False):
                raise ApiError(409, "excluded_candidate", "Restore this candidate before choosing it for Apply")
            authoring = state.get("authoring")
            if authoring is not None and candidate.get("authoring_revision") != authoring["revision"]:
                raise ApiError(409, "stale_authoring_candidate", "This candidate belongs to another appearance profile; its historical output remains available")
            if candidate["mask_version"] != state["mask_version"] or candidate["layout"] != state["groups"][0].get("layout"):
                raise ApiError(409, "stale_candidate", "This candidate belongs to a different selection or layout")
            if recipe is not None:
                raise ApiError(400, "ambiguous_candidate", "Select a complete candidate separately from editing its recipe")
            state["recipe"] = copy.deepcopy(candidate["recipe"])
            state["recipe_revision"] += 1
            state["results"]["complete"] = {"version": candidate_version, "recipe_revision": state["recipe_revision"], "valid": True}
            state["preview"] = candidate.get("preview")
        if recipe is not None and recipe != state["recipe"]:
            if recipe["style_image"] is not None:
                library.resolve_output(library.version_dir(asset_id, recipe["style_image"]), "image")
                _retain(state, recipe["style_image"])
            state["recipe"] = recipe
            state["recipe_revision"] += 1
            for result in state["results"].values():
                result["valid"] = False
            state["preview"] = None
        if group_instructions is not None:
            known = {g["id"] for g in state["groups"]}
            if not group_instructions.keys() <= known or any(len(v) > 10000 for v in group_instructions.values()):
                raise ApiError(400, "bad_group", "Instructions must name existing groups and remain within 10000 characters")
            instructions = state.setdefault("group_instructions", {})
            for group_id, instruction in group_instructions.items():
                if instructions.get(group_id, "") == instruction:
                    continue
                instructions[group_id] = instruction
                if group_id in state["results"]:
                    state["results"][group_id]["valid"] = False
                state["preview"] = None
        if excluded is not None:
            if state.get("strategy", "pairs") != "pairs" and excluded:
                raise ApiError(400, "atomic_candidate", "Whole-set candidates cannot exclude individual views")
            known = {g["id"] for g in state["groups"]}
            if not set(excluded) <= known:
                raise ApiError(400, "bad_group", "Excluded group is not in this capture set")
            state["excluded"] = sorted(set(excluded))
            state["preview"] = None
        state["revision"] += 1
        _save(asset_id, state)
        return state


def _finish_action(asset_id: str, state: dict, request: dict, params: dict) -> tuple[str, dict]:
    state["purpose"] = "finish"
    operation = request["action"]
    authoring = state.get("authoring")
    if authoring is not None and authoring["profile"]["method"] != "generated":
        raise ApiError(409, "wrong_method", "Automatic finishing is a model edit; create an explicit generated finishing pass")
    mask_version = state["mask_version"] or state.get("selection_source")
    if state["recipe"]["model"] not in ("fibo2-turbo", "krea-genesis"):
        raise ApiError(400, "finish_model", "Automatic finishing supports FIBO2 Turbo or Genesis")
    if state["recipe"]["feather"] != 0 or state["recipe"]["style_image"] is not None:
        raise ApiError(400, "finish_recipe", "Finishing uses hard boundaries and captured appearance: set feather0 and no style image")
    if mask_version is not None:
        mask = library.version_dir(asset_id, mask_version)
        if library.geometry_revision(mask) != state["geometry_revision"]:
            raise ApiError(409, "incompatible_selection", "Finishing selection belongs to different geometry")
        library.resolve_output(mask, "mask")
    params = params | {"mask_version": mask_version, "recipe": copy.deepcopy(state["recipe"])}
    if operation == "finish_plan":
        try:
            options = FinishSettings.from_dict(request.get("finish_options") or {})
        except (TypeError, ValueError) as error:
            raise ApiError(400, "finish_options", str(error)) from error
        return "paint_finish", params | {"op": "plan", "finish_settings": options.to_dict()}
    finishing = state.get("finishing")
    if not finishing:
        raise ApiError(409, "missing_finish_plan", "Plan the seam repairs first")
    folder = library.version_dir(asset_id, finishing["plan"])
    plan = FinishPlan.from_dict(library._read(library.resolve_output(folder, "plan")))
    if (plan.source != state["source"] or plan.geometry_revision != state["geometry_revision"]
            or plan.mask_version != mask_version or plan.recipe != state["recipe"]):
        raise ApiError(409, "stale_finish_plan", "Finishing inputs changed; build a new plan. Completed work remains in history.")
    params.update(plan_version=finishing["plan"], finish_settings=plan.settings.to_dict(),
                  dependencies=[finishing["plan"]])
    if operation == "finish_apply":
        if finishing.get("preview") is None:
            raise ApiError(409, "missing_finish_preview", "Complete and review the finishing draft first")
        preview_meta = library._read(library.version_dir(asset_id, finishing["preview"]) / "meta.json")
        if preview_meta.get("metrics", {}).get("retained_patches", 0) < 1:
            raise ApiError(409, "unchanged_finish", "No repair was retained. The source is unchanged; there is nothing to apply.")
        return "paint_finish", params | {"op": "apply", "preview": finishing["preview"]}
    if not plan.patches:
        raise ApiError(409, "no_finish_patches", "No qualified repair patch was found. Inspect the plan's unresolved regions.")
    if finishing.get("preview") is not None:
        raise ApiError(409, "already_complete", "This finishing pass is complete; review its draft or create a new plan")
    _reserve_authoring(state, len(plan.patches) + plan.settings.correction_budget, "finish:" + finishing["plan"])
    previous_run = finishing.get("run")
    if previous_run is not None:
        previous_folder = library.asset_dir(asset_id) / previous_run
        previous_checkpoint = previous_folder / "checkpoint.json"
        if previous_checkpoint.is_file():
            previous_patches = library._read(previous_checkpoint).get("patches", [])
            interrupted = [patch for patch in previous_patches if patch.get("decision") == "pending" and patch.get("attempts")]
            repeated = sum(not (previous_folder / (patch["attempts"][-1]["stem"] + "-generation.json")).is_file()
                           for patch in interrupted)
            _reserve_authoring(state, repeated, f"finish:{finishing['plan']}:resume:{state['revision']}")
    if finishing.get("run") is None:
        destination = library.new_version(asset_id, "paint_finish")
        finishing["run"] = destination.name
        _retain(state, destination.name)
    params.update(op="finish", model=plan.recipe["model"], run_version=finishing["run"])
    finishing["run_params"] = copy.deepcopy(params)
    finishing["status"] = "running"
    checkpoint = library.asset_dir(asset_id) / finishing["run"] / "checkpoint.json"
    if checkpoint.is_file():
        saved = library._read(checkpoint)
        completed = saved.get("patches", [])
        if (len(completed) == len(plan.patches) and {p.get("id") for p in completed} == {p.id for p in plan.patches}
                and all(p.get("decision") in ("retained", "rejected", "skipped") for p in completed)):
            return "paint_finish", params | {"op": "finalize", "replay_only": True}
    return "paint_finish_generate", params


def action(asset_id: str, session_id: str, request: dict) -> dict:
    from server import jobs

    with _lock:
        state = get(asset_id, session_id)
        _editable(state, request["revision"])
        operation = request["action"]
        strategy = state.get("strategy", "pairs")
        source_dir = library.version_dir(asset_id, state["source"])
        if library.geometry_revision(source_dir) != state["geometry_revision"]:
            raise ApiError(409, "stale_source", "Source geometry changed; create a new session")
        if operation not in ("capture", "finish_plan", "finish", "finish_apply") and state["capture"] is None:
            raise ApiError(409, "missing_capture", "Capture a view set first")
        if operation == "capture" and state["capture"] is not None:
            raise ApiError(409, "fixed_capture", "This capture set is fixed; start another session to change framing")
        params = {
            "op": operation, "session_id": session_id, "source": state["source"],
            "geometry_revision": state["geometry_revision"],
            "capture": state["capture"], "mask_version": state["mask_version"],
            "front_yaw": state["front_yaw"], "initial_faces": state["initial_faces"],
            "feather": state["recipe"]["feather"],
            "strategy": strategy, "selection_source": state.get("selection_source"),
            "panel_size": state.get("panel_size", 704 if strategy == "pairs" else 512),
        }
        authoring = state.get("authoring")
        if authoring is not None:
            params.update(authoring_profile=authoring["profile"], authoring_revision=authoring["revision"])
            params["authoring_prompt"] = AuthoringProfile.model_validate(authoring["profile"]).description(
                instructions=state["recipe"]["model"] == "fibo2-turbo")
        allocated = []
        step = "paint_set"
        if operation in ("finish_plan", "finish", "finish_apply"):
            step, params = _finish_action(asset_id, state, request, params)
        elif operation == "select":
            params.update({k: request[k] for k in ("view_id", "selection", "selection_mode")})
        elif operation == "generate":
            if authoring is not None:
                if authoring["profile"]["method"] != "generated":
                    raise ApiError(400, "wrong_method", "Use the selected source-transfer or Blender brush action")
                if state.get("sampling_profile_revision") != authoring["revision"]:
                    raise ApiError(409, "sampling_stale", "Refresh camera masks to measure the current profile")
                sampling = state.get("sampling")
                if authoring["profile"]["sampling"]["mode"] == "detail" and not (sampling and sampling["detail_admitted"]):
                    raise ApiError(409, "undersampled", "Captured views are below the declared detail sampling floor. Select a smaller material region and recapture, or explicitly choose a study preview.")
            if strategy != "pairs" and state.get("permission_projection") != PERMISSION_PROJECTION:
                raise ApiError(409, "mask_projection_update", "Refresh camera masks before generating. The saved UV selection stays unchanged; previous outputs remain in history.")
            if state.get("limitation"):
                raise ApiError(400, "unsupported_layout", state["limitation"])
            if (state["recipe"]["model"] == "syncmvd") != (strategy == "synchronized"):
                raise ApiError(400, "bad_strategy", "SyncMVD requires synchronized strategy; native editors require whole-sheet or legacy pairs")
            known = {g["id"]: g for g in state["groups"]}
            selected = request["groups"] if request["groups"] is not None else sorted(known)
            if not selected or not set(selected) <= known.keys():
                raise ApiError(400, "bad_group", "Choose existing view groups")
            pending = [key for key in dict.fromkeys(selected) if key not in state["excluded"]
                       and (request["regenerate"] or not state["results"].get(key, {}).get("valid"))]
            _reserve_authoring(state, len(pending), f"generate:{state['revision']}")
            for group_id in dict.fromkeys(selected):
                if group_id in state["excluded"]:
                    continue
                previous = state["results"].get(group_id)
                if previous and previous["valid"] and not request["regenerate"]:
                    continue
                folder = library.new_version(asset_id, "paint_group")
                group_params = params | {"group": known[group_id], "recipe": state["recipe"],
                                         "instruction": state.get("group_instructions", {}).get(group_id, ""),
                                         "dependencies": [v for v in (state["source"], state["capture"], state["mask_version"], state["recipe"]["style_image"]) if v]}
                allocated.append({"id": group_id, "version": folder.name, "params": group_params})
                if strategy != "pairs":
                    candidate_id = uuid.uuid4().hex[:16]
                    group_params["candidate_id"] = candidate_id
                    state.setdefault("candidates", []).append({
                        "id": candidate_id, "version": folder.name, "status": "running",
                        "mask_version": state["mask_version"], "recipe": copy.deepcopy(state["recipe"]),
                        "authoring_revision": authoring["revision"] if authoring is not None else None,
                        "layout": copy.deepcopy(known[group_id]["layout"]), "preview": None,
                    })
            if not allocated:
                raise ApiError(409, "already_complete", "Selected groups are complete or excluded; choose Regenerate to replace them")
            step = "paint_generate"
            params.update(model=state["recipe"]["model"], recipe=state["recipe"], allocated=allocated)
            state["preview"] = None
        elif operation == "diagnostic":
            if not state["groups"]:
                raise ApiError(409, "missing_layout", "Create a supported complete camera layout first")
            params["diagnostic"] = True
            params["diagnostic_mode"] = request.get("diagnostic_mode", "mask")
            params["candidates"] = [{"group": g, "version": state["capture"]} for g in state["groups"]]
        elif operation == "preview":
            included = [g for g in state["groups"] if g["id"] not in state["excluded"]]
            if not included:
                raise ApiError(409, "empty_selection", "Include at least one generated group")
            if any(not state["results"].get(g["id"], {}).get("valid") for g in included):
                raise ApiError(409, "incomplete", "Generate or exclude every remaining group before building the preview")
            params["candidates"] = [{"group": g, "version": state["results"][g["id"]]["version"]} for g in included]
        elif operation == "apply":
            if state["preview"] is None:
                raise ApiError(409, "missing_preview", "Build and review a current combined preview first")
            params["preview"] = state["preview"]
        elif operation != "capture":
            raise ApiError(400, "bad_action", "Unknown paint session action")
        if operation in ("apply", "finish_apply"):
            publication = state.get("applied") if operation == "apply" else state["finishing"].get("applied")
            existing = _published_result(asset_id, state, publication, params["preview"], "preview")
            if existing is not None:
                return existing
        params.setdefault("dependencies", [])
        params["dependencies"].extend(v for v in (state["source"], state["capture"], state["mask_version"],
                                               params.get("preview"), state.get("selection_source")) if v)
        params["dependencies"].extend(c["version"] for c in params.get("candidates", []))
        job, _ = jobs.submit(asset_id, step, state["source"], params, start=False)
        state["active"] = {"job": job.id, "action": operation, "allocated": allocated}
        state["error"] = None
        state["revision"] += 1
        try:
            _save(asset_id, state)
        except OSError:
            jobs.cancel(job.id)
            raise
        jobs.start_job(job)
        return {"job_id": job.id, "session": state}


def observe_job(asset_id: str, session_id: str) -> None:
    get(asset_id, session_id)


def dependencies(asset_id: str) -> set[str]:
    folder = library.asset_dir(asset_id) / "_paint_sessions"
    if not folder.exists():
        return set()
    with _lock:
        rows = [library._read(p) for p in folder.glob("*/session.json")]
    return {v for row in rows for v in row["retained_versions"]}
