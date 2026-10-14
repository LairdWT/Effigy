"""M16 A/T-pose gate on synthetic skeletons (image y grows downwards)."""

import math

import numpy as np

from steps import _pose as P


def skeleton(arm_deg: float, elbow_bend: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    pts = np.zeros((133, 2))
    pts[P.L_SH], pts[P.R_SH] = (60, 100), (40, 100)  # the person's left is image right
    pts[P.L_HIP], pts[P.R_HIP] = (57, 200), (43, 200)
    for sh, el, wr, side in ((P.L_SH, P.L_EL, P.L_WR, 1), (P.R_SH, P.R_EL, P.R_WR, -1)):
        a = math.radians(arm_deg)
        upper = np.array([side * math.sin(a), math.cos(a)]) * 40
        b = a + math.radians(elbow_bend)
        fore = np.array([side * math.sin(b), math.cos(b)]) * 40
        pts[el] = pts[sh] + upper
        pts[wr] = pts[el] + fore
    return pts, np.ones(133)


def test_a_and_t_pose_pass_others_fail():
    assert P.gate(*skeleton(45))["pose"] == "a"
    assert P.gate(*skeleton(90))["pose"] == "t"
    hanging = P.gate(*skeleton(5))
    assert hanging["pose"] == "other" and not hanging["ok"]
    bent = P.gate(*skeleton(45, elbow_bend=60))
    assert bent["pose"] == "other" and min(bent["elbows"]) < P.MIN_ELBOW
    pts, scores = skeleton(45)
    scores[P.L_WR] = 0.1  # a hand the model didn't find
    assert P.gate(pts, scores)["pose"] == "unsure"


def test_box_affine_centres_the_subject_at_the_model_aspect():
    alpha = np.zeros((1000, 800))
    alpha[200:800, 300:500] = 1  # 200 wide, 600 tall
    m = P._box_affine(alpha)
    corners = np.array([[300, 200, 1], [499, 799, 1]]) @ m.T
    assert np.allclose((corners[0] + corners[1]) / 2, [P.W / 2, P.H / 2], atol=1)
    assert 0 < corners[0][1] and corners[1][1] < P.H  # whole subject inside, with margin
