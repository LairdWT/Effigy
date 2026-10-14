"""Whole-body keypoints (DWPose, CPU onnxruntime) and the A/T-pose gate (IMPLEMENTATION.md M16).

The person box comes from the cut-out's alpha (prep already isolated one subject), so DWPose's YOLOX
detector isn't needed. Keypoints are COCO-WholeBody (133); the gate uses the 17 body ones.
"""

import os
from pathlib import Path

import cv2
import numpy as np

MODEL = "yzd-v/DWPose"  # Apache-2.0, dw-ll_ucoco_384.onnx
W, H = 288, 384  # model input
MEAN, STD = np.array([123.675, 116.28, 103.53]), np.array([58.395, 57.12, 57.375])  # RGB
# COCO body indices
L_SH, R_SH, L_EL, R_EL, L_WR, R_WR, L_HIP, R_HIP, L_ANK, R_ANK = 5, 6, 7, 8, 9, 10, 11, 12, 15, 16
# research 07 §3 gate H: A-pose 30-60° arm abduction, T-pose 80-100°; calibration constants
A_POSE, T_POSE = (30.0, 60.0), (80.0, 100.0)
MIN_ELBOW = 150.0  # straight-ish arms
MAX_LR_DIFF = 15.0  # symmetric
MIN_SCORE = 0.3


def load():
    import onnxruntime

    path = Path(os.environ.get("EFFIGY_MODELS", Path(__file__).resolve().parents[1] / "models"))
    return onnxruntime.InferenceSession(
        str(path / "DWPose" / "dw-ll_ucoco_384.onnx"), providers=["CPUExecutionProvider"]
    )


def _box_affine(alpha: np.ndarray) -> np.ndarray:
    """2×3 affine: the alpha's bounding box (×1.25, at the model's aspect) → the W×H input."""
    ys, xs = np.nonzero(alpha > 0.5)
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    w, h = (xs.max() - xs.min() + 1) * 1.25, (ys.max() - ys.min() + 1) * 1.25
    w, h = max(w, h * W / H), max(h, w * H / W)
    s = W / w
    return np.array([[s, 0, W / 2 - s * cx], [0, s, H / 2 - s * cy]], np.float32)


def keypoints(session, rgb: np.ndarray, alpha: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(133, 2) pixel coordinates in `rgb` and (133,) scores."""
    m = _box_affine(alpha)
    crop = cv2.warpAffine(rgb, m, (W, H), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0))
    x = ((crop - MEAN) / STD).transpose(2, 0, 1)[None].astype(np.float32)
    sx, sy = session.run(None, {session.get_inputs()[0].name: x})
    px, py = sx[0].argmax(-1) / 2.0, sy[0].argmax(-1) / 2.0  # SimCC, split ratio 2
    scores = np.minimum(sx[0].max(-1), sy[0].max(-1))
    inv = cv2.invertAffineTransform(m)
    pts = np.c_[px, py, np.ones_like(px)] @ inv.T
    return pts, scores


def _angle(u, v) -> float:
    c = np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v) + 1e-9)
    return float(np.degrees(np.arccos(np.clip(c, -1, 1))))


def gate(pts: np.ndarray, scores: np.ndarray) -> dict:
    """{"pose": "a"|"t"|"other"|"unsure", "ok": A- or T-pose, "arms": [l°, r°], "elbows": [l°, r°]}.
    Arm angle = between shoulder→wrist and the torso's downward axis (0° hanging, 90° horizontal)."""
    need = [L_SH, R_SH, L_EL, R_EL, L_WR, R_WR, L_HIP, R_HIP]
    if (scores[need] < MIN_SCORE).any():
        return {"pose": "unsure", "ok": False, "arms": None, "elbows": None}
    down = (pts[L_HIP] + pts[R_HIP]) / 2 - (pts[L_SH] + pts[R_SH]) / 2
    arms = [_angle(pts[w] - pts[s], down) for s, w in ((L_SH, L_WR), (R_SH, R_WR))]
    elbows = [
        _angle(pts[s] - pts[e], pts[w] - pts[e])
        for s, e, w in ((L_SH, L_EL, L_WR), (R_SH, R_EL, R_WR))
    ]
    straight = min(elbows) >= MIN_ELBOW and abs(arms[0] - arms[1]) <= MAX_LR_DIFF

    def within(r):
        return all(r[0] <= a <= r[1] for a in arms)

    pose = "a" if straight and within(A_POSE) else "t" if straight and within(T_POSE) else "other"
    return {"pose": pose, "ok": pose in ("a", "t"), "arms": arms, "elbows": elbows}


def keypoints_rgba(session, img: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Keypoints of an RGBA cut-out, composed on mid grey: the pose model never saw transparency."""
    alpha = img[..., 3].astype(np.float32) / 255
    bg = np.full_like(img[..., :3], 128)
    rgb = (img[..., :3] * alpha[..., None] + bg * (1 - alpha[..., None])).astype(np.uint8)
    return keypoints(session, rgb, alpha)
