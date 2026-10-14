"""steps/_bake.py on the CPU: UV rasterization, FlexGEMM-compatible volume sampling, GLB round trip."""

import json
import struct

import numpy as np
import pytest

torch = pytest.importorskip("torch")
from steps._bake import (
    ao_faces,
    ao_texels,
    bake_volume,
    box_filter,
    fill_dark_islands,
    fill_gutters,
    heal_seams,
    rasterize_uv,
    sample_volume,
    seam_delta,
    seams,
    write_glb,
)


def reference_sample(coords, attrs, r, p):
    """FlexGEMM grid_sample_3d trilinear, one point at a time."""
    table = {tuple(c): a for c, a in zip(coords.tolist(), attrs)}
    q = (p + 0.5) * r
    base = np.floor(q - 0.5).astype(int)
    acc, wsum = np.zeros(attrs.shape[1]), 0.0
    for i in range(8):
        c = base + [i & 1, (i >> 1) & 1, (i >> 2) & 1]
        if tuple(c) in table:
            w = np.prod(1 - np.abs(q - c - 0.5))
            acc, wsum = acc + w * table[tuple(c)], wsum + w
    return acc / max(wsum, 1e-12)


def test_sample_volume_matches_flexgemm_semantics():
    rng = np.random.default_rng(0)
    r = 16
    coords = np.unique(rng.integers(0, r, (900, 3)), axis=0)
    attrs = rng.random((len(coords), 6)).astype(np.float32)
    pts = rng.uniform(-0.5, 0.5, (300, 3)).astype(np.float32)
    got = sample_volume(
        torch.tensor(coords), torch.tensor(attrs), r, torch.tensor(pts), chunk=64
    ).numpy()
    want = np.stack([reference_sample(coords, attrs, r, p) for p in pts])
    np.testing.assert_allclose(got, want, atol=1e-5)
    centre = torch.tensor(
        [[-0.5 + 3.5 / r, -0.5 + 4.5 / r, -0.5 + 5.5 / r]]
    )  # voxel (3, 4, 5)'s centre
    lone = sample_volume(torch.tensor([[3, 4, 5]]), torch.tensor([[0.25, 0.5]]), r, centre)
    assert lone.tolist() == [[0.25, 0.5]]


def test_rasterize_covers_the_square_exactly():
    uv = torch.tensor([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=torch.float32)
    faces = torch.tensor([[0, 1, 2], [0, 2, 3]])
    fid, bary = rasterize_uv(uv, faces, 32, budget=100)  # tiny budget: exercises chunking
    assert (fid >= 0).all() and torch.allclose(bary.sum(-1), torch.ones(32, 32))
    pos = (uv[faces[fid]] * bary[..., None]).sum(-2)  # texel centres, recovered from barycentrics
    ys, xs = torch.meshgrid(torch.arange(32), torch.arange(32), indexing="ij")
    assert torch.allclose(pos, torch.stack([xs + 0.5, ys + 0.5], -1) / 32, atol=1e-5)
    half, _ = rasterize_uv(uv, faces[:1], 64)
    assert abs((half >= 0).float().mean().item() - 0.5) < 0.02


def test_bake_constant_volume_into_a_glb(tmp_path):
    verts = torch.tensor([[-0.3, -0.3, 0], [0.3, -0.3, 0], [0.3, 0.3, 0], [-0.3, 0.3, 0]])
    faces = torch.tensor([[0, 1, 2], [0, 2, 3]])
    uv = torch.tensor([[0.05, 0.05], [0.95, 0.05], [0.95, 0.95], [0.05, 0.95]])
    g = torch.stack(torch.meshgrid(*[torch.arange(16)] * 3, indexing="ij"), -1).reshape(-1, 3)
    attrs = torch.tensor([0.8, 0.4, 0.2, 0.0, 0.6, 1.0]).expand(
        len(g), 6
    )  # rgb, metal, rough, alpha
    layout = {"base_color": [0, 3], "metallic": [3, 4], "roughness": [4, 5], "alpha": [5, 6]}
    fid, bary = rasterize_uv(uv, faces, 64)
    rgba, mr, mask = bake_volume(fid, bary, verts, faces, g, attrs, layout, 16)
    assert 0.6 < mask.mean() < 0.9
    assert (rgba == [204, 102, 51, 255]).all() and (mr == [0, 153, 0]).all()  # gutters filled too
    write_glb(tmp_path / "m.glb", verts.numpy(), faces.numpy(), uv.numpy(), rgba, mr)
    data = (tmp_path / "m.glb").read_bytes()
    n = struct.unpack("<I", data[12:16])[0]
    gltf, binary = json.loads(data[20 : 20 + n]), data[28 + n :]
    acc = gltf["accessors"][gltf["meshes"][0]["primitives"][0]["attributes"]["TEXCOORD_0"]]
    view = gltf["bufferViews"][acc["bufferView"]]
    start = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    stored = np.frombuffer(binary[start : start + 8 * acc["count"]], np.float32).reshape(-1, 2)
    np.testing.assert_allclose(
        stored, uv.numpy(), atol=1e-6
    )  # glTF holds exactly the UVs we baked with


def test_bake_lists_the_orm_once_when_it_is_also_the_occlusion(tmp_path):
    """trimesh wrote a picture serving two slots (the ORM as metallic-roughness and as occlusion) as two
    images and two textures over one buffer view, so loaders decoded it twice: one image, one texture, both
    slots on it, the other slots untouched."""
    import trimesh

    verts = np.array([[-0.3, -0.3, 0], [0.3, -0.3, 0], [0.3, 0.3, 0], [-0.3, 0.3, 0]])
    faces = np.array([[0, 1, 2], [0, 2, 3]])
    uv = np.array([[0.05, 0.05], [0.95, 0.05], [0.95, 0.95], [0.05, 0.95]])
    rgba, orm, normal = (np.full((8, 8, c), x, np.uint8) for c, x in ((4, 200), (3, 100), (3, 128)))
    write_glb(tmp_path / "m.glb", verts, faces, uv, rgba, orm, normal_map=normal, occlusion=True)
    data = (tmp_path / "m.glb").read_bytes()
    n = struct.unpack("<I", data[12:16])[0]
    gltf = json.loads(data[20 : 20 + n])
    assert len(gltf["images"]) == 3 and len(gltf["textures"]) == 3  # base, normal, ORM
    m = gltf["materials"][0]
    slots = m["pbrMetallicRoughness"]["baseColorTexture"], m["normalTexture"], m["occlusionTexture"]
    assert (
        m["pbrMetallicRoughness"]["metallicRoughnessTexture"]["index"]
        == m["occlusionTexture"]["index"]
    )
    assert len({s["index"] for s in slots}) == 3
    mat = trimesh.load(tmp_path / "m.glb", force="mesh", process=False).visual.material
    assert np.asarray(mat.baseColorTexture)[0, 0, 0] == 200
    assert np.asarray(mat.metallicRoughnessTexture.convert("RGB"))[0, 0, 0] == 100
    assert np.asarray(mat.occlusionTexture.convert("RGB"))[0, 0, 0] == 100
    assert np.asarray(mat.normalTexture.convert("RGB"))[0, 0, 0] == 128


def test_bake_fills_a_texel_whose_sample_found_no_volume_from_its_neighbours():
    """M23b: a pit the clean rebuild left between hair strands samples empty volume (alpha 0); its colour
    comes from the texels around it instead of black, while the alpha channel keeps the sample."""
    verts = torch.tensor([[-0.3, -0.3, 0], [0.3, -0.3, 0], [0.3, 0.3, 0], [-0.3, 0.3, 0]])
    faces = torch.tensor([[0, 1, 2], [0, 2, 3]])
    uv = torch.tensor([[0.05, 0.05], [0.95, 0.05], [0.95, 0.95], [0.05, 0.95]])
    g = torch.stack(torch.meshgrid(*[torch.arange(16)] * 3, indexing="ij"), -1).reshape(-1, 3)
    hole = (g[:, 0] >= 7) & (g[:, 0] <= 8) & (g[:, 1] >= 7) & (g[:, 1] <= 8)  # four columns absent
    g = g[~hole]
    attrs = torch.tensor([0.8, 0.4, 0.2, 0.0, 0.6, 1.0]).expand(len(g), 6)
    layout = {"base_color": [0, 3], "metallic": [3, 4], "roughness": [4, 5], "alpha": [5, 6]}
    fid, bary = rasterize_uv(uv, faces, 64)
    rgba, _mr, _mask = bake_volume(fid, bary, verts, faces, g, attrs, layout, 16)
    assert (rgba[..., :3] == [204, 102, 51]).all()  # the colour everywhere, the pit included
    assert rgba[32, 32, 3] < 128 < rgba[4, 4, 3]  # the alpha channel still says the pit is empty


def test_rasterize_takes_face_and_barycentrics_from_one_triangle_on_a_shared_edge():
    """Texels on the quad's diagonal are covered by both triangles. face_id and bary must come from the
    same one, or the texel's recovered position is off (the bake sampled outside its hole, run to run)."""
    uv = torch.tensor([[0.05, 0.05], [0.95, 0.05], [0.95, 0.95], [0.05, 0.95]])
    faces = torch.tensor([[0, 1, 2], [0, 2, 3]])
    for _ in range(20):
        fid, bary = rasterize_uv(uv, faces, 64)  # the default budget: both triangles in one chunk
        m = fid >= 0
        pos = (uv[faces[fid[m]]] * bary[m][..., None]).sum(-2)
        ys, xs = torch.nonzero(m, as_tuple=True)
        assert torch.allclose(pos, torch.stack([xs + 0.5, ys + 0.5], -1) / 64, atol=1e-5)


def test_supersample_box_filters_a_one_texel_checker():
    checker = ((np.indices((4, 4)).sum(0) % 2) * 200).astype(np.uint8)[..., None]
    img, covered = box_filter(checker, np.ones((4, 4), bool), 2)
    assert (img == 100).all() and covered.all()  # each block: two 0 and two 200
    w = np.zeros((4, 4), bool)
    w[0, 1] = True  # one covered sample in the first block: the block takes just that one
    img, covered = box_filter(checker, w, 2)
    assert img[0, 0, 0] == 200 and covered.tolist() == [[True, False], [False, False]]


def test_supersampled_constant_volume_bakes_the_same_colour():
    verts = torch.tensor([[-0.3, -0.3, 0], [0.3, -0.3, 0], [0.3, 0.3, 0], [-0.3, 0.3, 0]])
    faces = torch.tensor([[0, 1, 2], [0, 2, 3]])
    uv = torch.tensor([[0.05, 0.05], [0.95, 0.05], [0.95, 0.95], [0.05, 0.95]])
    g = torch.stack(torch.meshgrid(*[torch.arange(16)] * 3, indexing="ij"), -1).reshape(-1, 3)
    attrs = torch.tensor([0.8, 0.4, 0.2, 0.0, 0.6, 1.0]).expand(len(g), 6)
    layout = {"base_color": [0, 3], "metallic": [3, 4], "roughness": [4, 5], "alpha": [5, 6]}
    fid, bary = rasterize_uv(uv, faces, 128)
    rgba, mr, mask = bake_volume(fid, bary, verts, faces, g, attrs, layout, 16, ss=2)
    assert rgba.shape == (64, 64, 4) and 0.6 < mask.mean() < 0.9
    assert (rgba == [204, 102, 51, 255]).all() and (mr == [0, 153, 0]).all()


def test_seam_healing_levels_a_colour_step_between_two_charts():
    """A quad cut along its diagonal into two charts, one half of the atlas each, baked 50 and 200."""
    verts = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 0, 0], [1, 1, 0], [0, 1, 0]], float)
    faces = np.array([[0, 1, 2], [3, 4, 5]])
    uv = np.array(
        [[0.05, 0.05], [0.45, 0.05], [0.45, 0.95], [0.55, 0.05], [0.95, 0.95], [0.55, 0.95]]
    )
    fid, _ = rasterize_uv(torch.tensor(uv, dtype=torch.float32), torch.tensor(faces), 64)
    mask = (fid >= 0).numpy()
    step = np.where((fid == 0).numpy()[..., None], 50, 200).astype(np.uint8).repeat(3, -1)
    img = fill_gutters(step, mask)
    seam = seams(verts, faces, uv, 64)
    before = seam_delta(img, seam)
    healed = fill_gutters(heal_seams(img, mask, seam), mask)
    assert before > 100 and seam_delta(healed, seam) < before / 4
    assert healed[mask].min() >= 50 and healed[mask].max() <= 200  # nothing overshoots
    same = uv.copy()
    same[[3, 4]] = uv[[0, 2]]  # the diagonal's two copies share UVs: welded, no seam
    assert len(seams(verts, faces, same, 64)[0]) == 0


@pytest.mark.skipif(not torch.cuda.is_available(), reason="ray tracing is cuBVH")
def test_ao_is_open_on_a_plane_and_dark_inside_a_box():
    import cumesh
    import trimesh

    def bvh(m):
        v = torch.tensor(m.vertices, dtype=torch.float32, device="cuda")
        return cumesh.cuBVH(v, torch.tensor(m.faces, dtype=torch.long, device="cuda"))

    def pts(y, xz):
        return torch.tensor([[x, y, z] for x, z in xz], dtype=torch.float32, device="cuda")

    xz = [(0, 0), (0.3, 0.2), (-0.3, 0.3), (0.2, -0.4)]
    up = torch.tensor([[0.0, 1, 0]] * 4, device="cuda")
    slab = trimesh.creation.box(extents=(2, 0.01, 2))  # its top face is the plane
    assert ao_texels(bvh(slab), pts(0.005, xz), up, 0.001, 10.0).min() == 1.0
    box = trimesh.creation.box(extents=(1, 1, 1))
    assert ao_texels(bvh(box), pts(-0.5, xz), up, 0.001, 10.0).max() < 0.3


@pytest.mark.skipif(not torch.cuda.is_available(), reason="ray tracing is cuBVH")
def test_ao_faces_turns_inward_normals_and_finds_enclosed_shells():
    """A box's faces are out when their vertex normals point out, in when those are flipped; a wall in front
    of one side takes some rays but not the vote; a box inside a closed box is enclosed, the outer one not."""
    import cumesh
    import trimesh

    def tensors(m):
        v = torch.tensor(m.vertices, dtype=torch.float32, device="cuda")
        f = torch.tensor(m.faces, dtype=torch.long, device="cuda")
        n = torch.tensor(m.vertex_normals, dtype=torch.float32, device="cuda")
        return v, f, n, cumesh.cuBVH(v, f)

    def box(size):
        return trimesh.creation.box(extents=(size,) * 3)

    v, f, n, bvh = tensors(box(1))
    inward, enclosed = ao_faces(v, f, n, bvh, 0.001)
    assert not inward.any() and not enclosed.any()
    assert ao_faces(v, f, -n, bvh, 0.001)[0].all()
    wall = trimesh.creation.box(extents=(0.01, 0.4, 0.4)).apply_translation([0.8, 0, 0])
    v, f, n, bvh = tensors(trimesh.util.concatenate([box(1), wall]))
    assert not ao_faces(v, f, n, bvh, 0.001)[0][:12].any()
    v, f, n, bvh = tensors(trimesh.util.concatenate([box(1), box(0.5)]))
    enclosed = ao_faces(v, f, n, bvh, 0.001)[1]
    assert not enclosed[:12].any() and enclosed[12:].all()


def test_small_dark_islands_in_the_ao_are_filled_and_crevices_stay():
    """M43c: a 12-texel-square hole of AO 0 in lit surface is another surface (an inner shell through a
    tear) and takes the surroundings' value; a long dark band is a crevice and keeps; a hole inside a dark
    region is not lifted; uncovered texels take no part."""
    s = 256
    ao = np.full((s, s), 0.9)
    mask = np.ones((s, s), bool)
    mask[:, :8] = False  # a gutter
    ao[40:44, 40:44] = 0.0  # the island: 16 texels, under 0.0003 of the atlas (20)
    ao[100:104, 20:240] = 0.05  # the crevice, 4 x 220 texels: far over the island size at s = 256
    ao[150:220, 150:220] = 0.1  # a dark region ...
    ao[180:183, 180:183] = 0.0  # ... with a darker spot inside: the ring is dark too
    ao[30:34, 0:4] = 0.0  # in the gutter
    out, share = fill_dark_islands(ao, mask)
    assert (out[40:44, 40:44] == 0.9).all()
    assert (out[100:104, 20:240] == 0.05).all()
    assert (out[180:183, 180:183] == 0.0).all() and (out[150:160, 150:160] == 0.1).all()
    assert (out[30:34, 0:4] == 0.0).all()
    assert abs(share - 16 / mask.sum()) < 1e-6
