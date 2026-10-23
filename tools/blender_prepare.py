"""Private Blender preparation worker. Invoked by uv_context with a saved job."""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path


def prepare(job: dict) -> dict:
    import bpy

    if bpy.app.online_access:
        raise RuntimeError("Preparation requires Blender offline mode")
    config_path: Path = Path(job["tools_config"])
    config: dict = json.loads(config_path.read_text(encoding="utf-8"))
    scripts: Path = Path(config["blenderMcp"]["libraryRoot"]) / "Skills/blender-asset-workflows/scripts"
    if not (scripts / "BlenderUvTools.py").is_file():
        raise RuntimeError("Configured Blender workflow library is unavailable")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(scripts))
    from blender_workflows.contracts import (
        Capability,
        Compatibility,
        ExecutionMode,
        Presence,
        ReviewState,
        UvBinding,
        UvRole,
    )
    from blender_workflows.engine_process import EngineCancellationSignal, EngineLimits
    from blender_workflows.pack_margins import UvpmSolverSettings
    from blender_workflows.session_state import create_blender_session
    from blender_workflows.uv_operation_state import uv_operation_key
    from blender_workflows.uv_runtime import (
        UvProviderBinding,
        UvWorkflowRuntime,
        clear_legacy_uv_runtime,
        configure_legacy_uv_runtime,
    )
    from blender_workflows.uvpm_lifecycle import UvpmEngineBinding
    from BlenderUvTools import (
        Operation,
        Provider,
        ProviderProfile,
        Readiness,
        UvRequest,
        execute_uv_request,
        probe_provider,
        release_prepared_provider,
    )

    bpy.context.preferences.use_preferences_save = False
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    mesh = bpy.data.meshes.new("EffigyPreparedMesh")
    mesh.from_pydata(job["vertices"], [], job["faces"])
    mesh.update()
    obj = bpy.data.objects.new("EffigyPrepared", mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    source_uv = mesh.uv_layers.new(name="SourceUV")
    for loop in mesh.loops:
        source_uv.data[loop.index].uv = job["uv"][loop.vertex_index]
    destination = mesh.uv_layers.new(name="PaintUV", do_init=True)
    if job["operation"] == "pack":
        for value in destination.data:
            value.uv = ((value.uv.x - 0.5) * job["uv_scale"] + 0.5,
                        (value.uv.y - 0.5) * job["uv_scale"] + 0.5)
    mesh.uv_layers.active = destination
    destination.active_render = True
    obj["effigy_source"] = job["source"]
    obj["effigy_geometry_revision"] = job["geometry_revision"]
    bpy.context.scene["effigy_isolated_session"] = True
    bpy.context.scene["effigy_preparation"] = job["source"]
    base = bpy.data.images.load(job["base_image"], check_existing=False)
    base.pack()
    material = bpy.data.materials.new("Source appearance")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    image = nodes.new("ShaderNodeTexImage")
    image.image = base
    uv_node = nodes.new("ShaderNodeUVMap")
    uv_node.uv_map = "SourceUV"
    material.node_tree.links.new(uv_node.outputs["UV"], image.inputs["Vector"])
    material.node_tree.links.new(image.outputs["Color"], nodes.get("Principled BSDF").inputs["Base Color"])
    mesh.materials.append(material)

    def run_provider(provider: Provider, operation: Operation) -> dict:
        module: str = "ZenUV" if provider == Provider.ZEN_UV else "uvpackmaster3"
        addons: dict = config["blenderAddons"]
        package: dict = next(p for p in addons["packages"] if p["module"] == module)
        runtime_root: Path = Path(job["runtime_root"])
        engine: Path | None = config_path.parent / addons["engineDirectory"] if provider == Provider.UVPACKMASTER else None
        profile = ProviderProfile(provider, runtime_root, module, config_path.parent / package["archive"],
                                  tuple(package["version"]), runtime_root / "Temp" / module,
                                  engine, tuple(addons["engineVersion"]) if engine is not None else None)
        binding = None
        if engine is not None:
            binding = UvpmEngineBinding(engine / "win/uvpm.exe", engine / "win", EngineLimits(**addons["engineLimits"]))
        signal = EngineCancellationSignal()
        receipt = probe_provider(profile, engine_binding=binding, cancellation=signal)
        if receipt.readiness != Readiness.READY:
            raise RuntimeError(f"{provider}: {receipt.readiness}: {receipt.detail}")
        request = UvRequest(provider, operation, obj.name, tuple(range(len(obj.data.polygons))),
                            "PaintUV", 1, job["atlas_size"], job["gutter_pixels"],
                            packing_solver=(UvpmSolverSettings(island_clearance_reserve_px=1, border_clearance_reserve_px=1)
                                            if provider == Provider.UVPACKMASTER else UvpmSolverSettings()))
        session = create_blender_session()
        session.attach()
        runtime = None
        try:
            capability = Capability(uv_operation_key(request), Presence.PRESENT, ReviewState.COMPLETE,
                                    Compatibility.COMPATIBLE, (ExecutionMode.INTERACTIVE,))
            runtime = UvWorkflowRuntime(session, (UvProviderBinding(profile, capability, binding),),
                                        (UvBinding(str(obj.session_uid), UvRole.SOURCE, "SourceUV"),
                                         UvBinding(str(obj.session_uid), UvRole.PAINT, "PaintUV", True)))
            configure_legacy_uv_runtime(runtime)
            return execute_uv_request(profile, request)
        finally:
            if runtime is not None:
                clear_legacy_uv_runtime(runtime)
            session.detach()
            release_prepared_provider(profile)

    observations: list[dict] = []
    if job["operation"] == "unwrap":
        observations.append(run_provider(Provider.ZEN_UV, Operation.UNWRAP))
        if obj.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        for value in obj.data.uv_layers["PaintUV"].data:
            value.uv = ((value.uv.x - 0.5) * job["uv_scale"] + 0.5,
                        (value.uv.y - 0.5) * job["uv_scale"] + 0.5)
    observations.append(run_provider(Provider.UVPACKMASTER, Operation.PACK))
    if obj.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    mesh = obj.data
    destination = mesh.uv_layers["PaintUV"]
    corners: list = [[list(destination.data[i].uv) for i in poly.loop_indices] for poly in mesh.polygons]
    positions: list = [list(v.co) for v in mesh.vertices]
    faces: list = [list(poly.vertices) for poly in mesh.polygons]
    if faces != job["faces"]:
        raise RuntimeError("UV provider changed source triangle order")
    if any(max(abs(a-b) for a, b in zip(p, q)) > 1e-6 for p, q in zip(positions, job["vertices"])):
        raise RuntimeError("UV provider changed vertex positions")
    bpy.ops.wm.save_as_mainfile(filepath=job["workfile"], check_existing=False)
    return {"corners": corners, "provider": observations, "blender_version": bpy.app.version_string,
            "source_uv_preserved": True, "geometry_preserved": True}


def main() -> None:
    import bpy

    spec: Path = Path(sys.argv[sys.argv.index("--") + 1])
    job: dict = json.loads(spec.read_text(encoding="utf-8"))

    def execute() -> None:
        result: dict
        try:
            result = {"ok": True, "result": prepare(job)}
        except (RuntimeError, ValueError, TypeError, AttributeError, KeyError, OSError, ImportError, IndexError) as error:
            traceback.print_exc()
            result = {"ok": False, "error": f"{type(error).__name__}: {error}"}
        Path(job["result"]).write_text(json.dumps(result), encoding="utf-8")
        bpy.ops.wm.quit_blender()

    bpy.app.timers.register(execute, first_interval=0.5)


if __name__ == "__main__":
    main()
