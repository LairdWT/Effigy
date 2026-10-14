"""Creature skeletons (IMPLEMENTATION.md M36): Mesh2Motion's CC0 rigs as templates, fitted to a mesh.

A template is its bones (steps/templates/<id>.json: name, parent, head, tail; written by tools/templates.py
from the pinned rig) plus what the steps need to know about it: how its sides are named, which bones are
its torso and its limbs (the skinning keeps limb weights off the torso, M20). The human skeleton stays
steps/_rig.py ("mixamo52").

The fit (no pose model reads animals): the mesh turned back by its lean (an animal generated from a
three-quarter picture stands at an angle: the cat at 36°), the template turned to it in quarter turns (its
proportions decide the axis: a dog is long, a bird with spread wings wide), its head put at the end with
more of the body above the back, then its box stretched onto the mesh's box. The user moves joints from
there in the editor. ponytail: shape rules with tuned constants (a streak 3:1, an ear dip of an eighth, a head
turn up to 60°, lone floor runs 3-15 % high), checked on eight animals (docs/IMPLEMENTATION.md, the cat);
a keypoint model for animals, once one is licence-clean, replaces them.
"""

import itertools
import json
from pathlib import Path

import numpy as np

from steps import _rig

DIR = Path(__file__).parent / "templates"
PIN = "https://raw.githubusercontent.com/Mesh2Motion/mesh2motion-app/79f3f61a9852ef70234a5a4a7c13ed87f7a71833"
RIGS = {  # the rig GLBs at the pinned commit (tools/templates.py) and their SHA-256
    "fox": (
        f"{PIN}/static/rigs/rig-fox.glb",
        "e8b7b87cfa1bee7ddf325e0c2dac3c5a9d0c4b0bebc2d91311bfb4800dd12741",
    ),
    "horse": (
        f"{PIN}/static/rigs/rig-horse.glb",
        "0c4f1ae689b185ee17f5458a4150eaac734679480ae1ee0f0e7f05336d1c95ee",
    ),
    "bird": (
        f"{PIN}/static/rigs/rig-bird.glb",
        "796df688f8b67b08a234306318e7d73a64a4001355a646240441451705668411",
    ),
    "kaiju": (
        f"{PIN}/static/rigs/rig-kaiju.glb",
        "65b19290123d5ced8d04ace3ebc362c1a8f6c8d9b247f486dde9c8b3f6a22764",
    ),
    "shark": (
        f"{PIN}/static/rigs/rig-shark.glb",
        "0a9e72b814a079eba7742039442ced5fd54cbcf88332695d47148b06ebb76962",
    ),
    "dragon": (
        f"{PIN}/static/rigs/rig-dragon.glb",
        "4c31e7b483672a84e2692badbea4f3d53106bd0e0c84deba9abde102ea74d74b",
    ),
    "spider": (
        f"{PIN}/static/rigs/rig-spider.glb",
        "c68da203fb89c7ab91dac5e2ff8617e9497e1b5dbfbfbad6318cea56f65e36cc",
    ),
    "snake": (
        f"{PIN}/static/rigs/rig-snake.glb",
        "6d3fdf0449ec8bb3f91136ba0c88cf9592ad02416e3ad9d356d6bd93e37e57e0",
    ),
}
# id: (the name users see, the side suffixes left/right, torso bones, limb bone name prefixes)
TEMPLATES = {
    "fox": (
        "Four-legged animal (dog, cat, fox, wolf)",
        ("_L", "_R"),
        ["Hips", "Spine_1", "Spine_2", "Spine_2.001", "Spine_3", "Spine_4"],
        ["Front_Leg_", "Back_Leg_"],
    ),
    "horse": (
        "Hoofed animal (horse, deer, cow)",
        ("_l", "_r"),
        ["hips", "spine_1", "spine_2", "spine_3", "spine_4", "spine_5", "spine_6"],
        ["front_scapula", "front_humerus", "front_leg", "back_leg"],
    ),
    "bird": (
        "Bird",
        ("_L", "_R"),
        ["hips", "spine_0", "spine_1", "spine_2", "spine_3"],
        ["wing_", "UpperLeg", "LowerLeg", "AnkleLeg", "Foot", "Toes"],
    ),
    "kaiju": (
        "A two-legged monster with a tail (kaiju, dinosaur)",
        ("_L", "_R"),
        ["Hips", "Spine_1", "Spine_2", "Spine_2.001", "Spine_3", "Spine_4"],
        ["Front_Leg_", "Back_Leg_"],
    ),
    "shark": (
        "A shark or fish",
        ("_l", "_r"),
        ["pelvis", "neck", "tail_1", "tail_2", "tail_3"],
        ["front_fin", "back_fin"],
    ),
    "dragon": (
        "A dragon (four legs, wings)",
        ("_l", "_r"),
        ["hips", *(f"spine_{i}" for i in range(5))],
        ["front_", "back_", "collar_", "hips_anchor", "shoulder_", "wing_"],
    ),
    "spider": (
        "A spider (eight legs)",
        ("_l", "_r"),
        ["hips", "spine_1", "spine_2"],
        ["legs_anchor", "leg_"],
    ),
    "snake": (
        "A snake (no legs)",
        ("_l", "_r"),  # none of its bones has a side
        ["head", "neck", *(f"tail{i:02d}" for i in range(1, 21))],
        [],
    ),
}
HUMAN = "mixamo52"
# the head at the end with less body above the back (a spider's abdomen stands higher than its head). ponytail: one
# set, not a rule per template; a tarantula with a flat abdomen goes Turn around
HEAD_LOW = {"spider"}
LEVEL = {
    "spider",
    "snake",
}  # the templates whose mesh may come lying tilted: rig_fit stands them up


def bones(template: str) -> list[dict]:
    return json.loads((DIR / f"{template}.json").read_text(encoding="utf-8"))


def twin(template: str, name: str) -> str | None:
    """The other side's bone (Ear_L ↔ Ear_R), or None for a bone on the middle line."""
    left, right = TEMPLATES[template][1]
    for a, b in ((left, right), (right, left)):
        if name.endswith(a):
            return name[: -len(a)] + b
    return None


def torso(template: str) -> list[str]:
    return TEMPLATES[template][2]


def limbs(template: str) -> list[str]:
    return [
        b["name"] for b in bones(template) if b["name"].startswith(tuple(TEMPLATES[template][3]))
    ]


def _yaw(deg: int) -> np.ndarray:
    a = np.radians(deg)  # about +Y: +Z turns towards +X
    return np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])


def lean(v: np.ndarray) -> float:
    """Degrees about Y in [-45, 45) that the long axis of the mesh's footprint seen from above is off z or x
    (an animal generated from a three-quarter picture: the cat 36°); 0 for a roundish footprint (a sitting
    animal: the axis is noise there) or a few degrees (a pose's asymmetry): the generator's frame faces the
    camera."""
    xz = v[:, [0, 2]] - v[:, [0, 2]].mean(0)
    w, e = np.linalg.eigh(xz.T @ xz)
    a = (np.degrees(np.arctan2(e[0, 1], e[1, 1])) + 45) % 90 - 45
    return float(a) if w[1] >= 1.5**2 * w[0] and abs(a) >= 3 else 0.0


def level(template: str, v: np.ndarray) -> np.ndarray:
    """The turn (`v @ level`) standing a LEVEL template's flat mesh (`v`: its surface) up: a spider generated from a
    picture taken from above lies tilted (the test spider 37°). Its floor: of the faces of its convex hull facing
    within 30° of down along its flattest axis, the one most of the mesh touches (PCA, under a quarter of the next; the axis alone leans
    towards a high abdomen), that face turned flat. Identity for any other template, a mesh that is not flat, or a
    floor under 3° or over 45° off level. Only for the templates that lie flat (a bird may bank, a dragon sit up)."""
    from scipy.spatial import ConvexHull, QhullError

    if template not in LEVEL:
        return np.eye(3)
    w, e = np.linalg.eigh(np.cov((v - v.mean(0)).T))
    if w[0] <= 1e-12 or w[0] >= 0.25 * w[1]:  # a planar surface has no hull
        return np.eye(3)
    try:
        hull = ConvexHull(v)
    except QhullError:
        return np.eye(3)
    down = -e[:, 0] * np.sign(e[1, 0] or 1.0)
    faces = hull.equations[hull.equations[:, :3] @ down >= np.cos(np.radians(30))]
    if not len(faces):
        return np.eye(3)
    # the face the mesh stands on: the most of it within a hundredth of its size (all its feet), not a face from
    # the feet to a spread wing's tip
    pts = v[:: max(1, len(v) // 20000)]
    near = 0.01 * float(np.ptp(v, 0).max())
    n = -faces[np.argmax([(np.abs(pts @ q[:3] + q[3]) < near).sum() for q in faces]), :3]
    if not 3 <= np.degrees(np.arccos(min(n[1], 1.0))) <= 45:
        return np.eye(3)
    return _turn(n, np.array([0.0, 1.0, 0.0])).T


def _voxels(v: np.ndarray, res: int = 64, cube: bool = False):
    """The mesh's solid (`v`: its surface densely, surface()) as (voxels, lo, pitch), voxel i's centre at
    (i - 1.5) · pitch + lo: its surface voxels, closed by one voxel, filled. A surface with wider holes stays a
    shell. `res` voxels along the box's longest side, or with `cube` as many voxels as a cube `res` wide (a flat
    dragon with spread wings: its body as many voxels deep as a fox's)."""
    from scipy import ndimage

    lo, ext = v.min(0), np.ptp(v, 0)
    pitch = float(np.cbrt(np.prod(np.maximum(ext, ext.max() / res))) if cube else ext.max()) / res
    occ = np.zeros(np.ceil(np.ptp(v, 0) / pitch).astype(int) + 5, bool)
    occ[tuple((np.floor((v - lo) / pitch).astype(int) + 2).T)] = True
    return ndimage.binary_fill_holes(ndimage.binary_dilation(occ)), lo, pitch


def wide(template: str) -> bool:
    """Wider than long (the dragon's and the bird's spread wings, the spider's legs): its box is not its body's."""
    pts = np.array([b[k] for b in bones(template) for k in ("head", "tail")])
    return bool(np.ptp(pts[:, 0]) > np.ptp(pts[:, 2]))


def _core(inside: np.ndarray) -> np.ndarray:
    """The voxel indices of the solid's thick core: deeper than half its greatest depth (the body without wings,
    legs or a tail)."""
    from scipy import ndimage

    depth = ndimage.distance_transform_edt(inside)
    return np.argwhere(depth > depth.max() / 2)


def _thin(vox) -> list[np.ndarray]:
    """The solid's thin parts (`vox`: its _voxels), each as its voxel indices: what an opening by a ball a third of
    the body's depth takes off (legs, arms, fins, wings, ears, a tail, specks of the skin)."""
    from scipy import ndimage

    inside = vox[0]
    depth = ndimage.distance_transform_edt(inside)
    body = ndimage.distance_transform_edt(~(depth > depth.max() / 3)) <= depth.max() / 3
    cube = np.ones((3, 3, 3))
    parts, _ = ndimage.label(inside & ~body, structure=cube)
    floor = np.argwhere(inside)[:, 1].min() + max(
        1, round(0.05 * np.ptp(np.argwhere(inside)[:, 1]))
    )
    out = []
    for i, sl in enumerate(ndimage.find_objects(parts), 1):
        part = parts[sl] == i
        # one standing on the floor in several feet splits into a part per foot, each voxel to the foot it is
        # nearest along the part (a spider's legs on a side meet in front of its abdomen: one part)
        feet = part.copy()
        feet[:, max(floor - sl[1].start, 0) :] = False
        feet, n = ndimage.label(feet, structure=cube)
        while n > 1 and (todo := part & (feet == 0)).any():
            grown = ndimage.grey_dilation(feet, footprint=cube) * todo
            if not grown.any():
                break  # ponytail: a piece no foot reaches stays out; never seen
            feet += grown
        out += (
            [np.argwhere(feet == k) + [s.start for s in sl] for k in range(1, n + 1)]
            if n > 1
            else [np.argwhere(part) + [s.start for s in sl]]
        )
    return out


def _limb(
    vox,
    thin,
    chain: np.ndarray,
    root,
    fractions,
    size: float,
    long: float,
    low: float,
    taken: set,
    side=None,
    ground: float = np.inf,
):
    """Points at `fractions` (0: the start, `chain`'s first point; 1: the tip) of the way from the start into the
    mesh's own limb and along it to its tip, a voxel ring at a time from the limb's root (its voxel nearest `root`,
    the trunk joint the chain hangs off: a fin's broad base is where it joins the body, not where the template's
    joint lands) on, skipping the rings before the one nearest the start: of the `thin` parts (_thin) not
    `taken`, within a quarter of `size` of the start, at least `long` long (not a speck of the skin) and wholly
    above `low` (a tail or a fin is not a leg standing on the floor) and reaching below `ground` (a leg hangs
    down from its root: it is not a wing spread level), the one nearest the template's chain as
    placed (`chain`: its joints) and, for a chain on a side (`side`: a point on the body's middle plane and the
    unit vector across it towards the chain), out on that side by a quarter of the chain tip's own offset (a
    right fin is not the dorsal fin on the middle line); its index goes into `taken`. None without one."""

    inside, lo, pitch = vox
    at = lambda i: (i - 1.5) * pitch + lo
    start = chain[0]
    best, gap = None, np.inf
    for k, idx in enumerate(thin):
        c = at(idx)
        if (
            k not in taken
            and np.ptp(c, 0).max() >= long
            and low < c[:, 1].min() < ground
            and np.linalg.norm(c - start, axis=1).min() < 0.25 * size
            and (
                side is None
                or (c.mean(0) - side[0]) @ side[1] > 0.25 * (chain[-1] - side[0]) @ side[1]
            )
        ):
            d = np.mean([np.linalg.norm(c - p, axis=1).min() for p in chain])
            if d < gap:
                best, gap = k, d
    if best is None:
        return None
    idx = thin[best]
    tube = np.zeros(inside.shape, bool)
    tube[tuple(idx.T)] = True
    dist = _steps(tube, idx[np.argmin(np.linalg.norm(at(idx) - root, axis=1))])
    rings = np.array(
        [at(np.argwhere(tube & (np.abs(dist - t) <= 1)).mean(0)) for t in range(dist.max() + 1)]
    )
    way = np.array([start, *rings[np.argmin(np.linalg.norm(rings - start, axis=1)) :]])
    run = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(way, axis=0), axis=1))])
    if run[-1] < 0.5 * np.linalg.norm(np.diff(chain, axis=0), axis=1).sum():
        return None  # an arm held to the chest is no thin part of its own: what is left is a stub
    taken.add(best)
    return np.array([[np.interp(t * run[-1], run, way[:, k]) for k in range(3)] for t in fractions])


def _steps(mask: np.ndarray, seed) -> np.ndarray:
    """Steps from voxel `seed` to each voxel of `mask` through it (26 neighbours); -1 where it does not reach."""
    from scipy import ndimage

    front = np.zeros(mask.shape, bool)
    front[tuple(seed)] = True
    dist, reached, step = np.full(mask.shape, -1), front.copy(), 0
    while front.any():
        dist[front] = step
        front = ndimage.binary_dilation(front, np.ones((3, 3, 3))) & mask & ~reached
        reached |= front
        step += 1
    return dist


def _snake(template: str, v: np.ndarray, yaw: float | None):
    """A template with no limbs (the snake) along the mesh's own body (`v`: its surface, standing level): its
    chain from the head on (head, neck, tail01 … tail_tip) along the longest path through the solid's core
    (deeper than a third of its greatest depth: loops lying close, merged by the voxels, stay apart; from the
    deepest voxel the farthest, from that the farthest; through the middle of each step's ring), at the
    template's distances along it; the head at the end whose middle stands higher (a head is thicker and held
    up; a tail lies flat; the test snake's tail is cut off by the generator as thick as its body: thickness alone
    is a coin toss), with `yaw` (the editor's Turn) the end heading nearer it; the rest (the head's own joints,
    the root) turned to the head's heading and scaled with it. Returns (pos, end, yaw: the head's heading).
    ponytail: a coil whose loops touch merges and the path short-cuts, a tail thinner than the core is cut
    short; the brief asks for "stretched out", the editor fixes the rest."""
    from scipy import ndimage

    inside, lo, pitch = _voxels(v, cube=True)
    depth = ndimage.distance_transform_edt(inside)
    core = depth > depth.max() / 3
    far = _steps(core, np.unravel_index(np.argmax(depth), inside.shape))
    dist = _steps(core, np.unravel_index(np.argmax(far), inside.shape))
    d, n = dist[dist >= 0], int(dist.max())
    ring = lambda w: np.convolve(
        np.bincount(d, w, n + 1), np.ones(3), "same"
    )  # a step and its neighbours
    way = np.stack([ring(i) for i in np.argwhere(dist >= 0).T], 1) / ring(None)[:, None]
    way = (way - 1.5) * pitch + lo
    bs = bones(template)
    parent = {b["name"]: b["parent"] for b in bs}
    head = {b["name"]: np.asarray(b["head"]) for b in bs}
    tail = {b["name"]: np.asarray(b["tail"]) for b in bs}
    size = lambda k: 1 + sum(size(c) for c in parent if parent[c] == k)
    spine = [
        next(k for k in parent if parent[k] and not parent[parent[k]])
    ]  # the root's child: the head
    while kids := [k for k in parent if parent[k] == spine[-1]]:
        spine.append(max(kids, key=size))  # on through the most bones: the neck, not the mouth
    knots = [*(head[k] for k in spine), tail[spine[-1]]]
    at_t = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(knots, axis=0), axis=1))])
    fwd = (knots[0] - knots[-1]) / np.linalg.norm(knots[0] - knots[-1])
    front = max((p - knots[0]) @ fwd for p in (*head.values(), *tail.values()))  # the snout
    length = front + at_t[-1]
    ends = []
    for c in (way, way[::-1]):  # head at the first end, or at the far one
        run = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(c, axis=0), axis=1))])
        at = lambda a, c=c, run=run: np.array([np.interp(a, run, c[:, j]) for j in range(3)])
        k = run[-1] / length
        o = at(k * front)  # the head joint
        h = float(np.degrees(np.arctan2(*(c[0] - o)[[0, 2]])))
        ends.append((h, at, k, o, c[0] - o))
    if yaw is None:  # the tenth standing higher
        m = max(1, n // 10)
        pick = int(way[-m:, 1].mean() > way[:m, 1].mean())
    else:
        pick = int(np.argmin([abs((e[0] - yaw + 180) % 360 - 180) for e in ends]))
    h, at, k, o, ahead = ends[pick]
    r = _yaw(h - np.degrees(np.arctan2(fwd[0], fwd[2])))
    r = _turn(r @ fwd, ahead) @ r  # turned about the vertical, then lifted as the head is

    def place(p):  # a template point: on the path when it is a chain joint, else with the head
        for q, a in zip(knots, at_t):
            if np.allclose(p, q, atol=1e-4):
                return at(k * (front + a))
        return o + k * (p - knots[0]) @ r.T

    return {b: place(p) for b, p in head.items()}, {b: place(p) for b, p in tail.items()}, h


def _out(bs: list[dict], pos: dict, end: dict) -> dict:
    """{name: {"parent", "position", "tail", "to"?}}: `to` the child a bone points at (its head on the bone's tail)."""
    out = {}
    for b in bs:
        n = b["name"]
        out[n] = {
            "parent": b["parent"],
            "position": pos[n].round(5).tolist(),
            "tail": end[n].round(5).tolist(),
        }
        to = next(
            (
                c["name"]
                for c in bs
                if c["parent"] == n and np.allclose(c["head"], b["tail"], atol=1e-4)
            ),
            None,
        )
        if to:
            out[n]["to"] = to
    return out


def _turn(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """The rotation taking direction `a` onto `b` by the shortest arc."""
    if not (np.linalg.norm(a) and np.linalg.norm(b)):  # a zero-length chain
        return np.eye(3)
    a, b = a / np.linalg.norm(a), b / np.linalg.norm(b)
    x, c = np.cross(a, b), float(a @ b)
    if c < -1 + 1e-9:  # ponytail: turned straight back is left unturned; never seen on a limb
        return np.eye(3)
    k = np.array([[0, -x[2], x[1]], [x[2], 0, -x[0]], [-x[1], x[0], 0]])
    return np.eye(3) + k + k @ k / (1 + c)


def _ear_tips(v: np.ndarray, centre: np.ndarray, radius: float, apart: float):
    """The tips of two ears standing up from a head (`v`: the surface, `centre`: the head joint, `apart`: the
    template's ear tips' spacing seen from above): within `radius` the highest point, and the highest at least
    half `apart` away from it; None without a dip between them an eighth of their height over the head joint
    deep (a domed head is highest in its middle; ears lying flat)."""
    near = v[(np.linalg.norm(v - centre, axis=1) < radius) & (v[:, 1] > centre[1])]
    if not len(near):
        return None
    one = near[np.argmax(near[:, 1])]
    off = near[np.linalg.norm(near[:, [0, 2]] - one[[0, 2]], axis=1) >= apart / 2]
    if not len(off):
        return None
    tips = [one, off[np.argmax(off[:, 1])]]
    mid, gap = (tips[0] + tips[1]) / 2, np.linalg.norm(tips[0] - tips[1])
    between = near[np.linalg.norm(near[:, [0, 2]] - mid[[0, 2]], axis=1) < 0.2 * gap, 1]
    low = tips[1][1]
    return tips if len(between) and between.max() < low - (low - centre[1]) / 8 else None


def facing(template: str, v: np.ndarray) -> int:
    """The quarter turn (degrees about Y) that faces the template's +Z front the way the mesh (`v`: its surface)
    faces: the axis by the proportions; the head at the end with more of the body above the back (a neck and a
    head, not a thin tail held up: the cat's reaches higher than its ears), or, with next to nothing above the
    back (a bird), at the end that reaches higher; for a template in HEAD_LOW the other end."""
    pts = np.array([b[k] for b in bones(template) for k in ("head", "tail")])
    ext = np.ptp(v, 0)
    ext = ext / ext.max()
    best = min(
        (0, 90),
        key=lambda d: np.abs(
            np.ptp(pts @ _yaw(d).T, 0) / np.ptp(pts @ _yaw(d).T, 0).max() - ext
        ).sum(),
    )
    inside, vlo, pitch = _voxels(v, cube=wide(template))
    if wide(template):
        # a template wider than long (spread wings, a spider's legs): the box says nothing about a body with its
        # wings folded; the axis of the thick core seen from above does, when it is long enough to have one
        core = _core(inside)[:, [0, 2]].astype(float)
        w, e = np.linalg.eigh(np.cov(core.T)) if len(core) > 2 else (np.ones(2), np.eye(2))
        if w[1] >= 1.5**2 * w[0]:
            # its long side along z: the template unturned
            best = 0 if abs(e[1, 1]) >= abs(e[0, 1]) else 90
    axis = 2 if best == 0 else 0  # the body's length runs along z (0°) or x (90°)
    lo, hi = v[:, axis].min(), v[:, axis].max()
    third = (hi - lo) / 3
    body = (np.argwhere(inside) - 1.5) * pitch + vlo
    ahead, behind = body[:, axis] > hi - third, body[:, axis] < lo + third
    middle = body[
        ~ahead & ~behind, 1
    ]  # empty for a mesh in two pieces: then the end that reaches higher
    up = body[:, 1] > (np.percentile(middle, 90) if len(middle) else np.inf)  # above the back
    front, back = (ahead & up).sum(), (behind & up).sum()
    if max(front, back) < 0.005 * len(body):
        front, back = v[v[:, axis] > hi - third, 1].max(), v[v[:, axis] < lo + third, 1].max()
    return best if (front >= back) != (template in HEAD_LOW) else best + 180


def surface(v: np.ndarray, f: np.ndarray, n: int = 30000, seed: int = 0) -> np.ndarray:
    """Points spread over the mesh by area: a low-poly model has too few vertices on its centre plane."""
    tri = v[f]
    area = np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    rng = np.random.default_rng(seed)
    pick = rng.choice(len(f), n, p=area / area.sum())
    a, b = rng.random((2, n, 1))
    flip = (a + b) > 1
    a, b = np.where(flip, 1 - a, a), np.where(flip, 1 - b, b)
    t = tri[pick]
    return np.concatenate([v, t[:, 0] + a * (t[:, 1] - t[:, 0]) + b * (t[:, 2] - t[:, 0])])


def _centreline(v: np.ndarray, axis: int, start: float, width: float, slices: int = 64):
    """The middle height of the body along its length, as a function of the position along `axis`: the mesh
    cut in slices on its centre plane, followed from `start` (the hips) outwards, each slice taking the piece
    nearest the last one's middle (an open mouth or a gap under a tail splits a slice; the trace stays on
    the body and runs on into the neck and the tail)."""
    lat = 2 - axis
    ext = np.ptp(v, 0)
    band = v[np.abs(v[:, lat] - np.median(v[:, lat])) < 0.08 * width]
    edges = np.linspace(v[:, axis].min(), v[:, axis].max(), slices + 1)
    centres = (edges[:-1] + edges[1:]) / 2
    floor = v[:, 1].min() + 0.05 * ext[1]
    spans = []
    for lo, hi in itertools.pairwise(edges):
        ys = np.sort(band[(band[:, axis] >= lo) & (band[:, axis] <= hi), 1])
        # the surface crossed upwards: points in runs (one per crossing), crossings in pairs, solid between
        cut = np.flatnonzero(np.diff(ys) > 0.03 * ext[1]) + 1
        runs = np.split(ys, cut) if len(ys) else []
        hits = [float(r.mean()) for r in runs]
        spans.append(list(zip(hits[0::2], hits[1::2], strict=False)))
        # a thin part lying alone on or just over the floor (a mouse's tail; within a tenth of the height): its
        # walls fill the band, one run (one held up, the cat's tail, or a snout ahead of the body: the trace stays on the body)
        if (
            len(runs) == 1
            and runs[0][0] < floor + 0.1 * ext[1]
            and 0.03 * ext[1] < np.ptp(runs[0]) < 0.15 * ext[1]
        ):
            spans[-1] = [(float(runs[0][0]), float(runs[0][-1]))]
    mid = np.full(slices, np.nan)
    i0 = int(np.clip(np.searchsorted(centres, start), 0, slices - 1))
    first = max(spans[i0], key=lambda sp: sp[1] - sp[0], default=None)  # the body at the hips
    if first is None:
        return None
    mid[i0] = (first[0] + first[1]) / 2
    for order in (range(i0 + 1, slices), range(i0 - 1, -1, -1)):
        last = mid[i0]
        for i in order:
            if spans[i]:
                sp = min(spans[i], key=lambda q: abs((q[0] + q[1]) / 2 - last))
                last = mid[i] = (sp[0] + sp[1]) / 2
    ok = ~np.isnan(mid)
    return lambda at: float(np.interp(at, centres[ok], mid[ok]))


def _feet(p: np.ndarray, axis: int) -> tuple[float, ...] | None:
    """Along `axis`, the middle of the feet at the low end and at the high end: what stands within 5 % of the
    height of the floor, less what lies on it (seen from above a streak three times as long as it is wide: a
    mouse's tail took the back feet behind its rump; a panda's long soles are paws), split at its widest gap;
    when that gap is under a fifth of the length (one group of feet: a bird, a kaiju) their one middle."""
    from scipy import ndimage

    length = float(np.ptp(p[:, axis]))
    low = p[p[:, 1] < p[:, 1].min() + 0.05 * np.ptp(p[:, 1])]
    if length <= 0 or len(low) < 2:
        return None
    cell = np.floor((low[:, [0, 2]] - low[:, [0, 2]].min(0)) / (length / 64)).astype(int)
    grid = np.zeros(cell.max(0) + 1, bool)
    grid[tuple(cell.T)] = True
    blob = ndimage.label(ndimage.binary_dilation(grid))[0][tuple(cell.T)]
    paws = []
    for b in np.unique(blob):
        c = low[blob == b][:, [0, 2]]
        w = np.linalg.eigvalsh(np.cov(c.T)) if len(c) >= 6 else np.ones(2)  # a few joints: a paw
        if w[1] <= 9 * max(w[0], 1e-12):  # not a streak
            paws.append(b)
    low = np.sort(low[np.isin(blob, paws), axis])
    gaps = np.diff(low)
    if not len(low):
        return None
    if not len(gaps) or gaps.max() < 0.2 * length:
        return (float(low.mean()),)
    i = int(np.argmax(gaps)) + 1
    return float(low[:i].mean()), float(low[i:].mean())


def fit(
    template: str, v: np.ndarray, yaw: float | None = None, f: np.ndarray | None = None
) -> tuple[dict, float]:
    """The template's bones on the mesh: {name: {"parent", "position", "tail", "to"?}} in the glTF frame, and
    the turn used, degrees about Y: the lean plus a quarter turn (`yaw` overrides the guess: the editor's Turn
    buttons add 90 or 180). `to`: the child a bone points at (the skinning follows it when the user moves that
    child).
    The template's box onto the mesh's box first (along the body its feet onto the mesh's); then each joint
    on the middle line (spine, neck, head, tail) to the middle of the mesh's cross-section where it stands,
    and the side joints with it by their height (an ear all the way, a foot on the ground not at all); a tail or a
    limb that sticks out and a head turned aside follow the mesh's own thin parts and ears."""
    surf = surface(v, f) if f is not None else v
    lev = level(template, surf)
    if not limbs(template):  # a snake: along its own body
        # densely: a low-poly mesh's 30000 points leave the snake's fine voxels a hollow shell
        pos, end, yaw = _snake(template, (surface(v, f, 200000) if f is not None else v) @ lev, yaw)
        turn = lambda d: {n: p @ lev.T for n, p in d.items()}
        return _out(bones(template), turn(pos), turn(end)), round(yaw, 1) % 360
    if yaw is None:
        a = lean(surf @ lev)
        if not a and wide(template):  # legs spread all round (a spider): the lean of its thick core
            inside, lo, pitch = _voxels(surf @ lev, cube=True)
            a = lean((_core(inside) - 1.5) * pitch + lo)
            a = a if abs(a) >= 10 else 0.0  # under 10°: a box dragon's neck to one side, not a lean
        yaw = a + facing(template, surf @ lev @ _yaw(a))
    yaw = round(float(yaw), 1) % 360
    base = (yaw + 45) % 90 - 45  # the lean; the rest a quarter turn
    back = lev @ _yaw(base)
    v, surf, quarter = v @ back, surf @ back, round(yaw - base) % 360  # the body along z or x
    bs = bones(template)
    r = _yaw(quarter)
    head = {b["name"]: np.asarray(b["head"]) @ r.T for b in bs}
    tail = {b["name"]: np.asarray(b["tail"]) @ r.T for b in bs}
    pts = np.array([*head.values(), *tail.values()])
    alo, ahi = pts.min(0), pts.max(0)
    mlo, mhi = v.min(0), v.max(0)
    scale = (mhi - mlo) / np.maximum(ahi - alo, 1e-6)
    pos = {n: mlo + (p - alo) * scale for n, p in head.items()}
    end = {n: mlo + (p - alo) * scale for n, p in tail.items()}
    parent = {b["name"]: b["parent"] for b in bs}
    axis = 2 if quarter % 180 == 0 else 0
    # along the body, piecewise: the ends on the box's ends, the template's feet onto the mesh's. Box onto box
    # alone put the cat's hips and back legs under its belly (its tail held up adds no length to its box, the
    # fox template's long one does to its own) and the fox's snout past the cat's face. A template hanging below
    # its root floats (the shark: fins and jaw down to -0.97 under a root at 0) and has no feet
    root = next(n for n in pos if not parent[n])
    floats = alo[1] < head[root][1] - 0.05 * float((ahi - alo).max())
    tf = (
        None if floats else _feet(np.array([p for n, p in pos.items() if parent[n]]), axis)
    )  # the root: between the feet
    mf = _feet(surf, axis)
    if tf and mf and len(tf) == len(mf) and mlo[axis] < tf[0] and tf[-1] < mhi[axis]:
        xp, fp = [mlo[axis], *tf, mhi[axis]], [mlo[axis], *mf, mhi[axis]]  # one group: three points
        for p in (*pos.values(), *end.values()):
            p[axis] = np.interp(p[axis], xp, fp)
    vox = _voxels(surf, cube=wide(template))
    if wide(template):
        # a template wider than long: along the body its middle line (abdomen to head, tail to snout) onto the
        # solid's middle, not its box onto the legs' (the spider's front legs reach further than its back legs)
        idx = np.argwhere(vox[0])
        on = idx[np.abs(idx[:, 2 - axis] - np.median(_core(vox[0])[:, 2 - axis])) <= 1, axis]
        mid = [
            p[axis]
            for n, p in (*pos.items(), *end.items())
            if parent[n] and twin(template, n) is None
        ]
        xp = [mlo[axis], min(mid), max(mid), mhi[axis]]
        fp = np.clip(
            [mlo[axis], *(np.array([on.min(), on.max()]) - 1.5) * vox[2] + vox[1][axis], mhi[axis]],
            mlo[axis],
            mhi[axis],
        )
        if np.all(np.diff(xp) > 0):
            for p in (*pos.values(), *end.values()):
                p[axis] = np.interp(p[axis], xp, fp)
    floor = mlo[1]
    hip = next(n for n in pos if parent[n] and not parent[parent[n]])  # the root's child
    skull = next((n for n in pos if n.lower() == "head"), None)
    if skull is None:
        raise ValueError(f"template {template!r} has no bone named head")

    def above(n):  # n's ancestors, nearest first
        a = parent[n]
        while a:
            yield a
            a = parent[a]

    seen = {}  # a point -> (inside before rig_fit's snap, inside after it): the chains share most of their joints
    snap = 0.05 * float(np.ptp(v[:, 1]))

    def kept(pts):  # (how many of pts are in the mesh after rig_fit's snap, how many before it)
        pts = np.array(pts)
        new = [p for p in pts if p.tobytes() not in seen]
        for p, ok in zip(new, _rig.inside(v, f, np.array(new)) if new else []):
            seen[p.tobytes()] = (int(ok), int(ok or _rig.snap_inside(v, f, p, snap) is not p))
        got = [seen[p.tobytes()] for p in pts]
        return sum(g[1] for g in got), sum(g[0] for g in got)

    # the head's own joints (nose, chin, ears) keep their shape and move with the head
    in_head = {n for n in pos if skull in above(n)}
    # the trunk: the chain from the hips to the head, and the tail; what hangs off it on the middle line
    # (a belly, a rib cage) moves with the trunk, not onto its centre line
    trunk = {n for n in pos if n == skull or n in above(skull)} | {
        n for n in pos if "tail" in n.lower()
    }
    # the band the centre line looks through, by the box's width; for a wide template (the wings' box takes the
    # body's sides into it) by its thick core's width too
    widths = [float(np.ptp(v[:, 2 - axis]))]
    if wide(template):
        widths.append(float(np.ptp(_core(vox[0])[:, 2 - axis])) * vox[2])
    lines = [ln for w in widths if (ln := _centreline(surf, axis, pos[hip][axis], w))]
    on = lambda ln: [pos[n] + [0, ln(pos[n][axis]) - pos[n][1], 0] for n in trunk if parent[n]]
    # the line putting more of the trunk in the mesh (a dragon sitting up: the box's band; lying flat: the core's)
    line = (
        max(lines, key=lambda ln: kept(on(ln)))
        if len(lines) > 1 and f is not None
        else next(iter(lines), None)
    )
    dy = {}  # the trunk (root excepted: it stays on the ground) onto the traced centre line
    for n in pos:
        if line and parent[n] and n in trunk:
            dy[n] = line(pos[n][axis]) - pos[n][1]
    shift = {}
    for n, p in pos.items():
        if n in dy:
            shift[n] = dy[n]
        elif n in in_head:
            shift[n] = dy.get(skull, 0.0)
        elif (
            twin(template, n) is None and parent[n]
        ):  # hanging off the trunk: its trunk ancestor's shift
            shift[n] = next((dy[a] for a in above(n) if a in dy), 0.0)
        elif (
            twin(template, n) is not None
        ):  # a side joint: its nearest middle ancestor's shift, by height
            a = parent[n]
            while a and a not in dy:
                a = parent[a]
            if a:
                share = (p[1] - floor) / max(pos[a][1] - floor, 1e-6)
                shift[n] = dy[a] * float(np.clip(share, 0, 1))
    if floats:  # no ground to stand on: the root goes with the hips
        shift[root] = dy.get(hip, 0.0)
    up = {n: np.array([0, shift.get(n, 0.0), 0]) for n in pos}
    pos = {n: p + up[n] for n, p in pos.items()}
    end = {n: p + up[n] for n, p in end.items()}
    # the chains: the tail (by name), then each limb from the trunk on through its longest child (a hand's fingers
    # and a foot's toes hang off its last bone, a wing's membrane fingers off its bones)
    kids = {n: [k for k in pos if parent[k] == n] for n in pos}
    tail_chain = [n for n in pos if "tail" in n.lower() and "tail" not in (parent[n] or "").lower()]
    while tail_chain and (
        kid := next((k for k in kids[tail_chain[-1]] if "tail" in k.lower()), None)
    ):
        tail_chain.append(kid)
    lim = set(limbs(template))
    chains = [tail_chain] if tail_chain else []

    def reach_of(n):  # the longest way from n's head to a leaf, along the template's bones
        return float(np.linalg.norm(tail[n] - head[n])) + max(map(reach_of, kids[n]), default=0.0)

    starts = [n for n in pos if n in lim and parent[n] not in lim]
    while starts:
        chains.append([starts.pop(0)])
        # on through one child, or through the one reaching half as far again as the rest (a wing's next
        # bone, its membrane fingers hanging off); a hand's fingers end it. A hub, its children reaching further
        # than the chain so far (the spider's leg anchor: four legs), starts a chain per child instead
        while ks := sorted(kids[chains[-1][-1]], key=reach_of, reverse=True):
            if len(ks) > 1 and reach_of(ks[0]) < 1.5 * reach_of(ks[1]):
                if reach_of(ks[1]) > reach_of(chains[-1][0]) - reach_of(ks[0]):
                    starts += ks
                    chains.pop()
                break
            chains[-1].append(ks[0])
    thin, taken = _thin(vox), set()
    cell = lambda p: tuple(
        np.clip(np.floor((p - vox[1]) / vox[2]).astype(int) + 2, 0, np.array(vox[0].shape) - 1)
    )

    lat = 2 - axis  # across the body
    across = np.eye(3)[lat]
    reach = {  # a foot lying on the template's own floor (a dragon's wing tip only touches it)
        n: max(head[n][1], tail[n][1]) - alo[1] <= 0.1 * (ahi[1] - alo[1]) for n in pos
    }
    # a chain sticking out of the mesh (the cat's tail held up, the shark's fins, the kaiju's arms): from its last
    # joint inside on, along the mesh's own thin part nearest it, the joints at the template's bone-length
    # fractions; what hangs off a moved bone turns and stretches with the chain. One wholly inside stays (the M36
    # animals' legs and tails)
    # what does not stand on the floor first (a tail, wings, fins, arms): a dragon sitting up has its wings low
    for chain in sorted(chains, key=lambda c: reach[c[-1]]):
        held = (
            list(_rig.inside(v, f, np.array([pos[n] for n in chain])))
            if f is not None
            else [bool(vox[0][cell(pos[n])]) for n in chain]
        )
        if all(held):
            continue
        a = max(held.index(False) - 1, 0)
        moved = chain[a:]
        bone = [float(np.linalg.norm(tail[n] - head[n])) for n in moved]
        along = _limb(
            vox,
            thin,
            np.array([*(pos[n] for n in moved), end[moved[-1]]]),
            pos[chain[0]],
            np.cumsum([0, *bone]) / max(sum(bone), 1e-9),
            float((mhi - mlo).max()),
            min(
                0.1 * float((mhi - mlo).max()),
                sum(np.linalg.norm(end[n] - pos[n]) for n in chain) / 4,
            ),
            -np.inf if floats or reach[chain[-1]] else floor + 0.1 * (mhi[1] - floor),
            taken,
            None
            if twin(template, chain[0]) is None
            else (pos[hip], np.sign(end[chain[-1]][lat] - pos[hip][lat]) * across),
            pos[chain[0]][1] if reach[chain[-1]] and not floats else np.inf,  # a leg hangs down
        )
        if along is None:
            continue
        p2, e2 = dict(pos), dict(end)
        # what hangs off it turns and stretches as the whole chain does (a wing's bones zigzag in the template:
        # a turn per bone would swing its membrane fingers about)
        was = end[moved[-1]] - pos[moved[0]]
        r = _turn(was, along[-1] - along[0]) * (
            np.linalg.norm(along[-1] - along[0]) / max(np.linalg.norm(was), 1e-9)
        )
        for i, n in enumerate(moved):
            h0 = pos[n]
            p2[n], e2[n] = along[i], along[i + 1]
            hang = [k for k in kids[n] if k not in chain]
            while hang:
                k = hang.pop()
                p2[k], e2[k] = p2[n] + (pos[k] - h0) @ r.T, p2[n] + (end[k] - h0) @ r.T
                hang += kids[k]
        # kept only when more of the joints it moves end up in the mesh after rig_fit's snap, or as many and
        # more before it (a thick arm held to the chest is traced into its edge; the box's guess snaps in)
        changed = [n for n in pos if p2[n] is not pos[n]]
        was_kept = kept([pos[n] for n in changed]) if f is not None else None
        # (all of them already in: nothing can beat that, the new ones need not be checked)
        if f is None or (
            was_kept != (len(changed), len(changed)) and kept([p2[n] for n in changed]) > was_kept
        ):
            pos, end = p2, e2
    # a head turned aside (the cat looks at the camera, 33° off its body): its face turned by the line between
    # its ear tips, each ear chain from its base to its tip. Without two ears standing up (a bird, a dog's
    # lying flat), or with tips far from the template's (horns, a raised tail at the wrong end), it stays straight
    is_ear = lambda n: n.lower().startswith("ear")
    ears = [[n] for n in in_head if is_ear(n) and not is_ear(parent[n])]
    for ear in ears:
        while kid := next((k for k in in_head if parent[k] == ear[-1] and is_ear(k)), None):
            ear.append(kid)
    tips = None
    if len(ears) == 2:
        want = [end[ear[-1]] for ear in ears]  # the template's ear tips
        across = (want[1] - want[0])[[0, 2]]
        reach = 1.5 * max(np.linalg.norm(end[n] - pos[skull]) for n in in_head)
        tips = _ear_tips(surf, pos[skull], reach, float(np.linalg.norm(across)))
    if tips is not None:
        if (
            tips[0][[0, 2]] @ across > tips[1][[0, 2]] @ across
        ):  # left and right along the template's ear line
            tips = tips[::-1]
        close = all(
            np.linalg.norm((t - w)[[0, 2]]) < 1.5 * np.linalg.norm(across)
            for t, w in zip(tips, want)
        )
        heading = lambda d: np.degrees(np.arctan2(d[0], d[2]))
        turn = (heading(tips[1] - tips[0]) - heading(want[1] - want[0]) + 180) % 360 - 180
        if close and abs(turn) <= 60:
            r, c = (
                _yaw(turn if abs(turn) >= 10 else 0),
                pos[skull],
            )  # under 10°: uneven ears (the horse's 8)
            for n in in_head:
                pos[n], end[n] = c + (pos[n] - c) @ r.T, c + (end[n] - c) @ r.T
            for ear, tip in zip(ears, tips):
                base, k = pos[ear[0]], len(ear)
                for i, n in enumerate(ear):
                    pos[n], end[n] = base + (tip - base) * i / k, base + (tip - base) * (i + 1) / k
    pos = {n: p @ back.T for n, p in pos.items()}  # turned forward by the lean again
    end = {n: p @ back.T for n, p in end.items()}
    return _out(bs, pos, end), yaw
