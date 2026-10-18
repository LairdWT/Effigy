"""Animation edit maths (IMPLEMENTATION.md §3.2 `anim_edit`, M37): numpy only, no Blender.

Three parts: read a GLB's animations as dense per-bone samples (`read_glb`, `sample_clip`), `evaluate`
a correction layer on them (the same eight steps as ui/src/anim/clip.ts; one fixture,
tests/fixtures/anim_edit/, both pass) and bake the result back into the GLB (`write_glb`).

A clip ("base") is {"fps", "frames": F, "bones": [{"name", "parent": name|None, "rotation"?: (F,4) x,y,z,w,
"translation"?: (F,3), "offset"?: (3,)}]}; `translation` is present for the bones whose channel is animated
(more than two keys), the constant ones are written back as they were; `offset` (M38) is the constant
translation of a bone without a moving one (skeleton space for the foot locks), carried unchanged.
"""

import copy
import itertools
import json
import math
import struct
from pathlib import Path

import numpy as np

from steps._common import StepError

ROT, POS = "rotation", "translation"


# --- quaternions and easing ------------------------------------------------------------------------------


def _s(t):  # smoothstep
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _unit(q):
    return q / np.linalg.norm(q, axis=-1, keepdims=True)


def _lerp(a, b, t):
    return a + (b - a) * np.asarray(t, float)[..., None]


def slerp(a, b, t):
    """Shortest-path slerp, normalised; nlerp when the angle is tiny (dot > 0.9995)."""
    a, b = np.broadcast_arrays(np.asarray(a, float), np.asarray(b, float))
    t = np.asarray(t, float)[..., None]
    d = (a * b).sum(-1, keepdims=True)
    b = np.where(d < 0, -b, b)
    d = np.abs(d)
    th = np.arccos(np.clip(d, 0, 1))
    near = d > 0.9995
    sn = np.where(near, 1.0, np.sin(th))
    wa = np.where(near, 1 - t, np.sin((1 - t) * th) / sn)
    wb = np.where(near, t, np.sin(t * th) / sn)
    return _unit(wa * a + wb * b)


def qmul(a, b):
    ax, ay, az, aw = np.moveaxis(np.asarray(a, float), -1, 0)
    bx, by, bz, bw = np.moveaxis(np.asarray(b, float), -1, 0)
    return np.stack(
        [
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz,
        ],
        -1,
    )


def _consistent(q):
    """Flip quaternions so neighbours are on the same side (q and -q are one rotation)."""
    r = np.where((q[1:] * q[:-1]).sum(-1) < 0, -1.0, 1.0)
    return q * np.concatenate([[1.0], np.cumprod(r)])[:, None]


def _gauss(x, sigma):
    r = math.ceil(3 * sigma)
    k = np.arange(-r, r + 1)
    w = np.exp(-(k**2) / (2 * sigma**2))
    idx = np.clip(np.arange(len(x))[:, None] + k, 0, len(x) - 1)  # edges held
    return (x[idx] * (w / w.sum())[None, :, None]).sum(1)


def _qrot(q, v):
    u = np.asarray(q[:3], float)
    t = 2 * np.cross(u, v)
    return v + q[3] * t + np.cross(u, t)


def _qinv(q):
    return np.asarray(q, float) * [-1, -1, -1, 1]


def _turn(axis, ang):
    return np.append(axis * math.sin(ang / 2), math.cos(ang / 2))


def _axis(*cands):  # the first candidate that is not (nearly) zero, normalised; None: all are
    for c in cands:
        if (n := np.linalg.norm(c)) >= 1e-8:
            return c / n
    return None


_EX, _EY, _ID = np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), np.array([0, 0, 0, 1.0])


def _path(par, n):
    """The bones from the root down to n."""
    out = []
    while n is not None:
        out.append(n)
        n = par.get(n)
    return out[::-1]


def _fk(path, rot, pos, off, f):
    """World turns and positions along a root-first path at frame f (skeleton space, M38)."""
    W, p, Ws, ps = _ID, np.zeros(3), [], []
    for n in path:
        t = pos[n][f] if n in pos else off.get(n, np.zeros(3))
        p = p + _qrot(W, t)
        W = qmul(W, rot[n][f]) if n in rot else W
        Ws.append(W)
        ps.append(p)
    return Ws, ps


def _two_bone(pw, WU, WL, WB, a, b, c, P):
    """U, L and B's new local turns putting B at P, B keeping its world turn (§3.2 3b); None: nothing to solve."""
    l1, l2 = np.linalg.norm(b - a), np.linalg.norm(c - b)
    if l1 * l2 < 1e-12 or np.linalg.norm(P - a) < 1e-12:
        return None  # a zero-length bone or a target on the hip: nothing to solve
    d = min(max(np.linalg.norm(P - a), abs(l1 - l2) + 1e-6), l1 + l2 - 1e-6)
    u, v = a - b, c - b
    k = _axis(np.cross(u, v), np.cross(u, _EX), np.cross(u, _EY))
    if k is None:
        return None  # the upper bone (nearly) zero long: no knee to turn
    th = math.acos(np.clip(u @ v / (l1 * l2), -1, 1))
    th2 = math.acos(np.clip((l1 * l1 + l2 * l2 - d * d) / (2 * l1 * l2), -1, 1))
    K = _turn(k, th2 - th)
    e, g = _unit(_qrot(K, v) + b - a), _unit(P - a)
    if 1 + e @ g < 1e-8:  # opposite: a half turn about any perpendicular
        H = _turn(_axis(np.cross(e, _EX), np.cross(e, _EY)), math.pi)
    else:
        H = _unit(np.append(np.cross(e, g), 1 + e @ g))
    nU, nL = qmul(H, WU), qmul(H, qmul(K, WL))
    return [_unit(qmul(_qinv(pw), nU)), _unit(qmul(_qinv(nU), nL)), _unit(qmul(_qinv(nL), WB))]


def _lock(rot, pos, off, par, lk, F):
    """One foot lock (§3.2 step 3b): two-bone IK of U > L > B pinning B to its world position at the span's middle."""
    chain = _path(par, lk["bone"])  # root .. U, L, B
    T = _fk(chain, rot, pos, off, (lk["from"] + lk["to"]) // 2)[1][-1]
    for f in range(max(0, lk["from"] - lk["blend"]), min(F - 1, lk["to"] + lk["blend"]) + 1):
        if f < lk["from"]:
            w = float(_s(1 - (lk["from"] - f) / lk["blend"]))
        else:
            w = 1.0 if f <= lk["to"] else float(_s(1 - (f - lk["to"]) / lk["blend"]))
        Ws, ps = _fk(chain, rot, pos, off, f)
        c = ps[-1]
        pw = Ws[-4] if len(Ws) > 3 else _ID
        r = _two_bone(pw, *Ws[-3:], *ps[-3:], c + (T - c) * w)
        if r is not None:
            for n, q in zip(chain[-3:], r, strict=True):
                rot[n][f] = q


def _between(u, v):
    """The shortest turn taking unit u to unit v (opposite: a half turn about u x X, else u x Y)."""
    d = u @ v
    if 1 + d < 1e-8:
        return _turn(_axis(np.cross(u, _EX), np.cross(u, _EY)), math.pi)
    return _unit(np.append(np.cross(u, v), 1 + d))


def _chain(pw, W, p, P, swivel):
    """M63: the chain's new local turns putting its last bone at P (ui/src/anim/clip.ts ikChain): first a turn about its
    root-tip line by `swivel` degrees, then the two-bone solve for two bones, FABRIK (16 rounds) for more; None: nothing
    to solve. W, p: world turns and positions, the top first; the last bone keeps its world turn."""
    n = len(W) - 1
    W, p = list(W), list(p)
    ax = p[n] - p[0]
    if swivel != 0 and np.linalg.norm(ax) > 1e-12:
        R = _turn(_unit(ax), math.radians(swivel))
        for i in range(n):
            W[i] = _unit(qmul(R, W[i]))
            if i > 0:
                p[i] = p[0] + _qrot(R, p[i] - p[0])
    if n == 2:
        return _two_bone(pw, *W, *p, P)
    L = [np.linalg.norm(p[i + 1] - p[i]) for i in range(n)]
    if min(L) < 1e-12 or np.linalg.norm(P - p[0]) < 1e-12:
        return None
    q = [x.copy() for x in p]
    for _ in range(16):
        q[n] = np.asarray(P, float).copy()
        for i in range(n - 1, -1, -1):
            q[i] = q[i + 1] + _unit(q[i] - q[i + 1]) * L[i]
        q[0] = p[0].copy()
        for i in range(1, n + 1):
            q[i] = q[i - 1] + _unit(q[i] - q[i - 1]) * L[i - 1]
    out, up, cur = [], pw, W[0]
    for i in range(n):
        t = _qrot(_qinv(W[i]), p[i + 1] - p[i])  # the next joint in bone i's own frame
        Wn = _unit(qmul(_between(_unit(_qrot(cur, t)), _unit(q[i + 1] - q[i])), cur))
        out.append(_unit(qmul(_qinv(up), Wn)))
        cur, up = qmul(Wn, qmul(_qinv(W[i]), W[i + 1])), Wn
    out.append(_unit(qmul(_qinv(up), W[n])))
    return out


def _ik_at(keys, x):
    """An IK control's (p, swivel, w) at base frame x (§3.2 step 3c); None: no IK there."""
    ks = sorted(keys, key=lambda k: k["f"])

    def fade(k, d):
        w = (
            k["w"]
            if d == 0
            else k["w"] * float(_s(1 - d / k["falloff"]))
            if d < k["falloff"]
            else 0.0
        )
        return (np.asarray(k["p"], float), k["swivel"], w) if w > 0 else None

    if x <= ks[0]["f"]:
        return fade(ks[0], ks[0]["f"] - x)
    if x >= ks[-1]["f"]:
        return fade(ks[-1], x - ks[-1]["f"])
    a, b = next((a, b) for a, b in itertools.pairwise(ks) if a["f"] <= x <= b["f"])
    t = float(_s((x - a["f"]) / (b["f"] - a["f"])))
    w = a["w"] + (b["w"] - a["w"]) * t
    if w <= 0:
        return None
    p = np.asarray(a["p"], float) + (np.asarray(b["p"], float) - a["p"]) * t
    return p, a["swivel"] + (b["swivel"] - a["swivel"]) * t, w


def _ik(rot, pos, off, par, ctl, F):
    """One IK control (§3.2 step 3c): its bone reaches the keyed target, the `chain` bones above it turning."""
    path, n = _path(par, ctl["bone"]), ctl["chain"]
    space = _path(par, ctl["space"]) if ctl.get("space") else None
    for f in range(F):
        if (at := _ik_at(ctl["keys"], f)) is None:
            continue
        p, swivel, w = at
        Ws, ps = _fk(path, rot, pos, off, f)
        if space:
            Wsp, psp = _fk(space, rot, pos, off, f)
            p = psp[-1] + _qrot(Wsp[-1], p)
        pw = Ws[-n - 2] if len(Ws) > n + 1 else _ID
        r = _chain(pw, Ws[-n - 1 :], ps[-n - 1 :], ps[-1] + (p - ps[-1]) * w, swivel * w)
        if r is not None:
            for name, q in zip(path[-n - 1 :], r, strict=True):
                rot[name][f] = q


# --- evaluate ---------------------------------------------------------------------------------------------


def _curve(x, ks, ident, mix):
    """The layer's value at base frame x from keys [(f, value, falloff)] sorted by f (§3.2 step 3)."""
    f0, v0, fo0 = ks[0]
    if x <= f0:
        d = f0 - x
        if d <= 0:
            return v0
        return mix(ident, v0, _s(1 - d / fo0)) if d < fo0 else ident
    f1, v1, fo1 = ks[-1]
    if x >= f1:
        d = x - f1
        if d <= 0:
            return v1
        return mix(ident, v1, _s(1 - d / fo1)) if d < fo1 else ident
    for (fa, va, _), (fb, vb, _) in itertools.pairwise(ks):
        if fa <= x < fb:
            return mix(va, vb, _s((x - fa) / (fb - fa)))


def _apply_keys(arr, keys, ident, mix):
    ks = sorted(
        (
            (float(k["f"]), np.asarray(k.get("q", k.get("v")), float), float(k.get("falloff", 0)))
            for k in keys
        ),
        key=lambda k: k[0],
    )
    return np.stack([_curve(float(x), ks, ident, mix) for x in range(len(arr))])


def evaluate(base: dict, layer: dict) -> dict:
    """`base` clip + correction `layer` -> the edited clip (same shape, "frames" = new length).
    Order: 1 dense base (given) · 2 smooth · 3 keys, offsets, 3b feet, 3c ik · 4 trim · 5 in_place · 6 ground · 7 loop · 8 speed."""
    fps = base["fps"]
    names = [b["name"] for b in base["bones"]]
    par = {b["name"]: b.get("parent") for b in base["bones"]}
    rot = {b["name"]: np.array(b[ROT], float) for b in base["bones"] if ROT in b}
    pos = {b["name"]: np.array(b[POS], float) for b in base["bones"] if POS in b}
    off = {b["name"]: np.array(b["offset"], float) for b in base["bones"] if "offset" in b}

    def top(n):  # no translated ancestor
        p = par.get(n)
        while p is not None:
            if p in pos:
                return False
            p = par.get(p)
        return True

    tops = [n for n in pos if top(n)]
    for n, sigma in (layer.get("smooth") or {}).items():  # 2
        if sigma > 0:
            if n in rot:
                rot[n] = _unit(_gauss(_consistent(rot[n]), sigma))
            if n in pos:
                pos[n] = _gauss(pos[n], sigma)
    for n, ks in (layer.get("keys") or {}).items():  # 3
        if ks:
            rot[n] = _unit(qmul(rot[n], _apply_keys(rot[n], ks, np.array([0, 0, 0, 1.0]), slerp)))
    for n, ks in (layer.get("offsets") or {}).items():
        if ks:
            pos[n] = pos[n] + _apply_keys(pos[n], ks, np.zeros(3), _lerp)
    for lk in layer.get("feet") or []:  # 3b
        _lock(rot, pos, off, par, lk, base["frames"])
    for ctl in layer.get("ik") or []:  # 3c
        _ik(rot, pos, off, par, ctl, base["frames"])
    if layer.get("trim"):  # 4
        a, b = layer["trim"]
        rot, pos = ({n: v[a : b + 1] for n, v in d.items()} for d in (rot, pos))
    G = len(next(iter({**rot, **pos}.values())))
    if layer.get("in_place") and G > 1:  # 5
        for n in tops:
            pos[n][:, [0, 2]] -= (
                np.arange(G)[:, None] / (G - 1) * (pos[n][-1, [0, 2]] - pos[n][0, [0, 2]])
            )
    for n in tops:  # 6
        pos[n][:, 1] += layer.get("ground", 0)
    n_loop = min(int(layer.get("loop", 0)), G - 1)  # 7
    if n_loop > 0:
        w = _s((np.arange(G - n_loop, G) - (G - n_loop) + 1) / n_loop)
        for n, q in rot.items():
            q[G - n_loop :] = slerp(q[G - n_loop :], q[0], w)
        for n, p in pos.items():
            cols = [0, 1, 2] if n not in tops or layer.get("in_place") else [1]
            p[G - n_loop :, cols] = _lerp(p[G - n_loop :], p[0], w)[:, cols]
    speed = layer.get("speed", 1)  # 8
    if speed != 1:
        Gn = math.floor((G - 1) / speed + 0.5) + 1
        x = np.minimum(np.arange(Gn) * speed, G - 1)
        i = np.minimum(np.floor(x).astype(int), G - 1)
        j, t = np.minimum(i + 1, G - 1), x - i
        rot = {n: slerp(q[i], q[j], t) for n, q in rot.items()}
        pos = {n: _lerp(p[i], p[j], t) for n, p in pos.items()}
        G = Gn
    bones = []
    for n in names:
        b = {"name": n, "parent": par[n]}
        if n in rot:
            b[ROT] = rot[n]
        if n in pos:
            b[POS] = pos[n]
        if n in off:
            b["offset"] = off[n]
        bones.append(b)
    return {"fps": fps, "frames": G, "bones": bones}


# --- GLB read ---------------------------------------------------------------------------------------------

_NCOMP = {"SCALAR": 1, "VEC3": 3, "VEC4": 4}


def read_glb(path) -> tuple[dict, bytes]:
    """(json document, BIN chunk padded to 4 bytes)."""
    data = Path(path).read_bytes()
    if data[:4] != b"glTF":
        raise StepError("failed", f"{path}: not a GLB")
    doc, blob, pos = None, b"", 12
    while pos < len(data):
        n, kind = struct.unpack_from("<II", data, pos)
        chunk = data[pos + 8 : pos + 8 + n]
        if kind == 0x4E4F534A:
            doc = json.loads(chunk)
        elif kind == 0x004E4942 and not blob:
            blob = chunk
        pos += 8 + n
    return doc, blob + b"\0" * (-len(blob) % 4)


def _acc(doc, blob, i) -> np.ndarray:
    a = doc["accessors"][i]
    if "sparse" in a or "bufferView" not in a or a["componentType"] != 5126:
        raise StepError(
            "failed", f"animation accessor {i}: only plain float accessors are supported"
        )
    bv = doc["bufferViews"][a["bufferView"]]
    if "EXT_meshopt_compression" in bv.get("extensions", {}):
        raise StepError("failed", "animation data in EXT_meshopt_compression is not supported")
    n, c = a["count"], _NCOMP[a["type"]]
    off, stride = bv.get("byteOffset", 0) + a.get("byteOffset", 0), bv.get("byteStride") or 4 * c
    if stride == 4 * c:
        return np.frombuffer(blob, "<f4", n * c, off).reshape(n, c).astype(float)
    raw = np.frombuffer(blob, np.uint8, (n - 1) * stride + 4 * c, off)
    return np.stack([raw[k * stride : k * stride + 4 * c].view("<f4") for k in range(n)]).astype(
        float
    )


def _parents(doc) -> dict[int, int]:
    return {c: i for i, n in enumerate(doc["nodes"]) for c in n.get("children", [])}


def _channels(doc, blob, anim):
    """Yield (channel, node name, path, interpolation, times, values) of an animation."""
    for ch in anim["channels"]:
        s = anim["samplers"][ch["sampler"]]
        interp = s.get("interpolation", "LINEAR")
        if interp == "CUBICSPLINE":
            raise StepError("failed", f"animation {anim.get('name')}: CUBICSPLINE is not supported")
        yield (
            ch,
            doc["nodes"][ch["target"]["node"]].get("name", f"node_{ch['target']['node']}"),
            ch["target"]["path"],
            interp,
            _acc(doc, blob, s["input"])[:, 0],
            _acc(doc, blob, s["output"]),
        )


def _sample(times, vals, interp, u, is_rot):
    if interp == "STEP" or len(times) == 1:
        return vals[np.clip(np.searchsorted(times, u + 1e-6, "right") - 1, 0, len(times) - 1)]
    i = np.clip(np.searchsorted(times, u, "right") - 1, 0, len(times) - 2)
    w = np.clip((u - times[i]) / (times[i + 1] - times[i]), 0, 1)
    w = np.where(w < 1e-4, 0.0, np.where(w > 1 - 1e-4, 1.0, w))  # a sample on a key is the key
    return slerp(vals[i], vals[i + 1], w) if is_rot else _lerp(vals[i], vals[i + 1], w)


def clip_index(doc, name):
    ix = [i for i, a in enumerate(doc.get("animations", [])) if a.get("name") == name]
    if len(ix) != 1:
        raise StepError(
            "bad_params", f"clip {name!r}: {'not found' if not ix else 'name is not unique'}"
        )
    return ix[0]


def sample_clip(doc, blob, name, fps) -> dict:
    """A clip's rotations and animated translations sampled at f/fps for f in 0..F-1 (§3.2 step 1)."""
    anim = doc["animations"][clip_index(doc, name)]
    chans = list(_channels(doc, blob, anim))
    dur = max(float(c[4].max()) for c in chans)
    F = math.floor(dur * fps + 0.5) + 1
    u = np.arange(F) / fps
    par, nodes = _parents(doc), {}
    for ch, node, path, interp, t, v in chans:
        # a translation that moves (by its values: two keys can move a root from A to B) is sampled
        if path == "rotation" or (path == "translation" and np.ptp(v, axis=0).max() > 1e-7):
            nodes.setdefault(ch["target"]["node"], {"name": node})[
                ROT if path == "rotation" else POS
            ] = _sample(t, v, interp, u, path == "rotation")
        elif path == "translation":
            nodes.setdefault(ch["target"]["node"], {"name": node})
    for k, b in nodes.items():  # M38: the constant translation of a bone without a moving one
        if POS not in b:
            const = next(
                (c[5][0] for c in chans if c[0]["target"] == {"node": k, "path": "translation"}),
                doc["nodes"][k].get("translation", [0, 0, 0]),
            )
            b["offset"] = np.asarray(const, float)
    if len({b["name"] for b in nodes.values()}) != len(nodes):
        raise StepError("failed", f"clip {name!r}: bone names are not unique")
    for k, b in nodes.items():
        p = par.get(k)
        while p is not None and p not in nodes:
            p = par.get(p)
        b["parent"] = nodes[p]["name"] if p is not None else None
    return {"fps": fps, "frames": F, "bones": list(nodes.values())}


# --- GLB write --------------------------------------------------------------------------------------------


def write_glb(doc, blob, edits: dict, fps: float) -> bytes:
    """The GLB with each edited clip's channels re-pointed to new dense accessors in an appended BIN tail.
    edits: {clip name: evaluate() result}. Everything else keeps its bytes.
    ponytail: old animation accessors stay in the file; compact when size matters."""
    doc, out = copy.deepcopy(doc), bytearray(blob)

    def add(arr, typ, minmax=False):
        a = np.ascontiguousarray(arr, "<f4")
        doc["bufferViews"].append({"buffer": 0, "byteOffset": len(out), "byteLength": a.nbytes})
        out.extend(a.tobytes())
        acc = {
            "bufferView": len(doc["bufferViews"]) - 1,
            "componentType": 5126,
            "count": len(a),
            "type": typ,
        }
        if minmax:
            acc["min"], acc["max"] = [float(a.min())], [float(a.max())]
        doc["accessors"].append(acc)
        return len(doc["accessors"]) - 1

    for name, res in edits.items():
        anim = doc["animations"][clip_index(doc, name)]
        bones, G = {b["name"]: b for b in res["bones"]}, res["frames"]
        dense_t = add(np.arange(G) / fps, "SCALAR", True)
        step_t = add([0, (G - 1) / fps], "SCALAR", True)
        samplers = []
        for ch, node, path, _, t, v in _channels(doc, blob, anim):
            b, typ = bones.get(node, {}), "VEC4" if path == "rotation" else "VEC3"
            new = b.get(path)
            if path == "scale" and len(t) > 2:
                raise StepError("failed", f"clip {name!r}: animated scale is not supported")
            if path not in ("rotation", "translation", "scale"):
                raise StepError("failed", f"clip {name!r}: {path} channels are not supported")
            if new is None or np.ptp(new, axis=0).max() < 1e-7:  # constant: its (new) value held
                s = {
                    "input": step_t,
                    "output": add(np.tile(v[0] if new is None else new[0], (2, 1)), typ),
                    "interpolation": "STEP",
                }
            else:
                s = {"input": dense_t, "output": add(new, typ), "interpolation": "LINEAR"}
            ch["sampler"] = len(samplers)
            samplers.append(s)
        anim["samplers"] = samplers
    doc["buffers"][0]["byteLength"] = len(out)
    return pack(doc, bytes(out))


def turns(path) -> dict[str, float]:
    """Per clip, the largest turn (degrees) any bone makes against its own first key. A retarget whose bone map missed
    writes a clip that plays and never moves (the Mr. Mak review's silent-clip gate); a real clip turns tens of degrees."""
    doc, blob = read_glb(path)
    out = {}
    for a in doc.get("animations", []):
        turn = 0.0
        for _, _, kind, _, _, vals in _channels(doc, blob, a):
            if kind == "rotation" and len(vals) > 1:
                q = vals / np.linalg.norm(vals, axis=1, keepdims=True)
                turn = max(
                    turn, float(np.degrees(2 * np.arccos(np.abs(q @ q[0]).clip(0, 1).min())))
                )
        out[a.get("name", "")] = round(turn, 2)
    return out


def pack(doc: dict, blob: bytes) -> bytes:
    """A GLB from its JSON document and its BIN chunk (padded to 4 bytes)."""
    j = json.dumps(doc, separators=(",", ":")).encode()
    j += b" " * (-len(j) % 4)
    blob += b"\0" * (-len(blob) % 4)
    return (
        struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(j) + 8 + len(blob))
        + struct.pack("<II", len(j), 0x4E4F534A)
        + j
        + struct.pack("<II", len(blob), 0x004E4942)
        + blob
    )
